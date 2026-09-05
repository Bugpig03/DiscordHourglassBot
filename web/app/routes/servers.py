"""Server directory and search routes."""

from flask import Blueprint, render_template, request
from app.database import Servers

servers_bp = Blueprint("servers", __name__)

SERVERS_PER_PAGE = 100


@servers_bp.route("/servers", methods=["GET"])
def servers():
    """Render the paginated servers list with optional search filtering by server name."""
    search_query = request.args.get("q", "").strip()
    servers_list, total_pages = load_servers(search_query)
    return render_template("servers.html", servers=servers_list, total_pages=total_pages)


def load_servers(search_query: str = "") -> tuple[list[dict], int]:
    """Retrieve and paginate servers from the database based on search criteria."""
    page = request.args.get("page", 1, type=int)

    base_query = (
        Servers
        .select(Servers.servername, Servers.avatar, Servers.server_id)
        .order_by(Servers.servername)
    )

    if search_query:
        base_query = base_query.where(Servers.servername.contains(search_query))

    total_count = base_query.count()
    total_pages = max(1, (total_count + SERVERS_PER_PAGE - 1) // SERVERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_query = base_query.paginate(page, SERVERS_PER_PAGE)
    servers_list = [
        {
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar
        }
        for server in paginated_query
    ]

    return servers_list, total_pages
