
# Hourglass - API - Documentation

Hourglass propose une API publique et sans clé d'authentification afin de récupérer facilement les données statistiques au format **JSON**, ainsi que des **cartes graphiques vectorielles en SVG** prêtes à être intégrées directement dans vos bots Discord, sites web ou dashboards externes.

## Base URL

```http
https://hourglassbot.net/
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
2. [Endpoints Cartes Graphiques SVG (v2.6.0)](#2-endpoints-cartes-graphiques-svg-v260)
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

## 2. Endpoints Cartes Graphiques SVG (v3.19.0)

Les endpoints ci-dessous renvoient une carte vectorielle autonome (`Content-Type: image/svg+xml`), avec la même mise en forme que les images du bot Discord : style du site, police Inter et textes en anglais.

> [!TIP]
> **Résolution flexible** : pour les membres, utilisez indifféremment le **pseudonyme Discord** (`hyst3ry`) ou l'**ID numérique** (`303525237012692994`).
>
> **Taille** : les cartes sont dessinées sur un canevas de 1200 px de large et s'affichent à 600 px (nettes sur les écrans haute densité). La hauteur dépend du contenu.
>
> **Personnalisation** : les cartes d'un membre reprennent la couleur, la bannière, le fond et les badges en vitrine choisis sur son profil.
>
> **Erreur 404** : un membre ou un serveur inconnu renvoie une carte d'erreur SVG (pas d'image cassée).
>
> Le paramètre `?lang=` des versions précédentes est ignoré : les cartes sont toujours en anglais.

| Carte | Endpoints | Paramètres |
|---|---|---|
| Profil d'un membre, tous serveurs (`/allstats`) | `GET /api/card/user/{username}` · `GET /api/card/allstats/{username}` | — |
| Profil d'un membre sur un serveur (`/stats`) | `GET /api/card/user/{username}/server/{server_id}` · `GET /api/card/stats/{username}/{server_id}` | — |
| Duel entre deux membres (`/versus`) | `GET /api/card/versus/{user1}/{user2}` | `?server={server_id}` : comparer sur un serveur (sinon tous serveurs) |
| Top 10 d'un serveur (`/top`) | `GET /api/card/top/server/{server_id}` · `GET /api/card/server/{server_id}/top` | `?type=voice\|messages`, `?period=all\|month\|week` |
| Top 10 tous serveurs (`/alltop`) | `GET /api/card/top` · `GET /api/card/top/global` · `GET /api/card/alltop` | `?type=voice\|messages`, `?period=all\|month\|week` |
| Statistiques d'un serveur (`/server`) | `GET /api/card/server/{server_id}` | — |
| Liste des commandes | `GET /api/card/commands` · `GET /api/card/help` · `GET /api/card/aide` | — |

Contenu des cartes :
- **Profil** : avatar, niveau et titre, rang, barre d'XP, puis 4 tuiles (vocal, messages, 30 derniers jours, « Tracked since ») et jusqu'à 3 badges en vitrine. « Tracked since » est la première activité vue par Hourglass sur ce serveur (`/stats`) ou sur tous les serveurs (`/allstats`).
- **Duel** : chaque camp a la couleur de profil de son membre ; un verdict, puis 5 manches (vocal, messages, 30 derniers jours, rang, badges) avec le gagnant mis en avant.
- **Top 10** : podium des 3 premiers, puis les places 4 à 10.
- **Serveur** : rang, 4 tuiles (vocal, messages, membres, en vocal maintenant) et la courbe du vocal sur 30 jours.

### Images PNG du bot (interne)
Le bot Discord récupère les mêmes cartes en PNG via `GET /internal/card/{member|versus|top|server}.png`, avec l'en-tête `X-Card-Token` égal à la variable `CARD_TOKEN`, définie à l'identique sur le site et sur le bot. Ces adresses répondent 404 tant que `CARD_TOKEN` n'est pas configuré.

---

## 3. Intégration Discord Bot

### Exemple en Python (`discord.py` / `nextcord` / `disnake`)
Puisque Discord affiche directement les URLs d'images dans les embeds :

```python
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!")

BASE_API = "https://hourglassbot.net/api/card"

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

const BASE_API = 'https://hourglassbot.net/api/card';

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

