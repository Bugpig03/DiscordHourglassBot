
# Hourglass - API - Documentation

Hourglass propose une API publique et sans clé d'authentification afin de récupérer facilement les données statistiques au format **JSON**, ainsi que des **cartes graphiques vectorielles en SVG** prêtes à être intégrées directement dans vos bots Discord, sites web ou dashboards externes.

## Base URL

```http
https://hourglass.mike-server.fr/
```
*(ou `http://localhost:5002/` en environnement de développement local)*

---

## 📑 Sommaire
1. [Endpoints JSON](#1-endpoints-json)
   - [Tous les utilisateurs](#tous-les-utilisateurs)
   - [Tous les serveurs](#tous-les-serveurs)
   - [Détail d'un utilisateur](#détail-dun-utilisateur)
   - [Détail d'un serveur](#détail-dun-serveur)
   - [Statistiques globales du bot](#statistiques-globales-du-bot)
   - [Statistiques d'un utilisateur (Global)](#statistiques-dun-utilisateur-global)
   - [Statistiques d'un utilisateur sur un serveur](#statistiques-dun-utilisateur-sur-un-serveur)
   - [Recherche rapide (Ctrl+K)](#recherche-rapide)
2. [Endpoints Cartes Graphiques SVG (v2.5.4)](#2-endpoints-cartes-graphiques-svg-v254)
   - [Profil utilisateur global (!allstats)](#profil-utilisateur-global-allstats)
   - [Profil utilisateur sur un serveur (!stats)](#profil-utilisateur-sur-un-serveur-stats)
   - [Top 10 vocal d'un serveur (!top)](#top-10-vocal-dun-serveur-top)
   - [Top 10 vocal global (!alltop)](#top-10-vocal-global-alltop)
   - [Statistiques d'un serveur (!server)](#statistiques-dun-serveur-server)
   - [Tableau d'aide des commandes (!aide)](#tableau-daide-des-commandes-aide)
3. [Intégration Discord Bot](#3-intégration-discord-bot)

---

## 1. Endpoints JSON

### Tous les utilisateurs
Récupère la liste de tous les utilisateurs enregistrés.
```http
GET /api/users
```
#### Réponse :
```json
[
  {
    "avatar": "https://cdn.discordapp.com/avatars/12345678910/a_a719ace11zaede1498769702d64.gif?size=1024",
    "user_id": 12345678910,
    "username": "username00"
  },
  {
    "avatar": null,
    "user_id": 987654321,
    "username": "username01"
  }
]
```

---

### Tous les serveurs
Récupère la liste de tous les serveurs suivis.
```http
GET /api/servers
```
#### Réponse :
```json
[
  {
    "avatar": "https://cdn.discordapp.com/icons/789456123/797e95d321ddda0e5ad6628cc9b.png?size=1024",
    "server_id": 789456123,
    "servername": "Servername00"
  },
  {
    "avatar": "https://cdn.discordapp.com/icons/369258147/ab69e6c99fd7ef9cfb83a6a8f.png?size=1024",
    "server_id": 369258147,
    "servername": "Servername01"
  }
]
```

---

### Détail d'un utilisateur
Récupère les informations d'un utilisateur par son ID Discord.
```http
GET /api/user/{user_id}
```
| Paramètre | Type | Description |
| :--- | :--- | :--- |
| `user_id` | `int` | **Obligatoire** - Identifiant Discord de l'utilisateur |

#### Réponse :
```json
{
  "avatar": "https://cdn.discordapp.com/avatars/1234567890/abc1234.png",
  "user_id": 1234567890,
  "username": "Malo"
}
```

---

### Détail d'un serveur
Récupère les informations d'un serveur par son ID Discord.
```http
GET /api/server/{server_id}
```
| Paramètre | Type | Description |
| :--- | :--- | :--- |
| `server_id` | `int` | **Obligatoire** - Identifiant Discord du serveur |

#### Réponse :
```json
{
  "avatar": "https://cdn.discordapp.com/icons/458361525162475520/def5678.png",
  "server_id": 458361525162475520,
  "servername": "Royaume"
}
```

---

### Statistiques globales du bot
Récupère les totaux cumulés sur l'ensemble de la base de données.
```http
GET /api/stats
```
#### Réponse :
```json
{
  "messages": 1000000,
  "scope": "global",
  "score": 0,
  "seconds": 5000000
}
```

---

### Statistiques d'un utilisateur (Global)
Récupère les statistiques cumulées d'un utilisateur sur tous les serveurs où il est présent.
```http
GET /api/stats/{user_id}
```
| Paramètre | Type | Description |
| :--- | :--- | :--- |
| `user_id` | `int` | **Obligatoire** - Identifiant Discord de l'utilisateur |

#### Réponse :
```json
{
  "messages": 3000,
  "scope": "user:1234567890",
  "score": 0,
  "seconds": 36000,
  "user_id": 1234567890
}
```

---

### Statistiques d'un utilisateur sur un serveur
Récupère les statistiques précises d'un utilisateur sur une guilde spécifique.
```http
GET /api/stats/{user_id}/{server_id}
```
| Paramètre | Type | Description |
| :--- | :--- | :--- |
| `user_id` | `int` | **Obligatoire** - Identifiant Discord de l'utilisateur |
| `server_id` | `int` | **Obligatoire** - Identifiant Discord du serveur |

#### Réponse :
```json
{
  "messages": 2691,
  "scope": "user:1234567890-server:458361525162475520",
  "score": 0,
  "seconds": 18200,
  "server_id": 458361525162475520,
  "user_id": 1234567890
}
```

---

### Recherche rapide
Effectue une recherche textuelle rapide parmi les utilisateurs et les serveurs (autocomplétion).
```http
GET /api/search?q={query}&type={all|users|servers}&limit={limit}
```
| Paramètre | Type | Défaut | Description |
| :--- | :--- | :--- | :--- |
| `q` | `string` | `""` | **Obligatoire** - Texte recherché (ex: `hyst`) |
| `type` | `string` | `all` | `all`, `users` ou `servers` |
| `limit` | `int` | `6` | Nombre maximal de résultats par catégorie (1 à 20) |

---

## 2. Endpoints Cartes Graphiques SVG (v2.5.4)

Les endpoints ci-dessous renvoient directement un fichier vectoriel avec l'en-tête HTTP `Content-Type: image/svg+xml`.

> [!TIP]
> **Résolution flexible** : Pour tous les endpoints utilisateurs, vous pouvez renseigner indifféremment le **pseudonyme Discord** (`hyst3ry`) ou l'**ID numérique** (`303525237012692994`).
>
> **Langue** : Ajoutez le paramètre d'URL `?lang=en` pour obtenir le visuel en anglais (par défaut `?lang=fr`).
>
> **Gestion d'erreur 404** : Si l'utilisateur ou le serveur est introuvable, l'API renvoie une carte d'erreur SVG stylisée pour éviter les images brisées dans Discord.

---

### Profil utilisateur global (!allstats)
Génère la carte de profil d'un utilisateur avec ses métriques globales, son rang mondial, son niveau XP, sa barre de progression et ses 3 meilleurs badges SVG.

```http
GET /api/card/user/{user_identifier}
GET /api/card/allstats/{user_identifier}
```
- **Dimensions** : 540 × 210 px
- **Paramètres** :
  - `{user_identifier}` : `username` ou `user_id`.
  - `?lang=fr` ou `?lang=en` (optionnel).

---

### Profil utilisateur sur un serveur (!stats)
Génère la carte de profil d'un joueur restreinte à un serveur particulier : rang au sein de la guilde, heures de vocal, messages, niveau / XP serveur et date d'arrivée.

```http
GET /api/card/user/{user_identifier}/server/{server_id}
GET /api/card/stats/{user_identifier}/{server_id}
```
- **Dimensions** : 540 × 215 px
- **Paramètres** :
  - `{user_identifier}` : `username` ou `user_id`.
  - `{server_id}` : Identifiant numérique du serveur.
  - `?lang=fr` ou `?lang=en` (optionnel).

---

### Top 10 vocal d'un serveur (!top)
Génère le classement sous forme de tableau SVG des 10 membres les plus actifs en vocal sur le serveur sélectionné (médailles or/argent/bronze, avatars, niveaux, temps et messages).

```http
GET /api/card/top/server/{server_id}
GET /api/card/server/{server_id}/top
```
- **Dimensions** : 560 × 535 px
- **Paramètres** :
  - `{server_id}` : Identifiant numérique du serveur.
  - `?lang=fr` ou `?lang=en` (optionnel).

---

### Top 10 vocal global (!alltop)
Génère le classement général des 10 utilisateurs les plus actifs en vocal sur l'ensemble de tous les serveurs du bot Hourglass.

```http
GET /api/card/top
GET /api/card/top/global
GET /api/card/alltop
```
- **Dimensions** : 560 × 535 px
- **Paramètres** :
  - `?lang=fr` ou `?lang=en` (optionnel).

---

### Statistiques d'un serveur (!server)
Génère la carte récapitulative des statistiques d'une guilde : temps vocal total cumulé, volume de messages, nombre de membres suivis, rang du serveur, date d'enregistrement et mise en avant du **Champion vocal du serveur**.

```http
GET /api/card/server/{server_id}
```
- **Dimensions** : 540 × 225 px
- **Paramètres** :
  - `{server_id}` : Identifiant numérique du serveur.
  - `?lang=fr` ou `?lang=en` (optionnel).

---

### Tableau d'aide des commandes (!help / !aide)
Génère un tableau élégant récapitulant les commandes disponibles du bot, leurs syntaxes dorées et leurs descriptions.

```http
GET /api/card/commands
GET /api/card/help
GET /api/card/aide
```
- **Dimensions** : 960 × 360 px
- **Paramètres** :
  - `?lang=fr` ou `?lang=en` (optionnel).

---

## 3. Intégration Discord Bot

### Exemple en Python (`discord.py` / `nextcord` / `disnake`)
Puisque Discord affiche directement les URLs d'images dans les embeds :

```python
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!")

BASE_API = "https://hourglass.mike-server.fr/api/card"

@bot.command(name="allstats")
async def allstats_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    image_url = f"{BASE_API}/user/{target.id}?lang=fr"
    
    embed = discord.Embed(color=0x38bdf8)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

@bot.command(name="stats")
async def stats_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    image_url = f"{BASE_API}/user/{target.id}/server/{ctx.guild.id}?lang=fr"
    
    embed = discord.Embed(color=0x38bdf8)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

@bot.command(name="top")
async def top_cmd(ctx):
    image_url = f"{BASE_API}/top/server/{ctx.guild.id}?lang=fr"
    embed = discord.Embed(color=0x38bdf8)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

@bot.command(name="alltop")
async def alltop_cmd(ctx):
    image_url = f"{BASE_API}/top?lang=fr"
    embed = discord.Embed(color=0x38bdf8)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

@bot.command(name="server")
async def server_cmd(ctx):
    image_url = f"{BASE_API}/server/{ctx.guild.id}?lang=fr"
    embed = discord.Embed(color=0x818cf8)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

@bot.command(name="aide")
async def aide_cmd(ctx):
    image_url = f"{BASE_API}/commands?lang=fr"
    embed = discord.Embed(color=0xf59e0b)
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)
```

### Exemple en JavaScript (`discord.js v14`)
```javascript
const { EmbedBuilder } = require('discord.js');

const BASE_API = 'https://hourglass.mike-server.fr/api/card';

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;

    if (message.content === '!alltop') {
        const embed = new EmbedBuilder()
            .setImage(`${BASE_API}/top?lang=fr`);
        await message.channel.send({ embeds: [embed] });
    }

    if (message.content === '!aide') {
        const embed = new EmbedBuilder()
            .setImage(`${BASE_API}/commands?lang=fr`);
        await message.channel.send({ embeds: [embed] });
    }
});
```

