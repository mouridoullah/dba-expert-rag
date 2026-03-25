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
- **Déploiement** : Docker & Docker Compose

---

## Déploiement avec Docker (Recommandé)

Cette méthode déploie l'intégralité de l'architecture (Base de données, Moteur IA, Interface Web) dans un réseau virtuel isolé.

### Prérequis
- Docker et Docker Compose installés.
- **NVIDIA Container Toolkit** installé sur l'hôte (indispensable pour que le conteneur Ollama puisse utiliser votre carte graphique GPU).

### 1. Configuration
Créez un fichier `.env` à la racine du projet :
```env
DB_HOST=db
DB_PORT=5432
DB_NAME=dbname
DB_USER=dbuser
DB_PASSWORD=dbpassword
OLLAMA_BASE_URL=http://ollama:11434
```

### 2. Lancement de l'infrastructure
Construisez et démarrez les conteneurs en arrière-plan :
```bash
docker compose up -d --build
```
*Note : Grâce au fichier `init.sql`, la base de données, les schémas vectoriels et les triggers Full-Text Search s'initialisent **automatiquement** au premier démarrage du conteneur Postgres.*

### 3. Initialisation des modèles IA
Lors du tout premier lancement, téléchargez les modèles dans le conteneur Ollama :
```bash
docker exec -it jarvis_ollama ollama pull qwen2.5-coder:7b
docker exec -it jarvis_ollama ollama pull nomic-embed-text
```

**L'application est maintenant accessible sur http://localhost:8501 !**

---

## Installation Locale (Mode Développement)

Si vous souhaitez développer ou faire tourner l'application sans Docker.

1. **Cloner le projet et préparer l'environnement :**
   ```bash
   git clone <ton_depot>
   cd jarvis
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configurer les variables d'environnement (`.env`) :**
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=lab_dba
   DB_USER=bdvm
   DB_PASSWORD=votre_mot_de_passe_securise
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **Migrations Base de Données :**
   Assurez-vous que l'extension `pgvector` est installée sur votre serveur PostgreSQL local, puis exécutez les scripts de migration :
   ```bash
   python migrate_fts.py
   python migrate_fts_french.py
   ```

---

## Utilisation (Ingestion de données)

Pour que l'IA puisse répondre, vous devez peupler la base de connaissances avec les documentations officielles.

**Si vous utilisez Docker :**
```bash
# Pour la documentation PostgreSQL (HTML)
docker exec -it jarvis_app python -m jarvis.ingestion.cli --engine postgres --docs-dir /app/data/docs_postgres

# Pour la documentation SQL Server (Markdown)
docker exec -it jarvis_app python -m jarvis.ingestion.cli --engine sqlserver --docs-dir /app/data/docs_sqlserver
```
*(Note : Pensez à monter un volume dans votre `docker-compose.yml` si vos documents sont sur votre machine hôte pour qu'ils soient accessibles dans `/app/data/`).*

**Si vous êtes en local :**
```bash
python -m jarvis.ingestion.cli --engine postgres --docs-dir /chemin/vers/docs_postgres
```

## Architecture du projet

- `jarvis/config/` : Validation Pydantic et gestion centralisée des Settings.
- `jarvis/core/` : Plomberie robuste (Pool de connexions PostgreSQL, Retry, Logs JSON, Metrics).
- `jarvis/ingestion/` : Parsers HTML/Markdown et injecteurs optimisés.
- `jarvis/llm/` : Gestion du modèle de langage, templating Jinja2 et filtre "Sniper".
- `jarvis/retrieval/` : Moteur de recherche FTS/Vectoriel et Routeur IA.
- `jarvis/ui/` : Interface Streamlit.