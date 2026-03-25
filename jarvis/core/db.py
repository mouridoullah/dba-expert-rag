"""
jarvis/core/db.py - Gestionnaire de base de données robuste
"""
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor, execute_batch
from contextlib import contextmanager
import logging
import atexit
from jarvis.core.exceptions import DatabaseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)



class DatabaseManager:
    """Gestionnaire de connexions PostgreSQL avec Pool et Retry"""
    
    def __init__(self, settings):
        self.settings = settings
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        try:
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=self.settings.db_pool_size,
                host=self.settings.db_host,
                port=self.settings.db_port,
                database=self.settings.db_name,
                user=self.settings.db_user,
                password=self.settings.db_password,
                connect_timeout=self.settings.db_connection_timeout
            )
            logger.info(f"Pool de connexions créé ({self.settings.db_pool_size} max)")
            atexit.register(self.close)
        except psycopg2.OperationalError as e:
            logger.error(f"Impossible de créer le pool : {e}")
            raise DatabaseError(str(e))
            
    def close(self):
        """Fermeture propre du pool de connexions"""
        if self.pool:
            self.pool.closeall()
            logger.info("🔒 Pool de connexions PostgreSQL fermé proprement via atexit.")
            
    @contextmanager
    def get_connection(self):
        """Context manager pour auto-commit/rollback"""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Erreur DB (rollback) : {e}")
            raise DatabaseError(str(e))
        finally:
            if conn:
                self.pool.putconn(conn)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError)
    )
    def execute_query(self, query: str, params: tuple = None, fetch_all: bool = True):
        """Exécuter un SELECT avec retry automatique"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor(cursor_factory=DictCursor)
                cur.execute(query, params or ())
                return cur.fetchall() if fetch_all else cur.fetchone()
        except psycopg2.Error as e:
            raise DatabaseError(f"Query failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError)
    )
    def execute_insert(self, query: str, params: tuple) -> int:
        """Exécuter un INSERT/UPDATE avec retry automatique"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                return cur.rowcount
        except psycopg2.Error as e:
            raise DatabaseError(f"Insert failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError)
    )
    def execute_insert_batch(self, query: str, params_list: list) -> int:
        """Exécuter un INSERT/UPDATE massif avec retry automatique"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                execute_batch(cur, query, params_list)
                return cur.rowcount
        except psycopg2.Error as e:
            raise DatabaseError(f"Batch Insert failed: {e}")

    def test_connection(self) -> bool:
        """Vérifier que la DB répond"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
            return True
        except DatabaseError:
            return False

if __name__ == "__main__":
    from jarvis.config.settings import settings
    
    # On configure un logging basique pour voir ce qui se passe dans le terminal
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseManager(settings)
    if db.test_connection():
        print("\nConnexion PostgreSQL parfaitement opérationnelle avec Pool et Retry !")
    else:
        print("\nÉchec de la connexion à la base de données.")
