import psycopg2
import os
from operator import itemgetter
import time
from datetime import datetime

dbName = os.environ.get('POSTGRESQL_DBNAME')
user = os.environ.get('POSTGRESQL_USER')
password = os.environ.get('POSTGRESQL_PASSWORD')
host = os.environ.get('POSTGRESQL_HOST')
port = os.environ.get('POSTGRESQL_PORT')

def routine():
    transfer_data()
    print("La fonction routine a été exécutée à :", datetime.now())

def ConnectToDataBase():
    conn = psycopg2.connect(
        dbname=dbName,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historical_stats (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        server_id BIGINT,
        messages INTEGER DEFAULT 0,
        seconds INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''') 
    return conn
 
def transfer_data():
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    try:
        # Récupérer les données de la table 'stats'
        cursor.execute("SELECT user_id, server_id, messages, seconds FROM stats")
        rows = cursor.fetchall()  # Récupérer toutes les lignes

        # Insérer les données dans la table 'historical_stats'
        for row in rows:
            cursor.execute('''
                INSERT INTO historical_stats (user_id, server_id, messages, seconds)
                VALUES (%s, %s, %s, %s)
            ''', (row[0], row[1], row[2], row[3]))

        # Commit des changements
        conn.commit()
        print(f"{cursor.rowcount} lignes insérées dans 'historical_stats'.")

    except Exception as e:
        print("Erreur lors de la récupération ou de l'insertion des données :", e)
        conn.rollback()  # Annuler les changements en cas d'erreur
    finally:
        # S'assurer que le curseur et la connexion sont fermés
        if cursor:
            cursor.close()
        if conn:
            conn.close()