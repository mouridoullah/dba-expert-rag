"""
jarvis/llm/expert.py - Le Rédacteur en chef (Génération de la réponse)
"""
import logging
from jinja2 import Environment, FileSystemLoader
from langchain_ollama import OllamaLLM
from jarvis.config.settings import settings

logger = logging.getLogger(__name__)

class Expert:
    """Expert DBA LLM : lit le contexte et génère une réponse"""
    
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.llm = OllamaLLM(
            model=self.settings.ollama_llm_model,
            base_url=self.settings.ollama_base_url,
            temperature=self.settings.expert_temperature
        )
        
        # On charge le système de templates
        env = Environment(loader=FileSystemLoader('jarvis/llm/prompts'))
        self.template = env.get_template('expert.jinja2')
        logger.info("👨‍💻 Expert LLM initialisé et Template chargé")
    
    def generate_answer(self, question: str, context_docs: list, history: list = None) -> str:
        """Fusionne les documents, l'historique et génère la réponse finale"""
        
        if not context_docs:
            return "Désolé, je n'ai trouvé aucun document pertinent dans la base de connaissances pour répondre à cette question."
            
        # Formatage des documents pour qu'ils soient lisibles par l'IA (Numérotation simplifiée)
        context_text = "\n\n".join([
            f"[Doc {i+1}: {row['titre_chapitre']}]\n{row['contenu']}"
            for i, row in enumerate(context_docs)
        ])
        
        history_text = ""
        if history:
            recent_history = history[-6:]
            history_lines = []
            for msg in recent_history:
                role = "UTILISATEUR" if msg["role"] == "user" else "ASSISTANT"
                history_lines.append(f"{role}: {msg['content']}")
            history_text = "\n\n".join(history_lines)
            
        # Injection de la question et du contexte dans le Template Jinja2
        prompt_final = self.template.render(
            context=context_text,
            question=question,
            history=history_text
        )
        
        logger.info("✍️ Début de la rédaction de la réponse par l'Expert...")
        try:
            reponse = self.llm.invoke(prompt_final)
            logger.info("✅ Réponse brute générée avec succès ! Passage au Sniper Python...")
            reponse_filtree = self._sniper_filter(reponse)
            return reponse_filtree
        except Exception as e:
            logger.error(f"❌ Erreur critique lors de la génération : {e}")
            return "Désolé, mon moteur de réflexion (Ollama) a rencontré un problème inattendu."

    def _sniper_filter(self, texte: str) -> str:
        """Censure algorithmique : détruit tout bloc ne contenant pas de source, trop court ou paresseux."""
        import re
        if not texte or "Désolé, cette information n'est pas" in texte:
            return texte
            
        blocs_valides = []
        blocs = re.split(r'\n{2,}', texte.strip())
        
        for bloc in blocs:
            if not bloc.strip():
                continue
                
            # Anti-paresse 1 : Le bloc est trop court pour constituer une réponse technique structurée
            if len(bloc.split()) < 5:
                logger.warning(f"🗡️ Sniper a censuré un bloc suspectement court : {bloc}")
                continue
                
            # Anti-paresse 2 : Le modèle renvoie vers la documentation au lieu d'expliquer
            bloc_lower = bloc.lower()
            if "pour plus d'informations" in bloc_lower or "consultez la doc" in bloc_lower:
                logger.warning(f"🗡️ Sniper a censuré une phrase paresseuse : {bloc[:50]}...")
                continue
            
            # Vérification de la présence stricte du tag numérique [Doc X] ou [X]
            if re.search(r'\[(?:Doc )?\d+\]', bloc, flags=re.IGNORECASE):
                blocs_valides.append(bloc)
            else:
                logger.warning(f"🗡️ Sniper a censuré un bloc non sourcé : {bloc[:50]}...")
                
        texte_filtre = '\n\n'.join(blocs_valides).strip()
        
        if not texte_filtre:
            logger.error("🛑 Le Sniper a intégralement détruit la réponse du LLM (100% Hallucination/Paresse).")
            return "Désolé, le système a généré une explication, mais elle a été bloquée par notre politique stricte anti-hallucination (Sources non vérifiables)."
            
        return texte_filtre

if __name__ == "__main__":
    # Test basique pour voir si le template charge bien
    logging.basicConfig(level=logging.INFO)
    expert = Expert()
    test_context = [{"titre_chapitre": "Test", "contenu": "PostgreSQL 17 introduit le vacuum progressif."}]
    rep = expert.generate_answer("Qu'apporte Postgres 17 pour le vacuum ?", test_context)
    print(f"\nRÉPONSE DU TEST :\n{rep}")
