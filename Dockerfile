# Utilisation d'une image Python légère
FROM python:3.10-slim

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# Installation des utilitaires système de base
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements et installation (utilise le cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code source
COPY . .

# Création des dossiers de cache pour éviter les problèmes de droits
RUN mkdir -p /app/data/cache/embeddings /app/data/cache/flashrank

# Exposition du port Streamlit
EXPOSE 8501

# Commande de lancement
CMD ["streamlit", "run", "jarvis/ui/app.py", "--server.address=0.0.0.0"]