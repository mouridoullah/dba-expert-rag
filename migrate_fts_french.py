import psycopg2
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jarvis.config.settings import settings

def execute_ddl():
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    print("1. Mise à jour rétroactive du dictionnaire FTS vers 'french'...")
    cur.execute("UPDATE knowledge_base SET tsv_contenu = to_tsvector('french', contenu);")
    
    print("2. Mise à jour du Trigger pour utiliser 'french'...")
    trigger_sql = """
    CREATE OR REPLACE FUNCTION tsvector_update_func() RETURNS trigger AS $$
    BEGIN
      NEW.tsv_contenu := to_tsvector('french', NEW.contenu);
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tsvectorupdate ON knowledge_base;
    CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
    ON knowledge_base FOR EACH ROW EXECUTE FUNCTION tsvector_update_func();
    """
    cur.execute(trigger_sql)
    
    print("Migration FTS French terminée avec succès !")
    conn.close()

if __name__ == "__main__":
    execute_ddl()
