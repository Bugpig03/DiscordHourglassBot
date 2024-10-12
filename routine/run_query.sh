#!/bin/bash

# Variables d'environnement pour PostgreSQL
DB_NAME=$POSTGRESQL_DBNAME
DB_USER=$POSTGRESQL_USER
DB_PASSWORD=$POSTGRESQL_PASSWORD
DB_HOST=$POSTGRESQL_HOST
DB_PORT=$POSTGRESQL_PORT

# Exécuter la requête SQL
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO historical_stats (user_id, server_id, messages, seconds) SELECT user_id, server_id, messages, seconds FROM stats;"
