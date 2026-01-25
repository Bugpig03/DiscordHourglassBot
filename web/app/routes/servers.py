from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import Servers

servers_bp = Blueprint("servers", __name__)

@servers_bp.route("/servers", methods=["GET"])
def servers():
    search_query = request.args.get("q", "").strip()  # récupère le paramètre 'q' si présent
    servers, total_pages = load_servers(search_query)
    return render_template("servers.html", servers=servers,total_pages=total_pages)


def load_servers(search_query=""):
    page = request.args.get('page', 1, type=int)
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

    # Trie user a afficher en fonction de la page
    nb_server_per_page = 30
    # Sécurité page vérifie si pas inf 1 et sup total de page
    # Formule : (Total + TaillePage - 1) // TaillePage
    total_pages = (len(servers_list) + nb_server_per_page - 1) // nb_server_per_page
    if page < 1 :
        page = 1
    elif page > total_pages:
        page = total_pages

    # Tri pages (utilisateur a afficher sur ma page chosi)
    servers_list = servers_list[(page-1)*nb_server_per_page:page*nb_server_per_page]

    return servers_list, total_pages
