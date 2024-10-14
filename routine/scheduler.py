import time
import os
import psycopg2
from datetime import datetime, timedelta

# Fonction pour calculer le temps restant avant 3h00
def time_until_3am():
    now = datetime.now()
    next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)

    # Si il est déjà passé 3h aujourd'hui, planifier pour demain
    if now >= next_run:
        next_run += timedelta(days=1)

    return (next_run - now).total_seconds()

# Fonction pour exécuter la commande SQL
def run_sql_query():
    try:
        # Récupérer les variables d'environnement
        db_name = os.environ.get('POSTGRESQL_DBNAME')
        db_user = os.environ.get('POSTGRESQL_USER')
        db_password = os.environ.get('POSTGRESQL_PASSWORD')
        db_host = os.environ.get('POSTGRESQL_HOST')
        db_port = os.environ.get('POSTGRESQL_PORT')

        # Connexion à PostgreSQL
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )

        # Créer un curseur
        cur = conn.cursor()

        # Exécuter la requête
        cur.execute("""
            INSERT INTO historical_stats (user_id, server_id, messages, seconds)
            SELECT user_id, server_id, messages, seconds
            FROM stats;
        """)

        # Valider la transaction
        conn.commit()

        # Fermer la connexion
        cur.close()
        conn.close()

        print(f"Requête exécutée avec succès à {datetime.now()}")

    except Exception as e:
        print(f"Erreur lors de l'exécution de la requête : {e}")

if __name__ == "__main__":

    while True:
        # Attendre jusqu'à 3h00
        sleep_time = time_until_3am()
        print(f"Attente de {sleep_time / 3600:.2f} heures jusqu'à 3h00.")
        time.sleep(sleep_time)

        # Exécuter la requête SQL
        run_sql_query()

        # Attendre 24 heures jusqu'au prochain cycle
        time.sleep(24 * 3600)
