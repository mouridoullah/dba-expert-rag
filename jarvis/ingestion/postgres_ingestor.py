"""
jarvis/ingestion/postgres_ingestor.py - Spécialiste du format HTML de Postgres
"""
from bs4 import BeautifulSoup
import re
from typing import Dict
from jarvis.ingestion.base_ingestor import BaseIngestor

class PostgresIngestor(BaseIngestor):
    """Parseur chirurgical pour la documentation HTML de PostgreSQL"""
    
    def read_file(self, filepath: str) -> str:
        """Nettoie le HTML et ne garde que le conteneur principal"""
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
        
        content_div = soup.find('div', id='docContent')
        if not content_div:
            return ""
        
        # Le fameux tir au sniper (Whitelisting)
        for nav in content_div.find_all('div', class_=['navheader', 'navfooter', 'toc']):
            nav.decompose()
        
        return content_div.get_text(separator='\n', strip=True)
    
    def extract_metadata(self, filepath: str, raw_text: str) -> Dict[str, str]:
        """Extrait la version et le titre"""
        # Ex: "docs_17/routine-vacuuming.html" -> version 17
        version_match = re.search(r'docs_(\d+)', filepath)
        version = version_match.group(1) if version_match else 'all'
        
        # Le titre est généralement la première vraie ligne non vide
        lines = raw_text.split('\n')
        titre = next((l.strip() for l in lines if len(l.strip()) > 0), "Chapitre Général")
        
        return {
            'moteur': 'postgres',
            'version': version,
            'categorie': 'documentation', # Postgres est classé globalement
            'titre_chapitre': titre[:100] # On limite la taille pour la lisibilité
        }
