# ==============================================================================
# HOURGLASS WEB APP v2.6.0 - Production Dockerfile
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# Dépendances système minimales pour psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY . /app

EXPOSE 5002

# Lancement en production avec Gunicorn (4 workers, écoute sur 5002)
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5002", "--timeout", "120", "run:app"]
