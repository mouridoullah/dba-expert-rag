"""
jarvis/core/logger.py - Configuration du logging structuré en JSON
"""
import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Formateur de logs au format JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
        }
        
        # Capture la trace complète si une exception a planté l'application
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(level: int = logging.INFO):
    """Applique le format JSON à toute l'application"""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Nettoie les anciens handlers (pour éviter les logs en double)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
