from flask import Blueprint, render_template, request
from app.database import db, Users, Stats, Servers
from peewee import fn
from datetime import datetime, timedelta
from app.functions import get_activity_sum_last_X_days, get_server_activity_sum_last_X_days

top_bp = Blueprint("top", __name__)

@top_bp.route("/top/users", methods=["GET"])
def top_users():
    users = load_users()

    # Récupérer tous les serveurs distincts
    servers = Servers.select().order_by(Servers.servername)

    return render_template("top_users.html", users=users, servers=servers)

@top_bp.route("/top/servers", methods=["GET"])
def top_servers():

    servers = load_servers()

    return render_template("top_servers.html", servers=servers)



def load_users():
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    server_id = request.args.get("server_id", "all")

    # Conversion période -> nombre de jours
    period_map = {
        "24h": 1,
        "7d": 7,
        "15d": 15,
        "1m": 30,
        "6m": 182,
        "1y": 365
    }
    search_day = period_map.get(period)

    # Base query pour récupérer les utilisateurs
    query = (Users
             .select(Users.user_id, Users.username, Users.avatar)
             .join(Stats, on=(Users.user_id == Stats.user_id)))
    
    if server_id != "all":
        query = query.where(Stats.server_id == int(server_id))

    query = query.group_by(Users.user_id)

    results = []

    for user in query:
        if search_day:
            if server_id != "all":
                activity = get_activity_sum_last_X_days(user.user_id, search_day,server_id)
            else:
                activity = get_activity_sum_last_X_days(user.user_id, search_day)
            total_seconds = activity["seconds"]
            total_messages = activity["messages"]
        else:
            if server_id != "all":
                total_seconds = (Stats
                                .select(fn.SUM(Stats.seconds))
                                .where(Stats.user_id == user.user_id)
                                .where(Stats.server_id == int(server_id))
                                .scalar()) or 0
                total_messages = (Stats
                                .select(fn.SUM(Stats.messages))
                                .where(Stats.user_id == user.user_id)
                                .where(Stats.server_id == int(server_id))
                                .scalar()) or 0
            else:
                total_seconds = (Stats
                                .select(fn.SUM(Stats.seconds))
                                .where(Stats.user_id == user.user_id)
                                .scalar()) or 0
                total_messages = (Stats
                                .select(fn.SUM(Stats.messages))
                                .where(Stats.user_id == user.user_id)
                                .scalar()) or 0

        results.append({
            "username": user.username,
            "avatar_url": user.avatar,
            "seconds": total_seconds,
            "messages": total_messages
        })

    # Tri final
    if sort_by == "messages":
        results.sort(key=lambda x: x["messages"], reverse=True)
    else:
        results.sort(key=lambda x: x["seconds"], reverse=True)

    return results


def load_servers():
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")

    # Conversion période -> nombre de jours
    period_map = {
        "24h": 1,
        "7d": 7,
        "15d": 15,
        "1m": 30,
        "6m": 182,
        "1y": 365
    }
    search_day = period_map.get(period)

    # Base query pour récupérer les serveurs
    query = (Servers
             .select(Servers.server_id, Servers.servername, Servers.avatar)
             .join(Stats, on=(Servers.server_id == Stats.server_id))
             .group_by(Servers.server_id))

    results = []

    for server in query:
        if search_day:
            activity = get_server_activity_sum_last_X_days(server.server_id, search_day)
            total_seconds = activity["seconds"]
            total_messages = activity["messages"]
        else:
            total_seconds = (Stats
                            .select(fn.SUM(Stats.seconds))
                            .where(Stats.server_id == server.server_id)
                            .scalar()) or 0
            total_messages = (Stats
                            .select(fn.SUM(Stats.messages))
                            .where(Stats.server_id == server.server_id)
                            .scalar()) or 0

        results.append({
            "servername": server.servername,
            "avatar_url": server.avatar,
            "seconds": total_seconds,
            "messages": total_messages
        })

    # Tri final
    if sort_by == "messages":
        results.sort(key=lambda x: x["messages"], reverse=True)
    else:
        results.sort(key=lambda x: x["seconds"], reverse=True)

    return results
