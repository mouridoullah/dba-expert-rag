"""
jarvis/ingestion/cli.py - L'interface de commande unifiée
"""
import click
import os
import logging
from jarvis.config.settings import settings
from jarvis.ingestion.postgres_ingestor import PostgresIngestor
from jarvis.ingestion.sqlserver_ingestor import SQLServerIngestor

# On active l'affichage des logs dans la console
logging.basicConfig(level=getattr(logging, settings.log_level), format=settings.log_format)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--engine', type=click.Choice(['postgres', 'sqlserver']), required=True, help="Le moteur cible")
@click.option('--docs-dir', type=click.Path(exists=True), required=True, help="Le chemin vers le dossier racine des documents")
@click.option('--limit', type=int, default=0, help="Limite de fichiers à traiter (0 = sans limite)")
def ingest(engine: str, docs_dir: str, limit: int):
    """Usine d'Ingestion Jarvis - Transforme la doc en vecteurs !"""
    
    if engine == 'postgres':
        ingestor = PostgresIngestor(settings)
        extension = '.html'
    else:
        ingestor = SQLServerIngestor(settings)
        extension = '.md'
    
    logger.info(f"🚀 Lancement de l'ingestion [{engine.upper()}] sur le dossier : {docs_dir}")
    
    # Dossiers techniques à ignorer
    DOSSIERS_EXCLUS = ['includes', 'media', 'samples', '.git']
    fichiers_traites = 0
    
    for root, dirs, files in os.walk(docs_dir):
        # On ignore les dossiers inutiles à la volée
        dirs[:] = [d for d in dirs if d not in DOSSIERS_EXCLUS]
        
        for file in files:
            if limit > 0 and fichiers_traites >= limit:
                break
                
            if file.endswith(extension):
                filepath = os.path.join(root, file)
                ingestor.ingest_file(filepath)
                fichiers_traites += 1
                
        if limit > 0 and fichiers_traites >= limit:
            break
            
    ingestor.print_stats()

if __name__ == '__main__':
    ingest()
