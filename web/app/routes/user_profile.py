from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.functions import *

user_profile_bp = Blueprint("user_profile", __name__)

@user_profile_bp.route("/profile/<username>", methods=["GET"])
def profile(username):

    user_id = get_user_id_by_username(username)

    if user_id is None: # check si l'utilisateur existe
        return redirect(url_for('home'))
    
    stats = load(user_id,username) # si oui alors load stats
    return render_template("user_profile.html", stats=stats)

def load(user_id,username):
    
    avatar_url = get_user_avatar_url(user_id)
    rank = get_global_rank_by_user_id_seconds(user_id)
    total_user = get_global_nb_user()
    total_time = ConvertSecondsToTime(get_total_seconds_by_user_id(user_id))
    total_messages = get_total_message_by_user_id(user_id)

    activity = get_activity_sum_last_X_days(user_id,30)
    total_time_last_30d = activity["seconds"]
    
    user_servers_stats = get_user_servers_stats(user_id)
    stats = {
            "avatar_url": avatar_url,
            "username": username,
            "rank": rank,
            "total_user": total_user,
            "total_time": total_time,
            "total_message": total_messages,
            "total_time_last_30d": total_time_last_30d,
            "user_servers_stats": user_servers_stats
            }
    return stats