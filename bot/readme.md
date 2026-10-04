# DISCORD BOT - HOURGLASS v3.0.0 (Go Edition)

## DESCRIPTION

Bot Discord haute performance réécrit en Go (Go 1.24+, DiscordGo, pgxpool) pour le tracking d'activité en temps réel (sessions vocales par salon, punchcard, live status, volume de messages et classements).

## DOCKER INSTALLATION

Déploiement du conteneur bot autonome (identique à l'ancien fonctionnement, adapté à la structure Go).

### 1. Build de l'image Docker
```bash
docker build -t bugpig/hourglass_bot ./bot-go
```

### 2. Variables d'environnement requises

- **DISCORD_TOKEN** : Token secret du bot Discord
- **POSTGRESQL_DBNAME** : Nom de la base de données PostgreSQL (ex: `hourglass`)
- **POSTGRESQL_USER** : Utilisateur PostgreSQL (ex: `postgres`)
- **POSTGRESQL_PASSWORD** : Mot de passe de la BDD
- **POSTGRESQL_HOST** : Adresse/hôte de votre conteneur PostgreSQL
- **POSTGRESQL_PORT** : Port de votre PostgreSQL (défaut: `5432`)

### 3. Lancement du conteneur
```bash
docker run -d \
  --name hourglass-bot \
  --restart unless-stopped \
  --network <votre_reseau_docker> \
  -e DISCORD_TOKEN="votre_token" \
  -e POSTGRESQL_HOST="votre_hote_postgres" \
  -e POSTGRESQL_PORT="5432" \
  -e POSTGRESQL_DBNAME="hourglass" \
  -e POSTGRESQL_USER="postgres" \
  -e POSTGRESQL_PASSWORD="votre_password" \
  bugpig/hourglass_bot
```
