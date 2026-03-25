"""
jarvis/ingestion/base_ingestor.py - Classe abstraite pour l'ingestion
Élimine la duplication entre les différents moteurs.
"""
from abc import ABC, abstractmethod
import logging
import hashlib
from typing import List, Dict
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from jarvis.core.db import DatabaseManager
from jarvis.config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Métadonnées associées à un chunk"""
    moteur: str
    version: str
    categorie: str
    titre_chapitre: str
    url_source: str
    contenu: str
    vecteur: List[float]

class BaseIngestor(ABC):
    """
    Classe abstraite pour ingérer des documents.
    Gère le découpage, la vectorisation, et l'insertion robuste.
    """
    
    def __init__(self, settings_obj=None):
        self.settings = settings_obj or settings
        self.db = DatabaseManager(self.settings)
        self.embedder = OllamaEmbeddings(
            model=self.settings.ollama_embedding_model,
            base_url=self.settings.ollama_base_url
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.ingest_chunk_size,
            chunk_overlap=self.settings.ingest_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.stats = {"files_processed": 0, "chunks_inserted": 0, "chunks_skipped": 0, "errors": 0}
        logger.info(f"{self.__class__.__name__} initialisé")
    
    @abstractmethod
    def read_file(self, filepath: str) -> str:
        """Lire et parser un fichier (À implémenter par l'enfant)"""
        pass
    
    @abstractmethod
    def extract_metadata(self, filepath: str, raw_text: str) -> Dict[str, str]:
        """Extraire les métadonnées (À implémenter par l'enfant)"""
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed_batch(self, contents: List[str]) -> List[List[float]]:
        """Vectoriser un lot entier de chunks avec Ollama (avec Retry automatique)"""
        try:
            return self.embedder.embed_documents(contents)
        except Exception as e:
            logger.error(f"Erreur vectorisation batch (Ollama) : {e}")
            raise

    def insert_chunks_batch(self, metadatas: List[ChunkMetadata]) -> bool:
        """Insérer un lot de chunks dans PostgreSQL intelligemment"""
        if not metadatas:
            return True
            
        hash_contents = [(hashlib.sha256(m.contenu.encode('utf-8')).hexdigest(), m) for m in metadatas]
        
        query = """
            INSERT INTO knowledge_base
            (moteur, version, categorie, titre_chapitre, url_source, hash_chunk, contenu, vecteur)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (hash_chunk) DO UPDATE SET
                version = EXCLUDED.version,
                categorie = EXCLUDED.categorie,
                titre_chapitre = EXCLUDED.titre_chapitre;
        """
        params_list = [
            (m.moteur, m.version, m.categorie, m.titre_chapitre, m.url_source, h, m.contenu, m.vecteur)
            for h, m in hash_contents
        ]
        
        try:
            self.db.execute_insert_batch(query, params_list)
            self.stats["chunks_inserted"] += len(metadatas)
            return True
        except Exception as e:
            logger.error(f"Erreur insertion DB en lot : {e}")
            self.stats["errors"] += len(metadatas)
            return False

    def ingest_file(self, filepath: str) -> int:
        """Orchestrer l'ingestion avec Batching et Check-Before-Compute (Vitesse x10)"""
        try:
            raw_text = self.read_file(filepath)
            if not raw_text or len(raw_text) < self.settings.ingest_min_chunk_length:
                self.stats["chunks_skipped"] += 1
                return 0
            
            metadata_dict = self.extract_metadata(filepath, raw_text)
            chunks = self.text_splitter.split_text(raw_text)
            
            chunks_to_embed = []
            enriched_contents = []
            
            valid_chunks = [c for c in chunks if len(c) >= self.settings.ingest_min_chunk_length]
            hash_to_chunk = {}
            for chunk in valid_chunks:
                contenu_enrichi = f"[Contexte : {metadata_dict['moteur'].upper()} {metadata_dict['version']} - {metadata_dict['titre_chapitre']}]\n{chunk}"
                hash_chunk = hashlib.sha256(contenu_enrichi.encode('utf-8')).hexdigest()
                hash_to_chunk[hash_chunk] = (chunk, contenu_enrichi)

            existing_hashes = set()
            if hash_to_chunk:
                hashes_tuple = tuple(hash_to_chunk.keys())
                check_query = "SELECT hash_chunk FROM knowledge_base WHERE hash_chunk IN %s"
                existing_records = self.db.execute_query(check_query, (hashes_tuple,), fetch_all=True)
                if existing_records:
                    existing_hashes = {row['hash_chunk'] for row in existing_records}

            for hash_chunk, (chunk, contenu_enrichi) in hash_to_chunk.items():
                if hash_chunk in existing_hashes:
                    update_query = """
                        UPDATE knowledge_base 
                        SET version = %s, categorie = %s, titre_chapitre = %s, url_source = %s
                        WHERE hash_chunk = %s
                    """
                    self.db.execute_insert(update_query, (
                        metadata_dict["version"], metadata_dict["categorie"],
                        metadata_dict["titre_chapitre"], filepath, hash_chunk
                    ))
                    self.stats["chunks_skipped"] += 1 
                else:
                    chunks_to_embed.append(chunk)
                    enriched_contents.append(contenu_enrichi)
            
            inserted_count = 0
            if chunks_to_embed:
                try:
                    logger.info(f"⏳ Vectorisation en lot de {len(chunks_to_embed)} chunks de {filepath}...")
                    vecteurs = self.embed_batch(enriched_contents)
                    
                    batch_metadatas = []
                    for content, vecteur in zip(enriched_contents, vecteurs):
                        batch_metadatas.append(ChunkMetadata(
                            moteur=metadata_dict["moteur"], version=metadata_dict["version"],
                            categorie=metadata_dict["categorie"], titre_chapitre=metadata_dict["titre_chapitre"],
                            url_source=filepath, contenu=content, vecteur=vecteur
                        ))
                    
                    if self.insert_chunks_batch(batch_metadatas):
                        inserted_count = len(batch_metadatas)
                        
                except Exception as e:
                    logger.warning(f"Batch ignoré suite à une erreur : {e}")
            
            self.stats["files_processed"] += 1
            logger.info(f"✅ {filepath} : {inserted_count} NOUVEAUX chunks insérés (les autres ont mis à jour les métadonnées).")
            return inserted_count
            
        except Exception as e:
            logger.error(f"❌ Erreur critique sur le fichier {filepath} : {e}")
            self.stats["errors"] += 1
            return 0

    def print_stats(self):
        print("\n" + "="*40 + "\nSTATISTIQUES D'INGESTION\n" + "="*40)
        for key, value in self.stats.items():
            print(f" - {key.replace('_', ' ').capitalize()} : {value}")
        print("="*40 + "\n")