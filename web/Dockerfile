#Docker file - WEB APP

FROM python:3.12.4

WORKDIR /app

COPY ./web /app

# Copier requirements.txt et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

ARG POSTGRESQL_DBNAME
ARG POSTGRESQL_USER
ARG POSTGRESQL_PASSWORD
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

CMD ["python", "run.py"]
