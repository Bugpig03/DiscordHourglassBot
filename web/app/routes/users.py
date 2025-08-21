from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import Users

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET"])
def users():
    search_query = request.args.get("q", "").strip()  # récupère le paramètre 'q' si présent
    users = load_users(search_query)
    return render_template("users.html", users=users)


def load_users(search_query=""):
    query = (Users
             .select(Users.username, Users.avatar)
             .order_by(Users.username)
    )

    if search_query:
        query = query.where(Users.username.contains(search_query))

    users_list = [
        {
            "username": user.username,
            "avatar": user.avatar
        } for user in query
    ]

    return users_list
