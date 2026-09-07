# Hourglass - WEB APP - CHANGELOG
 
## Version 2.5.4 - Cartes Statistiques & Commandes SVG dans l'API - 07/09/2026
### Features & API Enhancements
- **Cartes Statistiques & Classements au format SVG autonome** :
  - **Profil utilisateur sur un serveur (`!stats [user]`)** :
    - Route `/api/card/user/<user_identifier>/server/<server_id>` (alias `/api/card/stats/<user_identifier>/<server_id>`).
    - Génération d'une carte SVG 540x215 affichant l'avatar utilisateur, le nom et l'icône du serveur, le rang interne, le temps vocal, le volume de messages, le niveau et XP sur ce serveur avec jauge de progression, et la date d'ancienneté.
  - **Profil utilisateur global (`!allstats [user]`)** :
    - Route `/api/card/user/<user_identifier>` (alias `/api/card/allstats/<user_identifier>`).
    - Support transparent des identifiants numériques Discord (`user_id`) et des pseudonymes (`username`).
  - **Top 10 vocal d'un serveur (`!top`)** :
    - Route `/api/card/top/server/<server_id>` (alias `/api/card/server/<server_id>/top`).
    - Carte SVG 560x535 présentant le classement des 10 membres les plus actifs en vocal avec médailles or/argent/bronze, niveaux, temps vocal et messages.
  - **Top 10 vocal global (`!alltop`)** :
    - Route `/api/card/top` (alias `/api/card/top/global`, `/api/card/alltop`).
    - Classement général des 10 meilleurs utilisateurs du bot toutes guildes confondues au format SVG.
  - **Statistiques globales d'un serveur (`!server`)** :
    - Route `/api/card/server/<server_id>`.
    - Carte SVG 540x225 synthétisant l'activité de la guilde : heures vocales cumulées, total messages, membres répertoriés, rang du serveur, date de suivi et mise en avant du champion vocal du serveur.
  - **Tableau des commandes du bot (`!aide`)** :
    - Route `/api/card/commands` (alias `/api/card/help`, `/api/card/aide`).
    - Reproduction SVG fidèle 960x360 du tableau des commandes avec mise en valeur dorée du préfixe et des commandes, descriptions claires et support bilingue (`?lang=fr` / `?lang=en`).
- **Gestion des erreurs et intégration Discord optimisée** :
  - En cas d'identifiant introuvable (utilisateur ou serveur inexistant), l'API renvoie désormais une carte d'erreur SVG stylisée (statut 404) évitant l'affichage d'images brisées dans les embeds Discord.
  - En-tête HTTP `Cache-Control` calibré pour un rafraîchissement dynamique tout en soulageant la charge serveur.

## Version 2.5.3 - Épuration des Stats 30 Jours sur l'Accueil - 07/09/2026
### Improvements & Optimizations
- **Épuration de la Catégorie « Activité des 30 derniers jours » (`/`)** :
  - Suppression des cartes d'indicateurs superflues (« Membres actifs », « Profils actifs », « Serveurs actifs ») sur l'accueil pour alléger visuellement l'interface et concentrer l'attention sur les deux métriques d'activité reines : le temps passé en vocal (30j) et les messages envoyés (30j).
  - Nouvelle grille fluide 2 colonnes (`.home-stats-grid-2cols`) mettant en valeur ces deux cartes clés côte à côte sur écran large, et empilées proprement sur mobile.
- **Optimisation des performances SQL** :
  - Élimination des requêtes de décompte distinct lourd (`COUNT(DISTINCT ...)`) sur l'historique des 30 derniers jours, accélérant significativement le temps de chargement de la page d'accueil.
- **Incrémentation du cache statique (Cache Buster)** :
  - Passage à `v=24` pour `styles.css` dans `base.html`.

## Version 2.5.2 - UI Mobile, Stats 30 Jours & Icônes Vectorielles - 07/09/2026
### Features & Improvements
- **Nouvelle Catégorie « Activité des 30 derniers jours » sur l'Accueil (`/`)** :
  - Ajout d'une section dédiée à l'activité récente des 30 derniers jours avec 5 indicateurs clés : temps passé en vocal (30j), volume de messages (30j), membres actifs uniques (30j), profils actifs (30j) et serveurs actifs (30j).
  - Organisation claire et catégorisée du tableau de bord avec en-têtes de sections stylisés, icônes et badges distinctifs : *Activité des 30 derniers jours* (`30 derniers jours`), *Statistiques globales du bot* (`Depuis l'origine`), et *Télémétrie base de données & Stockage* (`Infrastructure`).
- **Sélecteur de Serveur Moderne sur le Top Utilisateurs (`/top/users`)** :
  - Remplacement de l'ancien `<select>` HTML par une barre de recherche fluide avec icône, bouton d'effacement rapide `✕`, et menu déroulant d'autocomplétion instantané affichant les avatars Discord réels des serveurs.
  - Option d'accès immédiat au classement global (`Tous les serveurs`) et bannière de filtre actif avec bouton de réinitialisation rapide.
  - Navigation complète au clavier (<kbd>↑</kbd><kbd>↓</kbd>, <kbd>↵</kbd>, <kbd>Échap</kbd>) et soumission automatique instantanée lors du choix.
- **Remplacement des emojis par des icônes vectorielles SVG** :
  - Harmonisation graphique complète avec les autres pages du site : suppression de tous les emojis bruts dans les en-têtes et les badges de catégories sur l'accueil (`/`) et dans le sélecteur de serveurs (`/top/users`) au profit d'icônes SVG vectorielles nettes et colorées (éclair ambre pour les 30 jours, globe cyan pour l'historique global, base de données violette pour l'infrastructure).

### Bug Fixes & Mobile Optimizations
- **Refonte Responsive de la Page Versus (`/versus`) sur Téléphone** :
  - **Arène en face-à-face côte à côte** : disposition en grille 2 colonnes (`grid-template-areas: "center center" "f1 f2"`) permettant de voir les deux combattants simultanément à l'écran sous le bandeau du vainqueur et le score, sans nécessiter 800px de défilement vertical.
  - **Alignement clair du comparatif de métriques** : affichage du titre de catégorie centré au-dessus de deux valeurs distinctes gauche (Joueur 1) et droite (Joueur 2) directement superposées à la jauge bicolore (suppression de l'empilement vertical confus sans distinction).
  - **Formulaire de recherche mobile** : passage en colonne avec bouton d'inversion des combattants pivoté à 90° (`⇅`), taille de police 16px sur les champs de saisie pour éliminer le zoom automatique intempestif sur Safari iOS, et masquage des touches clavier de bureau inutiles sur tactile.
  - **Graphique et conteneurs optimisés** : hauteur du graphique adaptée (260px), marges internes réduites pour éviter tout espace perdu ou défilement horizontal.
- **Correction du vide interne sous la barre de recherche sur téléphone (`/top/users`)** :
  - Élimination du `flex-basis: 240px` qui, en orientation colonne sur mobile, imposait une hauteur minimale artificielle de 240px au sélecteur de serveur et laissait un grand espace vide à l'intérieur du conteneur.
  - Réinitialisation propre à `flex: none` et `min-width: 0` sur mobile pour ajuster parfaitement le conteneur à sa hauteur réelle de contenu.
- **Incrémentation du cache statique (Cache Buster)** :
  - Passage à `v=23` pour `styles.css` dans `base.html` pour garantir la prise en compte immédiate sur tous les téléphones et navigateurs sans cache résiduel.

## Version 2.5.1 - Rafraîchissement du Cache & Assets - 06/09/2026
### Bug Fixes & Maintenance
- **Incrémentation du cache statique (Cache Buster)** :
  - Passage à `v=18` pour `styles.css` dans `base.html` afin d'éviter les problèmes de cache et de persistance sur les navigateurs des visiteurs, forçant le rechargement immédiat des nouveaux styles et composants sans manipulation manuelle.

## Version 2.5.0 - Mode Versus, Fix Crash Nouveaux Utilisateurs & UI Mobile - 06/09/2026
### Features & Improvements
- **Mode Versus (`/versus`)** :
  - Nouvelle page de confrontation en face-à-face pour comparer deux joueurs (`/versus?tab=users`) ou deux serveurs (`/versus?tab=servers`).
  - Arène graphique moderne : cartes combattants avec ruban de champion doré `🏆`, grand tableau d'affichage des scores central et jauges de duel bicolores animées pour chaque statistique (vocal, messages, niveau/XP, activité 30 jours, badges, rang).
  - Barres de recherche élégantes avec autocomplétion dynamique en direct (`/api/search`), affichage des vrais avatars Discord, badges de niveau, navigation complète au clavier (<kbd>↑</kbd><kbd>↓</kbd>, <kbd>↵</kbd>, <kbd>Échap</kbd>), bouton effacer `✕` et lancement automatique du duel.
  - **Filtre par serveurs en commun** : détection automatique des serveurs partagés entre 2 joueurs avec recalcul instantané des métriques, du rang interne, de la date d'arrivée, de l'activité 30 jours et de la courbe historique sur ce serveur spécifique.
  - Graphiques temporels superposés comparant l'évolution des deux entités sur la même échelle.
  - Bouton d'inversion rapide des combattants (`⇄`).
  - Bouton d'accès direct au mode Versus depuis les profils joueurs et serveurs.

### Bug Fixes & Mobile Optimizations
- **Correction du crash sur les profils utilisateurs (petit niveau / non classé)** :
  - Résolution de l'erreur 500 sur les profils de nouveaux joueurs ou à faible activité (`rank is None`, absence d'historique ou utilisateur non confirmé) avec fallback gracieux et affichage sécurisé.
- **Optimisations visuelles sur mobile (téléphone)** :
  - Correction du débordement du sélecteur de langue et du bouton Discord sur petit écran en mode portrait.
  - Adaptation responsive de l'arène de duel Versus et des barres de saisie.
- **Précision des graphiques historiques & ancienneté des serveurs** :
  - Les graphiques d'évolution temporelle débutent désormais à la date d'enregistrement réelle du profil ou du serveur (suppression des longues périodes plates inutiles depuis l'origine du bot).
  - Correction du calcul de date de suivi des serveurs où le bot n'a jamais été sollicité dans le chat (détection par l'utilisateur enregistré le plus ancien).

## Version 2.4 - Gamification & Modern UI - 05/09/2026
### Features & Improvements
- Added real-time Gamification engine: Level & XP system computed in memory without DB alterations
- Added 37 global badges with 100% SVG vector icons (zero emojis) and dynamic rarity styling
- Added "Niveau & XP" sorting to the Top leaderboard and level badges across all user lists
- Expanded Users and Servers directories pagination up to 100 items per page
- Automatic live filter updates across leaderboards (removed manual submit buttons)
- Cleaned and organized header navigation with Quick Search (Ctrl+K) and interactive live search dropdowns
- Upgraded number formatting with space separators for improved legibility

## Version 2.3.2 - Crash profile server - 25/01/2026
### Bug Fixes
- Patch for crash when click on server profile

## Version 2.3.1 - Cache Cache - 25/01/2026
### Bug Fixes
- Fixed cache update when new version of web app

## Version 2.3.0 - New Theme New Look ! - 25/01/2026
### Changes
- Updated overall UI theme and design with new info boxes and fresh icons (Blue theme!)
- Redesigned the home page for better usability
- Added pagination to Top, Users, and Servers pages for improved performance and clarity

### Minor changes
- Renamed “Docs” page to “Support” page
- Added a link to the Official Discord Server in the new Support page
- Redesigned user profile page
- Redesigned server profile page
- Server lists in user profiles are now sorted by date
- Added join date information on server and user pages
- Replaced unknown profile pictures with a dinosaur icon in preparation for incognito mode

## Version 2.2.1 - Fixes montly charts - 10/11/2025

### Bug Fixes
- Fixed month offset in the monthly charts

## Version 2.2.0 - Monthly Charts & Server Pie Charts - 10/11/2025

### New Features
- Added monthly charts based on hours
- Added server pie charts based on hours

### Minor changes
- Change some text on the home page
- Added version number to the web app footer

### Bug Fixes
- Fixed server profile picture dimensions and shape on the profile page

## Version 2.1.0 - API and Fixes - 28/08/2025

### New Features
- Added API for Hourglass (because why not?)
- Added 404 page error

### Bug Fixes
- Fixed crash when a non-existent username or server name is set on the profile page
- Updated descriptions on the home page and other pages
- Fixed typos
- Adjusted chart scales to be consistent with actual time intervals
- Fixed server avatar not loading on the server profile page
- Rounded activity values to show only one decimal
- Fixed miscalculation of activity values
- Improved top page responsiveness to display only one row per user (with hours and messages)
- Set the first date on charts to the bot's first day (28/04/2024)

## Version 2.0.0 - UI Rework - 21/08/2025

### Changes and Fixes

- Overall UI improvements
- Faster performance (Loading)
- New pages to search users and servers
- One chart to visualize key data
- New Top page with extended statistics

## Version 1.6.0 - Avatar Udpate and 2025 change - 15/01/2025

### Changes and Fixes

- Now display users and servers avatar on differents page
- Now you can click on server list in profile page
- Change about page for 2025
- Change footer page on every page

## Version 1.5.1 - Fix Activity and More Scroll - 29/12/2024

### Changes and Fixes 1.5.1

- Fixed an issue where activity values were incorrect.
- Added a scroll bar to the server page.
- Enabled the ability to click on a user in the server page to view their profile.

## Version 1.5.0 - Activity and Serveurs stats - 29/12/2024

### Revamped Home Page

- Displays the top 5 most active members, bot stats, and database stats.

### New Users Page

- Now displays a ranked list of all users.

### Enhanced Servers Page

- Includes more stats such as rankings and a complete list of users.

### Improved Profile Page

- Added more detailed stats, including:
  - Activity.
  - Global statistics.
  - A scrollable list of servers

## Version 1.4.0 - More Sizes and Time - 23/10/2024

- Provide more database size information
- display the timestamp for historical statistics

## Version 1.3.0 - Server Name - 18/10/2024

- Now display the server name instead of the server_id

## Version 1.2.0 - Web Box ! - 12/10/2024

- Changed the display of the top 25 with boxes. (and now its top30)
- Upgraded the user profile with box and rank information.
- Added a new servers page with boxes.
- Updated the about page with boxes.

## Version 1.1.0 - Profile Web - 05/10/2024

- Add new web interface profile (first version)
- Cleaning up some garbage

## Version 1.0.0 - Initial version after split - 05/10/2024

- First version since project split
