import psycopg2
import sys
import os

# Ajout du path pour pouvoir importer settings depuis un dossier au dessus
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
    
    print("1. Ajout de la colonne tsv_contenu...")
    cur.execute("ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS tsv_contenu tsvector;")
    
    print("2. Peuplement rétroactif des données existantes...")
    cur.execute("UPDATE knowledge_base SET tsv_contenu = to_tsvector('simple', contenu) WHERE tsv_contenu IS NULL;")
    
    print("3. Création du Trigger pour automatiser le calcul au moment de l'ingestion...")
    trigger_sql = """
    DROP TRIGGER IF EXISTS tsvectorupdate ON knowledge_base;
    CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
    ON knowledge_base FOR EACH ROW EXECUTE FUNCTION
    tsvector_update_trigger(tsv_contenu, 'pg_catalog.simple', contenu);
    """
    cur.execute(trigger_sql)
    
    print("4. Création de l'Index GIN ultra-performant...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fts_contenu ON knowledge_base USING GIN(tsv_contenu);")
    
    print("Migration SQL (Phase 4) terminée avec succès !")
    conn.close()

if __name__ == "__main__":
    execute_ddl()
