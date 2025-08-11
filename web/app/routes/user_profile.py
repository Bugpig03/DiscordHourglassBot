from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.functions import get_user_id_by_username,get_total_seconds_by_user_id,ConvertSecondsToTime

user_profile_bp = Blueprint("user_profile", __name__)

@user_profile_bp.route("/profile/<username>", methods=["GET"])
def profile(username):

    user_id = get_user_id_by_username(username)

    if user_id is None: # check si l'utilisateur existe
        return redirect(url_for('home.home'))
    
    stats = load(user_id) # si oui alors load stats
    return render_template("user_profile.html", stats=stats)

def load(user_id):
    
    total_time = ConvertSecondsToTime(get_total_seconds_by_user_id(user_id))
    stats = {"total_time": total_time}
    return stats