import psycopg2
import os
from operator import itemgetter

dbName = os.environ.get('POSTGRESQL_DBNAME')
user = os.environ.get('POSTGRESQL_USER')
password = os.environ.get('POSTGRESQL_PASSWORD')
host = os.environ.get('POSTGRESQL_HOST')
port = os.environ.get('POSTGRESQL_PORT')


# CONNECTION A LA BASE DE DONNEE

def ConnectToDataBase():
    conn = psycopg2.connect(
        dbname=dbName,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    
    # Création de la table 'stats' avec une clé primaire composite (user_id, server_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            user_id BIGINT,
            server_id BIGINT,
            messages INTEGER DEFAULT 0,
            seconds INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, server_id)
        )
        ''')
    
    return conn

# MODIFICATION DES DONNEES PAR RAPPORT AU SERVEUR CONTEXTUEL

def AddMessagesToUser(userID, serverID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Vérifie si l'utilisateur existe déjà dans la base de données avec le server_id
        cursor.execute('''
        SELECT user_id FROM stats WHERE user_id = %s AND server_id = %s
        ''', (userID, serverID))
        user_exists = cursor.fetchone()

        if user_exists:
            # L'utilisateur existe déjà, met à jour le nombre de messages
            cursor.execute('''
            UPDATE stats
            SET messages = messages + 1
            WHERE user_id = %s AND server_id = %s
            ''', (userID, serverID))
            print("[DATA] - Add +1 to message of user")
        else:
            # L'utilisateur n'existe pas, l'ajoute à la base de données
            cursor.execute('''
            INSERT INTO stats (user_id, server_id, messages) VALUES (%s, %s, 1)
            ''', (userID, serverID))
            print("[DATA] - User created and added +1 to messages of user")
        
        # Confirmation des changements
        conn.commit()

    except Exception as e:
        print(f"Error while updating/adding messages: {e}")
        conn.rollback()  # Annule les changements en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def AddSecondsToUser(userID, serverID, seconds):
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Vérifie si l'utilisateur existe déjà dans la base de données avec le server_id
        cursor.execute('''
        SELECT user_id FROM stats WHERE user_id = %s AND server_id = %s
        ''', (userID, serverID))
        user_exists = cursor.fetchone()

        if user_exists:
            # L'utilisateur existe déjà, met à jour le nombre de secondes
            cursor.execute('''
            UPDATE stats
            SET seconds = seconds + %s
            WHERE user_id = %s AND server_id = %s
            ''', (seconds, userID, serverID))
            print(f"[DATA] - Added {seconds} seconds to user")
        else:
            # L'utilisateur n'existe pas, l'ajoute à la base de données
            cursor.execute('''
            INSERT INTO stats (user_id, server_id, seconds) VALUES (%s, %s, %s)
            ''', (userID, serverID, seconds))
            print(f"[DATA] - User created and added {seconds} seconds to user")
        
        # Confirmation des changements
        conn.commit()

    except Exception as e:
        print(f"Error while updating/adding seconds: {e}")
        conn.rollback()  # Annule les changements en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

# RECUPERATION DES DONNEES PAR RAPPORT AU SERVEUR CONTEXTUEL (server ID)

def GetSecondsOfUserOnServer(userID, serverID): # seconds on one server
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le nombre de secondes de l'utilisateur dans la base de données
        cursor.execute('''
        SELECT seconds FROM stats WHERE user_id = %s AND server_id = %s
        ''', (userID, serverID))
        
        # Récupère le résultat de la requête
        seconds = cursor.fetchone()
        
        # Si l'utilisateur existe, retourne le nombre de secondes, sinon retourne 0
        if seconds is not None:
            return seconds[0]
        else:
            return 0

    except Exception as e:
        print(f"Error while retrieving seconds: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def GetMessagesOfUserOnServer(userID, serverID): #number of message on one server
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le nombre de messages de l'utilisateur dans la base de données
        cursor.execute('''
        SELECT messages FROM stats WHERE user_id = %s AND server_id = %s
        ''', (userID, serverID))
        
        # Récupère le résultat de la requête
        messages = cursor.fetchone()
        
        # Si l'utilisateur existe, retourne le nombre de messages, sinon retourne 0
        if messages is not None:
            return messages[0]
        else:
            return 0

    except Exception as e:
        print(f"Error while retrieving messages: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()
    
def GetTop10UsersBySecondsOnServer(serverID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le top 10 des utilisateurs avec le plus de secondes pour un serverID spécifique
        cursor.execute('''
        SELECT user_id, messages, seconds, score
        FROM stats
        WHERE server_id = %s
        ORDER BY seconds DESC
        LIMIT 10
        ''', (serverID,))
        
        # Récupère le résultat de la requête
        top_users = cursor.fetchall()
        
        print(top_users)
        return top_users

    except Exception as e:
        print(f"Error while retrieving top 10 users by seconds: {e}")
        return []  # Retourne une liste vide en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

# RECUPERATION DES DONNES SANS CONTEXTE (all)

def GetSecondsOfUser(userID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le total des secondes de l'utilisateur à travers tous les serveurs
        cursor.execute('''
        SELECT COALESCE(SUM(seconds), 0) FROM stats WHERE user_id = %s
        ''', (userID,))
        
        # Récupère le résultat de la requête
        total_seconds = cursor.fetchone()
        
        # Retourne le nombre total de secondes, ou 0 si aucun résultat
        return total_seconds[0]

    except Exception as e:
        print(f"Error while retrieving total seconds for user: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def GetMessagesOfUser(userID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le total des messages de l'utilisateur à travers tous les serveurs
        cursor.execute('''
        SELECT COALESCE(SUM(messages), 0) FROM stats WHERE user_id = %s
        ''', (userID,))
        
        # Récupère le résultat de la requête
        total_messages = cursor.fetchone()
        
        # Retourne le nombre total de messages, ou 0 si aucun résultat
        return total_messages[0]

    except Exception as e:
        print(f"Error while retrieving total messages for user: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def GetTop10UsersBySeconds():
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Récupère le top 10 des utilisateurs avec le plus de secondes, en agrégeant par utilisateur
        cursor.execute('''
        SELECT user_id, SUM(seconds) AS total_seconds, SUM(messages) AS total_messages, SUM(score) AS total_score
        FROM stats
        GROUP BY user_id
        ORDER BY total_seconds DESC
        LIMIT 10
        ''')
        
        # Récupère le résultat de la requête
        top_users = cursor.fetchall()
        
        return top_users

    except Exception as e:
        print(f"Error while retrieving top 10 users by seconds: {e}")
        return []  # Retourne une liste vide en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

# RECUPERATION POUR LES STATS SERVER

def GetTotalMessagesOnServer(serverID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()

    try:
        # Exécute la requête pour sommer les messages en filtrant par server_id
        cursor.execute('''
        SELECT COALESCE(SUM(messages), 0) FROM stats WHERE server_id = %s
        ''', (serverID,))
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        
        # Retourne le total des messages ou 0 si aucun résultat
        return result[0]

    except Exception as e:
        print(f"Error while retrieving total messages for server: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()

def GetTotalSecondsOnServer(serverID):
    conn = ConnectToDataBase()
    cursor = conn.cursor()

    try:
        # Exécute la requête pour sommer les secondes en filtrant par server_id
        cursor.execute('''
        SELECT COALESCE(SUM(seconds), 0) FROM stats WHERE server_id = %s
        ''', (serverID,))
        
        # Récupère le résultat de la requête
        result = cursor.fetchone()
        
        # Retourne le total des secondes ou 0 si aucun résultat
        return result[0]

    except Exception as e:
        print(f"Error while retrieving total seconds for server: {e}")
        return 0  # Retourne 0 en cas d'erreur
    
    finally:
        # Fermer le curseur et la connexion
        cursor.close()
        conn.close()


def SetUsername(user_id, username):
    """
    Initialise la table usernames si elle n'existe pas et met à jour le username pour un user_id donné.
    """
    conn = ConnectToDataBase()
    cursor = conn.cursor()
    
    try:
        # Créer la table si elle n'existe pas encore
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usernames (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255) NOT NULL
        )
        ''')
        
        # Mettre à jour ou insérer le username pour le user_id donné
        cursor.execute('''
        INSERT INTO usernames (user_id, username)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET username = EXCLUDED.username
        ''', (user_id, username))
        
        # Commit les changements
        conn.commit()

    except Exception as e:
        print(f"Error while initializing or updating usernames: {e}")
        conn.rollback()  # Annule les changements en cas d'erreur
    
    finally:
        cursor.close()
        conn.close()

def SetServerName(server_id, servername):
    """
    Initialise la table servernames si elle n'existe pas et met à jour le servername pour un server_id donné.
    """
    conn = ConnectToDataBase()
    cursor = conn.cursor()

    try:
        # Créer la table servernames si elle n'existe pas encore
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS servernames (
            server_id BIGINT PRIMARY KEY,
            servername VARCHAR(255) NOT NULL
        )
        ''')

        # Mettre à jour ou insérer le servername pour le server_id donné
        cursor.execute('''
        INSERT INTO servernames (server_id, servername)
        VALUES (%s, %s)
        ON CONFLICT (server_id) DO UPDATE
        SET servername = EXCLUDED.servername
        ''', (server_id, servername))

        # Commit les changements
        conn.commit()

    except Exception as e:
        print(f"Error while initializing or updating servernames: {e}")
        conn.rollback()  # Annule les changements en cas d'erreur

    finally:
        cursor.close()
        conn.close()