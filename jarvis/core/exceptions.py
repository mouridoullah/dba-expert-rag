"""
jarvis/core/exceptions.py - Exceptions personnalisées pour Jarvis
"""
class DatabaseError(Exception):
    """Exception custom pour les erreurs DB"""
    pass

class JarvisException(Exception):
    """Exception de base pour toutes les erreurs de l'application Jarvis"""
    pass

class DatabaseError(JarvisException):
    """Erreur lors de l'accès à PostgreSQL (Connexion, Pool, Requête)"""
    pass

class EmbeddingError(JarvisException):
    """Erreur lors du calcul des vecteurs par Ollama (Nomic)"""
    pass

class RoutingError(JarvisException):
    """Erreur lors du routage par l'IA (JSON invalide ou LLM indisponible)"""
    pass

class GenerationError(JarvisException):
    """Erreur lors de la rédaction de la réponse finale par l'Expert"""
    pass
