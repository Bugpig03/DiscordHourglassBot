"""Public REST API endpoints for accessing user, server, and statistical data."""

from flask import Blueprint, jsonify, request
from peewee import fn, JOIN
from app.analytics_tracking import record_search
from app.database import Servers, Users, Stats
from app.gamification import calculate_user_xp_and_level

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/users", methods=["GET"])
def get_users():
    """Retrieve all users with their Discord IDs, usernames, and avatar URLs."""
    users = Users.select(Users.user_id, Users.username, Users.avatar)
    data = [
        {
            "user_id": u.user_id,
            "username": u.username,
            "avatar": u.avatar,
        }
        for u in users
    ]
    return jsonify(data)


@api_bp.route("/api/servers", methods=["GET"])
def get_servers():
    """Retrieve all servers with their IDs, names, and icon URLs."""
    servers = Servers.select(Servers.server_id, Servers.servername, Servers.avatar)
    data = [
        {
            "server_id": s.server_id,
            "servername": s.servername,
            "avatar": s.avatar,
        }
        for s in servers
    ]
    return jsonify(data)


@api_bp.route("/api/user/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    """Retrieve details for a single user by user ID."""
    try:
        user = Users.get(Users.user_id == user_id)
        return jsonify({
            "user_id": user.user_id,
            "username": user.username,
            "avatar": user.avatar,
        })
    except Users.DoesNotExist:
        return jsonify({"error": "User not found"}), 404


@api_bp.route("/api/server/<int:server_id>", methods=["GET"])
def get_server(server_id: int):
    """Retrieve details for a single server by server ID."""
    try:
        server = Servers.get(Servers.server_id == server_id)
        return jsonify({
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar,
        })
    except Servers.DoesNotExist:
        return jsonify({"error": "Server not found"}), 404


@api_bp.route("/api/stats", defaults={"user_id": None, "server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>", defaults={"server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>/<int:server_id>", methods=["GET"])
def get_stats(user_id: int | None, server_id: int | None):
    """Retrieve cumulative statistics across global, user-specific, or server-specific scopes."""
    try:
        # Case 1: Global statistics across the entire bot
        if user_id is None and server_id is None:
            stat = (
                Stats
                .select(
                    fn.SUM(Stats.messages).alias("messages"),
                    fn.SUM(Stats.seconds).alias("seconds"),
                    fn.SUM(Stats.score).alias("score")
                )
                .dicts()
                .get()
            )
            return jsonify({
                "scope": "global",
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Case 2: Cross-server statistics for a specific user
        if user_id is not None and server_id is None:
            stat = (
                Stats
                .select(
                    fn.SUM(Stats.messages).alias("messages"),
                    fn.SUM(Stats.seconds).alias("seconds"),
                    fn.SUM(Stats.score).alias("score")
                )
                .where(Stats.user_id == user_id)
                .dicts()
                .get()
            )
            return jsonify({
                "scope": f"user:{user_id}",
                "user_id": user_id,
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Case 3: Precise stats for a user on a specific server
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


@api_bp.route("/api/search", methods=["GET"])
def search_global():
    """Quick search across users and servers for the global Ctrl+K palette and page search bars."""
    q = request.args.get("q", "").strip()
    target_type = request.args.get("type", "").strip().lower()
    try:
        limit = min(max(int(request.args.get("limit", 6)), 1), 20)
    except (ValueError, TypeError):
        limit = 6

    if not q:
        return jsonify({"users": [], "servers": []})
    record_search(q)

    # Search Users
    users_data = []
    if target_type in ("", "all", "users", "user"):
        matched_users = (
            Users
            .select(
                Users.user_id,
                Users.username,
                Users.avatar,
                fn.COALESCE(fn.SUM(Stats.seconds), 0).alias("total_seconds"),
                fn.COALESCE(fn.SUM(Stats.messages), 0).alias("total_messages")
            )
            .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
            .where(Users.username.contains(q))
            .group_by(Users.user_id, Users.username, Users.avatar)
            .order_by(Users.username)
            .limit(limit)
        )
        for u in matched_users:
            xp_info = calculate_user_xp_and_level(u.total_seconds, u.total_messages)
            users_data.append({
                "username": u.username,
                "avatar": u.avatar or "/static/images/base_avatar_big.png",
                "level": xp_info["level"],
                "url": f"/profile/{u.user_id}"
            })

    # Search Servers
    servers_data = []
    if target_type in ("", "all", "servers", "server"):
        matched_servers = (
            Servers.select(Servers.server_id, Servers.servername, Servers.avatar)
            .where(Servers.servername.contains(q))
            .order_by(Servers.servername)
            .limit(limit)
        )
        servers_data = [
            {
                "server_id": str(s.server_id),
                "servername": s.servername,
                "avatar": s.avatar or "/static/icons/server.png",
                "url": f"/server/{s.server_id}"
            }
            for s in matched_servers
        ]

    return jsonify({
        "users": users_data,
        "servers": servers_data
    })
