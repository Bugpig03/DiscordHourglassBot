# Profil top.gg d'Hourglass

Tout ce qu'il faut pour remplir la page d'édition du bot : **top.gg → ton profil → Hourglass → Edit**.

## 1. Short description (moins de 140 caractères)

C'est le texte affiché dans les résultats de recherche : il compte beaucoup pour être trouvé.

**Anglais (recommandé, 127 caractères)**

```
Voice & message leaderboards for your server: stat cards, XP levels, 63 badge tiers, streaks and a web dashboard. 12 languages.
```

**Français (122 caractères)**

```
Classements vocal et messages pour ton serveur : cartes de stats, niveaux XP, badges, séries et dashboard web. 12 langues.
```

## 2. Long description

Copie tout le contenu d'un des deux fichiers (Markdown + un peu de HTML, accepté par top.gg) :

- `long-description-en.md` : anglais, recommandé (la majorité des visiteurs de top.gg lisent l'anglais) ;
- `long-description-fr.md` : la même page en français.

Une seule description est possible sur top.gg : choisis la langue de ton public principal.

## 3. Prefix

```
/
```

## 4. Categories (12 maximum)

Tape chaque nom puis Entrée, sans `#`. Si top.gg propose une catégorie existante au nom proche, prends la sienne : ce sont celles que les visiteurs filtrent.

```
Leveling
Statistics
Leaderboard
Utility
Social
Fun
Voice
Analytics
Activity
Community
Ranking
Multilingual
```

## 5. Languages (12 maximum)

English, French, Spanish, Portuguese, Italian, German, Polish, Turkish, Russian, Hindi, Japanese, Korean.

## 6. Liens

| Champ | Valeur |
|---|---|
| Invite URL | `https://discord.com/oauth2/authorize?client_id=1210665993328926750` |
| Support URL | `https://discord.gg/WU3mTwkGZV` (invitation sans expiration, à vérifier dans Discord) |
| Website | `https://hourglassbot.net` |

## 7. Les images : comment ça marche

top.gg n'a pas de bouton « ajouter une image » dans la description : une image s'insère avec un **lien vers une image hébergée en ligne**. Dans la description longue, c'est déjà fait :

```html
<img src="https://hourglassbot.net/static/promo/banner.png" width="100%">
```

Les images sont hébergées sur ton propre site, dans `web/app/static/promo/` :

| Fichier | Contenu |
|---|---|
| `banner.png` | Bannière Hourglass (titre, slogan, points forts) |
| `features.png` | Les 4 points forts : vocal, classements, cartes, XP et badges |
| `card-stats.png` | Une vraie carte `/stats` (ton profil, en anglais) |
| `card-help.png` | La carte d'aide (non utilisée dans la description, en réserve) |

**Important** : elles ne seront visibles qu'une fois le site redéployé avec ce dossier. Avant de coller la description sur top.gg, vérifie que `https://hourglassbot.net/static/promo/banner.png` s'ouvre dans ton navigateur.

Pour changer une image : remplace le fichier, redéploie, et garde le même nom (top.gg peut garder l'ancienne en cache quelques heures).

## 8. Pour attirer plus de monde

- **Votes** : chaque vote fait monter le bot dans les classements de top.gg. Rappelle aux membres de ton serveur de support de voter (sans récompense liée à un autre bot, interdit par les règles).
- **Avis** : demande à quelques serveurs actifs de laisser un avis, ça rassure les nouveaux visiteurs.
- **Avatar** : l'avatar Discord du bot est celui affiché sur top.gg. Un avatar net et reconnaissable (le sablier) aide dans les listes.
