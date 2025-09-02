
# Hourglass - API - Documentation

Hourglass propose une API publique, sans clé afin de récupérer des données (stats) via des endpoints.

## Base URL

```http
https://hourglass.mike-server.fr/api/
```

## Endpoints
Listes des endpoints disponible par l'API de hourglass

### Utilisateurs
```http
GET /api/users
```
Récuperer tous les Utilisateurs de la base de données
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
    "user_id": 0987654321,
    "username": "username01"
  }
]
```

### Serveurs
```http
GET /api/servers
```
Récuperer tous les Serveurs de la base de données
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

### Statistiques globales
Récuperer les statistiques globales du bot
```http
GET /api/stats
```
#### Réponse :
```json
{
  "messages": 1000,
  "scope": "global",
  "score": 0,
  "seconds": 5000
}
```
### Statistiques d'un utilisateur
Récupérer les statistiques d'un utilisateur via son user_id
```http
GET /api/stats/${user_id}
```
| Paramètre | Type  | Description                                         |
| :-------- | :---  | :-------------------------------------------------- |
| `user_id` | `int` | **Obligatoire** User ID de l'utilisateur rechercher |

#### Réponse :
```json
{
  "messages": 3000,
  "scope": "user:1234567890",
  "score": 0,
  "seconds": 3000,
  "user_id": 1234567890"
}
```
### Statistiques d'un utilisateur sur un serveur
Récupérer les statistiques d'un utilisateur sur un server via son user_id et le server_id
```http
GET /api/stats/${user_id}/${server_id}
```
| Paramètre | Type  | Description                                         |
| :-------- | :---  | :-------------------------------------------------- |
| `user_id` | `int` | **Obligatoire** User ID de l'utilisateur rechercher |
| `server_id` | `int` | **Obligatoire** Server ID de serveur rechercher |

#### Réponse :
```json
{
  "messages": 2691,
  "scope": "user:1234567890",
  "score": 0,
  "seconds": 3000,
  "server_id": 5000
  "user_id": 1234567890
}
```
