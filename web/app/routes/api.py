from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.database import Servers, Users, Stats
from peewee import fn

api_bp = Blueprint("api", __name__)

# Récupère tous les utilisateurs et leurs données
@api_bp.route("/api/users", methods=["GET"])
def get_users():
    users = Users.select()
    data = [
        {
            "user_id": u.user_id,
            "username": u.username,
            "avatar": u.avatar,
        }
        for u in users
    ]
    return jsonify(data)

# Récupère tous les utilisateurs et leurs données
@api_bp.route("/api/servers", methods=["GET"])
def get_servers():
    servers = Servers.select()
    data = [
        {
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar,
        }
        for server in servers
    ]
    return jsonify(data)

# Récupère les données d'un utilisateurs
@api_bp.route("/api/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = Users.get(Users.user_id == user_id)
        return jsonify({
            "user_id": user.user_id,
            "username": user.username,
            "avatar": user.avatar,
        })
    except Users.DoesNotExist:
        return jsonify({"error": "User not found"}), 404

# Récupère les données d'un serveur
@api_bp.route("/api/server/<int:server_id>", methods=["GET"])
def get_server(server_id):
    try:
        server = Servers.get(Servers.server_id == server_id)
        return jsonify({
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar,
        })
    except Servers.DoesNotExist:
        return jsonify({"error": "Server not found"}), 404

# Récupère les stats d'un utilisateur sur tous les serveurs (ou spécifique si server_id donnée)
@api_bp.route("/api/stats", defaults={"user_id": None, "server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>", defaults={"server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>/<int:server_id>", methods=["GET"])
def get_stats(user_id, server_id):
    try:
        # Cas 1 : ni user_id ni server_id -> stats globales
        if user_id is None and server_id is None:
            stat = Stats.select(
                fn.SUM(Stats.messages).alias("messages"),
                fn.SUM(Stats.seconds).alias("seconds"),
                fn.SUM(Stats.score).alias("score")
            ).dicts().get()
            return jsonify({
                "scope": "global",
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Cas 2 : user_id fourni, pas de server_id -> toutes les stats de ce user (tous serveurs)
        if user_id is not None and server_id is None:
            stat = Stats.select(
                fn.SUM(Stats.messages).alias("messages"),
                fn.SUM(Stats.seconds).alias("seconds"),
                fn.SUM(Stats.score).alias("score")
            ).where(Stats.user_id == user_id).dicts().get()
            return jsonify({
                "scope": f"user:{user_id}",
                "user_id": user_id,
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Cas 3 : user_id et server_id fournis -> stats précises
        stat = Stats.get((Stats.user_id == user_id) & (Stats.server_id == server_id))
        return jsonify({
            "scope": f"user:{user_id}-server:{server_id}",
            "user_id": stat.user_id,
            "server_id": stat.server_id,
            "messages": stat.messages,
            "seconds": stat.seconds,
            "score": stat.score
        })

    except Stats.DoesNotExist:
        return jsonify({"error": "Stats not found"}), 404