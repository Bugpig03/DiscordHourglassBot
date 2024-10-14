# Dockerfile - Routine app avec Python Scheduler
FROM python:3.10

# Installer PostgreSQL client et les dépendances
RUN apt-get update && apt-get install -y postgresql-client

WORKDIR /app

# Copier les fichiers dans le conteneur
COPY ./routine /app

# Installer psycopg2 pour Python
RUN pip install psycopg2-binary

# Définir les variables d'environnement
ARG POSTGRESQL_DBNAME
ARG POSTGRESQL_USER
ARG POSTGRESQL_PASSWORD
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

# Exécuter le script Python lors du démarrage du conteneur
CMD ["python", "/app/scheduler.py"]
