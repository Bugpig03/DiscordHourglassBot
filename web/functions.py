import psycopg2
import os
import heapq
from collections import defaultdict

dbName = os.environ.get('POSTGRESQL_DBNAME')
user = os.environ.get('POSTGRESQL_USER')
password = os.environ.get('POSTGRESQL_PASSWORD')
host = os.environ.get('POSTGRESQL_HOST')
port = os.environ.get('POSTGRESQL_PORT')

# connection a la bdd
def ConnectToDatabase():
    """
    Connexion à la base de données PostgreSQL en mode lecture seule.
    """
    conn = psycopg2.connect(
        dbname=dbName,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    return conn

def GetDistinctServerCount():
    """
    Récupère le nombre de server_id distincts.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour compter les server_id distincts
        cursor.execute('''
        SELECT COUNT(DISTINCT server_id) FROM stats
        ''')
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        distinct_count = result[0]
        
        return distinct_count

    except Exception as e:
        print(f"Error while retrieving distinct server_id count: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetDistinctUserCount():
    """
    Récupère le nombre de user_id distincts.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour compter les user_id distincts
        cursor.execute('''
        SELECT COUNT(DISTINCT user_id) FROM stats
        ''')
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        distinct_count = result[0]
        
        return distinct_count

    except Exception as e:
        print(f"Error while retrieving distinct user_id count: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetDistinctUserServerComboCount():
    """
    Récupère le nombre de combinaisons distinctes de user_id et server_id.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour compter les combinaisons distinctes de user_id et server_id
        cursor.execute('''
        SELECT COUNT(DISTINCT (user_id, server_id)) FROM stats
        ''')
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        distinct_combo_count = result[0]
        
        return distinct_combo_count

    except Exception as e:
        print(f"Error while retrieving distinct user_id and server_id combo count: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetTotalMessages():
    """
    Récupère la somme totale des messages envoyés sur le bot.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT COALESCE(SUM(messages), 0) FROM stats
        ''')
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        total_messages = result[0]
        
        return total_messages

    except Exception as e:
        print(f"Error while retrieving total messages: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetTotalSeconds():
    """
    Récupère la somme totale des secondes de toutes les entrées dans la table.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT COALESCE(SUM(seconds), 0) FROM stats
        ''')
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        total_seconds = result[0]
        
        return total_seconds

    except Exception as e:
        print(f"Error while retrieving total seconds: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def ConvertSecondsToTime(seconds):
    # Calcul des heures, minutes et secondes
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Formatage du temps
    time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    
    return time_format

def GetTop25UsersBySeconds():
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Récupère le top 25 des utilisateurs avec le plus de secondes, en agrégeant par utilisateur
        cursor.execute('''
        SELECT user_id, SUM(seconds) AS total_seconds, SUM(messages) AS total_messages, SUM(score) AS total_score
        FROM stats
        GROUP BY user_id
        ORDER BY total_seconds DESC
        LIMIT 25
        ''')
        
        # Récupère le résultat de la requête
        top_users = cursor.fetchall()
        
        return top_users

    except Exception as e:
        print(f"Error while retrieving top 25 users by seconds: {e}")
        return []  # Retourne une liste vide en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def FormatGetTop25Users():
    top_users = GetTop25UsersBySeconds()
    
    # Convertir les secondes en temps formaté
    top_users_formatted = [
        {
            "user_id": GetUsernameById(user[0]),  # Indice pour user_id
            "formatted_time": ConvertSecondsToTime(user[1]),  # Indice pour total_seconds
            "total_messages": user[2],  # Indice pour total_messages
            "total_score": user[3]  # Indice pour total_score
        }
        for user in top_users
    ]
    
    return top_users_formatted

def GetUsernameById(user_id):
    """
    Récupère le nom d'utilisateur associé à user_id.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT username FROM usernames WHERE user_id = %s
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return user_id

    except Exception as e:
        print(f"Error while retrieving username: {e}")
        return user_id

    finally:
        cursor.close()
        conn.close()

def GetDatabaseSize():
    """
    Récupère la taille de la base de données en kilo-octets.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour obtenir la taille de la base de données en octets
        cursor.execute(f"SELECT pg_database_size('{dbName}')")
        
        # Récupère la taille de la base de données en octets
        result = cursor.fetchone()
        size_in_bytes = result[0]
        
        # Convertir la taille en kilo-octets
        size_in_kb = size_in_bytes / 1024
        
        return size_in_kb

    except Exception as e:
        print(f"Error while retrieving database size: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetCommittedTransactionCount():
    """
    Récupère le nombre de transactions validées (committed) dans la base de données.
    
    Returns:
        int: Le nombre de transactions validées.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        query = f"""
        SELECT xact_commit 
        FROM pg_stat_database 
        WHERE datname = '{dbName}';
        """
        cursor.execute(query)
        result = cursor.fetchone()
        print(result[0])
        return result[0] if result else 0
    
    except Exception as e:
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetTotalCharacterCountInDatabase():
    """
    Récupère le nombre total de caractères dans toutes les colonnes de type texte (VARCHAR, TEXT) 
    dans toute la base de données.
    
    Returns:
        int: Le nombre total de caractères dans la base de données.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()

    try:
        # Récupérer toutes les colonnes de type texte (VARCHAR, TEXT)
        query = """
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE data_type IN ('character varying', 'text')
        """
        cursor.execute(query)
        columns = cursor.fetchall()

        total_characters = 0
        
        # Pour chaque colonne de type texte, compter le nombre total de caractères
        for table_schema, table_name, column_name in columns:
            # Construire et exécuter la requête SQL pour chaque colonne
            count_query = f"""
            SELECT SUM(LENGTH({column_name})) 
            FROM {table_schema}.{table_name}
            """
            cursor.execute(count_query)
            result = cursor.fetchone()
            column_total = result[0] if result[0] is not None else 0
            
            # Ajouter le total de caractères de cette colonne au total global
            total_characters += column_total
        
        return total_characters

    except Exception as e:
        print(f"Error while retrieving total character count: {e}")
        return 0  # Retourne 0 en cas d'erreur

    finally:
        cursor.close()
        conn.close()