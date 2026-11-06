# Hourglass - WEB APP - CHANGELOG

## Version 3.38.0 - Record Vocal et Couleurs des Horaires - 06/11/2026
- **Record absolu** sur le graphique « Membres en vocal » : le plus grand nombre de membres en vocal en même temps depuis le début du suivi, avec la date et l'heure. Il s'affiche en doré à côté du pic de la période.
- **Nouvelles couleurs pour « Membres en vocal »** : la courbe bleue est remplacée par un dégradé du violet Hourglass, du violet profond en bas au lavande en haut.
- **Heures de pointe en couleur**
  - Chaque barre prend la nuance de son niveau d'activité, du violet sombre (calme) au lavande clair (très actif) pour le vocal, et du vert sombre au vert d'eau clair pour les messages. L'heure de pointe est entourée.
  - La grille par jour de la semaine passe de 5 à 8 nuances, de la plus sombre à la plus claire, au lieu de simples variations de transparence.
  - L'échelle va de l'heure la plus calme à la plus active (et non plus de 0 au maximum) : les heures calmes ne tombent plus toutes dans la même teinte pâle, et les écarts se voient beaucoup mieux.

## Version 3.37.0 - Graphique des Membres en Vocal - 06/11/2026
- **Nouveau graphique « Membres en vocal »** dans l'onglet Horaires de la page Analyses, sous « Présence des membres ». Il montre combien de membres le bot voit en vocal sur tous les serveurs, avec un point toutes les 15 minutes.
  - Deux périodes : 48 h ou 7 jours (7 jours par défaut). Le badge indique le pic de la période.
  - Le graphique est recalculé à partir des sessions vocales enregistrées par le bot, donc l'historique des 7 derniers jours est déjà rempli.
  - Chaque membre compte une fois, même si le bot a enregistré deux sessions qui se chevauchent. Une session restée ouverte pendant que le bot était hors ligne ne compte que jusqu'à son dernier signal.
  - Traduit dans les 12 langues.

## Version 3.36.3 - Graphique de Présence avec les Chiffres d'Origine - 06/11/2026
- **Le graphique « Présence des membres » global revient aux chiffres d'avant** (somme des membres de chaque serveur), en même temps que le bot v3.7.6.
  - Les relevés pris entre le 05/11 au soir et la mise à jour du bot comptaient chaque personne une seule fois. Ils sont environ un tiers plus bas et ne sont plus affichés, pour éviter un creux dans le graphique. Le reste de l'historique, d'avant comme d'après, s'affiche normalement.
  - La période est détectée automatiquement dans l'historique.

## Version 3.36.2 - Graphique de Présence sans la Rupture du 5 Novembre - 06/11/2026
- **Chute brutale du graphique « Présence des membres » le 05/11 au soir** : depuis le bot v3.7.1, chaque relevé compte chaque compte une seule fois (et depuis la v3.7.3, les bots aussi, une fois chacun). Avant, il additionnait les membres de chaque serveur : Hourglass à lui seul comptait pour 49 membres « en ligne » jour et nuit, comme les autres bots présents sur plusieurs serveurs, et un membre sur 5 serveurs comptait 5 fois. La vue 7 jours mélangeait les deux méthodes, d'où la falaise et une moyenne gonflée (« 30,2 % »).
  - Le graphique global et sa moyenne n'utilisent plus que les relevés du nouveau calcul, à partir du 05/11 vers 21 h. La rupture est détectée automatiquement dans l'historique (le total passe d'environ 977 à 684 d'un relevé à l'autre).
  - La vue 7 jours se remplit au fil des jours, et l'ancien historique disparaît de toute façon de la base au bout de 7 jours.
  - Le graphique de présence d'un serveur seul ne change pas (pas de double compte sur un seul serveur).

## Version 3.36.1 - Page des Badges sans Chevauchements et Interrupteurs Arène - 05/11/2026
- **Interrupteurs** (personnalisation du profil, onglet Confidentialité ; « Afficher les bots » de la page Membres) : la pastille ronde dans un rail carré faisait bizarre. Le rail et la pastille sont maintenant des **carrés en biais**, avec le même angle que les boutons et les étiquettes du site. Quand l'option est activée, la pastille glisse à droite sur fond violet. Au clavier, la mise au point s'affiche par un liseré clair, car le contour classique était masqué par la forme.
- **Cases à cocher des records** (onglet Vitrine) : celles du navigateur, rondes et bleues, sont remplacées par le même carré en biais, avec une coche quand le record est choisi.
- **Aperçu sur téléphone, onglet Vitrine** : l'aperçu fixé en haut affichait l'en-tête du profil en plus de la vitrine et prenait près de la moitié de l'écran (47 %). Il ne montre plus que la vitrine, la seule partie qui change dans cet onglet (28 %). Les onglets Apparence et Confidentialité ne changent pas (21 %).
- **Valeurs qui chevauchaient la date** dans la liste des détenteurs (« 29 114 messages » écrit par-dessus « depuis le… ») : la colonne avait une largeur fixe, trop étroite pour les grands nombres. La valeur et la date sont maintenant dans une même colonne, la valeur au-dessus et la date en dessous. Une valeur longue, comme celle de la Polyvalence (heures + messages), passe à la ligne au lieu de déborder.
- **Noms des paliers coupés dans la frise dépliée** (« MYTHIQUE », « PLATINE »…) : chaque palier prend au moins la largeur de son nom, et la frise passe sur une deuxième ligne quand la place manque.
- Contrôlé automatiquement, avec les plus longues valeurs et les plus longs pseudos, de 1440 à 320 px de large, en français, en allemand et en russe : plus aucun élément ne se superpose ni ne déborde.

## Version 3.36.0 - Menu des Badges et Paliers à Débloquer - 05/11/2026
- **Menu des 10 badges** sur la gauche des pages de badges. On passe de l'un à l'autre en gardant le serveur choisi, et chacun affiche le nombre de membres qui l'ont débloqué. Il reste visible pendant le défilement. Sur téléphone, il devient un bandeau qu'on fait défiler de côté, centré sur le badge ouvert.
- **Paliers à débloquer** : nouveau bloc sous le titre, avec ce que demande chacun des 7 paliers (« Bronze : 1 h », « Mythique : 2 500 h + 25 000 messages »…) et une phrase qui explique ce qui compte pour ce badge. Par exemple, pour le Classement, la meilleure place jamais atteinte, et une place perdue ensuite ne fait pas redescendre le palier.
- Traduit dans les 12 langues.

## Version 3.35.1 - Pages des Badges sur Tous les Workers - 05/11/2026
- **Page d'un badge en 404 une fois sur quatre** : au premier démarrage, les 4 workers du site créaient les nouvelles tables en même temps. PostgreSQL refuse alors un `CREATE TABLE IF NOT EXISTS` lancé en parallèle (`IntegrityError`), et le worker perdant désactivait la page jusqu'à son redémarrage. Les tables sont maintenant créées avec plusieurs essais. Un worker qui échoue malgré tout réessaie au plus une fois par minute, au lieu de rester désactivé. Reproduit en local avec 4 processus simultanés : 15 échecs sur 20 avant, 0 sur 20 après.
- Même protection pour les tables des records (badges Classement et Activité), des votes top.gg et du journal de sécurité. Elles existent déjà en production et n'étaient pas touchées, mais une future table neuve ne pourra plus perdre cette course.

## Version 3.35.0 - Pages des Badges - 05/11/2026
- **Nouvelle page par badge** (`/badge/<id>`), qu'on ouvre en cliquant sur un badge d'un profil : dans la vitrine, sur le nom d'un badge de l'onglet Badges, ou sur un de ses paliers (la page s'ouvre alors filtrée sur ce palier). Elle n'est pas dans le menu.
  - **Rareté des paliers** : pour chacun des 7 paliers, combien de membres l'ont atteint (ou mieux) et quel pourcentage ils représentent, puis le premier à l'avoir eu et à quelle date, ou combien l'avaient déjà avant octobre 2024. Cliquer sur un palier filtre la liste.
  - **Détenteurs** : triés du meilleur au moins bon, avec le palier, la valeur (heures, messages, place…) et la date d'obtention du palier actuel. Chaque ligne se déplie sur la **date de chacun des 7 paliers**. Recherche par pseudo, pagination.
  - **Derniers débloqués** (les 20 derniers paliers franchis) et **Presque** (les membres à 80 % ou plus du palier suivant).
  - **Filtre par serveur** : ne montrer que les membres d'un serveur. Les badges restent ceux de tous les serveurs.
- **Dates d'obtention reconstituées depuis l'historique**, badge par badge :
  - le jour où le cumul a franchi le seuil (vocal, messages, niveau, polyvalence), la fenêtre de 30 jours (activité), la série de jours actifs, l'arrivée sur le N-ième serveur, la première activité plus N jours (fidélité), le premier jour à cette place d'après les relevés quotidiens (classement), le N-ième vote (soutien) ;
  - avant le 05/10/2024, l'ancien bot ne gardait que les totaux : un palier déjà atteint à cette date est noté « avant oct. 2024 » plutôt qu'une fausse date ;
  - un palier que l'historique ne peut pas dater garde le jour où il a été vu pour la première fois.
- **Recalcul toutes les heures** par un seul worker, avec le code des badges du profil lui-même : les paliers de la page sont toujours ceux du profil. Vérifié sur tous les membres (9 350 paliers identiques). Le calcul complet prend moins d'une seconde. Deux nouvelles tables du site, `user_badge_values` et `user_badge_tiers`, sont créées au démarrage (migration `2026-11-05_web_v3.35.0_badge_stats.sql`).
- **Confidentialité** : les membres au profil privé, ou qui cachent leurs badges, sont comptés dans la rareté mais ne sont nommés nulle part (liste, premier détenteur, derniers débloqués, presque). Les bots et applications sont exclus.
- Traduit dans les 12 langues, adapté au téléphone.

## Version 3.34.3 - Ménage de l'Ancienne Page Versus - 05/11/2026
- **Styles de l'ancienne page Versus retirés** (remplacée en v3.34.0 par `css/pages/versus.css`) : 62 classes qui ne servaient plus nulle part (cartes de combattants, jauges, tableau de score…). Cela représente 137 règles en moins dans `styles.css` et `arene.css`, et 17 listes de sélecteurs allégées. Le haut de la page (recherche, échange, serveurs en commun) garde ses styles. Aucun changement visible.

## Version 3.34.2 - Libellés de l'Accueil - 05/11/2026
- **Accueil** : les tuiles « Utilisateurs uniques » et « Serveurs uniques » deviennent **« Utilisateurs enregistrés »** et **« Serveurs enregistrés »**, car elles comptent tout ce qu'Hourglass a enregistré depuis le début. La pastille de la première passe de « 684 personnes sur les serveurs » à **« 684 personnes actuellement »**. Traduit dans les 12 langues.

## Version 3.34.1 - Identifiants Discord Vérifiés - 05/11/2026
- **Connexions refusées par Discord (« invalid_client »)** : Discord refusait le couple identifiant / secret de l'application (`DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`), donc toute nouvelle connexion échouait avec « Impossible de valider la session auprès de Discord ». Ce n'est pas un bug du site : le secret configuré ne correspond plus à celui du Developer Portal. Pour éviter que ça se reproduise sans qu'on le voie :
  - **Check-up de l'admin** (onglet Sécurité) : nouvelle ligne « Identifiants Discord », vérifiée auprès de Discord lui-même toutes les 10 minutes. En rouge, elle dit quoi faire.
  - Les espaces, retours à la ligne ou guillemets collés autour de `DISCORD_CLIENT_ID` et `DISCORD_CLIENT_SECRET` sont retirés, car ils provoquent la même erreur.
- **Changer le secret Discord ne déconnecte plus personne** : quand la clé des sessions était dérivée de `DISCORD_CLIENT_SECRET`, elle est maintenant enregistrée en base au démarrage. Un nouveau secret ne change donc plus la clé.

## Version 3.34.0 - Nouvelle Page Versus, 100 XP par Vote et Connexion Discord Plus Fiable - 05/11/2026
### Page Versus repensée
- **Arène** : les deux adversaires face à face, chacun sur sa moitié, avec sa **bannière de profil** en fond (ou son avatar flouté) teintée de sa couleur, bleu à gauche, rouge à droite. Grand avatar, nom, titre et niveau, rang et heures en vocal. Le gagnant a une couronne et un contour doré, le perdant est légèrement atténué.
- **Au centre** : emblème VS, score en grand (4 : 2), verdict « bugpigo gagne le duel » ou « Égalité parfaite », et une barre qui montre la part des catégories gagnées. Le score n'est plus répété dans chaque carte.
- **Duel par catégorie** : pour chaque catégorie, les deux valeurs de part et d'autre, l'**avance du gagnant** (« +55,5 h », « 4 places devant ») et une barre partagée entre les deux couleurs, avec un repère au milieu ; la part du perdant est atténuée. Valeurs au format de la langue (1 436,1 h).
- **Correctif du classement** : la barre du rang donnait la plus grande part au moins bien classé (#6 contre #2). Elle est maintenant répartie selon 1 / rang : le meilleur classement a la plus grande part.
- **Courbe** : sans les points sur chaque mois, plus lisible ; mêmes couleurs que l'arène.
- **Téléphone** : score et verdict en haut, puis les deux adversaires côte à côte, et chaque catégorie sur trois lignes (nom, valeurs, barre). Traduit dans les 12 langues.

### Admin : chaque chiffre expliqué
- **Au survol d'une case chiffrée** (ou au toucher sur téléphone, ou avec le clavier), une phrase dit ce qu'elle compte et d'où vient le chiffre. Par exemple : « Moyenne par jour des visiteurs différents, comptés sans cookie… », ou « Sessions vocales jamais refermées depuis plus de 24 h… ».
  - Ça couvre toutes les sections : vue d'ensemble (bandeau d'état et tuiles), site web, comptes, profils, communauté et votes, bot et commandes, technique, sécurité.
  - Le libellé des cases qui ont une explication est souligné en pointillé.
- **Infobulles** : elles s'affichent maintenant aussi sur la page admin, qui ne chargeait pas leur style. Sur tout le site, elles se ferment quand on fait défiler un panneau, et pas seulement la page.

### Aperçus de liens (Discord et autres)
- **Grande image** sous l'aperçu d'un profil, d'une fiche serveur ou d'un duel entre membres : la même carte que celle du bot (avatar, bannière, niveau, heures, rang…). Nouvelles adresses publiques `/og/member/<id>.png`, `/og/server/<id>.png` et `/og/versus/<id1>/<id2>.png`, dessinées à la demande, gardées 10 minutes, limitées à 30 requêtes par minute.
- **Couleur de l'aperçu** : la barre le long de l'aperçu Discord prend le violet Hourglass au lieu du fond sombre du site (invisible), et la couleur choisie par le membre sur son profil.
- **Liens Versus** : titre « bugpigo vs eluen · Versus - Hourglass » et description du duel (heures en vocal et niveaux des deux membres ; le gagnant et le score pour un duel de serveurs), au lieu de l'aperçu générique.
- **Langue** : les robots d'aperçu ne disent pas quelle langue ils veulent, les aperçus étaient donc toujours en français. L'adresse affichée porte désormais `?lang=` pour toutes les langues sauf le français : un lien copié s'affiche dans la langue de celui qui le partage. Un visiteur garde toujours sa propre langue, le paramètre n'est lu que par les robots.
- **Profils privés** : la description de l'aperçu ne donne plus le nombre de badges, et la carte publique (aperçu et cartes SVG à intégrer) n'affiche plus la vitrine de badges quand le membre la cache aux visiteurs. Les cartes postées par le bot ne changent pas.

### Votes et XP
- **Chaque vote pour Hourglass sur top.gg rapporte 100 XP** (autant que 100 minutes en vocal ; un vote toutes les 12 heures). Les votes comptent pour le **niveau global**, partout où il apparaît : profil, page Membres (tri par XP et par niveau, sur la période choisie), recherche, cartes au survol, cartes du bot, Versus, liste des membres d'une fiche serveur. Ils ne comptent pas dans les chiffres propres à un serveur (classement d'un serveur, carte ou Versus limités à un serveur), un vote n'appartenant à aucun serveur.
- **Profil** : au survol du total d'XP, « Dont 300 XP de votes sur top.gg ».
- **Page Aide** : nouveau bloc « Votes pour Hourglass · +100 XP / vote » dans le système d'expérience, avec le lien pour voter. Traduit dans les 12 langues.

### Correctifs
- **Graphiques « par mois » : énorme pic en octobre 2024 sur les membres et serveurs plus anciens**. Quand le bot est passé au suivi détaillé, le 05/10/2024, les totaux de l'ancien bot ont été repris en une seule session vocale (et un seul lot de messages) par membre et par serveur, datée de ce jour-là : tout ce qui précédait apparaissait en octobre 2024, et rien avant. Ces totaux sont maintenant répartis sur les mois qu'ils couvrent, depuis l'arrivée du membre sur chaque serveur, comme le faisait déjà la courbe « Cumulé ». Le total ne change pas.
  - Ces mois sont des **estimations** (l'ancien bot ne gardait que les totaux) : barres atténuées et détourées, avec « Estimation : avant octobre 2024, le bot ne gardait que les totaux » au survol. Elles ne comptent pas dans la moyenne, ni dans le record « Meilleur mois ».
  - Profils, fiches serveur et page Analyses. Traduit dans les 12 langues.
- **Accueil, tuile « Utilisateurs uniques »** : la pastille du dessous affiche le **nombre réel de personnes présentes sur les serveurs du bot**, actives ou non (« 12 345 personnes sur les serveurs »), au lieu du nombre de profils enregistrés (une ligne par membre et par serveur, qui comptait plusieurs fois un même membre). C'est le chiffre « Membres uniques » de l'admin, relevé par le bot toutes les 15 minutes ; tant qu'aucun relevé n'existe, l'ancien texte reste affiché. Traduit dans les 12 langues.
- **« Impossible de valider la session auprès de Discord » alors que la connexion avait marché** : sur téléphone, la page de retour de Discord pouvait s'ouvrir deux fois (passage par l'appli Discord, rechargement). La 2ᵉ ouverture échouait, son code ayant déjà servi, et renvoyait un cookie sans le compte, qui remplaçait celui de la connexion réussie. Désormais :
  - une connexion qui échoue ne touche plus au cookie de session ;
  - une page de retour rechargée ou une page d'erreur atteinte alors qu'on est connecté envoie vers la page prévue, sans message d'erreur.
- **Connexion par la fenêtre popup (ordinateur)** : en cas d'échec, la fenêtre se fermait sans rien dire et on restait sur la page, déconnecté. La page affiche maintenant le message d'erreur.
- **Plus de connexion à moitié faite** : la session n'est écrite qu'une fois toutes les informations de Discord reçues. L'enregistrement de la connexion en base (statistiques de l'admin, bannière Discord) ne peut plus faire échouer la connexion.
- **Limite de requêtes Discord** : une réponse « trop de requêtes » de Discord avec une attente de 3 secondes au plus est réessayée une fois au lieu d'échouer.
- **Journal de sécurité** : une erreur interne pendant la connexion y est maintenant notée (« erreur interne : … »), et un refus de Discord indique sa raison (par exemple `invalid_grant`, code déjà utilisé ou expiré).
- Aucun membre connecté n'est déconnecté par cette mise à jour.

## Version 3.33.0 - Tri par Votes et Logs du Bot dans l'Admin - 01/11/2026
- **Page Membres : tri « Plus de votes »**. Classe les membres par votes pour Hourglass sur top.gg, sur la période choisie (24 h à Toujours), avec le rang et sa progression comme les autres tris. Chaque ligne affiche alors ses votes ; sur petit téléphone, cette puce remplace celle des heures.
- **Analyses, onglet Communauté** :
  - les photos de profil apparaissent dans « Membres les plus actifs », comme les icônes des serveurs à côté ;
  - les boutons « Voir tous les serveurs » et « Voir le classement complet » ont maintenant leur marge et sont alignés en bas des deux cartes.
- **Admin : nouvelle section « Logs du bot »** (groupe Technique). Elle affiche les 200 dernières lignes des logs du bot, recopiées en base par le bot à partir de la v3.7.0 (table `bot_logs`), sans passer par Portainer.
  - Plus récentes en bas, comme Portainer. La liste suit les nouvelles lignes, sauf si on remonte dans l'historique.
  - Actualisation toutes les 10 secondes tant que la section est ouverte (case « Direct »), sans recharger les lignes déjà affichées.
  - Filtres Tout / Alertes / Erreurs, déduits des ⚠️ et ❌ des messages du bot, et recherche dans le texte.

## Version 3.32.1 - Votes Affichés sans Retard - 01/11/2026
- **Un vote semblait apparaître puis disparaître selon les rafraîchissements** : chacun des 4 workers du site gardait le nombre de votes d'un membre en mémoire 2 minutes, et seul le worker qui recevait le webhook l'oubliait. Ce cache passe à 5 secondes : la requête lit la clé de la table (0,05 ms), elle n'a pas besoin de plus. Les cartes au survol et les cartes du bot, comme pour les autres statistiques, peuvent garder l'ancien total jusqu'à 2 minutes.

## Version 3.32.0 - Votes top.gg et Badge Soutien - 01/11/2026
### Votes
- **Les votes pour Hourglass sur top.gg sont enregistrés** dans une nouvelle table du site `topgg_votes` (créée au démarrage, migration `2026-11-01_web_v3.32.0_topgg_votes.sql`) : membre Discord, date, date du prochain vote possible, poids.
  - **En temps réel** par le webhook top.gg, sur `/webhooks/topgg` : signature HMAC-SHA256 vérifiée (`x-topgg-signature`, secret `whs_…` dans `TOPGG_WEBHOOK_SECRET`), requête de plus de 10 minutes refusée (rejeu). Les webhooks à l'ancien format (en-tête `Authorization`) sont acceptés avec le même secret. Tout refus va dans le journal de sécurité (« Webhook top.gg refusé ») ; limite de 120 requêtes par minute.
  - **Rattrapage toutes les heures** par l'API top.gg (`TOPGG_TOKEN`), et **historique de l'année passée** au premier passage : un vote manqué par le webhook est retrouvé. Un vote reçu deux fois n'est compté qu'une fois.
- **Badge « Soutien » (Supporter)**, le 10ᵉ : 1, 5, 10, 25, 50, 100 et 200 votes, de Bronze à Mythique. Un vote du week-end (qui compte double sur top.gg) compte une fois ici. Il apparaît partout où sont les badges : profil, vitrine, cartes du bot, page Aide.
- **Profil** : nombre de votes à côté de l'identifiant, avec « A voté » pendant les 12 heures du vote ; sur son propre profil, bouton **Voter** quand un vote est possible.
- **Accueil** : bouton « Voter sur top.gg » dans l'en-tête.
- **Admin, onglet Communauté** : votes de la période, du mois, votes en cours, total, votes par jour, meilleurs votants, et rappel des variables manquantes ; nouveau compteur « Webhooks top.gg refusés » dans l'onglet Sécurité.
- **Page Aide et textes** : 10 badges et 70 paliers. Page Confidentialité : paragraphe sur les votes dans les 12 langues.

## Version 3.31.5 - Tuile « Serveurs Uniques » de l'Accueil - 01/11/2026
- **Accueil** : la tuile « Serveurs actifs / Serveurs connectés » devient **« Serveurs uniques »**, comme « Utilisateurs uniques » à côté. Son chiffre est le nombre de serveurs suivis par Hourglass depuis le début (ce qu'elle comptait déjà) ; la pastille dessous indique **combien ont le bot actuellement** (icône bot), au lieu de « Serveurs connectés », trompeur. Traduit dans les 12 langues.

## Version 3.31.4 - HSTS Unique et Batterie de Tests de Sécurité - 01/11/2026
- **HSTS** : le proxy openresty envoie déjà son propre `Strict-Transport-Security`, ce qui faisait deux en-têtes contradictoires (les navigateurs ne retiennent que le premier). Avec `HSTS_FROM_PROXY=true` dans l'environnement, le site n'envoie plus le sien ; une ligne « HSTS » du check-up de l'admin indique qui l'envoie.
- **Batterie de tests de sécurité** `web/scripts/security_check.py` (55 contrôles, sans serveur, sans rien écrire en base) : en-têtes et CSP, cookie de session, contrôle d'accès (admin, sessions vocales réservées au propriétaire, jeton des cartes), CSRF, redirections ouvertes, `state` OAuth, XSS réfléchi (60 injections), injection SQL (dont temporelle et par cookie), traversée de répertoires, méthodes HTTP, taille des requêtes, pages d'erreur, limites de requêtes et IP falsifiée, en-tête Host. `--quiet` n'affiche que les échecs ; code de sortie 1 en cas d'échec.
- **Pied de page** : lien « Nouveautés ↗ » à côté du numéro de version, vers ce changelog sur GitHub (nouvel onglet), traduit dans les 12 langues.

## Version 3.31.3 - Admin : Listes Lisibles dans les Cartes Étroites - 01/11/2026
- **Journal de sécurité dans une carte étroite** (encadré « Derniers événements » de la vue d'ensemble) : la mise en page dépend maintenant de la largeur de la carte, pas de celle de l'écran. Sur grand écran, l'encadré gardait ses quatre colonnes et l'adresse de la page s'affichait une lettre par ligne ; il passe désormais au format compact : type et heure, puis IP, page et détail en dessous.
- **Barres de défilement** : les listes et journaux qui défilent dans leur carte réservent une place à la barre, qui ne recouvre plus les chiffres ni le texte.

## Version 3.31.2 - Check-up de Configuration Plus Clair - 01/11/2026
- **Check-up de l'onglet Sécurité de l'admin** : chaque ligne a un titre court (Clé de session, HTTPS, Connexion Discord…) et un texte qui dépend de son état. En vert, ce qui est en place (« Par code : le jeton Discord ne passe jamais par le navigateur. ») ; en rouge, le problème et le réglage à faire (« Mode implicite, moins sûr : définir DISCORD_CLIENT_SECRET. »). Avant, le texte était le même dans les deux cas : une ligne verte pouvait afficher « sans secret ».
- **Journal de sécurité en colonnes** : type, heure, membre et IP, page, puis le détail sur sa propre ligne, en entier (il était coupé sur le côté). Les pages s'affichent sans le nom de domaine (`/versus`).
- **Violations CSP** : les scripts bloqués venant d'une adresse `blob:` ne sont plus enregistrés. Le site n'en crée jamais ; ce sont des extensions du navigateur qui injectent du code avec un identifiant aléatoire.
- **Base de données (onglet Technique)** : toutes les tables sont listées automatiquement (avant, une liste fixe de 13 tables), avec leur nombre exact de lignes (`COUNT(*)` jusqu'à 512 Mo par table, estimation au-delà) au lieu de l'estimation de PostgreSQL, qui affichait 0 ou rien pour les tables jamais analysées.
- **Espace récupérable par table** : estimation de la place prise au-delà de ce que les lignes demandent (place laissée par des lignes supprimées, que PostgreSQL garde pour la table jusqu'à un `VACUUM FULL`), affichée en orange à partir de 1 Mo, avec le total en tête de la carte et la commande au survol. Exemple : `presence_history`, gonflée par les anciens relevés par serveur supprimés en bot v3.1.1.

## Version 3.31.1 - Admin aux Coins Droits, Clé de Session Stable - 01/11/2026
- **Admin** : coins droits partout (cartes, boutons, pastilles, listes, champs) ; seuls les points d'état, les avatars et l'indicateur de chargement restent ronds. Nouvelle icône pixel « Actualiser » (flèche circulaire) à la place de l'icône d'échange, qui ressemblait à des réglages.
- **Clé de session** : la clé déjà enregistrée en base passe avant celle dérivée de `DISCORD_CLIENT_SECRET`. Ajouter le secret Discord pour passer à la connexion par code ne déconnecte donc plus personne.

## Version 3.31.0 - Nouvelle Console Admin - 01/11/2026
- **L'admin devient une console pleine page**, séparée du thème Arène du site : thème sombre sobre, police IBM Plex Sans, coins légèrement arrondis, sans coins coupés ni titres en majuscules, chiffres alignés. Le blurple du site reste la seule couleur d'accent ; vert, orange et rouge ne servent qu'aux états.
- **Volet vertical à gauche** avec les sections regroupées (Pilotage : Vue d'ensemble, Site web, Comptes, Profils, Communauté ; Technique : Bot, Technique, Sécurité), un lien de retour au site, et des pastilles sur ce qui demande un coup d'œil : alertes de sécurité du jour, erreurs serveur, bot silencieux. Sur téléphone et tablette, le volet devient un menu coulissant.
- **Barre du haut** : titre de la section, heure de mise à jour, état du bot, bouton Actualiser et **période de toute la page (7, 30 ou 90 jours)**. `/admin/data?days=N` calcule les listes, graphiques et totaux sur la période choisie ; la période est gardée dans l'adresse et d'une visite à l'autre.
- **Vue d'ensemble** : bandeau d'état (bot, alertes de sécurité, erreurs serveur, check-up de configuration, sessions orphelines), huit chiffres clés avec la comparaison à la période précédente, courbe des visites et derniers événements de sécurité.
- **Site web** : quatre chiffres clés en tête (pages vues et visiteurs avec leur évolution, aujourd'hui, part du téléphone).

## Version 3.30.1 - Rapports CSP Plus Utiles - 01/11/2026
- Les violations CSP du journal de sécurité venaient de scripts ajoutés par les extensions du navigateur (le site lui-même n'a que des scripts autorisés). La CSP demande maintenant un extrait du script bloqué (`'report-sample'`), affiché dans le journal avec son fichier d'origine pour savoir qui l'a ajouté.
- Les rapports dont le script vient d'une extension (`chrome-extension:`, `moz-extension:`, `safari-web-extension:`…) ne sont plus enregistrés.

## Version 3.30.0 - Badges Classement et Activité Définitivement Acquis - 01/11/2026
- **Meilleure place et meilleurs 30 jours sauvegardés** pour chaque membre, dans une nouvelle table du site `user_best_records` (migration `2026-11-01_web_v3.30.0_user_best_records.sql`, aussi créée au démarrage). Les badges ne sont toujours pas stockés : seulement ces deux records, avec leur date.
  - Meilleure place au classement vocal global, avec le premier jour où elle a été atteinte et les heures de vocal à ce moment.
  - Meilleur total de vocal sur 30 jours glissants, avec la période.
  - Un record ne fait que s'améliorer ; en cas d'égalité, la première date est gardée.
- **Historique repris dès la création** : les relevés quotidiens de `historical_stats` (classement de chaque jour depuis octobre 2024) et les sessions vocales (fenêtres de 30 jours). Les totaux importés à la création des sessions vocales (5 octobre 2024, sessions de durée nulle jusqu'à 257 h) sont écartés, et une journée ne compte jamais plus de 24 h.
- **Mise à jour toutes les heures**, par un seul worker (verrou PostgreSQL) et en une requête pour tout le monde. Aucun calcul en plus à chaque visite, aucun changement côté bot.
- **Badges Classement et Activité** : le palier est le meilleur entre maintenant et le record. Ils ne redescendent plus quand quelqu'un vous dépasse ou après un mois calme. Descriptions : « Meilleure place au classement vocal global » et « Meilleur total de vocal sur 30 jours ».
  - La date du record s'affiche au survol du badge (vitrine, carte au survol) et de chaque palier dans l'onglet Badges du profil : « Meilleure place : #3, le 12 mars 2026 », « Record : 152 h, du 6 mai au 4 juin 2026 ».
  - Les cartes du bot (`/stats`, `/allstats`) suivent, avec le même calcul.
- **Nouveaux paliers du badge Classement** : Top 100 (Bronze), Top 50 (Argent), Top 25 (Or), Top 10 (Platine), Top 5 (Diamant), Top 3 (Légende), n°1 (Mythique). Avant : Top 3 en Diamant, n°1 en Légende, et n°1 avec 5 000 h en Mythique.
- **La place globale ne compte plus les bots et applications Discord** (profil, badge, record), comme la page Membres.
- 6 nouvelles phrases traduites dans les 10 autres langues.

### Titres par niveau
- **Nouveaux titres, à des niveaux ronds** : Recrue (1), Habitué (5), Confirmé (10), Vétéran (20), Champion (30), Maître (40), Grand Maître (50), Icône (60), Immortel (70), Titan (80), Gardien du Sablier (90), Maître du Temps (100). Ils remplacent les 7 anciens (Novice Curieux… Légende Hourglass) partout : profil, carte au survol, Versus, cartes du bot et aperçu de la personnalisation. Traduits dans les 12 langues.

### Page Aide
- **Titres par niveau** : les 12 titres avec leur niveau, l'XP demandée et le temps de vocal équivalent (arrondi), colorés par groupe (gris, bleu, violet, doré).
- **Paliers des badges** : les 9 badges et ce que demande chacun de leurs 7 paliers, de Bronze à Mythique (tableau sur ordinateur, grille par badge sur téléphone).
- Commandes affichées en commandes slash (`/stats`, `/top [type] [period] [scope]`, `/help`…) au lieu de l'ancien préfixe `!`, avec `/versus` ajoutée ; description mise à jour dans les 12 langues.

## Version 3.29.0 - Journal de Sécurité et Durcissement du Site - 01/11/2026
### Journal de sécurité
- **Nouvelle table `web_security_events`** (créée au démarrage, migration `2026-11-01_web_v3.29.0_security_events.sql`) : connexions réussies et échouées (state invalide, refus de Discord, jeton d'une autre application), accès admin et tentatives refusées, formulaires refusés (CSRF), limites de requêtes (429), scans de robots (`/.env`, `/.git`, `wp-login.php`, `phpmyadmin`, `.php`…), jetons de carte invalides, violations CSP, erreurs 500 (type d'erreur seulement) et requêtes trop grosses (413).
  - **IP abrégée** uniquement (IPv4 `82.64.12.x`, IPv6 `/48`), jamais complète. Suppression automatique après 90 jours.
  - Écriture par lots toutes les 30 s : les événements identiques d'une même minute sont regroupés avec un compteur, et un afflux (scanner) est plafonné par minute. Aucune requête SQL par visite.
- **Nouvel onglet admin « Sécurité »** : dix compteurs sur 24 h (avec les 7 jours, en orange ou rouge au-delà d'un seuil), événements par jour sur 30 jours, sources les plus actives et adresses visées sur 7 jours, journal des 300 derniers événements filtrable par type, accès à l'admin, et **check-up de la configuration** (clé de session, HTTPS, cookie, CSP, debug, mot de passe de la base, jeton des cartes, secret Discord, IP transmise par le proxy, journal, nombre d'admins). Une tuile « Alertes de sécurité » sur la vue d'ensemble y mène.
- Sur téléphone, les compteurs de l'admin passent à deux par ligne.
- Page Confidentialité : paragraphe « Journal de sécurité » dans les 12 langues, date de mise à jour au 1er novembre 2026.

### Durcissement
- **IP des visiteurs** : `X-Real-IP` et `X-Forwarded-For` ne sont plus crus que s'ils viennent du proxy (réseau privé ou machine locale). Si le port de l'application était joignable directement, un attaquant pouvait changer d'IP à chaque requête et contourner les limites.
- **Connexion par jeton (mode implicite)** : le site vérifie auprès de Discord que le jeton a été émis pour Hourglass ; le jeton d'un membre pour une autre application est refusé.
- **Session remise à neuf à la connexion** (anciennes clés et jeton CSRF renouvelés). Aucun membre déjà connecté n'est déconnecté par la mise à jour.
- **HSTS** (6 mois, sans préchargement) sur les pages servies en HTTPS.
- **Requêtes limitées à 256 Ko** (413 au-delà).
- **`Cache-Control: no-store`** sur `/admin`, `/me/` et `/auth/`.
- **Limites de requêtes** ajoutées sur `/admin` (60/min) et `/csp-report` (20/min).
- **Rapports CSP** : le navigateur signale les scripts bloqués à `/csp-report` (taille limitée, rapports vides ignorés).
- La comparaison du `state` OAuth du mode code se fait en temps constant, comme celle du mode jeton.

## Version 3.28.0 - Tri par Date d'Arrivée - 01/11/2026
- **Deux nouveaux tris sur les pages Membres et Serveurs** : « Arrivée : plus anciens » et « Arrivée : plus récents ».
  - Membre : sa première activité vue par Hourglass, comme « Membre depuis » sur son profil. Avec le filtre serveur, c'est sa première activité sur ce serveur.
  - Serveur : le jour où Hourglass a commencé à le suivre, comme sur sa fiche et la carte `/server`.
  - Chaque ligne affiche la date dans une étiquette calendrier (« 28 Avr 2024 »), avec le détail au survol. Sans rang ni flèches dans ce mode, comme pour le tri A–Z. Sur petit téléphone, la date remplace le temps vocal.
  - Recherche, serveur, période (les chiffres restent ceux de la période), bots masqués et pagination fonctionnent avec ce tri. Sans date connue, la ligne passe en fin de liste.
  - Les dates sont calculées en une requête groupée par source et mises en cache 10 minutes.
- 4 nouvelles phrases traduites dans les 10 autres langues.
- Étiquette « Non suivi » des serveurs quittés par le bot au style du site : coins coupés, majuscules, gris discret (elle était arrondie).

### Page admin
- **Plus aucun défilement horizontal**, à toutes les largeurs :
  - la barre d'onglets est une grille (7 onglets sur une ligne en grand écran, 4 + 3 en dessous de 1280 px) au lieu de défiler sur le côté ;
  - les tableaux (dernières connexions, derniers membres et serveurs arrivés, temps de réponse des commandes, taille des tables) passent à la ligne : le nom d'abord, puis ses détails, qui descendent sous le nom quand la carte est étroite.
- **Nouvel onglet « Profils »** : la personnalisation des profils quitte l'onglet Comptes, qui ne garde que les connexions. La tuile « Profils personnalisés » de la vue d'ensemble y mène.
- Communauté : le graphique des arrivées et départs de serveurs suit directement les membres présents, les deux tableaux des derniers arrivés viennent ensuite.
- Technique : le graphique des erreurs et les adresses 404 côte à côte.
- Listes avec pastille de couleur (couleurs de profil, fonds) : la valeur restait coincée sous la ligne, elle est de nouveau alignée à droite.

## Version 3.27.0 - Personnalisation du Profil Repensée, Palette Arène - 01/11/2026
### Page Personnaliser
- **Bannière : une seule galerie, avec « Aucune » en première case** (sélectionnée par défaut). Le choix « Aucune / Image de la galerie » disparaît : choisir « Aucune » enregistre l'absence de bannière, choisir une image l'affiche. Les pages ouvertes avant la mise à jour s'enregistrent toujours correctement.
  - Les 5 premières images sont affichées, les autres derrière « Voir les N autres » (ouvert d'office si l'image choisie en fait partie). La galerie ne défile plus à l'intérieur de la page.
- **Couleurs en cases carrées aux coins coupés**, remplies de la couleur, avec une coche sur la couleur choisie (les pastilles rondes dépassaient de leurs cases). 8 par ligne, sans case isolée sur téléphone. « Couleur de mon profil Discord » a sa propre ligne, avec son libellé.
- **Fond de la page** : même présentation, avec une case « Aucun » en premier à la place de la pastille barrée.
- Ordre de l'onglet Apparence calqué sur le profil : Bannière, Couleur, Fond. Descriptions raccourcies, icônes dans les onglets.
- **Bouton « Annuler »** dans la barre d'enregistrement quand des changements ne sont pas enregistrés : il remet les choix enregistrés, aperçu compris.
- **Téléphone et tablette** : l'aperçu devient compact (bannière, avatar, pseudo, barre de niveau) et reste collé en haut de l'écran pendant les réglages ; la vitrine n'apparaît dans l'aperçu que sur l'onglet Vitrine. Le choix actuel passe sous le titre de chaque réglage, et les onglets tiennent en entier jusqu'à 320 px.

### Couleurs du profil
- **Nouvelle palette de 16 couleurs accordée au thème Arène**, sans quasi-doublons et avec les couleurs du site : Blurple (par défaut), Bleu, Ciel, Cyan, Turquoise, Menthe, Vert, Citron vert, Jaune, Or, Orange, Corail, Rose, Fuchsia, Améthyste, Argent.
  - Les couleurs retirées sont lues comme la plus proche, sans rien réécrire en base : Indigo → Blurple, Violet → Améthyste, Ambre → Or, Pêche → Orange, Rouge → Corail, Émeraude → Menthe. Le profil, les cartes du bot et la page admin suivent.
- **Texte foncé sur la couleur du membre** : onglets actifs, boutons de période, badge de niveau (désormais uni). Le texte blanc était sous le seuil de lisibilité avec toutes les couleurs (1,5:1 sur Jaune ou Argent).
- Fond « Ardoise » retiré (presque identique au fond par défaut) : les profils qui l'avaient reviennent au fond par défaut.
- 7 nouvelles phrases traduites dans les 10 autres langues ; les traductions des libellés retirés sont supprimées.

## Version 3.26.1 - Images pour la Page top.gg - 31/10/2026
- **Images de présentation** dans `app/static/promo/`, servies à `https://hourglassbot.net/static/promo/...` pour la page top.gg du bot : bannière, bandeau des 4 points forts, une carte `/stats` et la carte d'aide, au style Arène des cartes.
- Textes du profil top.gg (description courte, description longue en anglais et en français, catégories, langues, liens) dans `docs/topgg/` à la racine du dépôt.

## Version 3.26.0 - Cartes du Bot aux Couleurs de l'Arène, dans la Langue du Membre - 28/10/2026
### Cartes
- **Toutes les cartes des commandes du bot passent à la DA Arène du site** (`/stats`, `/allstats`, `/versus`, `/top`, `/alltop`, `/server`, ainsi que la carte d'aide et les cartes « introuvable ») ; la structure de chaque carte ne change pas.
  - Coins coupés, contour fin et liseré de couleur en haut à gauche, halos de couleur en fond.
  - Polices du site : Chakra Petch pour les titres, chiffres et légendes (chiffres en italique), IBM Plex Sans pour les textes.
  - Icônes en pixel art à la place des emojis, dans des blocs aux coins coupés.
  - Couleurs par type : vocal en bleu, messages en vert, XP en ambre, serveur en corail, membres en violet. La couleur du profil reste celle du membre.
- **Carte membre** : niveau et serveur en étiquettes biseautées, rang en grand chiffre doré sur un « #N » en relief, et tuiles avec un liseré de couleur. Les badges en vitrine prennent la couleur de leur palier (Mythique en holographique).
- **Versus** : chaque moitié est teintée de la couleur de son joueur, avec « VS » dans un bloc coupé, une couronne pour le vainqueur, et des barres séparées au milieu.
- **Top 10** : podium avec contour et liseré aux couleurs des médailles, et grand numéro en relief.
- **Serveur** : icône du serveur aux coins coupés, quatre tuiles de couleur et courbe du vocal sur 30 jours.
- **Chiffres, dates et séparateurs dans le format de la langue** (« 1 564h », « 9 sept 2024 », « 1.564h » en allemand).

### Langues
- **Les cartes suivent la langue Discord du membre qui lance la commande** (paramètre `?lang=`, envoyé par le bot v3.4.0) : français, anglais, espagnol, portugais, italien, allemand, polonais, turc et russe.
  - Le hindi, le japonais et le coréen reçoivent la carte en anglais, faute de police pour ces écritures dans le moteur des cartes. Les textes du bot, eux, sont traduits.
  - Le russe utilise Inter pour le cyrillique (sans italique).
  - Les cartes intégrables `/api/card/...` acceptent aussi `?lang=` (anglais par défaut, comme avant).
- 39 nouvelles phrases traduites dans les 11 langues.

### Bots et applications Discord
- **Étiquette « BOT »** après le nom des bots et applications Discord (bots musique en vocal, par exemple) : classement des membres, membres d'une fiche serveur, profil, Versus et cartes au survol.
- **Filtre « Bots · Afficher » sur la page Membres, désactivé par défaut** : le classement ne montre que les vrais membres, et les rangs sont ceux des vrais membres. Un clic sur l'interrupteur réaffiche les bots, à leur place, avec l'étiquette. Le choix est gardé dans l'adresse (`?bots=1`) et dans la pagination.
- Les podiums de l'accueil et la carte `/top` du bot ne montrent plus de bots non plus.
- Les bots sont repérés par le bot Discord (v3.4.0, colonne `users.is_bot`). Tant que le bot n'a pas ajouté cette colonne, le site fonctionne comme avant, sans étiquette et sans rien masquer. La liste des bots est mise en cache 5 minutes.

### Filtres des pages Membres et Serveurs
- **Barre de filtres remise à plat** : chaque filtre a son titre au-dessus (sans « : »), et tous les champs font la même hauteur avec le même fond, le même contour et les mêmes coins coupés. Les deux recherches (membre, serveur) sont côte à côte, puis Période, Trier par et Bots. Les lignes se replient avec la largeur ; sur téléphone : recherches en pleine largeur, Période et Trier par côte à côte, puis Bots.
- **Listes déroulantes aux couleurs du site** à la place des listes du navigateur (Période, Trier par, et le serveur favori de la page Personnaliser) : bouton à chevron, liste aux coins coupés avec un liseré de couleur, option choisie cochée, au clavier comme à la souris (flèches, Entrée, Échap, Tab, une lettre pour sauter à l'option).
  - La liste s'ouvre vers le haut quand il manque de place en dessous et ne sort jamais de l'écran.
  - Le menu natif reste dans le formulaire, caché : l'envoi des filtres, le rechargement de la liste et les lecteurs d'écran fonctionnent comme avant.

### XP & Badges
- **1 XP par message** au lieu de 5 (1 minute en vocal donne toujours 1 XP) : le vocal pèse maintenant bien plus que les messages. Les niveaux, titres, badges « Niveau », classements par XP, cartes du bot et cartes au survol sont recalculés automatiquement (rien n'est stocké), donc les membres qui écrivent beaucoup perdent quelques niveaux. La page Aide est à jour dans les 12 langues.
- **Nouveau badge « Série »** : la plus longue série de jours actifs d'affilée (vocal ou messages), sur tout l'historique. Un palier atteint reste acquis, même après une journée sans activité.
  - 7 paliers : Bronze 5 jours, Argent 10, Or 30, Platine 60, Diamant 100, Légende 250, Mythique 365.
  - Disponible partout : onglet Badges du profil, vitrine, page Personnaliser, cartes du bot, Versus, cartes au survol. Il y a maintenant 9 badges et 63 paliers.
  - Les jours sont comptés en heure UTC, pour que le badge soit le même pour tous les visiteurs. Comme dans le calendrier d'activité, une session vocale qui passe minuit compte sur les deux jours. Le résultat est mis en cache 10 minutes.
- **« Record de série » du profil sur tout l'historique** : il ne regardait que les 365 derniers jours, alors qu'il est présenté comme « Record historique ». Il affiche maintenant la même valeur que le badge Série.

### Accueil
- **Podiums « Top Membres » et « Top Serveurs » sur les 30 derniers jours** (ils prenaient tout l'historique) : ce sont maintenant les plus actifs du moment, classés par temps vocal, puis par messages en cas d'égalité. Les chiffres sont les mêmes que le filtre « 30 jours » des pages Membres et Serveurs, dont le classement est réutilisé (cache de 60 s).
  - Une étiquette « 30 derniers jours » est affichée à côté du titre, et « Voir tout le classement » ouvre la page déjà filtrée sur 30 jours.
- **Graphique d'activité, tous les jours sur l'axe** (avant, un jour sur cinq environ) : le numéro de chaque jour, avec le mois en dessous au début et à chaque 1er du mois, et un trait discret au changement de mois. Les week-ends sont plus discrets et le jour actuel est en blanc. Sur téléphone, un numéro sur deux ou trois s'affiche selon la place, en partant d'aujourd'hui.

### Corrections
- **Boutons secondaires sans fond** (« Explorer les classements », « Analyses complètes », « Personnaliser », boutons d'export et de copie de la carte) : une règle ajoutée pendant le développement de cette version avait coupé leur style. Ils retrouvent leur fond de panneau.
- **Coins coupés au survol des tuiles de chiffres** (accueil, Analyses) : le contour coloré restait coupé sur les deux diagonales, car une ancienne règle masquait les traits qui les dessinent. Les diagonales prennent maintenant la couleur du contour.

### Technique
- Polices des cartes converties depuis celles déjà hébergées par le site (`app/cards/fonts`), avec leurs licences OFL. La version d'IBM Plex Sans des cartes est renommée « HG Sans », car « Plex » est un nom réservé par sa licence pour les versions modifiées.
- Le cache des cartes tient compte de la langue.

## Version 3.25.1 - Serveurs sans Activité, Pseudos des Comptes & Coins Coupés - 26/10/2026
### Corrections
- **« None » à la place du rang** : un serveur sans activité affichait « Rang Serveur #None » et « #None » dans ses chiffres. Il affiche maintenant « Serveur non classé » / « Non classé », traduit dans les 12 langues, sans le grand « # » vide derrière le nom.
  - Toutes les fiches serveur et un panel de profils (avec et sans activité) ont été vérifiés : plus aucun « None ».
  - Carte au survol : « Non classé » à la place d'un tiret, et un nom de secours (« Membre 123… ») quand le pseudo est inconnu.
  - Versus : un membre sans pseudo connu n'affiche plus « None » dans le champ de recherche, et les noms de secours sont traduits.
- **Admin, dernières connexions sans pseudo** : les personnes connectées au site sans jamais avoir parlé là où se trouve le bot n'avaient pas de ligne côté bot, donc ni pseudo ni avatar.
  - Le site enregistre maintenant le pseudo et l'avatar Discord à la connexion (deux colonnes ajoutées automatiquement à `web_accounts`).
  - Les comptes déjà connectés les complètent à leur prochaine visite, sans déconnexion. Un compte qui ne revient pas garde son identifiant.
- **Coins coupés au survol** : les panneaux qui s'allument au survol avaient un contour coloré coupé net sur les deux diagonales. Les diagonales prennent maintenant la couleur du contour, y compris sur les panneaux sans bordure.
- **Coins encore arrondis** : les cartes des podiums de l'accueil (deux coins arrondis à côté des deux coins coupés), la pagination, les cases de la grille des horaires, les boutons pour effacer une recherche, les étapes de la page Confidentialité, et plusieurs blocs de l'admin et de la page Personnaliser.

## Version 3.25.0 - Site en 12 Langues - 25/10/2026
### Langues
- **12 langues** : français, anglais, espagnol, portugais (Brésil), italien, allemand, polonais, turc, russe, hindi, japonais et coréen.
  - Toutes les pages, onglets, graphiques, info-bulles, cartes au survol, badges, records, galerie de bannières et couleurs de profil sont traduits.
  - La page Admin reste en français et en anglais (elle s'affiche en anglais dans les autres langues).
- **Menu des langues** dans la barre de navigation : le drapeau de la langue actuelle ouvre la liste des 12 langues, chacune écrite dans sa propre langue, avec son drapeau en pixel art. Sur téléphone, c'est une ligne du menu qui s'ouvre sur place.
- **Langue du navigateur** : un nouveau visiteur arrive dans la langue de son navigateur. Sans indication (moteurs de recherche, aperçus de liens), le site reste en français ; un navigateur qui ne demande que des langues absentes reçoit l'anglais. Un choix fait dans le menu est gardé comme avant (cookie `lang`).
- **Nombres et dates dans le format de chaque langue** : 1.234,5 en allemand, 1,23,456 en hindi, « 25. Oktober 2026 », « 25 октября 2026 г. », « 2026年10月25日 »… Les jours de la semaine des grilles horaires et du calendrier d'activité suivent aussi la langue.
- **Polices** : le russe, le hindi, le japonais et le coréen, que les polices Arène ne dessinent pas, utilisent la meilleure police système de chaque appareil ; pas d'espacement des lettres dans ces écritures.
- **Pages Confidentialité et Conditions d'utilisation traduites** dans les 12 langues, avec la mention « en cas de différence, la version française fait foi ». La page Confidentialité explique maintenant la détection de la langue du navigateur (rien n'est enregistré).

### Corrections
- **Page Aide** : la carte des badges décrivait encore l'ancien système (17 badges, 4 raretés) ; elle présente les 8 badges et leurs 7 paliers.
- **Page 404** et plusieurs infobulles (« Effacer », « Tous les serveurs »…) n'existaient qu'en français.
- **Temps vocal total de l'accueil** : le séparateur des milliers était toujours celui du français.
- **Date d'arrivée sur un profil** : elle restait en français dans les autres langues.
- **Badges, onglet Badges** : un nom de badge long (allemand, russe…) poussait le palier hors de la carte sur téléphone ; le palier passe à la ligne.
- Barre de navigation : en russe, les icônes des liens se masquent jusqu'à 1 420 px pour que tout tienne.

### Technique
- `app/i18n.py` : liste des langues, langue du visiteur, traductions `tr('Français', 'English')` et formats de nombres et de dates.
- `app/locales/<langue>.json` : une traduction par langue ; `app/locales/_phrases.json` liste les phrases du site.
- `scripts/i18n_extract.py` : repère les nouvelles phrases, indique ce qui manque à chaque langue (`todo <langue>`) et vérifie que chaque traduction garde ses `{valeurs}`.
- `app/flags.py` : les 12 drapeaux en pixel art, dessinés sur une grille de 15 × 10.

## Version 3.24.0 - Nouveau Thème « Arène », Progression au Classement & Cartes au Survol - 25/10/2026
### Design
- **Nouveau thème « Arène » sur tout le site**, choisi parmi les 3 pistes de la démo.
  - Gris Discord à la place du bleu marine, accent blurple à la place du bleu ciel, sur les pages, les graphiques et les badges du site.
  - Coins coupés et formes en biseau à la place des cartes arrondies en verre dépoli. Les avatars restent ronds.
  - Polices Chakra Petch (titres, chiffres, onglets) et IBM Plex Sans (texte), hébergées sur le site : aucun appel à Google, accents français complets.
  - Barre de navigation plate collée en haut, lien actif souligné.
  - Classements : rangs en chiffres italiques or, argent et bronze, heures en étiquette blurple.
- **Icônes en pixel art** sur tout le site, dessinées sur une grille de 9 × 9 comme le logo sablier : navigation (les icônes reviennent à côté des liens), onglets, boutons, tuiles, recherche, records et badges. Elles prennent la couleur du texte autour (et la couleur du membre sur son profil). Seuls le logo Discord et les drapeaux restent tels quels ; les cartes images du bot gardent leurs icônes.
- **Logo Discord, drapeaux et image de serveur par défaut en pixel art** : le logo Discord (boutons de connexion et d'invitation, pied de page, page Aide), les drapeaux FR / EN et l'image affichée pour un serveur sans icône suivent le style des autres icônes.
- **Plus d'emoji sur le site** : ceux du Versus (trophée, couronne, catégories du comparatif, graphique, épées), les croix de la page Confidentialité, mobile / ordinateur dans l'admin et les croix « retirer le filtre » deviennent des icônes pixel. Dans les graphiques, les noms de salons et la liste des serveurs du Versus, où une icône ne peut pas s'afficher, l'emoji est simplement retiré.
- **Un peu moins uniforme** : sur l'accueil, la tuile du temps total en vocal est plus large que les trois autres, avec un chiffre plus grand.
- **Plus de peps**
  - **Une couleur par type de chiffre**, partout : vocal en blurple, messages en vert menthe (tuiles, étiquettes, courbes et calendriers), membres en violet, serveurs en corail, niveaux et XP en ambre, rang en or. Les icônes des tuiles passent sur un fond plein de leur couleur. Sur un profil, tout garde la couleur du membre.
  - **Boutons « arcade »** : ombre dure sous les boutons principaux, le bouton s'enfonce quand on clique.
  - **Grands chiffres en filigrane** derrière les titres (#1 sur Membres et Serveurs, 30J sur Analyses, 1V1 sur Versus, le rang d'un serveur, le niveau d'un membre), « 24/7 » dans l'accueil et 1, 2, 3 derrière les podiums.
  - **Halos de couleur** très doux dans le fond de toutes les pages.
  - **Podium dans les classements** : les lignes 1, 2 et 3 en or, argent et bronze, avatar du n°1 cerclé d'or avec un reflet.
  - **Animations** : les chiffres clés défilent jusqu'à leur valeur à l'ouverture, les panneaux s'allument de leur couleur au survol, le point « en ligne » pulse. Coupé si l'appareil demande moins de mouvement.
- **Petites touches**
  - Le sablier du logo se retourne toutes les 6 secondes.
  - Un reflet passe sur les badges Légende et Mythique de la vitrine et sur la 1re place des podiums.
  - Écran de chargement en sablier, seulement quand une page met plus de 0,4 s à arriver.
  - Les animations sont coupées si l'appareil demande moins de mouvement.
- Les couleurs choisies par les membres pour leur profil ne changent pas.
- Aucune déconnexion : la session n'est pas touchée.

### Badges : nouveau système
- **8 badges au lieu de 37.** Les anciens badges n'étaient que des paliers d'une même famille (Premiers Échos 1 h, Habitué du Micro 10 h… Maître de la Voix 1 000 h) : chaque famille devient un seul badge qui monte de niveau.
  - Vocal, Messages, Niveau, Classement, Serveurs, Fidélité, Activité (vocal sur 30 jours) et Polyvalence (vocal + messages).
- **7 paliers, reconnaissables à leur couleur** : Bronze, Argent, Or, Platine, Diamant, **Légende** (violet lumineux) et **Mythique**, holographique (reflets arc-en-ciel qui défilent sur le cadre, l'icône et le nom) et volontairement très difficile. Tous les badges ont les mêmes 7 paliers, donc une couleur veut dire la même difficulté partout.
  - Vocal : 1, 10, 100, 500, 1 000, 2 500, 5 000 h · Messages : 25, 250, 1 000, 5 000, 10 000, 25 000, 50 000 · Niveau : 5, 10, 20, 30, 50, 70, 90 · Classement : Top 100, 50, 25, 10, 3, n°1, n°1 avec 5 000 h · Serveurs : 2, 3, 4, 6, 8, 12, 20 · Fidélité : 30, 60, 120, 250, 365, 730, 1 095 jours · Activité : 5, 15, 40, 80, 120, 200, 300 h sur 30 jours · Polyvalence : de 10 h + 100 messages à 2 500 h + 25 000 messages.
- **Onglet Badges** : une échelle de 7 paliers par badge, le palier actuel affiché en couleur, la progression vers le suivant ; en haut, les paliers atteints sur 56 et combien de badges ont atteint chaque palier.
- **Vitrine, Personnaliser, carte au survol, cartes du bot** : chaque badge s'affiche avec son palier (« Vocal · Diamant ») dans sa couleur. Sans choix, la vitrine montre les 3 plus hauts paliers.
- **Versus** : la ligne « Badges débloqués » devient « Paliers de badges » (sur 56).
- Les badges déjà mis en vitrine sont conservés : un ancien palier (par exemple « Voix d'Or ») devient automatiquement le badge de sa famille.

### Classements
- **Progression au classement** sur les pages Membres et Serveurs : ▲ places gagnées, ▼ places perdues, « = » même place, « NOUV. » pour une entrée dans le classement.
  - Comparaison avec le même classement il y a 7 jours (la veille pour la période 24 h), calculée à partir des sessions vocales et des messages déjà enregistrés : aucune nouvelle table.
  - Suit le tri choisi (vocal, messages, XP). Le rang affiché est maintenant le vrai rang, même pendant une recherche.
- **Carte au survol** (souris uniquement) sur les membres et serveurs des classements et des podiums de l'accueil.
  - Membre : niveau et titre, progression, rang global, vocal total et 30 jours, messages, badges de la vitrine (seulement si le membre ne l'a pas masquée), date de suivi. La carte prend la couleur de profil du membre.
  - Serveur : rang, membres suivis, vocal total et 30 jours, messages, état du bot, membres en vocal, date de suivi.
  - Données chargées à la demande (`/api/hover/user/<id>`, `/api/hover/server/<id>`), en cache 2 minutes.

### Profil
- **La couleur du membre s'applique à tout son profil** : onglets, boutons, interrupteurs de période, tuiles de statistiques, étiquettes d'heures, icônes et pastilles qui restaient en blurple.
- **Nouvelle couleur par défaut : Blurple**, celle du site. Les profils jamais personnalisés passent automatiquement au blurple au premier démarrage (une seule fois). « Ciel », l'ancien défaut, reste disponible.
- **Badges** : cadres d'icônes carrés (ils étaient encore arrondis).

### Responsive
- Revue de toutes les pages et de tous les onglets, connecté et déconnecté, de 320 px (petit téléphone) à 1920 px (grand écran) : 320, 375, 414, 600, 768, 1024, 1280, 1440 et 1920 px, plus le menu mobile, la recherche et les duels du Versus.
  - Classements : colonne de rang compacte, avatars qui ne se déforment plus.
  - Tuiles de statistiques : 2 par ligne sur téléphone au lieu d'une.
  - Onglets et boutons de période : plus de lettres coupées par le biseau.
  - Profil, onglet Serveurs fréquentés : le nom du serveur n'est plus écrasé.
  - Analyses, Horaires : l'étiquette des connectés ne dépasse plus de l'écran.
  - Versus : le choix Joueur / Serveur tient sur la largeur.
  - Admin : les listes (membres et serveurs arrivés…) passent sur deux lignes au lieu de défiler de côté.
  - Barre de navigation : elle n'est plus décalée de quelques pixels quand une barre de défilement est présente.
  - Membres : la liste du filtre serveur passait sous les lignes du classement, qui apparaissaient à travers.
  - Membres : le champ du filtre serveur dépassait du cadre des filtres sur ordinateur (il prenait toute la largeur en plus de son libellé). Quand la ligne est trop courte, il passe maintenant sur une deuxième ligne.
  - Accueil sur petit téléphone (320 px) : les podiums dépassaient de l'écran ; le bouton « Voir tout » passe sous le titre quand la carte est étroite.
  - Fiche serveur, salons les plus actifs : le graphique et la liste ne poussent plus la carte hors de l'écran sur téléphone.
  - Barre de navigation entre 1025 et 1360 px : le bouton de compte, et surtout « Se connecter » pour un visiteur déconnecté, sortait de l'écran. Les liens se resserrent, puis les icônes des liens et le raccourci « Ctrl+K » se masquent, jusqu'à ce que tout tienne.
  - Plus aucun texte sous 10 px, et sur téléphone les champs de recherche, liens de classement et boutons « voir plus » ont une zone de toucher d'au moins 36 px.
  - Versus, duel de serveurs : le nombre de membres affichait « top.users_unit » au lieu de « membres » (traduction manquante, déjà présente avant cette version).

### Finitions
- **Fin des boutons « Autres sections »** en bas de chaque onglet (Analyses, profil, fiche serveur) : la barre d'onglets suffit.
- **Contour continu sur les coins coupés** : la ligne de couleur d'une boîte (bordure, trait du haut des tuiles et des records) suit maintenant aussi la diagonale des coins, au lieu de s'arrêter net. Même couleur, même épaisseur, y compris au survol.
- **Listes (membres, serveurs, membres d'un serveur, serveurs d'un profil)** : toute la ligne devient grise au survol (plus de petit cadre gris à l'intérieur), toute la ligne est cliquable et ouvre la carte d'aperçu.

## Version 3.23.1 - Connexion Stable entre les Pages & Onglets sans Texte Coupé - 24/10/2026
### Corrections
- **Déconnexions aléatoires d'une page à l'autre** (apparues avec la v3.23.0).
  - Les 4 workers Gunicorn lisent la clé de session en base au démarrage. Démarrés au même instant, l'un d'eux pouvait échouer (création concurrente de la table `web_settings`) et retomber sur une autre clé. On était alors connecté sur certaines pages et pas sur d'autres, selon le worker qui répondait.
  - La création de la table est maintenant une étape à part, dont l'erreur de concurrence est ignorée. La lecture est retentée jusqu'à 8 fois, environ 9 secondes, avant d'abandonner, et un avertissement apparaît dans les logs si un worker doit utiliser une autre clé.
  - La clé déjà enregistrée en base est conservée : aucune nouvelle déconnexion.
- **Onglets : plus aucun texte coupé.**
  - Le bloc de texte d'un onglet centré prenait la largeur du titre, si bien que le sous-titre, souvent plus long, était toujours tronqué.
  - Le bloc prend maintenant la largeur de sa ligne la plus longue.
  - Si un sous-titre ne tient pas, tous les sous-titres de la barre sont masqués.
  - Si même un titre ne tient pas, chaque onglet garde sa largeur naturelle et la barre défile.
- **Onglets sur téléphone** : une grille au lieu d'une barre qui défile, avec toutes les sections visibles d'un coup, l'icône au-dessus du titre, 3 ou 4 par ligne (3 × 2 pour l'admin).

## Version 3.23.0 - Vraie Date d'Arrivée des Serveurs, Ancienneté des Compagnons & Sessions Durables - 23/10/2026
### Corrections
- **Date d'arrivée des serveurs** : 45 serveurs sur 49 affichaient le 4 octobre 2026.
  - Cause : la colonne `servers.first_tracked_at` a été ajoutée ce jour-là avec `DEFAULT CURRENT_TIMESTAMP`, si bien que tous les serveurs déjà connus ont reçu la date de la migration.
  - La date affichée est maintenant la plus ancienne entre `first_tracked_at` et la première ligne de statistiques du serveur.
  - Partout où elle apparaît : fiche serveur, carte `/server` (« Tracked since »), et dans l'admin les 30 derniers serveurs arrivés ainsi que le graphique des arrivées par mois.
  - Migration facultative `database/migrations/2026-10-23_web_v3.23.0_server_first_tracked_fix.sql` : elle corrige aussi les dates enregistrées, et ne fait que les avancer.

### Profil
- **Compagnons vocaux fréquents** : mention discrète « Données depuis le … », avec une infobulle explicative.
  - C'est la première session vocale du membre enregistrée avec son salon.
  - Les sessions plus anciennes, archivées sans salon, ne permettent pas de savoir qui était ensemble.

### Connexion
- **Les membres restent connectés après une mise à jour.**
  - Sans `SECRET_KEY`, `FLASK_SECRET_KEY` ni `DISCORD_CLIENT_SECRET`, la clé qui signe le cookie de session était un fichier du conteneur, perdu à chaque redéploiement, ce qui déconnectait tout le monde.
  - La clé est maintenant créée une seule fois en base (table `web_settings`), puis réutilisée par tous les workers et à chaque démarrage.
  - Si l'une de ces variables est déjà définie, rien ne change.
  - Dans ce cas précis, cette mise à jour déconnecte les membres une dernière fois.
- Admin, onglet Technique : nouvelle tuile **« Clé de session »**, qui indique d'où vient la clé. Elle passe en rouge si les membres seront déconnectés à chaque mise à jour.

## Version 3.22.0 - Admin Réorganisé & Onglets Mieux Alignés - 23/10/2026
### Admin
- **Six onglets regroupés par thème**, avec une icône chacun :
  - **Vue d'ensemble** (nouvel onglet par défaut) : 8 chiffres clés (visites, visiteurs, comptes liés, profils personnalisés, membres présents, serveurs, commandes, erreurs serveur), chacun cliquable vers son onglet, et la courbe des visites sur 30 jours ;
  - **Site web** (ex-Fréquentation) ;
  - **Comptes** : connexions et personnalisation des profils, réunies en un seul onglet, en deux parties titrées ;
  - **Communauté** : membres présents, derniers membres et serveurs arrivés, arrivées et départs du bot ;
  - **Bot** : état du bot et commandes ;
  - **Technique** : santé du site et taille des tables de la base.
- La rangée de 4 chiffres au-dessus des onglets passe dans la Vue d'ensemble, ce qui allège le haut de la page.
- Titres de partie dans les onglets qui regroupent plusieurs sujets.
- Les anciens liens (`#tab-health`, `#tab-commands`, `#tab-custom`) ouvrent le bon onglet.

### Onglets (toutes les pages)
- Icône et titre **centrés** dans leur part de la barre.
- Un onglet n'est plus jamais plus étroit que son titre : sur écran étroit, la barre défile au lieu de faire se chevaucher les titres, avec un fondu à droite tant que des onglets sont cachés (désormais sur toutes les tailles d'écran).
- Les sous-titres sont coupés avec « … » quand la place manque, au lieu d'élargir la barre.

## Version 3.21.0 - Passe Mobile, Déconnexion & Connexion Discord sur Téléphone - 23/10/2026
### Téléphone
- **Menu burger refait** :
  - panneau opaque (le texte de la page ne transparaît plus), avec la page assombrie et bloquée derrière ;
  - **carte du compte en haut**, toujours ouverte (avatar, pseudo, Mon profil, Admin, Déconnexion) au lieu d'un menu déroulant imbriqué ;
  - liens de 50 px de haut, recherche en pleine largeur sans le raccourci « Ctrl+K » inutile sur téléphone, langue et Inviter côte à côte ;
  - le bouton « Se connecter » passe en tête quand on n'est pas connecté ;
  - il se ferme au toucher à l'extérieur, sur un lien, avec Échap, ou quand l'écran devient assez large.
- **Membres / Serveurs** :
  - suppression du grand vide sous la recherche (le bloc de recherche prenait 220 px de haut en affichage vertical) ;
  - Période et Trier par côte à côte ;
  - le pseudo passe au-dessus du badge de niveau au lieu d'être tronqué.
- **Accueil** : les 4 chiffres clés en grille 2 × 2 compacte (269 px au lieu de 688 px).
- Boutons de filtre et onglets de personnalisation d'au moins 40 à 44 px de haut, plus faciles à toucher.
- Champs de saisie à 16 px : l'iPhone ne zoome plus tout seul quand on touche un champ.

### Corrections
- **Déconnexion** : retour à l'accueil. Avant, on revenait à la page précédente, ce qui donnait une erreur 404 depuis `/admin`, réservée aux admins connectés.
- **Connexion Discord sur téléphone** :
  - plus de fenêtre popup, une navigation normale à la place : une fenêtre ouverte par script n'est jamais confiée à l'application Discord ;
  - adresse d'autorisation officielle `discord.com/oauth2/authorize`, sans `/api/` : l'ancienne forme empêchait Android d'ouvrir l'application.
  - Discord ne garantit pas ce passage par l'application. Si elle ne s'ouvre pas, la connexion se fait dans le navigateur, une seule fois.

## Version 3.20.0 - Onglets Plus Clairs & Admin : Arrivées et Membres Présents - 23/10/2026
### Navigation dans les pages (profil, fiche serveur, Analyses, admin)
- **Les onglets deviennent une vraie barre de sections.**
  - Avant, des boutons séparés ressemblaient aux filtres (Vocal / Messages…), et beaucoup de visiteurs ne voyaient pas que c'étaient des onglets.
  - Maintenant, une seule barre regroupe les sections. Celle qui est ouverte est surélevée et soulignée par la couleur du profil.
- **Un sous-titre sous chaque onglet** dit ce qu'il contient : « Séries, calendrier, sessions », « Évolution et répartition », « Présence et heures de pointe »…
- **« Autres sections » en bas de chaque onglet** : des boutons vers les autres sections, qui remontent jusqu'à la barre.
- Sur mobile :
  - la barre défile horizontalement, avec un fondu à droite tant que d'autres sections sont cachées ;
  - la section ouverte reste toujours visible dans la barre ;
  - les sous-titres sont masqués pour gagner de la place.
- Le style des onglets, copié dans trois fichiers CSS, est réuni dans `styles.css`.

### Admin (onglet Bot & base)
- **« Membres présents sur les serveurs »** : les personnes uniques vues par le bot sur tous ses serveurs, y compris celles qui n'ont jamais parlé ni rejoint un vocal. Chacune compte une fois, même présente sur plusieurs serveurs, et les bots sont exclus.
  - Le total, en ligne, **jamais actifs** (nombre et %), déjà actifs, serveurs par membre ;
  - une courbe sur 30 jours, qui commence au premier relevé, sans faux zéros.
  - Données relevées par le bot v3.3.0 toutes les 15 minutes (table `bot_member_snapshots`). Un message s'affiche tant qu'aucun relevé n'existe.
- **30 derniers membres arrivés** : la date de leur première activité vue par Hourglass, et le serveur où elle a eu lieu.
- **30 derniers serveurs arrivés** : la date d'ajout du bot, et son départ éventuel.
- Ces listes défilent et ont un champ de recherche, comme les autres longues listes de l'admin.

## Version 3.19.0 - Nouvelles Cartes de Statistiques - 20/10/2026
### Cartes (bot Discord et cartes SVG intégrables)
- **Toutes les cartes sont refaites dans le style du site**, et le site les dessine aussi pour le bot : une seule mise en forme pour les deux.
  - Le bot récupère des PNG via `/internal/card/{member,versus,top,server}.png`, protégés par la variable `CARD_TOKEN`, à partager avec le bot.
  - Les cartes publiques `/api/card/...` gardent leurs adresses, en SVG.
- **Pensées pour être lues en petit**, sans cliquer :
  - canevas de 1200 px de large, rendu net en 2x ;
  - gros chiffres, au moins 24 px de texte, au maximum 4 statistiques principales ;
  - police Inter embarquée (licence OFL), textes toujours en anglais pour toutes les communautés.
- **Carte de profil** (`/stats`, `/allstats`) :
  - elle reprend la **couleur**, la **bannière** de la galerie, le **fond uni** et les **3 badges en vitrine** du profil, ou les plus rares si le membre n'en a pas choisi ;
  - niveau et titre, rang, barre d'XP, puis 4 tuiles : vocal, messages, 30 derniers jours et **« Tracked since »**.
  - « Tracked since » remplace l'ancienne date d'arrivée sur le serveur Discord : c'est la première activité vue par Hourglass **sur ce serveur** pour `/stats`, et **sur tous les serveurs** pour `/allstats`.
- **Carte de duel** (`/versus`), refaite :
  - chaque camp a la couleur de profil de son membre, avec une seconde couleur si les deux se ressemblent ;
  - un verdict (« eluen wins 4–1 »), puis 5 manches : vocal, messages, 30 derniers jours, rang, badges. Le gagnant de chaque manche est mis en avant ;
  - elle compare sur le serveur ou sur tous les serveurs. Nouvelle carte SVG `/api/card/versus/{user1}/{user2}[?server=]`.
- **Top 10** (`/top`, `/alltop`) :
  - podium des 3 premiers, puis les places 4 à 10 sur deux colonnes ;
  - suppression du niveau estimé à partir d'une seule mesure, qui était trompeur ;
  - même classement que la page Membres, filtres vocal / messages et toutes périodes / 30 jours / 7 jours ;
  - avatars téléchargés en parallèle : ≈ 3 s → 0,6 s.
- **Carte serveur** (`/server`) : rang, 4 tuiles (vocal, messages, membres, en vocal maintenant) et la courbe du vocal sur 30 jours.
- Les emojis et caractères absents de la police (emojis, CJK) sont retirés des noms au lieu d'afficher des carrés vides.
- Cartes mises en cache 2 minutes dans un cache dédié et limité (48 entrées) : les images intégrées n'encombrent pas la mémoire des workers.
- Ancien code des cartes SVG supprimé de `routes/api.py`, remplacé par `app/cards/` (design, données, mise en page) et `routes/cards.py`.

### Déploiement
- Nouvelles dépendances : `Pillow`, `resvg-py`, `fonttools`. Ce sont des wheels Linux précompilées, sans paquet système à installer.
- Nouvelle variable **`CARD_TOKEN`** : une chaîne secrète, à mettre à la même valeur sur le bot (v3.2.0).

## Version 3.18.1 - Graphique de Présence Plus Rapide - 19/10/2026
### Performances
- **Présence des membres** (page Analyses) : le regroupement « un point par heure » est fait par PostgreSQL (`DISTINCT ON` sur l'heure locale) et plus en Python.
  - Avant, les relevés des 7 derniers jours étaient tous envoyés au site : avant le bot v3.1.1, il en enregistrait un toutes les 8 secondes environ, soit des dizaines de milliers de lignes.
  - Mesuré sur une copie des données de prod : la courbe sur 7 jours passe de **≈ 400 ms à ≈ 30 ms**, et le calcul complet de la page Analyses de **≈ 450 ms à ≈ 125 ms**. Le résultat est identique, point par point.
- Migration facultative `database/migrations/2026-10-19_web_v3.18.1_missing_indexes.sql` : crée les 4 index composites prévus dans `schema_v3.sql` qui manquent en prod (activité d'un membre ou d'un serveur sur une période), sans bloquer les tables.

## Version 3.18.0 - Pas de Bannière par Défaut & Onglet Apparence Plus Lisible - 19/10/2026
### Personnalisation
- **Aucune bannière par défaut**.
  - Une bannière ne s'affiche que si le membre a choisi une image de la galerie.
  - Les anciens réglages sans image choisie sont lus comme « Aucune » : anciens modes Discord ou dégradé, ou galerie sans image.
  - Quand on ouvre la galerie, l'image « Aurore » est présélectionnée.
- **Onglet Apparence réorganisé** :
  - une courte introduction rappelle que l'aperçu change en direct et qu'il faut enregistrer ;
  - chaque réglage a une icône, un titre, une description courte et, à droite, le **choix actuel** (« Corail », « Galaxie », « Aucune », « Par défaut »…), mis à jour en direct ;
  - les options sont alignées sous le titre ; « Aucune » est en premier pour la bannière, puis « Image de la galerie » ;
  - le **nom de chaque image** s'affiche sous sa miniature dans la galerie, au lieu d'une simple infobulle.
- Admin : un profil compte comme personnalisé pour sa bannière seulement si une image est choisie.

### Base de données
- Valeur par défaut de `user_profile_settings.banner_mode` : `none`.
- Migration facultative `database/migrations/2026-10-19_web_v3.18.0_banner_none_default.sql` : elle passe à `none` les lignes qui n'ont pas d'image choisie.

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
