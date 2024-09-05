FROM python:3.10

# Supervisord installation
RUN apt-get update && apt-get install -y supervisor

WORKDIR /app

COPY . .

# Requirement for python
RUN pip install discord.py
RUN pip install Flask
RUN pip install psycopg2

EXPOSE 5002

ARG DISCORD_TOKEN
ARG POSTGRESQL_DBNAME
ARG POSTGRESQL_USER
ARG POSTGRESQL_PASSWORD
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
