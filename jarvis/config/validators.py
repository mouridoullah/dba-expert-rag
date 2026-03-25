"""
jarvis/config/validators.py - Sanitarisation des entrées utilisateur
"""
from pydantic import BaseModel, Field, field_validator

class SearchQuery(BaseModel):
    """Modèle strict pour valider la question de l'utilisateur"""
    
    question: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="La question technique de l'utilisateur"
    )

    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Nettoyage de base de la question."""
        # Note : La DB est protégée par les liaisons paramétrées (%s) de psycopg2.
        # Aucune liste noire (blacklist) de mots-clés SQL n'est souhaitée pour
        # un assistant orienté Base de Données (ex: un user demande "Comment DROP TABLE").
        
        return v.strip()
