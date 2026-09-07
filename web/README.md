# WEB APP - Hourglass Dashboard

## Description

Application web moderne permettant de visualiser et d'analyser en temps réel les statistiques récoltées par le bot Discord Hourglass (temps passé en vocal, volume de messages textuels, classements, progression et analyses graphiques).

---

## 🚀 Dernières Nouveautés & Mises à Jour (Version 2.4 - 05/09/2026)

L'ensemble des fonctionnalités ci-dessous a été développé sans aucune altération du schéma de la base de données (calculs purs en mémoire et temps réel) :

### 1. ⚡ Système de Gamification en Temps Réel (Niveaux & XP)
- **Moteur d'Expérience** (`app/gamification.py`) :
  - **Formule** : $1\text{ minute en vocal} = 1\text{ XP}$, $1\text{ message} = 5\text{ XP}$.
  - **Courbe quadratique** : $\text{Niveau} = \lfloor\sqrt{\text{XP} / 100}\rfloor + 1$.
  - Paliers progressifs avec calcul du pourcentage de complétion du niveau en cours.
- **Titres Honorifiques Dynamiques** :
  - Déblocage automatique de titres selon le niveau (ex : *Initié Actif*, *Membre Confirmé*, *Expert des Ondes*, *Vétéran de l'Éther*, *Grand Maître*, *Légende Hourglass*).
- **Carte d'Expérience sur le Profil** (`user_profile.html`) :
  - Affichage visuel du niveau, titre, jauge animée de progression vers le palier suivant, et métriques détaillées.
- **Documentation Didactique** (`supports.html`) :
  - Explication claire et illustrée du système d'expérience sur la page Support.

### 2. 🎖️ 37 Badges Équitables avec Icônes Vectorielles SVG (Zéro Émoji)
- **Design Vectoriel Moderne** :
  - Remplacement de 100% des anciens émojis par de vraies icônes vectorielles SVG épurées (`viewBox="0 0 24 24"`), sobres et élégantes.
  - Teintes dynamiques selon la rareté :
    - **Commune** : Vert émeraude (`#10b981`)
    - **Rare** : Bleu cyan (`#38bdf8`)
    - **Épique** : Violet améthyste (`#c084fc`)
    - **Légendaire** : Or ambré (`#fbbf24`)
    - **Verrouillé** : Ardoise discrète (`#64748b`) avec pastille cadenas en surimpression.
- **Progression 100% Globale et Équitable (Non Punitive)** :
  - Suppression de tous les badges restrictifs monoserveur (comme les anciens « Fidèle au Poste » et « Âme du Serveur »).
  - Tous les critères se basent sur le cumul global du joueur : être sur plusieurs serveurs ne pénalise jamais l'obtention d'un badge.
  - Répartition équilibrée :
    - 7 badges vocaux (1h, 10h, 50h, 100h, 200h, 500h, 1 000h).
    - 7 badges messages (25, 250, 500, 1 000, 2 500, 5 000, 10 000 msgs).
    - 6 paliers de niveau (Niveau 5, 10, 15, 20, 30, 50).
    - 3 distinctions de classement (Top 50, Top 10, Podium Top 3).
    - 4 badges d'exploration de communautés (2, 3, 4 et 6 serveurs).
    - 4 badges d'ancienneté fidèle (30 jours, 60 jours, 120 jours, 250 jours).
    - 3 badges de dynamisme récent (5h, 15h, 40h de vocal sur 30 jours).
    - 3 badges de polyvalence mixte (10h/100m, 50h/500m, Virtuose 100h/1 000m).

### 3. 🖼️ Carte de Profil Exportable (API SVG Haute Définition)
- **Endpoint API** (`/api/card/user/<username>`) :
  - Génération à la volée d'une carte SVG vectorielle avec avatar, statistiques vocales, messages, rang global, niveau actuel et les 3 badges majeurs débloqués.
- **Modale d'Exportation Intégrée** :
  - Bouton d'export direct sur le profil avec fenêtre modale offrant prévisualisation, lien direct, et snippets prêts à l'emploi en Markdown et HTML.

### 4. 🏆 Classement Top : Tri par Niveau/XP et Filtres Automatiques
- **Nouveau Filtre « Niveau & XP »** :
  - Option de tri `sort_by=xp` sur la page `/top/users` avec affichage d'une pilule dorée dédiée (`★ XX XXX XP`).
- **Application Instantanée des Filtres** :
  - Changement automatique à la sélection sans devoir appuyer sur un bouton « Appliquer » (boutons supprimés pour une interface allégée et réactive).

### 5. 🏷️ Affichage Systématique du Niveau à Côté des Pseudos
- Intégration du composant `.user-level-tag` (`Nv. X` en français / `Lv. X` en anglais) avec code couleur par palier (Novice, Adepte, Vétéran, Maître) sur :
  - Le classement Top Utilisateurs (`top_users.html`).
  - L'annuaire global des utilisateurs (`users.html`).
  - La liste des membres d'un serveur (`server_profile.html`).
  - Les menus déroulants de recherche en direct.

### 6. 🔍 Recherche Instantanée Globale (Ctrl+K) & Menus Déroulants Locaux
- **Palette de Commande Rapide** :
  - Déclenchement au raccourci clavier `Ctrl + K` (mis à jour pour Windows/Linux au lieu de Cmd+K).
  - Navigation complète au clavier (`↑`, `↓`, `Entrée`, `Échap`).
- **Barres de Recherche Locales Améliorées** :
  - Sur les pages `/users` et `/servers`, la recherche affiche désormais les résultats en temps réel dans un menu déroulant dynamique sans quitter la page.

### 7. 📄 Affichage de 100 Éléments par Page
- Passage de `USERS_PER_PAGE` et `SERVERS_PER_PAGE` de 30 à **100** sur les annuaires `/users` et `/servers`.
- Recalcul automatique de la pagination et réduction drastique du nombre de pages à parcourir.

### 8. 🎨 Ergonomie de la Barre de Navigation & Design
- **Suppression du Module Versus** : retrait complet de la route `/compare` et des éléments d'interface associés.
- **En-tête Rangé & Épuré** : conteneur de sélection de page centré, suppression du débordement du bouton Discord.
- **Typographie des Nombres** : séparateurs de milliers avec espaces (`thousands_fr`) sur les statistiques clés et graphiques pour une lecture optimale.

### 9. 🐛 Correctif Graphiques d'Historique
- Correction du parsing des dates dans `graphs.html` (résolution du problème d'affichage « Invalid Date » sur les points de données mensuels).

### 10. 🌐 Internationalisation Bilingue (FR / EN) & Footer
- Support bilingue intégral français et anglais géré par cookie avec persistance.
- Pied de page mis à jour : **`version 2.5.4 - 07/09/2026`**.

---

## 🛠️ Déploiement

Pour déployer l'application, utilisez l'image Docker officielle :
```bash
docker pull bugpig/hourglass_web
```

### Variables d'Environnement

Définissez les variables d'environnement suivantes avant de lancer l'application :

| Variable | Description |
|---|---|
| `POSTGRESQL_DBNAME` | Nom de la base de données PostgreSQL |
| `POSTGRESQL_USER` | Utilisateur PostgreSQL |
| `POSTGRESQL_PASSWORD` | Mot de passe PostgreSQL |
| `POSTGRESQL_HOST` | Hôte du serveur PostgreSQL |
| `POSTGRESQL_PORT` | Port du serveur PostgreSQL (ex: 5432) |
| `SECRET_KEY` | Clé secrète pour Flask et la gestion des sessions |

---

## 🧪 Lancement Local

```bash
# Installation des dépendances
pip install -r requirements.txt

# Lancement du serveur de développement
python run.py
```
Accédez au tableau de bord sur `http://127.0.0.1:5002`.