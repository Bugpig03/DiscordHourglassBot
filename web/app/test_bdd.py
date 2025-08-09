from database import db, Users, Servers, HistoricalStats, Stats

# Ouvre la connexion
db.connect()

# Test : compter le nombre d'utilisateurs
nb_users = Users.select().count()
print(f"Nombre d'utilisateurs dans la table users : {nb_users}")

# Test : récupérer le premier serveur
first_server = Servers.select().first()
if first_server:
    print(f"Premier serveur : {first_server.servername} (ID: {first_server.server_id})")
else:
    print("Aucun serveur trouvé.")

# Ferme la connexion
db.close()