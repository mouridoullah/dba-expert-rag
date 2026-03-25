"""
jarvis/config/settings.py - Configuration centralisée du projet Jarvis
"""
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Configuration de Jarvis - chargée depuis variables d'env ou .env"""
    
    # ========== DATABASE (PostgreSQL) ==========
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "lab_dba"
    db_user: str = "bdvm"
    db_password: str  # Sera chargé depuis .env (pas de default, c'est obligatoire !)
    db_pool_size: int = 5
    db_connection_timeout: int = 10
    
    # ========== OLLAMA (Embeddings + LLM) ==========
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_llm_model: str = "qwen2.5-coder:7b"
    ollama_temperature: float = 0.1
    expert_temperature: float = 0.0
    
    # ========== INGESTION ==========
    ingest_chunk_size: int = 800
    ingest_chunk_overlap: int = 100
    ingest_min_chunk_length: int = 20
    
    # ========== LOGGING ==========
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ========== STREAMLIT ==========
    streamlit_page_title: str = "Jarvis DBA"
    streamlit_layout: str = "wide"
    
    # ========== CACHE PATHS ==========
    storage_embeddings_cache: str = "./data/cache/embeddings"
    storage_flashrank_cache: str = "./data/cache/flashrank"
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}
    
    def validate_environment(self) -> bool:
        """Valider que tous les paramètres critiques sont présents"""
        required_fields = ["db_password", "db_host", "db_name", "db_user", "ollama_base_url"]
        missing = [field for field in required_fields if not getattr(self, field, None)]
        
        if missing:
            logger.error(f"Configuration incomplète. Champs manquants : {missing}")
            return False
        
        logger.info("Configuration valide avec succès")
        return True

# Instance singleton accessible partout
settings = Settings()

if __name__ == "__main__":
    print("Configuration actuelle de Jarvis :")
    print(f"  Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(f"  Ollama: {settings.ollama_base_url}")
    
    if settings.validate_environment():
        print("\nTous les paramètres sont correctement configurés !")
    else:
        print("\nDes paramètres manquent. Vérifiez votre fichier .env")
