# Hourglass - WEB APP - CHANGELOG
 
## Version 3.17.2 - Admin : Recherche et Défilement des Longues Listes - 19/10/2026
### Admin
- **Toute liste ou tableau de plus de 8 éléments** a une hauteur limitée, défile dans sa carte et reçoit un **champ de recherche** :
  - le filtre ne tient compte ni des majuscules ni des accents ;
  - un compteur « trouvés / total » est affiché, et « Aucun résultat » quand rien ne correspond.
- **Listes plus complètes** :
  - sources : 50 au lieu de 10 ;
  - recherches : 100 au lieu de 20 ;
  - profils et serveurs consultés : 50 au lieu de 10 ;
  - dernières connexions : 100 au lieu de 20 ;
  - adresses 404 : 50 au lieu de 10 ;
  - serveurs et options des commandes : 50 au lieu de 10 ;
  - bannières, badges et records : tous au lieu des 9 ou 10 premiers.

## Version 3.17.1 - Chargement Plus Rapide de la Page Analyses - 19/10/2026
### Performances
- **Cache des Analyses partagé entre les workers Gunicorn**.
  - Chaque résultat est aussi écrit dans un fichier JSON du conteneur : dossier temporaire `hourglass-graphs`, modifiable avec `GRAPHS_CACHE_DIR`.
  - Avant, chacun des 4 workers avait son propre cache, vidé à chaque recyclage (`--max-requests`), et seule la clé par défaut (FR, Europe/Paris) était préchauffée. Un visiteur qui tombait sur un worker neuf, ou qui avait un autre fuseau horaire ou une autre langue, attendait le calcul complet.
  - Un worker sans résultat reprend celui d'un autre worker. Un fichier verrou fait qu'un seul worker à la fois recalcule une clé ; un verrou de plus de 2 minutes, laissé par un worker planté, est repris.
- **Données intégrées directement dans la page** quand elles sont déjà en cache : plus de second aller-retour vers `/api/graphs/data`, et les graphiques s'affichent dès le chargement des scripts.
- Sinon, la requête des données est **préchargée** (`<link rel="preload">`) : elle part avec la page au lieu d'attendre Chart.js et le script de la page.

## Version 3.17.0 - Fond Uni & Bannière Simplifiée - 19/10/2026
### Personnalisation
- **Fond de la page : couleur unie** au lieu de la galerie d'images.
  - 12 teintes sombres au choix (minuit, marine, indigo, violet, prune, bordeaux, rouille, olive, forêt, sarcelle, ardoise, noir), ou le fond par défaut du site.
  - Les teintes restent sombres pour garder le texte et les cartes lisibles. L'aperçu se met à jour en direct.
- **Bannière : Galerie ou Aucune**. L'option Discord est supprimée ; un profil qui utilisait la bannière Discord (ou l'ancien dégradé) affiche l'image de la galerie choisie, « Aurore » par défaut.
- Les 42 images de fond (≈ 1,8 Mo) sont retirées du site et du script `scripts/make_profile_gallery.py`.
- Admin, onglet Personnalisation : « Couleurs de fond » remplace « Fonds d'écran », et les types de bannière ne comptent plus que Galerie et Aucune.

### Base de données
- Nouvelle colonne `user_profile_settings.background_color`, ajoutée automatiquement au démarrage.
- Migration facultative `database/migrations/2026-10-19_web_v3.17.0_profile_background_color.sql` : elle ajoute la colonne, passe les anciens modes de bannière à `image` et vide `background_image`, qui n'est plus utilisée.

## Version 3.16.0 - Graphiques Plus Clairs & Personnalisation - 18/10/2026
### Analyses
- Onglets renommés : **« Évolution »** (ex-Tendances) et **« Horaires »** (ex-Rythme).
- Onglet Horaires : la **présence des membres** passe en haut.
- « Quand la communauté est active » devient **« Heures de pointe »** :
  - un seul indicateur à la fois, Vocal ou Messages, au lieu de deux courbes sur deux axes ;
  - en barres, le nombre moyen de membres en vocal (ou de messages) par heure, avec l'heure de pointe mise en évidence ;
  - la grille jour × heure suit l'indicateur choisi.

### Profils membre et serveur
- **Onglet Graphiques fusionné**, avec les mêmes règles que la page Analyses : un seul graphique d'évolution (Vocal / Messages, Par mois / 30 jours, Par période / Cumulé) remplace les quatre graphiques (heures et messages cumulés, puis par mois ou par jour).
- Profil membre :
  - le temps en vocal par **serveur** et par **salon** est réuni dans une seule carte, avec un graphique en anneau et un classement ;
  - le bloc « Affluence & Rythme horaire » est supprimé de l'onglet Activité, et retiré des blocs masquables.
- Fiche serveur :
  - le rythme horaire et la punchcard sont réunis en une carte **« Heures de pointe »**, comme sur la page Analyses ;
  - la grille jour × heure s'affiche aussi pour les petits serveurs ;
  - les salons vocaux et textuels sont réunis en une carte **« Salons les plus actifs »** (Vocal / Messages).
- Nouveau script commun `static/js/activity_charts.js` pour les deux profils.

### Personnalisation
- **20 couleurs de profil** au lieu de 10 : bleu, cyan, pourpre, fuchsia, corail, pêche, jaune, vert, menthe, argent.
- Bannière :
  - l'option **Dégradé est supprimée** ;
  - la **galerie** devient le choix par défaut, avec l'image « Aurore » ;
  - un ancien choix « dégradé », ou le mode Discord sans bannière Discord, affiche l'image de la galerie.
- Correction : cliquer sur une image de la galerie met de nouveau à jour l'aperçu en direct. L'image restait masquée après un premier échec de chargement.

### Admin
- Correction des **profils consultés en double** :
  - les vues sont enregistrées par membre (ID résolu), et non plus par l'adresse tapée (pseudo ou ID) ;
  - les anciennes lignes sont regroupées par profil à l'affichage.

## Version 3.15.0 - Admin : Onglet Commandes du Bot - 18/10/2026
### Nouveautés
- **Onglet « Commandes » de la page admin** (données du bot v3.1.0) : commandes par jour sur 30 jours, total, part en messages privés, taux d'erreur, commandes les plus utilisées, serveurs qui les utilisent le plus, options les plus choisies (type de classement, période…) et tableau des temps de réponse (moyenne, p95, erreurs) par commande. Message explicatif tant que le bot n'a encore rien enregistré.

## Version 3.14.0 - Page Admin & Mesure d'Audience Anonyme - 18/10/2026
### Nouveautés
- **Page `/admin`**, réservée aux IDs Discord listés dans la variable d'environnement `ADMIN_USER_IDS` (séparés par des virgules) ; pour tout autre visiteur, elle répond 404. Lien « Admin » dans le menu du compte, visible seulement des admins. Cinq onglets :
  - **Fréquentation** : pages vues et visiteurs uniques par jour (30 ou 90 jours), pages les plus vues, sources (Discord, Google, accès direct…), profils et fiches serveur les plus consultés, heures de visite, part mobile / ordinateur et FR / EN, recherches les plus tapées.
  - **Comptes** : comptes Discord liés au moins une fois (et part des membres suivis), nouveaux comptes par semaine, comptes actifs par jour / 7 jours / 30 jours, dernières connexions.
  - **Personnalisation** : profils personnalisés, couleurs, types de bannière, bannières et fonds les plus choisis, badges en vitrine, records épinglés, blocs masqués, profils privés.
  - **Bot & base** : serveurs (présents, quittés, actifs sur 30 jours, arrivées et départs par mois), membres suivis, vocal en cours, messages sur 24 h, bot en ligne ou silencieux (dernier relevé de présence), sessions vocales orphelines, taille de la base et des tables.
  - **Santé** : erreurs 404 / 429 / 500 par jour, adresses 404 les plus fréquentes, durée du dernier calcul de la page Analyses.

### Mesure d'audience
- **Anonyme et sans cookie** : un visiteur est une empreinte `sha256(clé du jour + IP + navigateur)` tronquée ; la clé change chaque jour, est partagée par les workers via la table `web_daily_salt` et supprimée le lendemain. Aucune IP n'est enregistrée, impossible de reconnaître quelqu'un d'un jour à l'autre. Empreintes effacées après 30 jours, statistiques agrégées après 400 jours.
- Robots (Discordbot, crawlers, aperçus de liens…), fichiers statiques, API, pré-chargements et pages admin ne sont pas comptés. Pour la recherche en direct, seul le terme final d'une saisie est retenu.
- **Aucune requête SQL par visite** : les compteurs sont gardés en mémoire et écrits en base toutes les 60 secondes par un thread de fond.
- Connexions Discord enregistrées (première et dernière connexion, nombre, jours d'activité en étant connecté). Les comptes déjà connus via les réglages de profil (depuis la v3.3.0) sont repris automatiquement.
- **Politique de confidentialité mise à jour** (mesure d'audience anonyme, données de connexion).

### Technique
- Nouvelles tables propres au site (`web_*`), créées automatiquement au démarrage : `database/migrations/2026-10-18_web_v3.14.0_admin_stats.sql` (facultative), également ajoutées à `schema_v3.sql`. Aucune table du bot n'est modifiée.
- L'IP du visiteur est lue par une fonction partagée `client_ip()` (limiteur de requêtes et mesure d'audience).

## Version 3.13.0 - Galerie Pop Culture : 24 Thèmes Animés & Jeux Vidéo - 18/10/2026
### Nouveautés
- **12 nouveaux thèmes inspirés des animés et des jeux vidéo**, disponibles à la fois en bannière et en fond d'écran : Ville néon (cyberpunk sous la pluie), Donjon pixel (RPG rétro éclairé aux torches), Arcade 8-bit (envahisseurs générés, vaisseau, lasers, effet écran cathodique), Grande vague (estampe japonaise), Ciel d'animé (coucher de soleil, cumulus, poteaux électriques), Sanctuaire (torii, lanternes, brume), Manga (lignes de vitesse et trame), HUD mecha (interface de cockpit), Forêt enchantée (champignons lumineux, lucioles), Plateformes rétro (jeu de plateformes 16 bits), Vaporwave (soleil tranché, damier, glitch) et Planète (géante gazeuse à anneaux).
- **12 de plus** : Hyperespace (saut en vitesse lumière), Pluie de code (glyphes verts inventés), Grotte de cristal, Monde de lave (volcan, coulées, lac incandescent), Nuit enneigée, Abysses (rayons, méduses, bulles), Lune de sang (château gothique, chauves-souris), Monde de blocs (paysage en cubes façon jeu bac à sable), Ruines du désert, Lo-fi pluie (fenêtre sous la pluie, ville floue), Galaxie et Orage.
- La galerie passe à **36 bannières** et **42 fonds d'écran** ; sur « Personnaliser mon profil », les sélecteurs défilent dans leur propre zone pour garder la page compacte.

### Technique
- Images entièrement originales générées par `scripts/make_profile_gallery.py` : aucun personnage, logo ni décor existant n'est reproduit (pas de droits à gérer). Les sprites de l'arcade sont générés aléatoirement. Galerie complète : environ 3,3 Mo, miniatures comprises.

## Version 3.12.0 - Onglet Badges Réorganisé par Familles - 18/10/2026
### Interface
- **Résumé en tête de l'onglet Badges** : « 28 / 37 badges débloqués · 76 % », barre de progression et décompte par rareté (Commun, Rare, Épique, Légendaire).
- **Badges rangés en 8 familles** (Vocal, Messages, Niveau, Classement, Serveurs, Fidélité, Activité du mois, Polyvalence), chacune affichée comme une échelle de paliers reliés, du plus facile au plus difficile, avec son compteur (« 6/7 ») et la mention « Complet » une fois terminée. Paliers débloqués à la couleur de leur rareté avec une coche, palier en cours en surbrillance avec sa mini-barre, paliers suivants grisés ; la description passe en info-bulle. Les grandes familles (5 paliers et plus) occupent toute la largeur, les petites vont par deux.
- **Filtre** Tous / Débloqués / À débloquer.
- **Valeurs lisibles** : un palier affiche seulement son seuil (« 500 h », « Niveau 30 », « Top 10 », « 50 h + 500 messages ») ; seul le palier en cours montre l'avancement (« 766,6 / 1 000 h », « #75 · objectif Top 50 »), au lieu de « 766,5 / 1,0 h » sur chaque carte.

## Version 3.11.1 - Page Analyses Instantanée - 18/10/2026
### Performance
- **Plus d'attente sur la page Analyses** : le cache sert toujours immédiatement le dernier résultat calculé ; quand il a plus de 5 minutes, il est recalculé en arrière-plan par un seul thread pendant que les visiteurs reçoivent la version précédente (au plus 6 h d'âge). Avant, le premier visiteur après chaque expiration attendait tout le calcul, et les autres attendaient derrière lui.
- **Cache préchauffé au démarrage** : chaque worker Gunicorn calcule les analyses (français, Europe/Paris) 2 secondes après son lancement ; le premier visiteur après un déploiement n'attend plus. Désactivable avec `GRAPHS_WARMUP=false`.
- **Un seul calcul à la fois par langue et fuseau** : plusieurs visiteurs arrivant sur un cache vide déclenchent un seul calcul ; un fuseau horaire peu courant ne bloque plus les autres (l'ancien verrou était global).
- **Totaux mensuels calculés une seule fois par requête** : les barres « par mois » et les courbes cumulées faisaient deux fois le même parcours complet des sessions vocales et des messages. Désormais partagés (aussi sur les profils, où les records les recalculaient une troisième fois, et sur les fiches serveur). Premier calcul de la page Analyses en local : 128 → 87 ms.
- Un recalcul de plus de 2 secondes est signalé dans les logs (`Analytics cache ... refreshed in ... ms`), pour repérer une base qui devient lente.

## Version 3.11.0 - Page Analyses Réorganisée - 18/10/2026
### Interface
- **3 onglets clairs au lieu de 4** : *Tendances*, *Rythme* et *Communauté* ; environ 6 graphiques au lieu de 12, sans perte d'information.
- **Tendances** : un seul graphique avec trois sélecteurs (Vocal / Messages, Par mois / 30 jours, Par période / Cumulé) remplace les 5 graphiques des anciens onglets Activité et Progression (heures et messages par mois, cumuls, activité quotidienne). Total et moyenne de la période affichés au-dessus ; la période en cours reste estompée.
- **Rythme** : la courbe des 24 heures et la grille jour × heure réunies dans une même carte « Quand la communauté est active », puis la **présence des membres sur 7 jours ou 48 h** (sélecteur, 7 jours par défaut ; une date par jour sous l'axe ; la courbe « Hors ligne », qui écrasait les autres, est masquée par défaut et réapparaît d'un clic sur la légende ; le taux moyen de connectés de la période reste affiché en pastille).
- **Communauté** : les nouveaux membres par mois, puis deux classements compacts côte à côte (serveurs et membres les plus actifs, Vocal / Messages) avec liens vers les fiches et vers les pages Serveurs et Membres. Ils remplacent les deux camemberts illisibles et le grand graphique du top 10.
- **Cartes du haut centrées sur les 30 derniers jours** (vocal, messages, membres actifs, serveurs actifs) avec l'évolution en % par rapport aux 30 jours précédents, au lieu de totaux déjà présents sur l'accueil.
- Mobile : cartes en 2 × 2, onglets sur toute la largeur, sélecteurs et grille jour × heure adaptés.

### Corrections
- **Fin des fausses données de présence** : quand l'historique était vide ou avait un trou de plus de 2 heures (bot hors ligne), le site inventait des valeurs à partir des chiffres actuels et les **enregistrait en base**, où elles passaient ensuite pour de vraies mesures. Les périodes sans relevé restent désormais vides, et le graphique affiche « Pas de données de présence sur cette période ». Les valeurs déjà inventées par le passé restent en base.

### Technique
- Données de la page regroupées par onglet dans `/api/graphs/data` (toujours mises en cache 5 minutes) ; séries vocal et messages alignées mois par mois côté serveur. La présence réutilise les 7 jours d'instantanés que le bot conserve déjà (un toutes les 15 minutes, regroupés par heure). Un graphique peut désormais garder ses propres graduations (`ticks.autoSkip: false`) au lieu des 8 imposées aux séries longues par `charts.js`. Le script de la page passe d'environ 1 500 à 330 lignes et l'adaptateur de dates de Chart.js n'est plus chargé.

## Version 3.10.0 - Onglet Accueil & Galerie de Fonds d'Écran Élargie - 18/10/2026
### Interface
- **Retour de l'onglet « Accueil »** en première position dans la barre de navigation (le logo mène toujours aussi à l'accueil).

### Nouveautés
- **18 fonds d'écran de profil au lieu de 8** : 6 nouveaux dessinés pour le format plein écran (voie lactée, hexagones lumineux, forêt de nuit, bokeh, vagues de lignes, grille de points) et 4 thèmes de bannière déclinés en fond (synthwave, crépuscule, sakura, braises).
- **Fonds plein écran légèrement floutés** (flou de 6 px appliqué en CSS, débordant un peu de l'écran pour éviter un liseré sombre sur les bords) : l'image reste reconnaissable sans concurrencer le contenu. Même rendu dans l'aperçu de « Personnaliser mon profil ».

### Technique
- `scripts/make_profile_gallery.py` accepte une liste de thèmes à régénérer (`python scripts/make_profile_gallery.py app/static/images/profile forest,flow`) ; les bannières existantes sont inchangées. La galerie de fonds pèse environ 600 Ko au total, miniatures comprises.

## Version 3.9.0 - Galerie d'Images : Bannières & Fonds d'Écran de Profil - 17/10/2026
### Nouveautés
- **Galerie de 12 bannières** au choix pour l'en-tête du profil : aurore boréale, nébuleuse, synthwave, crépuscule en montagne, océan de nuit, low poly, topographie, ville en pixel art, sakura, braises, circuit et dunes. Nouveau choix « Galerie » à côté de Discord, Dégradé et Aucune.
- **Fond d'écran du profil** : 8 images (nébuleuse, aurore, topographie, circuit, ville pixel, dunes, océan, low poly) affichées derrière toute la page, assombries vers le bas pour garder le contenu lisible. Visible par tous les visiteurs du profil.
- Sélection par miniatures dans l'onglet *Apparence* de « Personnaliser mon profil » ; l'aperçu montre la bannière et le fond d'écran en direct.

### Technique
- Images originales générées par `scripts/make_profile_gallery.py` (Pillow + numpy, aucune image tierce donc aucun droit à gérer), en WebP : environ 760 Ko pour toute la galerie, avec des miniatures de 2 à 7 Ko pour le sélecteur. Servies par le site lui-même (compatible avec la CSP) et en cache 7 jours.
- Pas d'envoi d'image par les membres : seules les clés de la galerie sont acceptées (rien à modérer ni à stocker).
- Deux colonnes ajoutées à `user_profile_settings` (`banner_image`, `background_image`) : `database/migrations/2026-10-17_web_v3.9.0_profile_images.sql`. Le site les ajoute lui-même au démarrage si elles manquent.
- Type MIME `image/webp` déclaré explicitement (certains systèmes servaient les WebP en `application/octet-stream`).

## Version 3.8.0 - Vitrine du Profil & Retour de l'Accueil d'Origine - 17/10/2026
### Nouveautés
- **Bloc « Vitrine » sur le profil**, juste sous l'en-tête : il regroupe tout ce que le membre choisit lui-même (badges mis en avant, serveur favori, records). Un cadre à sa couleur la distingue du reste de la page. Le propriétaire a un lien « Modifier ma vitrine ».
- Le serveur favori y gagne une vraie carte (icône, rang sur le serveur et nombre de membres, temps vocal).
- Page de personnalisation : l'onglet « Mise en avant » devient **« Vitrine »**, et l'aperçu montre la vitrine, mise à jour en direct.

### Retraits
- **« Mon espace » est retiré de l'accueil** : tout le monde retrouve la bannière d'accueil d'origine (présentation, invitation du bot, classements), connecté ou non.
- La vitrine de badges et le serveur favori quittent le pied de l'en-tête, et les records ne sont plus sous les totaux : tout est dans la vitrine.

## Version 3.7.0 - Page de Personnalisation Simplifiée - 17/10/2026
### Interface
- **« Personnaliser mon profil » refaite en trois onglets** : *Apparence* (couleur, bannière), *Mise en avant* (serveur favori, vitrine de badges, records) et *Confidentialité* (profil privé, blocs visibles). Une ligne par réglage avec un titre et une phrase d'explication courte, au lieu de six grands blocs empilés. L'onglet ouvert est conservé après l'enregistrement.
- **Contrôles plus compacts** : bannière en sélecteur à 3 choix, badges en pastilles colorées selon la rareté (liste défilante), records en liste à cocher avec leur valeur, visibilité en interrupteurs regroupés (en-tête et résumé, onglet Activité, autres onglets).
- **Barre d'enregistrement fixe** avec l'indication « Modifications non enregistrées », et confirmation du navigateur si on quitte la page sans enregistrer.
- L'aperçu reprend désormais exactement l'en-tête du profil (niveau, serveur favori, vitrine).

### Retraits
- Le choix de l'ordre des sections de l'onglet Activité est supprimé : l'ordre est fixe (séries, calendrier, rythme horaire, compagnons). Un ordre déjà enregistré est ignoré.
- Le lien « Personnaliser mon profil » est retiré du menu du compte (en haut à droite). La page reste accessible depuis le bouton « Personnaliser » de son profil et depuis « Mon espace ».

## Version 3.6.0 - Réorganisation de la Page de Profil - 17/10/2026
### Interface
- **En-tête du profil restructuré** en trois zones : identité (avatar, pseudo, titre, date d'arrivée et ID sur une seule ligne discrète, statut vocal en direct) avec les boutons « Personnaliser » et « Duel / Versus » alignés à droite ; barre de niveau et d'XP intégrée à l'en-tête ; pied d'en-tête avec le serveur favori à gauche et la vitrine de badges à droite.
- **Fin des doublons** : le rang global et le niveau n'apparaissent plus à la fois en pastilles et en cartes, et la carte de niveau séparée disparaît (elle est dans l'en-tête).
- **Séries et assiduité** (onglet Activité) : les 4 grandes cartes deviennent un bandeau compact, pour éviter trois rangées de cartes d'affilée.
- Records par défaut sans doublon avec ce bandeau : plus longue session, meilleur mois en vocal, meilleur mois en messages, meilleur compagnon vocal (la meilleure journée reste dans le bandeau des séries).
- **Mobile** : totaux en grille 2 × 2 compacte, informations d'identité empilées sans séparateurs orphelins, pastille de statut accrochée à l'avatar, pourcentage d'XP sur une seule ligne.

## Version 3.5.0 - Mise en Page du Profil & Mode Privé - 17/10/2026
### Nouveautés
- **Ordre de l'onglet Activité** : le membre réordonne les sections séries et assiduité, calendrier d'activité, rythme horaire et compagnons vocaux (boutons monter / descendre, utilisables au clavier). Le journal des sessions reste en dernier.
- **Visibilité par bloc** : vitrine de badges, records épinglés, chacune des quatre sections de l'onglet Activité et les onglets Graphiques, Serveurs fréquentés et Badges peuvent être masqués aux visiteurs. Le propriétaire voit toujours tous ses blocs, marqués « Masqué aux visiteurs ».
- **Profil privé** : les visiteurs ne voient plus que l'en-tête, le niveau et les totaux, avec un message indiquant que le membre garde ses statistiques détaillées privées. Le membre reste visible dans les classements, les comparaisons Versus et les fiches serveur (précisé sur la page de personnalisation).

### Sécurité & confidentialité
- Un bloc masqué n'est pas envoyé au visiteur, données comprises : les séries JSON des graphiques et du rythme horaire ne sont plus incluses dans la page quand l'onglet ou la section est masqué.
- Un lien vers un onglet masqué (`#tab-charts`…) ouvre simplement l'onglet Activité au lieu d'afficher une page vide.

### Interface
- Sur téléphone, les 3 badges de la vitrine s'affichent côte à côte en tuiles compactes.

## Version 3.4.0 - Vitrine de Badges & Records Épinglés - 17/10/2026
### Nouveautés
- **Vitrine de badges** en bas de l'en-tête du profil : le membre choisit jusqu'à 3 badges débloqués à mettre en avant (couleur selon la rareté, description au survol). Sans choix, ses 3 badges les plus rares s'affichent automatiquement ; un badge perdu (par exemple un rang du podium) disparaît de la vitrine.
- **Records épinglés** au-dessus des onglets du profil : jusqu'à 4 records parmi plus longue session, meilleure journée, plus longue série, meilleur mois en vocal, meilleur mois en messages, serveur principal, meilleur compagnon vocal, heure de pointe et jours actifs sur un an. Par défaut : plus longue session, meilleur mois en vocal, meilleure journée et meilleur compagnon vocal. Un record sans données n'est pas affiché.
- Sur « Personnaliser mon profil » : sélection des badges (les plus rares en premier) et des records sous forme de cartes, avec compteur et limite ; la vitrine se met à jour dans l'aperçu en direct.

### Technique
- Les records réutilisent les données déjà en cache du profil (calendrier, compagnons, rythme horaire) ; seuls la plus longue session et les meilleurs mois ajoutent des requêtes, elles aussi mises en cache 2 minutes. Les sessions d'archive (instantanés quotidiens) sont exclues de la plus longue session.

## Version 3.3.0 - Personnalisation du Profil : Couleur, Bannière & Serveur Favori - 17/10/2026
### Nouveautés
- **Page « Personnaliser mon profil »** (`/me/profile`), accessible depuis le menu du compte, « Mon espace » et un bouton « Personnaliser » visible uniquement par le propriétaire sur son profil. Aperçu en direct avant d'enregistrer ; formulaire protégé par jeton CSRF et limité à 60 requêtes/min.
- **Couleur du profil** : 10 teintes adaptées au thème sombre, ou la couleur du profil Discord du membre (éclaircie automatiquement si elle est trop sombre pour rester lisible). Elle colore la bannière, le contour de l'avatar, la carte de niveau et la barre d'XP, les onglets, le calendrier d'activité et les courbes de temps vocal du profil.
- **Bannière en haut du profil** : bannière Discord du membre (récupérée à la connexion), dégradé de sa couleur, ou aucune bannière (en-tête compact d'avant). Une bannière Discord expirée laisse simplement place au dégradé.
- **Serveur favori** mis en avant sous le pseudo, avec le rang et le temps vocal du membre sur ce serveur (seuls les serveurs où il a de l'activité peuvent être choisis).

### Technique
- Nouvelle table `user_profile_settings`, utilisée uniquement par le site : `database/migrations/2026-10-17_web_v3.3.0_profile_settings.sql` (également ajoutée à `schema_v3.sql`). Le site la crée lui-même au démarrage si elle manque, et affiche le profil par défaut si elle est inaccessible.
- Les réglages sont lus à chaque visite (une requête par clé primaire) : un changement est visible immédiatement, malgré le cache de 2 minutes des graphiques.

## Version 3.2.0 - Performances : Pool de Connexions, Caches, Index & Gunicorn Multi-threads - 17/10/2026
### Performance
- **Pool de connexions PostgreSQL** (`PooledPostgresqlDatabase`, 8 connexions max par worker, recyclées après 5 min d'inactivité) : plus d'ouverture/fermeture de connexion à chaque requête, et la session est créée directement en UTC (une requête `SET TIME ZONE` en moins par page). L'API de recherche passe d'environ 35 ms à 4 ms en local.
- **Cache des classements (60 s)** : `/members` et `/servers` ne recalculent plus tout le classement à chaque visite, frappe de la recherche en direct ou changement de page ; recherche, tri et pagination se font en mémoire (≈ 50 ms → 5 ms, 1 à 2 requêtes SQL au lieu de 4 à 6).
- **Cache des blocs publics des profils et fiches serveur (2 min)** : graphiques, calendrier d'activité, compagnons vocaux et punchcard (≈ 70-80 ms → 17-19 ms, 48 → 20 requêtes SQL). Les données dépendant du visiteur (journal des sessions, statuts de présence) restent recalculées à chaque visite et ne sont jamais mises en cache.
- **Index composites** `(user_id, joined_at)`, `(server_id, joined_at)` sur `voice_sessions` et `(user_id, created_at)`, `(server_id, created_at)` sur `message_events` pour les calculs « 24 h / 7 jours / période » par membre ou serveur. Migration sans coupure : `database/migrations/2026-10-17_web_v3.2.0_indexes.sql` (`CREATE INDEX CONCURRENTLY`), également ajoutée à `schema_v3.sql`.
- **Gunicorn multi-threads** : 4 workers × 4 threads (`gthread`) au lieu de 4 workers synchrones ; une requête lente ne bloque plus un worker entier. Recyclage des workers toutes les ~2000 requêtes.

### Corrections
- `/members?server_id=<texte>` et `?period=<inconnu>` provoquaient une erreur 500 ; les valeurs invalides retombent désormais sur « tous les serveurs » / « toujours ».

## Version 3.1.0 - Politique de Sécurité du Contenu, En-têtes HTTP & Limite de Débit - 17/10/2026
### Sécurité
- **Content-Security-Policy stricte** sur toutes les pages : scripts autorisés uniquement depuis le site, `cdn.jsdelivr.net` (Chart.js) et les trois scripts en ligne restants via un **nonce unique par requête** ; images limitées au site et au CDN Discord ; `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`, `upgrade-insecure-requests` en HTTPS. Un code injecté (script ou attribut `onerror`) est bloqué par le navigateur même si une faille XSS apparaissait. Mode test possible via `CSP_REPORT_ONLY=true`.
- **En-têtes de sécurité** : `X-Frame-Options: DENY` (anti-clickjacking), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (caméra, micro, géolocalisation, paiement désactivés).
- **Limite de débit par adresse IP** (fenêtre glissante d'une minute) : cartes SVG `/api/card/*` 30/min, recherche `/api/search` 90/min, reste de l'API 120/min, authentification 30/min, fiches serveur et chargement des membres 120/min. Réponse `429` avec `Retry-After`. L'IP du visiteur est lue dans `X-Real-IP` / `X-Forwarded-For` posés par le reverse proxy (limitation désactivée avec un avertissement si le proxy ne les transmet pas).
- **Déconnexion protégée (POST + jeton CSRF)** : un simple lien ou une image `/auth/logout` sur un site tiers ne déconnecte plus les visiteurs. Retour à la page d'origine uniquement si elle appartient au site.

## Version 3.0.1 - Correctifs de Sécurité (XSS, Redirection Ouverte, Cookie) - 17/10/2026
### Sécurité
- **XSS stockée dans la recherche (gravité élevée)** : la recherche globale (Ctrl+K), les suggestions du filtre serveur et de la page Versus inséraient noms de serveurs et pseudos sans échappement dans la page ; un nom de serveur contenant du HTML pouvait exécuter du code chez toute personne le voyant en résultat. Toutes les valeurs externes passent désormais par `HG.esc()`.
- **XSS via les données de graphiques** : les blocs JSON des profils, fiches serveur, accueil et Versus (`json.dumps(...)|safe`) ne neutralisaient pas `</script>` ; un nom de serveur, de salon ou un pseudo pouvait refermer le bloc et injecter du code. Nouveau filtre `safe_json` (échappement de `<`, `>`, `&`, U+2028/2029 en séquences `\u`, JSON identique une fois lu).
- **Redirection ouverte après connexion (gravité moyenne)** : le paramètre `next` acceptait `/\site-externe`, interprété comme `//site-externe` par les navigateurs. Seuls les chemins internes sont désormais acceptés (barres obliques inverses, caractères de contrôle, schémas et domaines rejetés).
- **Cookie de session `Secure`** : envoyé uniquement en HTTPS (désactivable en local via `SESSION_COOKIE_SECURE=false`).
- **Fuseau horaire dans le SQL** : la valeur du cookie `user_tz` n'atteint plus les requêtes que si elle figure dans la liste officielle des fuseaux IANA (liste blanche stricte via `sql_timezone()`), au lieu d'un simple nettoyage de caractères.

## Version 3.0.0 - Réorganisation du Site : Navigation à Plat, Pages Membres & Serveurs, Mon Espace - 17/10/2026
### Navigation
- **Barre du haut sans menus déroulants** : `Membres · Serveurs · Analyses · Versus`, recherche (Ctrl+K) et compte. Le logo mène à l'accueil ; « Support » devient « Aide & commandes » dans le pied de page.
- **Fin des niveaux de navigation empilés** : les pastilles de section et les onglets Utilisateurs/Serveurs en haut des listes sont supprimés (jusqu'à 4 niveaux avant les résultats auparavant).

### Pages Membres & Serveurs (fusion annuaire + classement)
- **`/members`** remplace `/top/users` et `/users` : une seule liste, classée par heures en vocal par défaut, avec tri par messages, XP ou **nom (A–Z)**, **recherche par pseudo en direct**, filtres de période et de serveur. Les membres sans activité suivie apparaissent en fin de classement.
- **`/servers`** remplace `/top/servers` et l'ancien annuaire : même principe (tri vocal / messages / A–Z, recherche, période) ; les serveurs que le bot a quittés restent listés avec un badge « Non suivi ».
- En tri alphabétique, les numéros de rang sont masqués (ils n'ont pas de sens dans cet ordre).
- **Redirections permanentes (301)** de `/users`, `/top/users` et `/top/servers` vers les nouvelles pages, filtres conservés (`/users` conserve l'ordre alphabétique) : liens partagés et référencement préservés.
- **Correctif lien du bot** : `hourglassbot.net/top`, envoyé par la commande Discord `/top` (« View full leaderboard on website »), menait à une page 404 ; il redirige désormais vers `/members`, y compris pour les messages déjà postés.

### Mon espace (accueil, membre connecté)
- Pour un membre connecté connu du bot, le bandeau d'accueil devient un résumé personnel : niveau, titre, rang et progression d'XP, activité des dernières 24 h et 7 jours, série en cours, XP total, raccourcis « Mon profil » / « Me comparer » et **ses serveurs suivis par Hourglass** (d'après la connexion Discord) avec son temps sur chacun.
- Visiteurs anonymes et comptes inconnus du bot : accueil inchangé.

### Technique
- Routes : `top.top_users` → `/members`, `top.top_servers` → `/servers` ; module `routes/servers.py` et templates `users.html` / `servers.html` supprimés, `routes/users.py` réduit à la redirection.
- Nouveau partiel `partials/my_space.html`.

## Version 2.12.0 - Scripts & Styles Extraits des Templates (Mise en Cache Navigateur) - 17/10/2026
### Performance & Maintenance
- **≈ 175 Ko de JavaScript sortis des templates** vers des fichiers statiques mis en cache par le navigateur (7 jours, invalidés automatiquement à chaque modification) : `js/base.js` (navigation, recherche globale, connexion Discord : chargé sur toutes les pages), `js/pages/graphs.js` (71 Ko), `user_profile.js`, `server_profile.js`, `versus.js`, `top_users.js`, `home.js`. Les pages HTML s'allègent d'autant à chaque visite.
- **Valeurs Jinja transmises par un bloc JSON** (`#hgBaseConfig`, `#hgPageConfig`, `#topServerDataset`) rendu avec `|tojson` au lieu d'être injectées dans le code : échappement correct des traductions contenant des apostrophes ou guillemets.
- **Feuilles de style par page** (`css/pages/graphs.css`, `user_profile.css`, `server_profile.css`) à la place des blocs `<style>`, chargées au même endroit (ordre de priorité CSS inchangé).
- Le script d'en-tête (fuseau horaire, remplacement des images cassées) reste en ligne volontairement pour s'exécuter avant le reste de la page.

### Corrections
- **Avatar par défaut de la recherche globale** : l'API renvoyait un fichier inexistant (`default_avatar.png`, erreur 404) pour les comptes sans avatar.

## Version 2.11.1 - Infobulles Instantanées, Zéro Gestionnaire Inline & Scripts Différés - 17/10/2026
### UX
- **Infobulles instantanées partout** (`data-tip`) : punchcards (fiche serveur et `/graphs`), pastilles de statut, temps exact des membres, statut du bot et totaux de l'accueil. Affichage immédiat au survol, au focus clavier et au toucher sur mobile (les infobulles natives `title` étaient lentes et inaccessibles au doigt). Valeurs formatées selon la langue.

### Technique & Performance
- **Plus aucun gestionnaire d'événement dans le HTML** (56 `onclick` / `onmouseover` / `onmouseout` / `onerror` supprimés) :
  - Clics : attribut `data-call` + écouteur délégué unique (`static/js/ui.js`).
  - Survols : effets en CSS `:hover` (cases du punchcard, lignes du journal des sessions, bouton de connexion Discord).
  - Images cassées : un seul gestionnaire global dans `<head>` bascule sur l'avatar par défaut ou sur `data-fallback` (icône serveur, masquage).
  - Ouvre la voie à une politique de sécurité de contenu (CSP) stricte.
- **Scripts différés (`defer`)** : Chart.js, son adaptateur de dates et les helpers ne bloquent plus l'affichage de la page.
- L'infobulle spécifique du calendrier d'activité est remplacée par le système global.

## Version 2.11.0 - Filtres & Recherches en Direct sans Rechargement - 17/10/2026
### UX
- **Classements (`/top/users`, `/top/servers`) mis à jour sur place** : changer la période, le tri, le serveur ou la page ne recharge plus toute la page ; seuls les résultats sont remplacés (indicateur de chargement discret). L'URL suit les filtres (liens partageables) et le bouton Retour du navigateur restaure l'état précédent.
- **Correctif double envoi** : les listes déroulantes de filtres envoyaient le formulaire deux fois (attribut `onchange` + écouteur JS).
- **Recherche en direct dans les annuaires (`/users`, `/servers`)** : la grille se filtre pendant la frappe (après 300 ms de pause), le champ garde le focus, la croix d'effacement apparaît dès qu'il y a du texte. La liste de suggestions, devenue redondante avec la grille filtrée, est retirée.
- **Recherche des membres d'un serveur en direct** : la liste et le compteur de membres se mettent à jour sans recharger la fiche (les graphiques restent en place) ; « Voir plus » continue de fonctionner sur les résultats filtrés.

### Technique
- Nouveau module partagé `static/js/live-list.js` (régions `data-live-region`, formulaires `data-live-form`, champs `data-live-search`). Sans JavaScript ou en cas d'erreur réseau, les formulaires et liens fonctionnent comme avant (navigation classique).

## Version 2.10.1 - Pagination Moderne des Classements & Annuaires - 17/10/2026
### UX
- **Nouvelle pagination partagée** (`/top/users`, `/top/servers`, `/users`, `/servers`) remplaçant « Précédent · Page X sur Y · Suivant » :
  - Numéros de page cliquables avec première et dernière page toujours visibles et ellipses (`1 … 4 5 6 … 37`).
  - Flèches précédent / suivant fixes (grisées aux extrémités).
  - Champ « Aller à » pour sauter directement à une page (listes de plus de 7 pages).
  - Raccourcis clavier ← / → pour changer de page (inactifs pendant la saisie et dans la recherche globale).
  - Tous les filtres actifs (période, tri, serveur, recherche) sont conservés dans les liens.
  - Version compacte sur mobile (pages éloignées masquées), `aria-current` et libellés accessibles.
- Les numéros de page invalides ou hors limites sont ramenés à la page la plus proche.

## Version 2.10.0 - Liste des Membres Paginée & Calendrier d'Activité Fiable - 17/10/2026
### Performance
- **Fiche serveur : membres chargés par tranches de 50** : seuls les 50 premiers membres du classement sont rendus avec la page (≈ 580 Ko → ≈ 230 Ko de HTML sur un serveur de 135 membres) ; un bouton « Voir plus (N restants) » ajoute les suivants sans recharger via `GET /server/<id>/members?offset=…` (recherche `q` conservée). Sans JavaScript, le bouton reste un lien vers la liste complète (`?all=1`).
- Les statuts de présence des membres restent réservés aux membres du serveur, y compris dans les tranches chargées à la demande.

### Corrections
- **« Journée record » et calendrier d'activité réalistes** : les relevés d'archive couvrant plusieurs jours (relevés mensuels de l'ancienne routine) étaient imputés en bloc à leur premier jour, produisant des journées de plus de 300 h. Ils n'ont pas de détail par jour et sont désormais exclus du calendrier, de la journée record et des séries (ils restent comptés dans les totaux, les graphiques mensuels et l'XP).
- **Sessions à cheval sur minuit** : le temps vocal en direct est découpé entre les deux jours selon le temps réellement passé, et chaque journée est plafonnée à 24 h.
- **Formats localisés** : date de la journée record (« 3 sept 2026 » au lieu de « 2026-09-03 ») et pourcentages (progression d'XP, assiduité) suivent la langue du site.

## Version 2.9.1 - Favicon Visible, Accessibilité & Formatage des Nombres - 17/10/2026
### Identité visuelle
- **Favicon sur pastille ronde `#5865F2`** : le logo pixel-art d'origine (21×21, inchangé pixel pour pixel) est désormais posé sur un disque bleu Discord. Il ne disparaît plus sur les onglets clairs, les résultats Google et les favoris.
- **Jeu d'icônes complet** : `favicon.svg` (vectoriel, net à toute densité), `favicon-32.png` (pixels d'origine en 1:1), `favicon.ico` multi-tailles 16/32/48 servi à la racine `/favicon.ico` (exigé par Google), `apple-touch-icon.png` (180 px) et icônes 192/512 px avec `site.webmanifest`. Agrandissements en multiples entiers sans lissage pour garder les pixels nets.
- **Aperçus de liens** : l'image Open Graph par défaut passe à l'icône 512 px (au lieu du logo blanc de 21 px).
- Script de régénération : `web/scripts/make_favicons.py`.

### Accessibilité & SEO
- **Navigation au clavier visible** : contour bleu ciel (`:focus-visible`) sur les liens et boutons lors de la navigation à la touche Tab ; aucun changement au clic souris.
- **Contraste du texte secondaire** : le gris `#64748b` (≈ 3,5:1, sous le seuil WCAG AA) passe à `#8b9bb0` (≈ 5,8:1) pour les sous-titres, légendes et dates.
- **Titres `<h1>`** sur les profils, fiches serveur, annuaires, support et page 404 (même rendu visuel), et titre `<h1>` masqué visuellement sur `/graphs` et les classements pour les moteurs de recherche et lecteurs d'écran.

### Corrections
- **Nombres formatés selon la langue partout** : le filtre historique `thousands_fr` suit désormais la langue (`1 826,8 h` / `1,826.8 h`), ce qui corrige les classements, l'accueil et les listes ; heures des salons, compagnons vocaux, serveurs fréquentés et moyennes également formatées.
- **Recherche globale (`Ctrl+K`)** : le champ prend le focus immédiatement à l'ouverture, les premières lettres d'une frappe rapide ne sont plus perdues.

## Version 2.9.0 - Refonte de la Lisibilité des Graphiques & Calendrier d'Activité - 17/10/2026
### Graphiques
- **Séries denses allégées** : sur les courbes de 30 jours, les séries de plus de 30 mois et les graphiques sur 24 h, l'axe horizontal n'affiche plus qu'environ 8 libellés à l'horizontale (au lieu de toutes les dates inclinées à 45°), et les points n'apparaissent qu'au survol. Appliqué automatiquement à toutes les pages via un plugin Chart.js partagé (`hgDenseSeries`).
- **Accueil : barres + courbe au lieu de deux courbes superposées** : les heures en vocal sont des barres (axe gauche « Heures »), les messages une courbe (axe droit « Messages ») ; les axes sont titrés et colorés, l'infobulle affiche les deux valeurs formatées.
- **Formatage des nombres unifié** : légendes de moyenne, pourcentages des donuts et cartes de stats des profils/serveurs suivent la langue du site (`1 826,8 h` en français, `1,826.8 h` en anglais). Nouveau filtre Jinja `num` et helper JS `HG.fmt`, au rendu identique.

### Calendrier d'activité (profil)
- **Grille alignée sur les jours de la semaine** : chaque colonne est désormais une semaine commençant le lundi (la grille démarrait auparavant sur un jour quelconque, les lignes ne correspondaient à aucun jour précis).
- **Repères de lecture** : noms des mois au-dessus des colonnes et jours de la semaine (Lun / Mer / Ven) sur le côté.
- **Infobulle instantanée et stylée** au survol d'une case : « 12 oct. 2026 : 3,2 h · 45 messages » (ou « aucune activité »).

## Version 2.8.9 - Cache des Analyses, Avatars Allégés & Aperçus de Liens Discord - 17/10/2026
### Performance
- **Cache de 5 minutes sur les analyses globales (`GET /api/graphs/data`)** :
  - Les ~30 requêtes SQL de la page `/graphs` ne sont plus exécutées qu'une fois toutes les 5 minutes par worker (clé : langue + fuseau horaire). Réponse ~150 ms → ~30 ms.
- **Avatars Discord servis en 256 px au lieu de 1024 px** :
  - Réécriture automatique des URL `cdn.discordapp.com` dans les pages HTML et l'API JSON (recherche Ctrl+K), soit ~16x moins de pixels téléchargés sur `/users`, `/server/<id>` et les classements.
  - Chargement différé natif (`loading="lazy"`) sur les images Discord.
- **Cache navigateur des fichiers statiques (7 jours)** : `styles.css` et `charts.js` sont versionnés automatiquement d'après leur date de modification (`?v=<horodatage>`), plus besoin d'incrémenter `v=30` à la main.
- **Chart.js épinglé (`4.5.1`) et adaptateur date-fns (`3.0.0`)** : une future version majeure publiée sur le CDN ne peut plus casser les graphiques en production.

### Graphiques
- **États vides explicites** : sur les fiches serveur et les profils, le graphique d'affluence horaire et le punchcard affichent « Pas encore assez d'activité » au lieu d'une courbe plate ou d'une grille vide ; les pastilles « Pic vocal / Pic messages : - » sont masquées dans ce cas.
- **Période en cours signalée** : le mois en cours (barres mensuelles) et la journée en cours (courbes journalières) sont estompés ou en pointillés, avec la mention « Mois en cours : données partielles » / « Aujourd'hui : journée en cours » dans l'infobulle, au lieu de ressembler à une chute d'activité.
- **Grilles de cartes équilibrées** : 4 cartes en 4 colonnes (2×2 sur écran moyen) sur les profils et serveurs, 5 cartes en 5 colonnes (3 + 2 élargies) sur `/graphs` : plus de carte isolée seule sur sa ligne.
- Nouveau fichier partagé `static/js/charts.js` (helpers Chart.js communs à toutes les pages).

### UX & Partage
- **Aperçus de liens enrichis (Open Graph)** : les liens partagés sur Discord affichent un titre, une description et une image. Les profils montrent l'avatar, le niveau, les heures en vocal, les messages et les badges ; les serveurs affichent leurs totaux.
- **Balise `meta description`** sur toutes les pages (référencement).
- **Mobile** : les onglets « Joueur vs Joueur / Serveur vs Serveur » et des classements ne provoquent plus de défilement horizontal sur petits écrans.
- **Traduction** : « SERVERS ACTIFS » / « Servers connectés » → « SERVEURS ACTIFS » / « Serveurs connectés » sur l'accueil.

### Technique
- Prise en compte de `X-Forwarded-Proto` derrière le reverse proxy (`ProxyFix`) pour générer des URL absolues en `https`.

## Version 2.8.8 - Durcissement Sécurité des Sessions & OAuth2 - 16/10/2026
### Sécurité
- **Suppression de la clé secrète Flask codée en dur** :
  - La clé de signature des cookies n'a plus de valeur par défaut publiée dans le dépôt (qui permettait de forger une session et d'usurper un compte).
  - Ordre de résolution : `SECRET_KEY` / `FLASK_SECRET_KEY`, sinon clé dérivée de `DISCORD_CLIENT_SECRET`, sinon clé aléatoire persistée dans `web/.flask_secret_key` (partagée entre les workers Gunicorn).
- **Vérification stricte du paramètre `state` OAuth2 (`POST /auth/token-login`)** :
  - Le `state` est désormais obligatoire et comparé en temps constant ; l'omettre ne permet plus de contourner la protection CSRF du flux implicite.
- **Mode debug Flask désactivé par défaut** dans `run.py` (activable via `FLASK_DEBUG=true` en local).

### Performance
- **Fiche serveur (`/server/<id>`) : 187 → 49 requêtes SQL** (323 → 51 pour un membre connecté) :
  - Statuts de présence des membres récupérés en une seule requête au lieu d'une par membre.
  - La liste des membres n'est plus rechargée une seconde fois pour le graphique « Top 10 membres ».
  - `load_users_from_server` ne charge plus les présences par défaut (le comparateur `/versus` n'en a pas besoin).

## Version 2.8.7 - Persistance des Sessions, Confidentialité Présence & Compteurs Serveur Publics - 12/10/2026
### Sécurité & Confidentialité
- **Confidentialité Renforcée du Statut Discord Individuel (`/profile/<user>`)** :
  - La pastille de présence Discord (en ligne, absent, ne pas déranger, hors-ligne) et l'indicateur d'activité vocale en direct sont désormais strictement masqués pour les visiteurs sans serveur commun.
  - Le statut d'un utilisateur n'est visible que s'il s'agit de son propre profil ou si le visiteur connecté partage au moins un serveur Discord en commun avec lui.
- **Compteurs de Présence Serveur Agrégés et Publics (`/server/<id>`)** :
  - Les statistiques globales du serveur (en ligne, absent, ne pas déranger, hors-ligne/invisible et en vocal) sont désormais accessibles à tous les visiteurs sans restriction de rôle ou d'appartenance.
  - Optimisation SQL de l'agrégation directe par statut garantissant des temps de réponse instantanés sans surcharge mémoire.

### Authentification & Sessions
- **Durabilité & Persistance Étendue des Sessions (60 jours)** :
  - Élimination des déconnexions intempestives forçant à se reconnecter constamment via Discord OAuth2.
  - Configuration de cookies de session permanents (`PERMANENT_SESSION_LIFETIME = timedelta(days=60)` avec `SameSite="Lax"` et `HttpOnly=True`).
  - Maintien transparent de la session à travers la fermeture du navigateur et des onglets.

## Version 2.8.6 - Chargement Asynchrone des Analyses & Spinners de Chargement - 10/10/2026
### Performance & UX
- **Navigation Instantanée & Rendu Asynchrone (`/graphs`)** :
  - Élimination complète du délai d'attente de 2 secondes à l'ouverture de la page d'analyses.
  - Séparation du rendu HTML initial (< 75 ms) et du traitement analytique SQL via le nouvel endpoint d'API dédié `GET /api/graphs/data`.
- **Spinners de Chargement Circulaires & Placeholders Shimmer** :
  - Intégration d'indicateurs de chargement circulaires bicolores animés (`.chart-spinner-ring`) dans chaque conteneur de graphique et sur la matrice punchcard horaire.
  - Affichage d'effets skeleton shimmer discrets sur les cartes récapitulatives KPI pendant la récupération en arrière-plan.
  - Transition fluide en fondu (fade-out) des indicateurs de chargement dès la réception et le tracé des graphiques.

## Version 2.8.5 - Optimisation Performance Graphiques & Lazy-Loading par Onglet - 10/10/2026
### Performance & UX
- **Lazy-Loading des Graphiques par Onglet (`/graphs`)** :
  - Découpage de l'initialisation des 11 graphiques Chart.js en modules dédiés par onglet (`tab-activity`, `tab-history`, `tab-servers`, `tab-community`).
  - Au chargement initial de la page, seuls les graphiques de l'onglet actif (*Activité*) sont instanciés et tracés.
  - Les 7 autres graphiques des onglets masqués (*Historique*, *Serveurs*, *Communauté*) ne sont construits et animés qu'à la demande lors du clic sur leur onglet respectif.
  - Suppression totale du blocage du fil d'exécution JavaScript (Main Thread) du navigateur, assurant un rendu instantané et un défilement ultra-fluide à 60/120 FPS.

## Version 2.8.4 - Correctif JavaScript Recherche Globale (Ctrl+K) & Navbar - 09/10/2026
### Bug Fixes
- **Restauration de la Recherche Globale et du Raccourci Clavier (`Ctrl+K`)** :
  - Correction d'une accolade fermante manquante dans l'écouteur `DOMContentLoaded` de `base.html`.
  - Rétablissement complet de la modal de recherche globale, de la navigation par touches fléchées et de la recherche dynamique en direct.

## Version 2.8.3 - Calibration Client ID Bot Officiel & Déconnexion Globale Sécurisée - 09/10/2026
### Features & Sécurité
- **Calibrage du Client ID Officiel Discord (`1210665993328926750`)** :
  - Harmonisation du client ID OAuth2 sur le bot officiel Hourglass pour correspondre exactement aux redirections configurées dans le portail développeur Discord.
  - Résolution définitive du blocage `redirect_uri OAuth2 non valide` lors des flux d'autorisation.
- **Déconnexion Globale Forcée & Purge des Sessions Obsolètes** :
  - Rotation de la clé secrète Flask (`SECRET_KEY`) pour révoquer cryptographiquement tous les anciens cookies de session.
  - Ajout d'un hook `before_request` de réinitialisation automatique purgeant toute session sans versionnage strict (`2.8.3`).

## Version 2.8.2 - Connexion Pop-up Discord OAuth2 & Simplification du Portail - 08/10/2026
### Features & UX
- **Authentification Discord OAuth2 en Pop-up Non-Intrusive** :
  - Ouverture d'une fenêtre pop-up centrée (500x750) lors du clic sur "Se connecter", évitant toute rupture de navigation sur la page en cours.
  - Détection automatique de la validation Discord, transmission du signal `DISCORD_AUTH_SUCCESS` via `postMessage`, fermeture automatique de la pop-up et rafraîchissement transparent de la page mère.
  - Normalisation intelligente des URI de redirection (`127.0.0.1` vers `localhost`, détection automatique de la production `https://hourglassbot.net/auth/callback`).
- **Simplification Radicale du Portail de Connexion (`/login`)** :
  - Suppression intégrale des formulaires manuels d'ID/pseudo et des longs blocs descriptifs.
  - Carte minimaliste épurée (440px) centrée sur l'action essentielle : bouton officiel `[ Se connecter avec Discord ]`.
  - Mention sobre de conformité Discord OAuth2.

## Version 2.8.1 - Page de Connexion par Identifiant Discord & Calibrage Navbar - 08/10/2026
### Features & Fixes
- **Page de Connexion Unifiée & Professionnelle (`/login` & `/auth/login`)** :
  - Création d'une page de connexion dédiée (`login.html`) aux couleurs d'Hourglass en dark glassmorphism.
  - Connexion directe par identifiant Discord (ID Snowflake à 18-19 chiffres ou pseudo Discord) avec récupération instantanée du profil, de l'avatar et des serveurs associés depuis la base de données.
  - Suppression définitive du mode `dev-login` et redirection transparente de toutes les anciennes routes vers la page de connexion unifiée.
  - Prise en charge optionnelle du bouton "Continuer avec Discord" via OAuth2.
- **Calibrage et Résolution du Débordement Navbar** :
  - Fixation de la hauteur de la pastille utilisateur (`.auth-user-btn`) à 34px avec centrage vertical parfait.
  - Troncature automatique des pseudos longs (`max-width: 85px` avec points de suspension `...`) pour garantir qu'aucun élément ne dépasse de la capsule de la barre de navigation.
  - Redesign du bouton "Inviter" avec icône robot vectorielle et style verre cyan distinctif.

## Version 2.8.0 - Confidentialité Avancée, Authentification Discord OAuth2 & Contrôle d'Accès - 08/10/2026
### Features & Sécurité
- **Authentification Discord OAuth2 (`web/app/auth.py`)** :
  - Intégration de la connexion officielle Discord OAuth2 (scopes `identify guilds`).
  - Menu utilisateur dans la barre de navigation avec avatar, pseudo, lien vers mon profil et bouton de déconnexion.
  - Mode développement local (`/auth/dev-login`) permettant de simuler n'importe quel compte ou ID Discord en un clic pour tester les permissions sans clés OAuth2 configurées en local.
- **Confidentialité Stricte des Sessions Vocales Utilisateur (`/profile/<username>`)** :
  - L'historique détaillé des sessions vocales individuelles est réservé exclusivement au propriétaire du profil connecté.
  - Les visiteurs anonymes et les tiers voient un encart élégant de confidentialité avec invitation à se connecter via Discord.
  - Aucune fuite de données de session dans le DOM ou les requêtes SQL pour les tiers non autorisés.
- **Protection des Sessions et des Présences en Direct sur les Serveurs (`/server/<id>`)** :
  - L'accès au journal des sessions vocales d'un serveur et à la barre de statut des membres (En ligne / Absent / DND / En vocal) est strictement réservé aux utilisateurs connectés et membres avérés du serveur.
  - Double vérification de présence : via les serveurs Discord OAuth2 et par recoupement avec les tables d'activité en base de données.
  - Masquage automatique des pastilles de statut et d'activité vocale sur les membres pour les visiteurs non autorisés.

## Version 2.7.7 - Moyenne Journalière sur le Rythme Horaire & Lissage Linéaire Pré-Routine - 07/10/2026
### Features & Fixes
- **Moyenne Journalière par Tranche Horaire (Option B)** :
  - Transformation des volumes cumulés du graphique de distribution horaire 24h (`get_hourly_activity_distribution`) en moyennes quotidiennes réelles (`heures/jour` et `messages/jour`).
  - Division par le nombre de jours d'activité distincts sur chaque type d'événement, garantissant qu'un utilisateur ne dépasse jamais 1.0 h/jour par créneau horaire.
  - Mise à jour cohérente des unités, infobulles et axes de `user_profile.html`, `server_profile.html` et `graphs.html` (FR et EN).
- **Interpolation Linéaire Pré-Routine (Courbes de Progression)** :
  - Implémentation de `interpolate_pre_routine_progression` pour les membres / serveurs actifs avant l'introduction de la routine de snapshot quotidien (12 octobre 2024).
  - Suppression du plateau artificiel à 0 et de la falaise verticale d'octobre 2024 grâce à une transition linéaire proportionnelle entre la date d'arrivée et le 1er novembre 2024.

## Version 2.7.6 - Correctifs de Sécurité Dependabot & Automatisation Dynamique du Footer - 07/10/2026
### Sécurité & Fixes
- **Résolution des Vulnérabilités de Dépendances (Dependabot)** :
  - Verrouillage de `Werkzeug==3.1.9` dans `requirements.txt` pour éliminer les failles de sécurité Windows device names / traversal (GHSA-29vq-49wr-vm6x).
  - Synchronisation de l'ensemble des modules Python sans aucune vulnérabilité résiduelle.
- **Affichage Dynamique et Garanti de la Version en Pied de Page (`translations.py`)** :
  - Intégration d'un résolveur direct dans `get_text('footer.version')` garantissant la synchronisation immédiate avec `APP_VERSION` et `APP_VERSION_DATE` du CHANGELOG.
 
## Version 2.7.5 - Tooltips Cumulatifs Enrichis & Sélecteur de Granularité Globale 30j/Mois - 07/10/2026
### Features & Améliorations
- **Tooltips Intelligents avec Deltas Relatifs sur les Courbes Cumulées** :
  - Enrichissement des tooltips Chart.js sur toutes les courbes d'évolution cumulées (heures et messages).
  - Calcul et affichage en temps réel du delta exact par rapport au point précédent (ex: `178 369 messages (+29 500 ce mois)` ou `(+1 200 ce jour)`).
  - Déploiement homogène sur la page d'analyse globale (`/graphs`), les profils utilisateurs (`/profile/<user>`) et les profils de serveurs (`/server/<id>`).
- **Sélecteur de Granularité sur les Graphiques Globaux (`/graphs`)** :
  - Ajout du groupe de boutons interactif `[Mois par mois]` / `[30 derniers jours]` dans l'onglet Évolution globale de `/graphs`.
  - Intégration côté backend des progressions journalières sur 30 jours (`get_daily_hours_progression` et `get_daily_messages_progression`).
  - Commutation dynamique en JavaScript (sans aucun rechargement de page) avec conservation des tooltips adaptatifs (`ce mois` en vue mensuelle vs `ce jour` en vue quotidienne).

## Version 2.7.4 - Correctif Décalage Mensuel des Courbes Cumulées & Élimination du Pic Nocturne Hérité - 07/10/2026
### Fixes & Améliorations
- **Alignement Chronologique des Courbes Cumulées Mensuelles (`functions.py`)** :
  - Correction du décalage de 1 mois dans `get_first_of_month_messages_sum` et `get_first_of_month_hours_sum`.
  - La valeur cumulée au 1er de chaque mois est désormais enregistrée *avant* l'incrémentation du volume d'activité de ce mois (les messages/heures d'un mois s'affichent désormais fidèlement entre le 1er du mois et le 1er du mois suivant).
  - Parfaite cohérence rétablie entre la courbe d'évolution cumulée, le delta sur 30 jours (ex: `+31 179 sur 30j`) et l'histogramme d'activité mensuelle.
  - Ajout systématique du point au 1er du mois en cours (`YYYY-MM-01`) pour une continuité parfaite jusqu'à la date du jour (`today`).
  - Nettoyage du point de départ originel du bot (`2024-04-28`) sur les graphiques globaux afin de supprimer tout point fictif antérieur.
- **Élimination du Faux Pic Nocturne à 04h/05h (`functions.py`)** :
  - Application du filtre strict `is_legacy == False` sur les requêtes horaires de `MessageEvents` dans `get_hourly_activity_distribution` (distribution 24h) et `get_hourly_punchcard_data` (matrice 7j × 24h).
  - Les lots historiques migrés n'impactent plus les tranches nocturnes des profils utilisateurs, serveurs et globaux.
- **Audit Exhaustif des Visualisations Graphiques** :
  - Vérification de l'ensemble des requêtes analytiques (progressions quotidiennes sur 30 jours, deltas journaliers/mensuels, heatmap GitHub annuelle, timeline 48h, diagrammes circulaires) : toutes confirmées synchrones et fidèles aux données brutes.
 
## Version 2.7.3 - Correctif Crash Session Vocale Active sur le Profil Utilisateur - 05/10/2026
### Fixes
- **Sessions Vocales en Direct & Profils Utilisateurs (`functions.py`)** :
  - Résolution d'un crash critique (Erreur 500 / `NameError`) lors de la consultation du profil d'un membre actuellement connecté dans un salon vocal.
  - Récupération et résolution correctes du nom de serveur (`server_name` via `Servers.servername`) dans `get_user_active_voice`.
  - Sécurisation du typage booléen pour les statuts caméra et partage d'écran en direct.
 
## Version 2.7.2 - Découpage Horaire Proportionnel des Sessions Vocales & KPI d'Assiduité - 05/10/2026
### Fixes & Améliorations
- **Découpage Horaire Proportionnel des Sessions Vocales (`functions.py`)** :
  - Découpage heure par heure via une CTE récursive (`generate_series`) pour la distribution des pics d'activité sur 24h (`get_hourly_activity_distribution`).
  - Élimination des faux pics d'activité : une session vocale chevauchant plusieurs tranches horaires (ex: 21h06 à 23h50) distribue désormais fidèlement ses minutes sur chaque heure active au lieu d'attribuer toute la durée à l'heure de début.
  - Uniformisation du découpage horaire sur les profils utilisateurs (`user_id`), les pages de serveurs (`server_id`) et les graphiques globaux.
- **Découpage Multi-Jours & Multi-Heures de la Matrice Punchcard (`get_hourly_punchcard_data`)** :
  - Décomposition proportionnelle des sessions vocales à travers les jours et les heures de la semaine (matrice 7j × 24h).
- **Refonte des Cartes KPI d'Assiduité du Profil Utilisateur (`user_profile.html`)** :
  - Harmonisation complète des 4 cartes d'assiduité (Série actuelle, Meilleure série, Jours actifs, Assiduité globale) avec le design moderne du Dashboard principal (`dashboard-kpi-grid`).
  - Ajout des bordures d'accentuation supérieures lumineuses (orange, ambre, émeraude, bleu), des icônes d'en-tête dédiées et des badges d'état pills.
- **Épuration de l'Interface Utilisateur** :
  - Retrait du bouton et de la modale superflus « Exporter ma carte de profil » sur le profil web.
 
## Version 2.7.1 - Détection Fuseau Horaire Visiteur, Gestion Été/Hiver & Standardisation UTC - 05/10/2026
### Fixes & Améliorations
- **Détection Automatique du Fuseau Horaire Visiteur (`base.html` & `functions.py`)** :
  - Détection client transparente via `Intl.DateTimeFormat().resolvedOptions().timeZone` et enregistrement dans un cookie `user_tz`.
  - Prise en charge automatique multi-pays (Canada, Japon, France, etc.) et fallback par défaut sur `Europe/Paris`.
- **Gestion Automatique du Changement d'Heure Été / Hiver (`zoneinfo.ZoneInfo`)** :
  - Prise en charge native des transitions solstice / équinoxe (DST : UTC+2 en été, UTC+1 en hiver en France) via la base IANA Python 3.9+.
- **Standardisation UTC Globale de la Base de Données (`database.py` & `database.go`)** :
  - Forçage strict de `SET TIME ZONE 'UTC'` sur chaque connexion au pool PostgreSQL tant pour le bot Go que pour l'application Flask.
  - Résolution définitive du décalage de 2 heures constaté sur les heures de début de sessions vocales.
- **Localisation des Horodatages & Graphiques** :
  - Conversion et affichage localisé des sessions vocales récentes (`joined_at_str` et sessions actives).
  - Graphique de présence 48h, distribution horaire des pics d'activité (24h), punchcard 7j×24h et heatmap GitHub alignés sur l'heure locale de chaque visiteur.

## Version 2.7.0 - Modernisation du Dashboard, Navigation Épurée & Hub Communautaire - 05/10/2026
### Features & Améliorations
- **Refonte Complète de la Navigation (`base.html`)** :
  - Consolidation des 7 liens plats en 4 piliers modernes et épurés : *Accueil*, *Statistiques* (menu déroulant), *Communauté* (menu déroulant), et *Support*.
  - Menus déroulants ergonomiques avec icônes, descriptions, pont de survol invisible (`::before`) et buffer anti-décrochage pour une navigation fluide sur desktop et mobile.
- **Nouveau Dashboard d'Accueil (`home.html`)** :
  - Hero d'accueil avec boutons d'actions parfaitement alignés et cadrés (Invitation Discord et Exploration des classements).
  - 4 cartes KPI globales parfaitement symétriques (Temps vocal total, Messages, Utilisateurs uniques, Servers actifs) avec bordures supérieures lumineuses et pilules d'état colorées.
  - Graphique d'activité dynamique sur 30 jours (Chart.js) comparant le rythme vocal et textuel.
  - Podiums Top 3 pour les membres et les serveurs avec médailles or, argent et bronze.
  - Allègement de l'accueil : suppression des requêtes et de la barre de télémétrie de base de données.
- **Hub de Navigation Croisée (`hub-nav-bar`)** :
  - Barre de pilules interactive sur `/servers`, `/users`, `/top/servers` et `/top/users` permettant de basculer instantanément entre annuaires, classements vocal/messages et l'outil Versus.

## Version 2.6.1 - Correctif Connectés vs Hors-ligne 48h & Épuration Liste Serveurs - 04/10/2026
### Fixes & Améliorations
- **Graphique 48h Connectés vs Hors-ligne (`/graphs`)** :
  - Intégration d'un algorithme de backfill et lissage transparent pour combler automatiquement les heures sans données ou lors d'un redémarrage.
  - Regroupement horaire éliminant tout doublon d'étiquette temporelle sur l'axe X.
  - Calcul et affichage fidèle du ratio moyen de membres connectés.
- **Liste des Serveurs (`servers.html`)** :
  - Suppression de la mention erronée de date d'activité ainsi que de la pastille « Bot actif » pour un affichage minimaliste, rapide et épuré.
- **Statut en Direct** :
  - Retrait de l'émoji micro dans la pastille « En direct » pour un design sobre et uniforme.

## Version 2.6.0 - Analytics Granulaires, Sessions Vocales en Direct, Compagnons Vocaux & Cartes Vectorielles - 04/10/2026
### Features & Architecture
- **Analytics Granulaires & Sessions Vocales (`voice_sessions` & `channels`)** :
  - Suivi détaillé des sessions vocales avec horodatage d'arrivée (`joined_at`), de départ (`left_at`), durée réelle en secondes et détection de streaming/caméra.
  - Heatmap annuelle et mensuelle d'activité style GitHub (`user_profile.html`).
  - Punchcard horaire 7j/7 et 24h/24 pour l'analyse des habitudes d'activité vocale.
  - Compagnons vocaux fréquents : identification des membres partageant le plus de temps en salon vocal avec calcul précis du temps passé ensemble.
  - Journal complet des sessions vocales récentes avec statuts en direct (`LIVE`), terminées ou historiques (`LEGACY`).
  - Graphique de répartition du temps par salon vocal (`userFavoriteChannelsChart`).
- **Refonte et Simplification de la Navigation par Onglets** :
  - **Profil Utilisateur** : Réorganisation claire en onglets thématiques (*Activité*, *Graphiques*, *Serveurs fréquentés*, *Badges*). Déplacement du journal des sessions à la fin de l'onglet Activité. Suppression de tous les badges numériques superflus sur les onglets.
  - **Profil Serveur** : Réorganisation en 3 onglets limpides (*Activité*, *Graphiques*, *Membres*) avec suppression de tous les numéros parasites.
  - **Graphiques Globaux** : Suppression de l'onglet redondant « Tous les graphiques », simplification du titre en « Activité », suppression des badges numériques.
- **Identité Visuelle & Cartes de Statistiques Vectorielles** :
  - Remplacement total des émojis par des icônes vectorielles SVG (Feather/Lucide) sur toutes les pages et visualisations.
  - Cartes générées avec liens en anglais (`/profile/<id>`, `/server/<id>`) pour une cohérence globale.
  - Mise à niveau vers Bot v3.0.0 (Go Edition) et Dashboard v2.6.0.
- **Conformité & RGPD** :
  - Mise à jour complète de la politique de confidentialité (`/privacy`) et des CGU (`/terms`) au 04/10/2026 détaillant le suivi de sessions tout en garantissant l'absence totale de captation audio, vidéo ou contenu textuel.

## Version 2.5.10 - Granularité Dynamique des Graphiques & Gestion des Homonymes - 22/09/2026
### Features & Architecture
- **Granularité Temporelle des Graphiques (`/server` et `/profile`)** :
  - Ajout d'un sélecteur de granularité interactif : `Mois par mois` vs `30 derniers jours (par jour)`.
  - Détection et sélection automatique par défaut pour les nouveaux profils et serveurs avec peu de recul historique (< 3 points mensuels) afin d'offrir une courbe riche jour par jour plutôt qu'une ligne bipoint.
  - Bascule dynamique et instantanée sans rechargement de page pour l'ensemble des 4 graphiques d'activité (heures cumulées, messages cumulés, heures par période, messages par période) avec mise à jour automatique des moyennes et des libellés.
- **Gestion Robuste des Homonymes & Résolution par ID Discord (`/profile`)** :
  - Support natif et prioritaire du `user_id` Snowflake Discord dans les routes de profil : `/profile/<user_id>`.
  - Mise à jour de l'ensemble des liens internes du site (classements `/top`, liste `/users`, fiche serveur `/server/<id>`, recherche Ctrl+K, duels Versus) pour pointer directement vers le `user_id` unique, éliminant tout risque de conflit ou de mélange de statistiques entre utilisateurs portant le même pseudo.
  - Page de désambiguïsation propre (`user_disambiguation.html`) lorsqu'un utilisateur accède manuellement à un pseudo partagé par plusieurs comptes (ex: `/profile/Kiro`), permettant de sélectionner le bon compte avec badges, dates d'arrivée et statistiques distinctes.
  - Affichage épuré du profil utilisateur avec badge discret d'identifiant Discord (`ID : <user_id>`), sans message d'avertissement perturbateur.
- **Maintenance & Versioning** :
  - Actualisation du pied de page du tableau de bord : `version 2.5.10 - 22/09/2026` (FR / EN).
  - Mise à jour du badge de version de la carte d'aide SVG (`/api/card/help`) : `v2.5.10 • SLASH ACTIVE` / `v2.5.10 • SLASH ACTIF`.
  - Synchronisation de la documentation technique (`API.md` et `README.md`).

## Version 2.5.9 - Refonte Visuelle des Graphiques & Épuration des Libellés - 21/09/2026
### UI & Visual Enhancements
- **Épuration des graphiques analytiques (`/graphs#tab-community`)** :
  - Suppression de toutes les explications et notes entre parenthèses dans les titres, sous-titres, axes, légendes et boutons (`Vocal`, `Messages`, `Combiné`, `Logarithmique`, `Linéaire`).
  - Remplacement intégral des emojis par des icônes vectorielles SVG intégrées (Feather/Lucide) adaptées au thème sombre.
  - Épuration des libellés du Top 10 des membres et des profils comportementaux de la matrice de corrélation.
- **Sécurité & Dépendances (`requirements.txt`)** :
  - Résolution intégrale des alertes de vulnérabilités (CVE-2025-66221, CVE-2026-27199, CVE-2026-21860, CVE-2026-28684, CVE-2026-27205).
  - Retrait de `Werkzeug` direct dans `requirements.txt` (délégué automatiquement aux versions validées de Flask).
  - Actualisation de l'ensemble des paquets vers leurs dernières versions PyPI : `Flask==3.1.3`, `python-dotenv==1.2.3`, `peewee==4.5.1`, `psycopg2==2.9.13`, `click==8.5.0`, `MarkupSafe==3.0.3`.

## Version 2.5.8 - Test des Workflows & Déploiement CI/CD - 21/09/2026
### Maintenance & CI/CD
- **Incrémentation de version pour validation des workflows** :
  - Déclenchement et validation des pipelines automatisés de tests, de build Docker et de déploiement continu (CI/CD workflows).
  - Actualisation de la version du pied de page du tableau de bord : `version 2.5.8 - 21/09/2026` (FR / EN).
  - Mise à jour du badge de version dans la carte d'aide vectorielle SVG (`/api/card/help`) : `v2.5.8 • SLASH ACTIVE` / `v2.5.8 • SLASH ACTIF`.
  - Documentation de l'API (`API.md`) et guide du projet (`README.md`) synchronisés en v2.5.8.

## Version 2.5.7 - Conformité RGPD, Nouvelles Pages Légales & Alias Discord - 15/09/2026
### Features & Legal Compliance
- **Conformité RGPD & Respect de la Vie Privée** :
  - Création de la page dédiée `/privacy` (et `/confidentialite`) bilingue (Français & Anglais) détaillant la politique de confidentialité, la minimisation des données (compteurs d'activité, pseudonymes, avatars et identifiants Discord publics sans stockage de contenus de messages ni de flux vocaux), la finalité légitime de gamification et la procédure d'exercice des droits (accès, rectification, suppression).
  - Identification explicite de l'organisme responsable du traitement des données : **SnoutLabs**.
- **Conditions Générales d'Utilisation (CGU / Terms of Service)** :
  - Création de la page dédiée `/terms` (et `/cgu`) bilingue définissant les règles d'utilisation, l'interdiction de fraude ou saturation d'API, le respect des *Discord Developer Terms of Service* et les limites de responsabilité.
- **Support des Alias d'URL Recommandés par Discord Developer Portal** :
  - Ajout des alias de routes normalisés pour une intégration optimale avec le portail développeur Discord et la certification de bots :
    - `/terms-of-service` et `/terms-of-services` servant les CGU.
    - `/privacy-policy` servant la politique de confidentialité.
    - Conservation des URLs canoniques et francophones (`/terms`, `/privacy`, `/cgu`, `/confidentialite`).
- **Transition de Marque & Domaine Officiel** :
  - Migration complète de l'ensemble des références vers le nouveau nom de domaine officiel : `hourglassbot.net`.
  - Suppression intégrale des anciennes mentions de marque Mike Server dans le code, la documentation et les templates.
  - Mise en avant exclusive de **SnoutLabs** dans le pied de page (`footer.powered_by`) et les mentions légales.
- **Pied de Page (Footer) Enrichi** :
  - Ajout de liens de navigation rapides vers la Politique de confidentialité, les Conditions d'utilisation et le serveur Discord d'assistance et de gestion des données.
  - Actualisation de la version affichée : `version 2.5.7 - 15/09/2026`.
- **Cartes SVG & API** :
  - Actualisation du badge de statut sur la carte `/help` à `v2.5.7 • SLASH ACTIVE` / `v2.5.7 • SLASH ACTIF`.
  - Mise à jour du nom de domaine officiel dans le footer des cartes SVG vers `hourglassbot.net`.
  - Documentation de l'API (`API.md`) actualisée en v2.5.7.

## Version 2.5.6 - Correctif Crash Profil, Optimisations Mobile Versus & Prévention Débordements Cartes SVG - 08/09/2026
### Bug Fixes & Responsive Optimizations
- **Correctif Crash Serveur Profil Utilisateur (`/profile/<username>`)** :
  - Résolution de l'exception Flask `BuildError: Could not build url for endpoint 'api.get_user_stat_card' with values ['lang', 'username']` causée par le renommage du paramètre de route en `<user_identifier>`.
  - Restauration de la signature d'endpoint standard `username: str` sur les routes `/api/card/user/<username>` et `/api/card/user/<username>/server/<int:server_id>`.
  - Maintien de la flexibilité de recherche transparente : la fonction `_resolve_user` continue d'accepter aussi bien un pseudonyme (`username`) qu'un ID numérique Discord (`user_id`).
- **Optimisation Mobile Avancée de la Page Versus (`/versus`)** :
  - **Correction du débordement en grille CSS (Blowout)** : ajout de `min-width: 0;` sur `.versus-fighter-card` et d'une troncature avec ellipse (`text-overflow: ellipsis; white-space: nowrap;`) sur les pseudonymes des combattants, empêchant l'élargissement indésirable de la page au-delà de 100vw sur mobile.
  - **Panneau de duel central affiné** : stylisation du pilier central (`.versus-center-pillar`) en panneau vitré compact (`background: rgba(255, 255, 255, 0.025); border-radius: 14px;`) avec espacements optimisés pour une intégration fluide entre les cartes de combattants.
  - **Repères colorés des métriques de duel** : ajout d'indicateurs visuels bleu ciel (`#93c5fd` - Joueur 1) et rose (`#fda4af` - Joueur 2) sur les valeurs numériques de chaque métrique.
  - **Support ultra-mobile (écrans <= 480px)** : masquage automatique du total de membres dans le badge de rang (`.rank-total`) pour éviter tout saut de ligne, réduction proportionnée des avatars (48px), des tags joueurs (16px), des scores et des textes de victoires.
  - **Rafraîchissement du cache CSS** : incrémentation de la version des styles à `v=25` dans `base.html`.
- **Prévention des Débordements de Texte sur les Cartes SVG & PNG** :
  - **Taille de police adaptative pour les métriques** : introduction de la fonction `_metric_font_size(text)` réduisant dynamiquement la taille de police (15px -> 13.5px -> 12px) dès que les nombres ou heures formatées dépassent 7 ou 9 caractères (ex: `1,450,890`, `125,890h`).
  - **Formatage compact des heures élevées** : conversion automatique en entier sans décimale (`1,250h`) au-delà de 1 000 heures vocales.
  - **Descriptions concises des commandes (`/help`)** : réécriture et calibrage des 6 descriptions en anglais et français pour tenir confortablement dans les tuiles de 380px sans risque de troncature ni de chevauchement sur les polices système.
  - **Sécurisation des bannières et titres** : troncature avec ellipse sur les noms de serveurs (`clean_srvname`), les pseudonymes des champions vocaux (`champ_name`) et les messages d'erreur 404 (`_render_error_svg`).
  - **Badge de version actualisé** : mise à jour du badge en haut à droite à `v2.5.6 • SLASH ACTIVE` / `v2.5.6 • SLASH ACTIF`.

## Version 2.5.5 - Refonte Visuelle des Cartes SVG, Harmonisation & Zéro Chevauchement - 07/09/2026
### Improvements & UI Redesign
- **Harmonisation visuelle et refonte complète des Cartes SVG de l'API** :
  - **Élimination définitive des collisions de texte (Zero Collision)** :
    - Remplacement du badge de rang horizontal à coordonnées fixes par une pilule verticale empilée (*Stacked Rank Badge*) de 96×38 px avec libellé supérieur centré (`GLOBAL RANK` / `SERVER RANK`) et rang inférieur centré (`#1`, `Unranked`, `Non classé`), garantissant l'absence totale de chevauchement quelle que soit la longueur du texte.
    - Largeur adaptative dynamique du badge de niveau (`lvl_badge_w = max(110, min(290, ...))`) et sécurisation du titre à 20 caractères, prévenant tout débordement hors du conteneur ou collision avec le badge de rang.
    - Équilibrage parfait de la carte utilisateur serveur (`!stats`) avec 4 tuiles métriques alignées (`VOCAL`, `MESSAGES`, `XP SERVEUR`, `MEMBRE DEPUIS`), comblant l'ancien vide latéral.
    - Gestion sécurisée de la date d'arrivée avec valeur par défaut propre (`Inconnue` / `Unknown`) évitant les chaînes pendantes sans date.
  - **Classements Top 10 Vocal à hauteur dynamique & bordures de médailles** :
    - Calcul automatique de la hauteur du classement (`y_start + max(1, count) * row_height + 42`) supprimant l'espace vide noir lorsque le serveur ou le bot compte moins de 10 membres actifs.
    - Avatars agrandis à 32px (rayon 16px) avec cerclage distinctif aux couleurs des médailles : Or (`#f59e0b`) pour le 1er, Argent (`#94a3b8`) pour le 2e, Bronze (`#d97706`) pour le 3e, et Cyan subtil pour les suivants.
  - **Carte d'Aide & Référence des Commandes (`/help` / `!help` / `!aide`)** :
    - Badge de version actualisé à `v2.5.5 • SLASH ACTIVE` / `v2.5.5 • SLASH ACTIF`.
    - Harmonisation complète des tags et descriptions en anglais et en français (tags `SERVER RANKING`, `GLOBAL RANKING`, `SERVER METRICS` en anglais).
  - **Carte d'erreur 404 modernisée** :
    - Arrondis 20px, halo carmin élégant et troncature de sécurité à 70 caractères pour les messages d'erreur.

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
