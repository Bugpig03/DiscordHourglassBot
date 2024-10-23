import psycopg2
import os
import heapq
from collections import defaultdict
from datetime import datetime

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

def GetTopUsersBySeconds():
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT user_id, SUM(seconds) AS total_seconds, SUM(messages) AS total_messages, SUM(score) AS total_score
        FROM stats
        GROUP BY user_id
        ORDER BY total_seconds DESC
        LIMIT 30
        ''')
        
        # Récupère le résultat de la requête
        top_users = cursor.fetchall()
        
        return top_users

    except Exception as e:
        print(f"Error while retrieving top users by seconds: {e}")
        return []  # Retourne une liste vide en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def FormatGetTopUsers():
    top_users = GetTopUsersBySeconds()
    
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

def GetServerNameById(server_id):
    """
    Récupère le nom du serveur associé à server_id.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT servername FROM servernames WHERE server_id = %s
        ''', (server_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return server_id

    except Exception as e:
        print(f"Error while retrieving servername: {e}")
        return server_id

    finally:
        cursor.close()
        conn.close()

def GetUserIdByUsername(username):
    """
    Récupère l'ID utilisateur (user_id) associé à un nom d'utilisateur (username).
    """
    conn = ConnectToDatabase()  # Connexion à la base de données (à implémenter)
    cursor = conn.cursor()
    
    try:
        # Requête SQL pour récupérer le user_id à partir du username
        cursor.execute('''
        SELECT user_id FROM usernames WHERE username = %s
        ''', (username,))
        
        # Récupérer le résultat de la requête
        result = cursor.fetchone()
        
        if result:
            return result[0]  # Retourne user_id si trouvé
        else:
            return None  # Retourne None si le username n'existe pas

    except Exception as e:
        print(f"Error while retrieving user_id: {e}")
        return None  # Retourne None en cas d'erreur
    
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
        # Exécute la requête SQL pour obtenir la taille de la base de données en Ko directement
        cursor.execute(f"SELECT pg_database_size('{dbName}') / 1024 AS size_in_kb")
        
        # Récupère la taille de la base de données en Ko
        result = cursor.fetchone()
        size_in_kb = result[0]
        
        return size_in_kb

    except Exception as e:
        print(f"Error while retrieving database size: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetTableSize(tableName):
    """
    Récupère la taille d'une table spécifique en kilo-octets.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour obtenir la taille de la table en Ko
        cursor.execute(f"SELECT pg_total_relation_size('{tableName}'::regclass) / 1024 AS size_in_kb")
        
        # Récupère la taille de la table en Ko
        result = cursor.fetchone()
        size_in_kb = result[0]
        
        return size_in_kb

    except Exception as e:
        print(f"Error while retrieving table size: {e}")
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

def GetMostRecentDate():
    """
    Récupère la date la plus récente de la colonne 'created_at' d'une table.
    """
    conn = ConnectToDatabase()
    cursor = conn.cursor()
    
    try:
        # Exécute la requête SQL pour obtenir la date la plus récente
        cursor.execute("SELECT MAX(created_at) FROM historical_stats")
        
        # Récupère la date la plus récente
        result = cursor.fetchone()
        most_recent_date = result[0]
        
        return most_recent_date

    except Exception as e:
        print(f"Error while retrieving the most recent date: {e}")
        return None  # Retourne None en cas d'erreur
    
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

def GetUserServerStats(user_id):
    """
    Récupère pour un utilisateur donné (user_id), la liste des serveurs auxquels il appartient,
    ainsi que pour chaque serveur : le nombre total de secondes, le nombre de messages,
    et la date de création de l'entrée la plus ancienne.
    
    Renvoie une liste de dictionnaires contenant ces informations pour chaque serveur.
    """
    conn = ConnectToDatabase()  # Connexion à la base de données (à implémenter)
    cursor = conn.cursor()
    
    try:
        # Requête pour récupérer les informations de chaque serveur auquel l'utilisateur appartient
        query = '''
        SELECT server_id, COALESCE(SUM(seconds), 0) as total_seconds, 
               COALESCE(SUM(messages), 0) as total_messages, 
               MIN(date_creation) as date_creation
        FROM stats
        WHERE user_id = %s
        GROUP BY server_id
        '''
        
        cursor.execute(query, (user_id,))
        
        # Récupérer tous les résultats
        results = cursor.fetchall()
        
        # Préparer la liste des statistiques par serveur
        server_stats = []
        for row in results:
            server_stats.append({
                'server_id': row[0],            # ID du serveur
                'server_name': GetServerNameById(row[0]),
                'total_seconds':  ConvertSecondsToTime(row[1]),        # Somme des secondes sur ce serveur
                'total_messages': row[2],       # Somme des messages sur ce serveur
                'rank': GetUserRankBySeconds(user_id,row[0]),
                'total_members': GetUniqueUsersCountByServerId(row[0]),
                'creation_date': FormatSQLTimestampToFrench(row[3])      # Date de création la plus ancienne
            })
        
        return server_stats

    except Exception as e:
        print(f"Error while retrieving user server stats: {e}")
        return []  # Retourne une liste vide en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def GetUserRankBySeconds(user_id, server_id):
    """
    Récupère le rang d'un utilisateur dans un serveur donné, basé sur le nombre de secondes.
    """
    conn = ConnectToDatabase()  # Remplacer par ta fonction de connexion à la base de données
    cursor = conn.cursor()

    try:
        # Requête pour récupérer le rang de l'utilisateur
        query = '''
        SELECT rank FROM (
            SELECT user_id, server_id, 
                   RANK() OVER (PARTITION BY server_id ORDER BY seconds DESC) AS rank
            FROM stats
        ) AS ranked
        WHERE user_id = %s AND server_id = %s;
        '''

        # Exécution de la requête avec les paramètres user_id et server_id
        cursor.execute(query, (user_id, server_id))

        # Récupérer le résultat
        result = cursor.fetchone()

        if result:
            return result[0]  # Retourne le rang
        else:
            return None  # Si l'utilisateur n'est pas trouvé dans ce serveur

    except Exception as e:
        print(f"Erreur lors de la récupération du rang de l'utilisateur: {e}")
        return None  # Retourne None en cas d'erreur

    finally:
        cursor.close()
        conn.close()

def GetServersStats():
    """
    Récupère la liste des serveurs avec le total de secondes, le nombre total de messages,
    et le nombre de membres uniques (utilisateurs) par serveur.
    """
    conn = ConnectToDatabase()  # Connexion à la base de données
    cursor = conn.cursor()

    try:
        # Requête SQL pour agréger les statistiques par serveur
        query = '''
        SELECT server_id, 
               SUM(seconds) AS total_seconds, 
               SUM(messages) AS total_messages, 
               COUNT(DISTINCT user_id) AS total_members
        FROM stats
        GROUP BY server_id
        ORDER BY server_id;
        '''

        # Exécution de la requête
        cursor.execute(query)

        # Récupérer tous les résultats
        results = cursor.fetchall()

        # Transformer les résultats en une liste de dictionnaires
        servers_stats = []
        for row in results:
            server_id, total_seconds, total_messages, total_members = row
            servers_stats.append({
                'server_id': server_id,
                'server_name': GetServerNameById(server_id),
                'total_seconds':  ConvertSecondsToTime(total_seconds),
                'total_messages': total_messages,
                'total_members': total_members
            })

        return servers_stats

    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques des serveurs: {e}")
        return []

    finally:
        cursor.close()
        conn.close()

def FormatSQLTimestampToFrench(timestamp):
    """
    Transforme un objet datetime (timestamp) en 'jour mois année' (ex: 5 octobre 2024).
    """
    # Dictionnaire des mois en français
    mois_francais = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril",
        5: "mai", 6: "juin", 7: "juillet", 8: "août",
        9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    # Extraire le jour, le mois et l'année
    jour = timestamp.day
    mois = mois_francais[timestamp.month]
    annee = timestamp.year
    
    # Formatage de la date
    return f"{jour} {mois} {annee}"

def FormatSQLTimestampAndHoursToFrench(timestamp):
    """
    Transforme un objet datetime (timestamp) en 'jour mois année, heure:minute:seconde' 
    (ex: 5 octobre 2024 à 14:30:45).
    """
    # Dictionnaire des mois en français
    mois_francais = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril",
        5: "mai", 6: "juin", 7: "juillet", 8: "août",
        9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    # Extraire le jour, le mois, l'année, l'heure, les minutes et les secondes
    jour = timestamp.day
    mois = mois_francais[timestamp.month]
    annee = timestamp.year
    heure = timestamp.hour
    minute = timestamp.minute
    seconde = timestamp.second
    
    # Formatage de la date et de l'heure
    return f"{jour} {mois} {annee} à {heure:02}:{minute:02}:{seconde:02}"


def GetUniqueUsersCountByServerId(server_id):
    """
    Récupère la somme des utilisateurs uniques (distincts) pour un serveur spécifique.
    """
    conn = ConnectToDatabase()  # Connexion à la base de données
    cursor = conn.cursor()

    try:
        cursor.execute('''
        SELECT COUNT(DISTINCT user_id) AS total_members
        FROM stats
        WHERE server_id = %s;
        ''', (server_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]  # Retourne le nombre d'utilisateurs distincts
        else:
            return 0  # Retourne 0 si aucun utilisateur n'est trouvé

    except Exception as e:
        print(f"Error while retrieving unique users count for server {server_id}: {e}")
        return 0  # Retourne 0 en cas d'erreur

    finally:
        cursor.close()
        conn.close()