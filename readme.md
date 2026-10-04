# ⏳ HOURGLASS - Discord Activity & Analytics Suite

[![Bot Version](https://img.shields.io/badge/Bot-v3.0.0_(Go)-00ADD8?style=flat-square&logo=go)](https://golang.org)
[![Web Dashboard](https://img.shields.io/badge/Dashboard-v2.6.0_(Flask)-000000?style=flat-square&logo=flask)](https://hourglassbot.net)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_16-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Deploy-Docker_Compose-2496ED?style=flat-square&logo=docker)](https://www.docker.com)
[![GDPR Compliant](https://img.shields.io/badge/GDPR-Compliant-10B981?style=flat-square)](https://hourglassbot.net/privacy)

**Hourglass** est une suite analytique et de gamification haute performance pour Discord.  
Le projet combine un **bot Discord natif écrit en Go (v3.0.0)** pour une capture d'événements ultra-rapide et légère en mémoire, et un **tableau de bord web interactif en Flask / Python (v2.6.0)** offrant des métriques détaillées, des visualisations graphiques avancées et des cartes statistiques exportables.

---

## 🏛️ Architecture du Projet

```text
DiscordHourglassBot/
├── bot/                    # Bot Discord v3.0.0 en Go (Haute performance, DiscordGo & pgxpool)
│   ├── card/               # Moteur de génération des cartes d'activité vectorielles
│   ├── config/             # Chargement des variables d'environnement
│   ├── database/           # Connexion et requêtes PostgreSQL
│   ├── fonts/              # Typographies vectorielles DejaVu
│   ├── handlers/           # Écouteurs d'événements Gateway & Slash Commands
│   ├── Dockerfile          # Image multi-stage Docker ultra-légère pour le bot
│   └── main.go             # Point d'entrée principal du bot Go
│
├── web/                    # Dashboard Web v2.6.0 en Python (Flask, Chart.js, Bilingue FR/EN)
│   ├── app/                # Application Flask (routes, templates, composants, gamification, API)
│   ├── Dockerfile          # Image Docker du dashboard web
│   ├── run.py              # Serveur Flask / WSGI
│   └── requirements.txt    # Dépendances Python
│
└── database/               # Schémas et scripts de migration de données
    ├── schema_v3.sql       # DDL complet PostgreSQL pour le schéma v3.0
    └── migrate_v3.py       # Script de migration automatique avec garantie mathématique de parité
```

---

## ✨ Fonctionnalités Clés

### 🎙️ Tracking Vocale & Granularité v3.0
- **Sessions Vocales Précises (`voice_sessions`)** : Horodatage d'arrivée (`joined_at`), de départ (`left_at`), durée à la seconde près, suivi par salon (`channel_id`).
- **Détection des Équipements & Statuts** : Indicateurs booléens de streaming (partage d'écran) et de caméra activée (sans aucun enregistrement audio ou vidéo).
- **Statut en Direct (`live_server_status`)** : Suivi en direct du nombre de membres connectés, absents, ne pas déranger et en vocal.
- **Compagnons Vocaux Fréquents** : Algorithme déterminant les membres avec lesquels un utilisateur passe le plus de temps en vocal.
- **Punchcard Horaire 24h & 7j/7** : Visualisation matricielle de la répartition de l'activité sur la semaine.
- **Heatmap Style GitHub** : Calendrier annuel et mensuel d'assiduité vocale.

### 🎮 Gamification & Badges
- **Système d'Expérience (XP) & Niveaux** : $1\text{ min en vocal} = 1\text{ XP}$, $1\text{ message} = 5\text{ XP}$. Formule quadratique équitable.
- **Titres Honorifiques Dynamiques** : Titres débloqués automatiquement selon les paliers de niveau.
- **37 Badges Équitables** : Basés sur le cumul global (non punitifs si l'utilisateur est sur plusieurs serveurs) avec icônes vectorielles SVG.

### 🖼️ Cartes Statistiques Vectorielles
- Cartes de profil et de serveur générées dynamiquement en haute résolution.
- Génération native en Go via `gg` et API Web en SVG pur (`/api/card/...`).
- Format internationalisé avec liens directs vers les profils globaux (`hourglassbot.net/profile/<id>`).

### ⚖️ Respect de la Vie Privée & RGPD
- **Minimisation stricte** : Aucun contenu de message textuel n'est jamais lu ou stocké.
- **Aucune écoute audio** : Aucun flux vocal n'est capté ni enregistré.
- **Droit à l'oubli** : Procédure de purge complète des données sous 72h.

---

## 🚀 Déploiement des Conteneurs Indépendants

Chaque module possède son propre `Dockerfile` autonome dans son sous-dossier et se connecte directement à votre base de données PostgreSQL existante via son adresse IP locale.

### 1. Bot Discord (`./bot`)
```bash
# Build de l'image
docker build -t bugpig/hourglass_bot ./bot

# Lancement du conteneur
docker run -d \
  --name hourglass-bot \
  --restart unless-stopped \
  -e DISCORD_TOKEN="votre_token_discord" \
  -e POSTGRESQL_HOST="<IP_LOCALE_BDD>" \
  -e POSTGRESQL_PORT="5432" \
  -e POSTGRESQL_DBNAME="hourglass" \
  -e POSTGRESQL_USER="postgres" \
  -e POSTGRESQL_PASSWORD="votre_mot_de_passe" \
  bugpig/hourglass_bot
```

### 2. Dashboard Web (`./web`)
```bash
# Build de l'image
docker build -t bugpig/hourglass_web ./web

# Lancement du conteneur
docker run -d \
  --name hourglass-web \
  --restart unless-stopped \
  -p 5002:5002 \
  -e POSTGRESQL_HOST="<IP_LOCALE_BDD>" \
  -e POSTGRESQL_PORT="5432" \
  -e POSTGRESQL_DBNAME="hourglass" \
  -e POSTGRESQL_USER="postgres" \
  -e POSTGRESQL_PASSWORD="votre_mot_de_passe" \
  -e FLASK_SECRET_KEY="cle_secrete_aleatoire" \
  bugpig/hourglass_web
```

---

## 🗄️ Mise à Niveau de la Base de Données & Migration v3.0

Pour mettre à niveau une base de données existante (v2.x) vers le schéma v3.0 sans perte de données :

### 1. Appliquer le schéma SQL DDL
Exécutez le script SQL sur votre instance PostgreSQL :
```bash
psql -U postgres -d hourglass -f database/schema_v3.sql
```

### 2. Migrer l'ancien historique vers le nouveau format
Le script `migrate_v3.py` convertit les totaux cumulés et les snapshots de `stats` et `historical_stats` en sessions et événements horodatés avec le flag `is_legacy = TRUE` :
```bash
# Simulation à blanc (vérification de parité sans écriture) :
python database/migrate_v3.py --dry-run

# Application réelle :
python database/migrate_v3.py --execute
```

---

## 🤖 Commandes Slash du Bot (Discord)

| Commande | Description | Options |
|---|---|---|
| `/stats` | Affiche la carte statistique de l'utilisateur sur le serveur actuel | `[membre]` (optionnel) |
| `/allstats` | Affiche la carte statistique globale (tous serveurs confondus) | `[membre]` (optionnel) |
| `/top` | Affiche le classement du serveur actuel sous forme de carte vectorielle | `[critere]` (vocal, messages, xp) |
| `/alltop` | Affiche le classement global de tous les serveurs suivis | `[critere]` (vocal, messages, xp) |
| `/server` | Affiche la fiche statistique complète du serveur actuel | - |
| `/versus` | Compare les statistiques de deux membres dans un duel visuel | `<membre1>` `<membre2>` |
| `/help` | Affiche le guide d'utilisation et les liens vers le dashboard | - |

---

## 🌐 Liens Utiles

- **Dashboard Officiel** : [https://hourglassbot.net](https://hourglassbot.net)
- **Politique de Confidentialité & RGPD** : [https://hourglassbot.net/privacy](https://hourglassbot.net/privacy)
- **Conditions Générales d'Utilisation** : [https://hourglassbot.net/terms](https://hourglassbot.net/terms)
- **Support Discord Officiel** : [https://discord.gg/WU3mTwkGZV](https://discord.gg/WU3mTwkGZV)

---
*Propulsé par SnoutLabs • Hourglass Bot v3.0.0 & Dashboard v2.6.0*
