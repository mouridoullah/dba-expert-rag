"""
jarvis/ingestion/sqlserver_ingestor.py - Spécialiste du format Markdown de Microsoft
"""
import os
import re
from typing import Dict
from jarvis.ingestion.base_ingestor import BaseIngestor

class SQLServerIngestor(BaseIngestor):
    """Parseur pour la documentation Markdown de SQL Server"""
    
    def read_file(self, filepath: str) -> str:
        """Lecture avec nettoyage du Frontmatter Microsoft"""
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
            # Supprime le bloc d'en-tête YAML --- ... --- typique des docs Microsoft
            text = re.sub(r'^---[\s\S]*?---', '', text, flags=re.MULTILINE)
            return text.strip()
    
    def extract_metadata(self, filepath: str, raw_text: str) -> Dict[str, str]:
        """Extrait la version, la catégorie dynamique, et le titre"""
        # Version via le nom (ex: backup-2022.md)
        version_match = re.search(r'-(20\d{2})', os.path.basename(filepath))
        version = version_match.group(1) if version_match else 'all'
        
        # Catégorie via le dossier parent (ex: data/raw/.../docs/t-sql/... -> t-sql)
        # On sécurise la recherche du mot 'docs' dans le chemin
        parts = filepath.split(os.sep)
        try:
            idx = parts.index('docs')
            categorie = parts[idx + 1] if len(parts) > idx + 1 else 'general'
        except ValueError:
            categorie = 'general'
            
        # Titre via le premier #
        lines = raw_text.split('\n')
        titre = next((l.replace('#', '').strip() for l in lines if l.startswith('#')), "Chapitre Général")
        
        return {
            'moteur': 'sqlserver',
            'version': version,
            'categorie': categorie,
            'titre_chapitre': titre[:100]
        }
