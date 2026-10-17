# ==============================================================================
# HOURGLASS WEB APP - Production Dockerfile
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
# 4 processes x 4 threads: a slow request (charts, cards) no longer blocks a whole worker.
# Workers are recycled every ~2000 requests to keep in-memory caches and fragmentation in check.
CMD ["gunicorn", "--workers", "4", "--worker-class", "gthread", "--threads", "4", \
     "--max-requests", "2000", "--max-requests-jitter", "200", \
     "--bind", "0.0.0.0:5002", "--timeout", "120", "run:app"]
