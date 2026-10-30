# Hourglass - Discord BOT - CHANGELOG

## Version 3.4.0 - Cartes dans la Langue du Membre - 28/10/2026

- **Les cartes suivent la langue Discord** du membre qui lance la commande : le bot envoie sa langue au site (`lang`), qui dessine la carte dans la nouvelle DA Arène (site v3.26.0).
- **Messages du bot traduits** dans les 12 langues du site : liens « Voir le profil complet », « Comparaison complète », « Classement complet » et « Tableau de bord du serveur », messages « aucune activité enregistrée », commande réservée aux serveurs, duel sans deux membres valides. Une langue Discord absente répond en anglais.
- Les réponses de secours en texte (site injoignable) et `/help` restent en anglais.
- **Repérage des bots et applications Discord** : nouvelle colonne `users.is_bot`, remplie quand le bot enregistre un membre (message ou vocal). Toutes les 15 minutes, avec le comptage des membres, les bots présents sur les serveurs sont aussi marqués, y compris ceux enregistrés avant cette version. Le site s'en sert pour l'étiquette « BOT » et pour masquer les bots de ses classements par défaut (v3.26.0).
  - La colonne est ajoutée au démarrage si elle manque. Si l'ajout échoue, le bot continue d'enregistrer les membres comme avant. Migration facultative : `database/migrations/2026-10-30_bot_v3.4.0_users_is_bot.sql`.

## Version 3.3.0 - Comptage des Membres Uniques - 23/10/2026

- **Relevé des membres présents sur les serveurs**, toutes les 15 minutes avec le relevé de présence, pour la page admin du site (v3.20.0) :
  - membres **uniques** sur l'ensemble des serveurs : chacun compte une fois, et les bots sont exclus ;
  - combien sont en ligne, combien ont déjà une activité enregistrée (et donc combien n'ont jamais parlé ni rejoint un vocal), le nombre d'appartenances et le nombre de serveurs listés.
- Le bot se sert des listes de membres que Discord lui envoie déjà au démarrage (intent des membres) : aucune nouvelle permission, et aucun identifiant de membre n'est stocké, seulement des totaux.
- Table `bot_member_snapshots`, créée au démarrage si elle manque, et purgée après 90 jours. Migration facultative : `database/migrations/2026-10-23_bot_v3.3.0_member_snapshots.sql`.

## Version 3.2.0 - Cartes Dessinées par le Site Web - 20/10/2026

- **Les cartes images viennent du site web (v3.19.0)** : le bot ne dessine plus rien.
  - Il demande le PNG à `WEB_INTERNAL_URL` (par défaut `https://hourglassbot.net`) avec l'en-tête `X-Card-Token` égal à `CARD_TOKEN`.
  - Les cartes reprennent ainsi la couleur, la bannière, le fond et les badges en vitrine du profil du membre.
  - Si le site ne répond pas, ou si `CARD_TOKEN` n'est pas configuré, la commande répond en **texte**.
- **`/versus`** : nouvelle option **`scope`**, pour comparer sur ce serveur (par défaut) ou sur tous les serveurs.
- **`/help`** répond par un message texte (embed) : plus lisible, liens cliquables, sans problème de taille d'image.
- `/stats` : la date affichée est la première activité vue par Hourglass sur le serveur, et non plus la date d'arrivée sur le serveur Discord, qui était au format américain.
- `/top` et `/alltop` : même classement que la page Membres du site.
- Nombres au format international (`12,450`).
- Suppression du moteur de dessin (`fogleman/gg`, `golang.org/x/image`) et des polices DejaVu : image Docker et binaire plus légers.

### Variables d'environnement à ajouter
- `CARD_TOKEN` : la même valeur que sur le site.
- `WEB_INTERNAL_URL` : facultative. Par exemple `http://hourglass-web:5002` si le bot et le site sont sur le même réseau Docker, sinon l'adresse publique du site.

## Version 3.1.1 - Allègement de presence_history - 18/10/2026

- **Fin des relevés de présence par serveur** : le bot enregistrait une ligne par serveur toutes les 15 minutes (conservées 7 jours), soit des millions de lignes (~250 Mo en prod), alors que le site ne lit que le relevé global (`server_id` vide). Seul le relevé global est désormais enregistré : environ 670 lignes sur 7 jours.
- **Purge automatique au démarrage** des anciens relevés par serveur, par lots de 50 000 lignes pour ne pas bloquer la table.
- Pour rendre l'espace disque au système, lancer une fois après le déploiement `database/migrations/2026-10-18_bot_v3.1.1_presence_history_cleanup.sql` (`VACUUM FULL`).

## Version 3.1.0 - Suivi de l'utilisation des commandes - 18/10/2026

- **Enregistrement de chaque commande slash** dans la nouvelle table `bot_command_events`, affichée dans l'onglet « Commandes » de la page admin du site :
  - nom de la commande, serveur (vide en message privé), options de choix (`type`, `period`, `scope`), réussite et durée de traitement ;
  - **aucun identifiant de membre** : les options de type utilisateur (mentions de `/stats`, `/versus`…) ne sont jamais enregistrées ;
  - une commande qui plante (récupérée par le `recover`) est comptée en erreur ; `/stats` ou `/server` refusés en DM sont notés `dm_refused`.
- Écriture en arrière-plan (goroutine, délai de 3 s) : une base lente ne retarde jamais la réponse à l'utilisateur.
- Purge automatique des événements de plus de 90 jours, avec le nettoyage de l'historique de présence (toutes les 15 min).
- Table créée au démarrage si elle manque (`CREATE TABLE IF NOT EXISTS`) ; migration facultative : `database/migrations/2026-10-18_bot_v3.1.0_command_events.sql`.

## Version 3.0.5 - Fiabilité du temps vocal & commandes en DM - 16/10/2026

- **Réouverture des sessions limitée aux vraies sessions orphelines (`SyncVoiceSession`)** :
  - Seules les sessions clôturées par la réconciliation (marquées `left_at = last_heartbeat`) dans le même salon sont rouvertes. Une déconnexion normale suivie d'un retour dans les 2 h ne compte plus l'absence comme du temps vocal.
  - La durée retirée lors de la réouverture est soustraite de `stats`, ce qui supprime le double comptage à la clôture suivante.
  - Heure de clôture des sessions orphelines normalisée en UTC.
- **Commandes slash robustes en messages privés** :
  - `/stats` et `/server` répondent par un message éphémère hors serveur au lieu de provoquer un panic (`i.Member` nil).
  - `/top` bascule automatiquement en classement global en DM.
  - `recover()` sur le dispatch des commandes : un panic ne peut plus arrêter le bot.
- **Stream & caméra en temps réel** : l'activation/arrêt du partage d'écran ou de la webcam dans le même salon met immédiatement à jour la session active.
- **Allègement de la charge PostgreSQL** :
  - Resynchronisation des présences (toutes les 30 s) en une seule requête groupée (`unnest`) au lieu d'une requête par membre et par serveur, et réécriture limitée aux statuts réellement modifiés.
  - `UpsertUser` / `UpsertServer` ne réécrivent plus la ligne quand rien n'a changé (auparavant à chaque message et toutes les 30 s par serveur).

## Version 3.0.4 - Correctifs de sécurité critiques (Dependabot) - 07/10/2026

- **Mise à niveau des dépendances Go et élimination des vulnérabilités Dependabot** :
  - `github.com/jackc/pgx/v5` mis à niveau vers `v5.11.0` (correction de l'injection SQL GHSA-j88v-2chj-qfwx et vulnérabilités de sécurité mémoire).
  - `golang.org/x/crypto` mis à niveau vers `v0.57.0` (résolution de 39 vulnérabilités CVE/GHSA sur SSH, DoS et bypass d'authentification).
  - `golang.org/x/image` mis à niveau vers `v0.46.0` (résolution de 11 vulnérabilités d'épuisement mémoire et crashs TIFF/BMP/WEBP).
  - `github.com/gorilla/websocket` mis à niveau vers `v1.5.3` (résolution de la vulnérabilité GHSA-w67g-5rqw-f597 sur le générateur PRNG).
  - `golang.org/x/sys` (v0.48.0) et `golang.org/x/text` (v0.42.0) synchronisés avec les derniers correctifs.

## Version 3.0.3 - Réconciliation vocale bidirectionnelle & reprise automatique des sessions - 04/10/2026

- **Réconciliation bidirectionnelle robuste (`reconcileSessions`)** :
  - Synchronise les sessions vocales depuis Discord vers la BDD pour chaque membre actuellement en salon vocal.
  - Temporisation de 5 secondes au démarrage (`OnReady`) pour attendre la réception des paquets `GUILD_CREATE`.
  - Exécution continue toutes les 30 secondes dans la boucle Heartbeat pour une auto-réparation instantanée en cas de coupure réseau.
- **Reprise automatique des sessions sans perte de temps (`SyncVoiceSession`)** :
  - Détection et réouverture transparente des sessions coupées lors d'une mise à jour ou d'un redémarrage du bot (`left_at = NULL`).
  - Aucun utilisateur en vocal ne subit de coupure ni de perte de temps lors des redéploiements.
- **Synchronisation automatique à la connexion des serveurs (`OnGuildCreate`)** :
  - Prise en charge immédiate de tous les membres déjà connectés dans les salons vocaux dès l'arrivée du serveur.

## Version 3.0.2 - Enregistrement automatique de présence 48h & Optimisations - 04/10/2026

- **Enregistrement périodique automatique (`presence_history`)** :
  - La boucle d'événements enregistre désormais automatiquement un instantané toutes les 15 minutes pour chaque serveur et pour le global.
  - Calcul fidèle des membres hors-ligne réels : `offline = memberCount - (online + idle + dnd)`.
  - Nettoyage automatique des instantanés datant de plus de 7 jours.
- **Cartes visuelles et commandes en anglais par défaut** :
  - Toutes les cartes générées (`stats`, `versus`, `top`, `server`, `help`) sont rédigées en anglais officiel.
- **Réponse différée immédiate (< 10 ms)** :
  - Élimination définitive de l'erreur *"L'application ne répond plus"*.
- **Synchronisation Bulk Overwrite** :
  - Déploiement atomique de toutes les commandes slash Discord via `ApplicationCommandBulkOverwrite`.

## Version 2.6.2 - Cartes en anglais par défaut, avatars agrandis dans le top et refonte de /help - 07/09/2026

- **Langue anglaise par défaut (`en`) pour toutes les cartes et commandes** :
  - L'ensemble des requêtes de cartes émises par le bot (`stats`, `allstats`, `top`, `alltop`, `server`, `help`) transmettent explicitement le paramètre `?lang=en` à l'API.
  - L'API Hourglass a été mise à jour pour définir l'anglais (`en`) comme langue par défaut sur l'intégralité des routes de génération de cartes.
  - Tous les messages textuels de secours (fallback) ainsi que les descriptions et paramètres des commandes slash sont désormais rédigés en anglais.
- **Avatars agrandis et fiabilisés dans les classements Top 10 (`/top` et `/alltop`)** :
  - Intégration des photos de profil (avatars) de chaque membre du classement avec un diamètre agrandi à 32px dans un cercle net et bordé.
  - Attribution automatique d'un avatar Discord officiel par défaut pour les membres sans photo de profil afin d'assurer l'affichage systématique de l'image.
  - Élargissement de la carte du top à 620px et hauteur de ligne à 42px pour une lisibilité parfaite des pseudos, niveaux, temps vocal et messages.
- **Refonte graphique complète et moderne de la carte `/help`** :
  - Nouveau design épuré en grille 2 colonnes (820×490px) présentant les 6 commandes principales (`/stats`, `/allstats`, `/top`, `/alltop`, `/server`, `/help`).
  - Chaque bloc comprend un badge de catégorie coloré, la puce de la commande slash, la description détaillée et le rappel du préfixe classique (legacy).
  - En-tête modernisé avec icône de sablier luisante, titre Hourglass Bot et badge d'état interactif (`v2.6.2 • SLASH ACTIVE`).
- **Conservation intégrale de la logique métier** :
  - Aucun changement apporté au suivi des temps vocaux, au comptage des messages, ni aux opérations de base de données.

## Version 2.6.1 - Rendu des polices et avatars dans les cartes PNG - 07/09/2026

- **Résolution du problème de texte manquant dans les cartes** :
  - Embarquement direct des polices vectorielles TrueType DejaVu (`DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`, `DejaVuSansMono.ttf`, etc.) dans le dossier `bot/fonts/` du projet.
  - Configuration explicite du dossier de polices (`FONTS_DIRS`) et des familles génériques dans `resvg_py.svg_to_bytes` pour garantir un rendu parfait des textes (niveaux, temps vocal, messages, pseudonymes, titres) dans tous les environnements (Docker Linux, Windows, macOS).
- **Intégration et affichage des avatars distants** :
  - Ajout d'une fonction asynchrone `_inline_remote_images` avec cache mémoire pour convertir à la volée les URLs HTTP/HTTPS des avatars et icônes en Data URIs Base64 (`data:image/png;base64,...`).
  - Permet à `resvg` de dessiner les photos de profil des utilisateurs et les icônes de serveur sans restriction réseau.

## Version 2.6.0 - Commandes Slash Discord & Renommage !aide en !help - 07/09/2026

- **Support complet des commandes Slash (`/`) de Discord** :
  - Migration vers le système de commandes hybrides de Discord (`@bot.hybrid_command` / `app_commands`).
  - Toutes les commandes peuvent désormais être invoquées sous forme de commandes slash modernes (`/stats`, `/allstats`, `/top`, `/alltop`, `/server`, `/help`) avec autocomplétion, descriptions intégrées et sélecteur d'utilisateur dans l'interface Discord.
  - Rétrocompatibilité totale avec les préfixes classiques (`!stats`, `!allstats`, etc.).
  - Synchronisation automatique des commandes slash auprès de l'API Discord au démarrage (`bot.tree.sync()`).
  - Prise en charge du différé (`ctx.defer()`) pour éviter toute expiration de l'interaction Discord lors de la génération des cartes.
- **Renommage de la commande d'aide** :
  - `!aide` est désormais renommée en `!help` (et `/help`).
  - L'alias `!aide` reste conservé pour assurer une transition transparente.
- **Conservation de la logique métier** :
  - La logique de suivi (temps passé en vocal, messages envoyés, mise à jour des avatars et pseudos) reste 100% inchangée.

## Version 2.5.1 - Affichage graphique PNG natif sur Discord & Correction doublon fallback - 07/09/2026

- **Affichage natif des cartes en image PNG dans Discord** :
  - Intégration de `resvg-py` pour convertir instantanément le SVG généré par l'API en PNG haute définition.
  - Résout le comportement de Discord qui affichait le fichier `.svg` sous forme de bloc de code brut (`<svg ...`) au lieu d'une véritable image graphique.
  - Les cartes (`!stats`, `!allstats`, `!top`, `!alltop`, `!server`, `!aide`) s'affichent désormais directement comme une image dans les salons Discord.
- **Correction du message texte en double (fallback)** :
  - Découplage strict de la requête API et de l'envoi Discord pour empêcher l'envoi intempestif du message textuel lorsque la carte est bien récupérée.
  - Le message texte d'origine n'est désormais envoyé qu'exclusivement si l'API est injoignable ou en cas de panne réseau.

## Version 2.5.0 - Réponses des commandes en cartes graphiques SVG - 07/09/2026

- **Affichage des réponses en cartes vectorielles SVG** :
  - Pour chaque commande du bot (`!stats [user]`, `!allstats [user]`, `!top`, `!alltop`, `!server`, `!aide`), le bot renvoie désormais la carte SVG correspondante générée par l'API Hourglass sous forme de fichier attaché plutôt qu'un message textuel brut.
  - Conservation stricte de l'ensemble de la logique de suivi (comptage de messages, temps vocal, mise à jour des avatars et pseudonymes en base de données).
  - Gestion de secours (fallback) automatique : en cas de non-disponibilité, d'erreur ou de timeout de l'API Hourglass, le bot renvoie automatiquement le message textuel standard pour garantir une disponibilité 100%.
  - Configuration de l'URL de l'API via la variable d'environnement `HOURGLASS_API_URL` (défaut : `https://hourglassbot.net`).

## Version 2.4.2 - !stats update avatar - 17/01/2025

    - Fix duplication bug of users in DB

## Version 2.4.1 - !stats update avatar - 16/01/2025

    - command !stats now update avatar of tag user

## Version 2.4.0 - Avatar Update and time format ! - 15/01/2025

- Now saved avatar servers and users on DB
- Update time format to h:min:s
- Security improvement with empty commit in DB
- BDD change with news colums for avatars
- Change name of for table usernames to users and servernames table to servers

## Version 2.3.0 - Serveur Name - 18/10/2024

- Server name are now saved.

## Version 2.2.1 - Creation time - 05/10/2024

- Now retrieve the creation date of each profile.

## Version 2.2.0 - Split discord bot and web app - 05/10/2024

- Split the project into two separate parts for better modularity.
- The web version has its own changelog and starts at version 1.0.0

## Version 2.1.1 - Fix alltop command - 15/09/2024

- The display of seconds for the "alltop" command was incorrect

## Version 2.1.0 - Bot Page and More Stats! - 09/09/2024

- Added a new bot page on the website to display all bot statistics.
- Introduced new user count and profile count statistics.
- Made minor improvements to the website.
- Database stats (size and transactions)

## Version 2.0.0 - Database System and Username Display - 03/09/2024

- Migrated the database system to PostgreSQL.
- Implemented a TOP 25 leaderboard on the website with username display.
- Fixed the SPAM message issue.

## Version 1.2.0 - Web Interface - 18/08/2024

- Launched the website to view bot statistics.
- Added the `server` command to get server stats.
- Implemented a parallel processing system for the Discord bot and web.

## Version 1.1.0 - Cross-Server Stats - 20/06/2024

- Added the `allstats` command for cross-server statistics.
- Added the `top` command to get the top 10 users.
- Added the `alltop` command for cross-server top statistics.
- Added the `aide` command for help.
- Fixed message formatting issues in Hourglass responses.

## Version 1.0.0 - Initial Release - 28/04/2024

- Basic `stats` command for displaying user statistics.
