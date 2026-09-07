# Hourglass - Discord BOT - CHANGELOG

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
  - Configuration de l'URL de l'API via la variable d'environnement `HOURGLASS_API_URL` (défaut : `https://hourglass.mike-server.fr`).

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
