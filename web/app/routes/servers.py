from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import Servers

servers_bp = Blueprint("servers", __name__)

@servers_bp.route("/servers", methods=["GET"])
def servers():
    search_query = request.args.get("q", "").strip()  # récupère le paramètre 'q' si présent
    servers = load_servers(search_query)
    return render_template("servers.html", servers=servers)


def load_servers(search_query=""):
    query = (Servers
             .select(Servers.servername, Servers.avatar, Servers.server_id)
             .order_by(Servers.servername)
    )

    if search_query:
        query = query.where(Servers.servername.contains(search_query))

    servers_list = [
        {
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar
        } for server in query
    ]

    return servers_list
