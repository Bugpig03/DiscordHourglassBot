from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.functions import *

server_profile_bp = Blueprint("server_profile", __name__)

@server_profile_bp.route("/server/<server_id>", methods=["GET"])
def server(server_id):
    search_query = request.args.get("q", "").strip()

    if get_servername_by_server_id(server_id) is None: # check si server_id valide
       return redirect(url_for('home.home'))

    get_servername_by_server_id(server_id)
    stats = load(server_id) # si oui alors load stats
    return render_template("server_profile.html", stats=stats)

def load(server_id, search_query=""):
    
    stats = {
            "avatar_url": get_server_avatar_url(server_id),
            "servername": get_servername_by_server_id(server_id),
            "rank": get_server_rank(server_id),
            "total_server": get_global_nb_server(),
            "total_time": ConvertSecondsToTime(get_total_seconds_by_server_id(server_id)),
            "total_message": get_total_message_by_server_id(server_id),
            "total_time_last_30d": get_server_activity_sum_last_X_days(server_id,30),
            "users": load_users_from_server(server_id, search_query)
            }
    return stats


def load_users_from_server(server_id, search_query=""):
    query = (Users
        .select(Users.username, Users.avatar)
        .join(Stats, on=(Users.user_id == Stats.user_id))  # explicit join
        .where(Stats.server_id == server_id)
        .order_by(Users.username)
    )

    if search_query:
        query = query.where(Users.username.contains(search_query))

    return [
        {"username": user.username, "avatar": user.avatar}
        for user in query
    ]