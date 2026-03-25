"""
jarvis/retrieval/search.py - Moteur de recherche vectoriel optimisé et Routeur IA
"""
import logging
import json
import re
import hashlib
from typing import Tuple, List

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from flashrank import Ranker, RerankRequest
from jarvis.core.metrics import metrics
from jarvis.core.db import DatabaseManager
from jarvis.core.exceptions import RoutingError, EmbeddingError
from jarvis.config.settings import settings
import diskcache

# On rend les logs httpx moins bavards pour y voir plus clair
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class VectorSearch:
    """Gère le routage de la question et la recherche dans la base de connaissances"""
    
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.db = DatabaseManager(self.settings)
        
        # Le dictionnaire qui sert de cache (désormais persistant sur disque paramétrable)
        self._embedding_cache = diskcache.Cache(self.settings.storage_embeddings_cache)
        
        self.embedder = OllamaEmbeddings(
            model=self.settings.ollama_embedding_model,
            base_url=self.settings.ollama_base_url
        )
        self.llm = OllamaLLM(
            model=self.settings.ollama_llm_model,
            base_url=self.settings.ollama_base_url,
            temperature=self.settings.ollama_temperature,
            format="json",
            request_timeout=30 # Sécurité anti-freeze
        )
        self.ranker = Ranker(cache_dir=self.settings.storage_flashrank_cache)
        logger.info("VectorSearch initialisé avec FlashRank (Re-ranker)")

    @metrics.timer("calcul_embedding")
    def get_cached_embedding(self, text: str) -> list:
        """Ne dérange Ollama que si la question est 100% nouvelle"""
        # On crée une empreinte digitale unique de la question
        hash_key = hashlib.md5(text.encode()).hexdigest()
        
        # Cache Hit : On connaît déjà la réponse !
        if hash_key in self._embedding_cache:
            logger.info("⚡ CACHE HIT : Vecteur de la question récupéré en RAM instantanément !")
            return self._embedding_cache[hash_key]
            
        # Cache Miss : On fait travailler la carte graphique
        try:
            logger.info("🐌 CACHE MISS : Calcul du vecteur via Ollama...")
            vecteur = self.embedder.embed_query(text)
            self._embedding_cache[hash_key] = vecteur
            return vecteur
        except Exception as e:
            raise EmbeddingError(f"Le calcul vectoriel a échoué : {e}")

    @metrics.timer("routing_hybride")
    def query_router(self, question: str) -> Tuple[str, str]:
        """Routeur hybride : Fast Path (Regex) d'abord, Slow Path (IA) en secours"""
        question_lower = question.lower()
        
        # ==========================================
        # ⚡ FAST PATH : Détection par Regex (0.001s)
        # ==========================================
        moteur_fast = None
        version_fast = "all"
        
        # 1. Détection Postgres
        if "postgres" in question_lower:
            moteur_fast = "postgres"
            # Cherche un nombre à 2 chiffres précédé du nom (ex: postgres 16, postgresql 17)
            match_version = re.search(r'postgres(?:ql)?\s+(1[0-9])\b', question_lower)
            if match_version:
                version_fast = match_version.group(1)
                
        # 2. Détection SQL Server
        elif "sql server" in question_lower or "sqlserver" in question_lower:
            moteur_fast = "sqlserver"
            # Cherche une année (ex: sql server 2019)
            match_version = re.search(r'sql\s*server\s*(20[1-2][0-9])\b', question_lower)
            if match_version:
                version_fast = match_version.group(1)

        # Si le Fast Path a trouvé un moteur, on coupe court !
        if moteur_fast:
            logger.info(f"⚡ ROUTAGE RAPIDE (Regex) => Moteur: [{moteur_fast.upper()}] | Version: [{version_fast.upper()}]")
            return moteur_fast, version_fast

        # ==========================================
        # 🐌 SLOW PATH : Détection par l'IA (Force JSON)
        # ==========================================
        logger.info("🐌 ROUTAGE LENT : La question est ambiguë, appel à l'IA...")
        prompt = f"""Analyse la question technique suivante pour deviner la base de données ciblée.
        Réponds obligatoirement par un objet JSON valide avec les clés "moteur" ("sqlserver", "postgres", ou "all") et "version" (année, version, ou "all"). Ne mets aucun autre texte.
        Question: {question}"""
        
        try:
            response = self.llm.invoke(prompt)
            # Extraction Regex robuste pour ignorer la politesse du LLM
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            if match:
                clean_response = match.group(0)
            else:
                clean_response = response.strip().strip("`").removeprefix("json").strip()
                
            data = json.loads(clean_response)
            
            moteur = str(data.get("moteur", "all")).strip().lower()
            version = str(data.get("version", "all")).strip().lower()
            
            logger.info(f"🧭 Routage IA => Moteur: [{moteur.upper()}] | Version: [{version.upper()}]")
            return moteur, version
        
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Le Routeur IA a vomi un format illisible ({e}). Fallback automatique sur 'all'.")
            return "all", "all"
        except Exception as e:
            logger.warning(f"⚠️ Échec du routage IA : {e}. Fallback sur 'all'.")
            return "all", "all"
    
    @metrics.timer("recherche_pgvector_fts_rerank")
    def hybrid_search(self, question: str, moteur: str, version: str) -> List[dict]:
        """Effectue la vraie recherche hybride (Vector + FTS PostgreSQL) suivie d'un Re-ranking"""
        resultats = []
        
        try:
            # 1. On utilise le Cache au lieu de calculer à chaque fois !
            vecteur_question = self.get_cached_embedding(question)
            
            if moteur == 'all':
                logger.info("⚖️ Recherche Fédérée activée (Postgres + SQL Server, Mode Vrai Hybride)")
                for mot in ['sqlserver', 'postgres']:
                    query = """
                        SELECT titre_chapitre, contenu, 
                               (vecteur <=> %s::vector) as vector_distance,
                               ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) as text_score
                        FROM knowledge_base 
                        WHERE moteur = %s
                        ORDER BY (ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) * 1.5) + (1.0 / (1.0 + (vecteur <=> %s::vector))) DESC 
                        LIMIT 15;
                    """
                    res = self.db.execute_query(query, (str(vecteur_question), question, mot, question, str(vecteur_question)), fetch_all=True)
                    if res:
                        resultats.extend(res)
            else:
                if version == 'all':
                    query = """
                        SELECT titre_chapitre, contenu, 
                               (vecteur <=> %s::vector) as vector_distance,
                               ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) as text_score
                        FROM knowledge_base 
                        WHERE moteur = %s 
                        ORDER BY (ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) * 1.5) + (1.0 / (1.0 + (vecteur <=> %s::vector))) DESC 
                        LIMIT 30;
                    """
                    res = self.db.execute_query(query, (str(vecteur_question), question, moteur, question, str(vecteur_question)), fetch_all=True)
                else:
                    query = """
                        SELECT titre_chapitre, contenu, 
                               (vecteur <=> %s::vector) as vector_distance,
                               ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) as text_score
                        FROM knowledge_base 
                        WHERE moteur = %s AND (version = %s OR version = 'all') 
                        ORDER BY (ts_rank_cd(tsv_contenu, websearch_to_tsquery('french', %s)) * 1.5) + (1.0 / (1.0 + (vecteur <=> %s::vector))) DESC 
                        LIMIT 30;
                    """
                    res = self.db.execute_query(query, (str(vecteur_question), question, moteur, version, question, str(vecteur_question)), fetch_all=True)
                
                if res:
                    resultats = res

            logger.info(f"📑 {len(resultats)} fragments candidats récupérés. Passage au Re-ranking !")
            
            if resultats:
                # 2. Préparation pour FlashRank
                passages = [
                    {"id": i, "text": doc["contenu"], "meta": doc}
                    for i, doc in enumerate(resultats)
                ]
                
                # 3. Requête de Re-ranking
                rerankrequest = RerankRequest(query=question, passages=passages)
                reranked = self.ranker.rerank(rerankrequest)
                
                # 4. Extraction du Top 5 le plus pur
                top_5 = [item["meta"] for item in reranked[:5]]
                
                logger.info(f"🎯 Re-ranking accompli : le Top {len(top_5)} a été isolé avec succès.")
                return top_5
                
            return []
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche vectorielle ou du Re-ranking : {e}")
            return []

if __name__ == "__main__":
    # Test rapide (Tu remarqueras que si tu lances le script deux fois, la 2ème sera instantanée)
    logging.basicConfig(level=logging.INFO)
    search = VectorSearch()
    m, v = search.query_router("Comment configurer le WAL sur Postgres 17 ?")
    
    # 1er Appel (Cache Miss)
    print("--- 1er Appel ---")
    docs1 = search.hybrid_search("Comment configurer le WAL sur Postgres 17 ?", m, v)
    
    # 2ème Appel (Cache Hit !)
    print("--- 2ème Appel (Test du Cache) ---")
    docs2 = search.hybrid_search("Comment configurer le WAL sur Postgres 17 ?", m, v)