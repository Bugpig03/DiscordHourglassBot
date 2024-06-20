import sqlite3
import os
from operator import itemgetter

def ConnectToDataBase(serverID): #connect a la database si elle n'existe pas création
    dbName = 'data/server_' + str(serverID) +'.db'
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        messages INTEGER UNSIGNED DEFAULT 0,
        seconds INTEGER UNSIGNED DEFAULT 0,
        score INTEGER UNSIGNED DEFAULT 0,  
        loot_commun INTEGER UNSIGNED DEFAULT 0,
        loot_uncommun INTEGER UNSIGNED DEFAULT 0,
        loot_rare INTEGER UNSIGNED DEFAULT 0,
        loot_epic INTEGER UNSIGNED DEFAULT 0,
        loot_legendary INTEGER UNSIGNED DEFAULT 0,
        loot_mythical INTEGER UNSIGNED DEFAULT 0
      
    )
    ''')
    return conn

def AddMessagesToUser(userID, serverID):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    # Vérifie si l'utilisateur existe déjà dans la base de données
    cursor.execute('''
    SELECT id FROM users WHERE id = ?
    ''', (userID,))
    user_exists = cursor.fetchone()

    if user_exists:
        # L'utilisateur existe déjà, met à jour le nombre de messages
        cursor.execute('''
        UPDATE users
        SET messages = messages + 1
        WHERE id = ?
        ''', (userID,))
        print("[DATA] - Add +1 to message of user")
    else:
        # L'utilisateur n'existe pas, l'ajoute à la base de données
        cursor.execute('''
        INSERT INTO users (id, messages) VALUES (?, 1)
        ''', (userID,))

        print("[DATA] - User created and add +1 to messages of user")
    
    conn.commit()
    conn.close()

def AddSecondsToUser(userID, serverID, seconds):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    # Vérifie si l'utilisateur existe déjà dans la base de données
    cursor.execute('''
    SELECT id FROM users WHERE id = ?
    ''', (userID,))
    user_exists = cursor.fetchone()

    if user_exists:
        # L'utilisateur existe déjà, met à jour le nombre de secondes
        cursor.execute('''
        UPDATE users
        SET seconds = seconds + ?
        WHERE id = ?
        ''', (seconds, userID))
        print(f"[DATA] - Add {seconds} seconds to user")
    else:
        # L'utilisateur n'existe pas, l'ajoute à la base de données
        cursor.execute('''
        INSERT INTO users (id, seconds) VALUES (?, ?)
        ''', (userID, seconds))

        print(f"[DATA] - User created and add {seconds} seconds to user")
    
    conn.commit()
    conn.close()

def GetSecondsOfUser(userID, serverID):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    # Récupère le nombre de secondes de l'utilisateur dans la base de données
    cursor.execute('''
    SELECT seconds FROM users WHERE id = ?
    ''', (userID,))
    
    # Récupère le résultat de la requête
    seconds = cursor.fetchone()
    
    # Ferme la connexion à la base de données
    conn.close()
    
    # Si l'utilisateur existe, retourne le nombre de secondes, sinon retourne 0
    if seconds is not None:
        return seconds[0]
    else:
        return 0

def GetMessagesOfUser(userID, serverID):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    # Récupère le nombre de secondes de l'utilisateur dans la base de données
    cursor.execute('''
    SELECT messages FROM users WHERE id = ?
    ''', (userID,))
    
    # Récupère le résultat de la requête
    messages = cursor.fetchone()
    
    # Ferme la connexion à la base de données
    conn.close()
    
    # Si l'utilisateur existe, retourne le nombre de secondes, sinon retourne 0
    if messages is not None:
        return messages[0]
    else:
        return 0
    
def GetTop10UsersBySeconds(serverID):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, messages, seconds, score, loot_commun, loot_uncommun, loot_rare, loot_epic, loot_legendary, loot_mythical
    FROM users
    ORDER BY seconds DESC
    LIMIT 10
    ''')
    
    top_users = cursor.fetchall()
    conn.close()
    return top_users

def GetUserStatsFromAllDBs(userID):
    data_folder = 'data'
    all_user_stats = []

    # Parcourir tous les fichiers de base de données dans le dossier 'data'
    for filename in os.listdir(data_folder):
        if filename.endswith(".db"):
            serverID = int(filename.split('_')[1].split('.')[0])
            user_stats = GetUserStatsFromDB(userID, serverID)
            if user_stats:
                all_user_stats.append(user_stats)

    return all_user_stats

# Fonction pour récupérer les statistiques d'un utilisateur dans une base de données spécifique
def GetUserStatsFromDB(userID, serverID):
    conn = ConnectToDataBase(serverID)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, messages, seconds, score, loot_commun, loot_uncommun, loot_rare, loot_epic, loot_legendary, loot_mythical
    FROM users
    WHERE id = ?
    ''', (userID,))
    
    user_stats = cursor.fetchone()
    conn.close()
    return user_stats

# Fonction pour agréger les secondes de tous les utilisateurs à travers toutes les bases de données
def AggregateUserSeconds():
    data_folder = 'data'
    user_seconds = {}

    # Parcourir tous les fichiers de base de données dans le dossier 'data'
    for filename in os.listdir(data_folder):
        if filename.endswith(".db"):
            serverID = int(filename.split('_')[1].split('.')[0])
            conn = ConnectToDataBase(serverID)
            cursor = conn.cursor()
            cursor.execute('SELECT id, seconds FROM users')
            rows = cursor.fetchall()
            for row in rows:
                user_id = row[0]
                seconds = row[1]
                if user_id in user_seconds:
                    user_seconds[user_id] += seconds
                else:
                    user_seconds[user_id] = seconds
            conn.close()

    # Convertir le dictionnaire en liste de tuples pour le tri
    sorted_user_seconds = sorted(user_seconds.items(), key=itemgetter(1), reverse=True)
    return sorted_user_seconds[:10]  # Retourner les 10 premiers utilisateurs triés par secondes

