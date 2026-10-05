# ==============================================================================
# HOURGLASS WEB APP v2.7.3 - Production Dockerfile
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY . /app

EXPOSE 5002

# Lancement en production avec Gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5002", "--timeout", "120", "run:app"]
