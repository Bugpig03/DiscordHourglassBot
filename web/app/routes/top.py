from flask import Blueprint, render_template, request
from app.database import db, Users, Stats
from peewee import fn
from datetime import datetime, timedelta

top_bp = Blueprint("top", __name__)

@top_bp.route("/top", methods=["GET"])
def top():
    users = load()
    return render_template("top.html", users=users)

def load():
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")

    now = datetime.utcnow()

    if period == "24h":
        since = now - timedelta(days=1)
    elif period == "7d":
        since = now - timedelta(days=7)
    elif period == "15d":
        since = now - timedelta(days=15)
    elif period == "1m":
        since = now - timedelta(days=30)
    elif period == "6m":
        since = now - timedelta(days=182)
    elif period == "1y":
        since = now - timedelta(days=365)
    else:
        since = None

    query = (Users
             .select(
                 Users.username,
                 Users.avatar,
                 fn.SUM(Stats.messages).alias('total_messages'),
                 fn.SUM(Stats.seconds).alias('total_seconds')
             )
             .join(Stats, on=(Users.user_id == Stats.user_id))
            )

    if since:
        query = query.where(Stats.date_creation >= since)

    query = query.group_by(Users.user_id)

    if sort_by == "messages":
        query = query.order_by(fn.SUM(Stats.messages).desc())
    else:
        query = query.order_by(fn.SUM(Stats.seconds).desc())

    users = []
    for stat in query.limit(50):
        users.append({
            "username": stat.username,
            "avatar_url": stat.avatar,
            "messages": stat.total_messages or 0,
            "seconds": stat.total_seconds or 0
        })

    return users
