from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import Users

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET"])
def users():
    search_query = request.args.get("q", "").strip()  # récupère le paramètre 'q' si présent
    users , total_pages = load_users(search_query)
    return render_template("users.html", users=users, total_pages=total_pages)


def load_users(search_query=""):
    page = request.args.get('page', 1, type=int)
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

    # Trie user a afficher en fonction de la page
    nb_user_per_page = 30
    # Sécurité page vérifie si pas inf 1 et sup total de page
    # Formule : (Total + TaillePage - 1) // TaillePage
    total_pages = (len(users_list) + nb_user_per_page - 1) // nb_user_per_page
    if page < 1 :
        page = 1
    elif page > total_pages:
        page = total_pages

    # Tri pages (utilisateur a afficher sur ma page chosi)
    users_list = users_list[(page-1)*nb_user_per_page:page*nb_user_per_page]

    return users_list, total_pages
