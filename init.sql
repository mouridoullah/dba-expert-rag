-- ==========================================
-- Schéma de la Base de Connaissances (Jarvis)
-- ==========================================

-- 1. Activation de l'extension vectorielle
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Création de la table principale
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    moteur VARCHAR(50) NOT NULL,              -- 'postgres' ou 'sqlserver'
    version VARCHAR(50) NOT NULL,             -- '17', '2022', ou 'all'
    categorie VARCHAR(100),                   -- Catégorie de la documentation
    titre_chapitre VARCHAR(255),              -- Titre du document (limité à 100-255 chars)
    url_source TEXT,                          -- Chemin du fichier ou URL d'origine
    hash_chunk VARCHAR(64) UNIQUE NOT NULL,   -- Empreinte SHA-256 (Pour éviter les doublons/N+1 queries)
    contenu TEXT NOT NULL,                    -- Le fragment de texte brut
    vecteur vector(768),                      -- Le vecteur mathématique (nomic-embed-text = 768 dims)
    tsv_contenu tsvector                      -- La colonne pré-calculée pour le Full-Text Search
);

-- 3. Indexation Vectorielle (HNSW pour des performances optimales avec pgvector)
CREATE INDEX IF NOT EXISTS idx_vecteur_hnsw 
ON knowledge_base USING hnsw (vecteur vector_cosine_ops);

-- 4. Indexation Full-Text Search (GIN)
CREATE INDEX IF NOT EXISTS idx_fts_contenu 
ON knowledge_base USING GIN(tsv_contenu);

-- 5. Fonction et Trigger pour l'automatisation du FTS (Dictionnaire Français)
CREATE OR REPLACE FUNCTION tsvector_update_func() RETURNS trigger AS $$
BEGIN
  NEW.tsv_contenu := to_tsvector('french', NEW.contenu);
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvectorupdate ON knowledge_base;
CREATE TRIGGER tsvectorupdate 
    BEFORE INSERT OR UPDATE ON knowledge_base 
    FOR EACH ROW 
    EXECUTE FUNCTION tsvector_update_func();