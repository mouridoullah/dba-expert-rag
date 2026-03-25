# Jarvis : Assistant DBA Senior (RAG)

Jarvis est un assistant virtuel conversationnel propulsé par l'IA, conçu spécifiquement pour assister les Administrateurs de Bases de Données (DBA). Il exploite une architecture **RAG (Retrieval-Augmented Generation) Hybride**, garantissant des réponses techniques ultra-précises et sourcées à partir de la documentation officielle de **PostgreSQL** et **SQL Server**.

## Fonctionnalités Principales

- **Recherche Hybride Avancée** : Combine la recherche vectorielle sémantique (`pgvector`) et la recherche plein texte stricte (`websearch_to_tsquery('french')` de PostgreSQL) pour ne rater aucun détail technique.
- **Re-ranking Intelligent** : Utilisation de `FlashRank` (TinyBERT) en local pour réorganiser les résultats et isoler le Top 5 le plus pertinent.
- **Routage Dynamique (Fast/Slow Path)** : Redirige intelligemment la question vers la bonne documentation métier grâce à une analyse Regex ou à un LLM routeur de secours.
- **Bouclier Anti-Hallucination ("Sniper Python")** : Censure algorithmique stricte qui oblige le LLM à sourcer chaque affirmation technique et détruit les phrases paresseuses génériques.
- **Ingestion Massive Optimisée** : Pipelines ETL capables de lire du HTML et du Markdown, d'ignorer les métadonnées bruyantes, avec un mécanisme "Check-Before-Compute" en RAM pour ingérer des milliers de documents sans surcharger la base de données.
- **Interface UI Intuitive** : Une application Web fluide développée avec Streamlit.

## Stack Technique

- **Backend** : Python 3.10+
- **Base de données** : PostgreSQL avec l'extension `pgvector`
- **IA Locale** : Ollama (modèle `qwen2.5-coder:7b` pour le texte, `nomic-embed-text` pour les vecteurs)
- **Frameworks** : LangChain, Pydantic, Tenacity
- **Frontend** : Streamlit

## Configuration & Installation

1. **Cloner le projet et préparer l'environnement :**
   ```bash
   git clone <ton_depot>
   cd jarvis
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configurer les variables d'environnement :**
   Créez un fichier `.env` à la racine du projet (ignoré par Git) :
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=dbname
   DB_USER=dbuser
   DB_PASSWORD=dbpassword
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **Migrations Base de Données :**
   Assurez-vous que l'extension `pgvector` est installée sur PostgreSQL, puis exécutez les migrations de Full-Text Search :
   ```bash
   python migrate_fts.py
   python migrate_fts_french.py
   ```

## Utilisation

### 1. Ingestion de la documentation (Base de Connaissances)
Utilisez le CLI d'ingestion pour peupler votre base vectorielle avec la documentation technique :

```bash
# Pour la documentation PostgreSQL (HTML)
python -m jarvis.ingestion.cli --engine postgres --docs-dir /chemin/vers/docs_postgres

# Pour la documentation SQL Server (Markdown)
python -m jarvis.ingestion.cli --engine sqlserver --docs-dir /chemin/vers/docs_sqlserver
```

### 2. Lancement de l'Application Web
Démarrez l'interface conversationnelle Streamlit :

```bash
streamlit run jarvis/ui/app.py
```

## Architecture du projet

- `jarvis/config/` : Validation Pydantic et gestion centralisée des Settings.
- `jarvis/core/` : Plomberie robuste (Pool de connexions PostgreSQL, Retry, Logs JSON, Metrics).
- `jarvis/ingestion/` : Parsers HTML/Markdown et injecteurs optimisés.
- `jarvis/llm/` : Gestion du modèle de langage, templating Jinja2 et filtre "Sniper".
- `jarvis/retrieval/` : Moteur de recherche FTS/Vectoriel et Routeur IA.
- `jarvis/ui/` : Interface Streamlit.
