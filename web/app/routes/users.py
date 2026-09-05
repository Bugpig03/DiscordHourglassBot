"""User directory and search routes."""

from flask import Blueprint, render_template, request
from peewee import fn, JOIN
from app.database import Users, Stats
from app.gamification import calculate_user_xp_and_level

users_bp = Blueprint("users", __name__)

USERS_PER_PAGE = 100


@users_bp.route("/users", methods=["GET"])
def users():
    """Render the paginated users list with optional search filtering by username."""
    search_query = request.args.get("q", "").strip()
    users_list, total_pages = load_users(search_query)
    return render_template("users.html", users=users_list, total_pages=total_pages)


def load_users(search_query: str = "") -> tuple[list[dict], int]:
    """Retrieve and paginate users from the database based on search criteria."""
    page = request.args.get("page", 1, type=int)

    base_query = (
        Users
        .select(
            Users.user_id,
            Users.username,
            Users.avatar,
            fn.COALESCE(fn.SUM(Stats.seconds), 0).alias("total_seconds"),
            fn.COALESCE(fn.SUM(Stats.messages), 0).alias("total_messages")
        )
        .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
    )
    if search_query:
        base_query = base_query.where(Users.username.contains(search_query))

    base_query = (
        base_query
        .group_by(Users.user_id, Users.username, Users.avatar)
        .order_by(Users.username)
    )

    total_count = Users.select().where(Users.username.contains(search_query)).count() if search_query else Users.select().count()
    total_pages = max(1, (total_count + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_query = base_query.paginate(page, USERS_PER_PAGE)
    users_list = []
    for user in paginated_query:
        xp_info = calculate_user_xp_and_level(user.total_seconds, user.total_messages)
        users_list.append({
            "username": user.username,
            "avatar": user.avatar,
            "level": xp_info["level"],
            "total_xp": xp_info["total_xp"]
        })

    return users_list, total_pages
