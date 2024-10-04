#Docker file - WEB APP

FROM python:3.10

WORKDIR /app

COPY ./web /app

# Requirement for python
RUN pip install Flask
RUN pip install psycopg2

EXPOSE 5003

ARG POSTGRESQL_DBNAME
ARG POSTGRESQL_USER
ARG POSTGRESQL_PASSWORD
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

CMD ["python", "server.py"]
