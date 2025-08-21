#Docker file - WEB APP

FROM python:3.12.4

WORKDIR /app

# Installer les dépendances en premier pour profiter du cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./web /app

# Copier requirements.txt et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

# Variables d'environnement
ENV POSTGRESQL_DBNAME=${POSTGRESQL_DBNAME}
ENV POSTGRESQL_USER=${POSTGRESQL_USER}
ENV POSTGRESQL_PASSWORD=${POSTGRESQL_PASSWORD}
ENV POSTGRESQL_HOST=${POSTGRESQL_HOST}
ENV POSTGRESQL_PORT=${POSTGRESQL_PORT}

CMD ["python", "run.py"]
