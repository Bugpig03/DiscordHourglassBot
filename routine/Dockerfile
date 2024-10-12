# Dockerfile - ROUTINE APP avec Cron
FROM python:3.10

# Installer cron et PostgreSQL client pour exécuter des requêtes SQL
RUN apt-get update && apt-get install -y cron postgresql-client

WORKDIR /app

# Copier les fichiers dans le conteneur
COPY ./routine /app

# Copier le script shell
COPY run_query.sh /app/run_query.sh

# Rendre le script exécutable
RUN chmod +x /app/run_query.sh

# Créer une tâche cron pour exécuter le script à 3h00 chaque jour
RUN echo "0 3 * * * /app/run_query.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/daily-sql-task

# Donner les droits corrects au fichier cron
RUN chmod 0644 /etc/cron.d/daily-sql-task

# Appliquer la tâche cron
RUN crontab /etc/cron.d/daily-sql-task

# S'assurer que le conteneur reste actif avec cron en cours d'exécution
CMD cron -f
