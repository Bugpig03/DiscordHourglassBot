import psycopg2
import time
import os
from datetime import datetime, timedelta

dbName = os.environ.get('POSTGRESQL_DBNAME')
user = os.environ.get('POSTGRESQL_USER')
password = os.environ.get('POSTGRESQL_PASSWORD')
host = os.environ.get('POSTGRESQL_HOST')
port = os.environ.get('POSTGRESQL_PORT')

# Fonction pour exécuter la requête SQL
def execute_sql():
    try:
        # Connexion à la base de données
        connection = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,  # ou autre port si nécessaire
            database=dbName
        )

        cursor = connection.cursor()

        # La requête SQL
        insert_query = """
        INSERT INTO historical_stats (user_id, server_id, messages, seconds)
        SELECT user_id, server_id, messages, seconds
        FROM stats;
        """
        cursor.execute(insert_query)
        connection.commit()

        print(f"Query executed successfully at {datetime.now()}")

    except Exception as error:
        print(f"Error executing query: {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

# Fonction pour attendre jusqu'à 3h00
def wait_until_3am():
    now = datetime.now()
    # Calculer le prochain 3h00
    next_3am = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
    if now.hour < 3:
        next_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)

    # Temps restant avant 3h00
    time_to_wait = (next_3am - now).total_seconds()

    print(f"Waiting {time_to_wait // 3600} hours and {(time_to_wait % 3600) // 60} minutes until 3am...")
    time.sleep(time_to_wait)

# Boucle principale
if __name__ == "__main__":
    while True:
        # Attendre jusqu'à 3h00
        wait_until_3am()
        # Exécuter la requête SQL à 3h00
        execute_sql()
