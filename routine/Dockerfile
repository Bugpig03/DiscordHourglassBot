#Docker file - ROUTINE APP

FROM python:3.10

WORKDIR /app

COPY ./routine /app

# Requirement for python
RUN pip install psycopg2
RUN pip install schedule

ARG POSTGRESQL_DBNAME
ARG POSTGRESQL_USER
ARG POSTGRESQL_PASSWORD
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

CMD ["python", "main.py"]
