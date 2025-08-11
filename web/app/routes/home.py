from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import db, Users, Servers, HistoricalStats, Stats
from peewee import fn
from app.functions import format_date_fr, ConvertSecondsToTime

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def home():
    stats = load()
    return render_template("home.html", stats = stats)

@home_bp.route("/commands", methods=["GET"])
def commands():
    return render_template("commands.html")


def load():
    db.connect()
    
    nb_users = Users.select().count()
    nb_profiles = Stats.select().count()
    nb_servers = Servers.select().count()
    nb_messages = Stats.select(fn.SUM(Stats.messages)).scalar() or 0
    nb_time = ConvertSecondsToTime(Stats.select(fn.SUM(Stats.seconds)).scalar() or 0)

    # Taille totale de la base en octets
    query_db_size = db.execute_sql(
        "SELECT pg_database_size(current_database())"
    )
    size_db_bytes = query_db_size.fetchone()[0]
    size_db_ko = size_db_bytes // 1024  # conversion en Ko

    # Taille table stats en octets
    query_stats_size = db.execute_sql(
        "SELECT pg_total_relation_size('public.stats')"
    )
    size_stats_bytes = query_stats_size.fetchone()[0]
    size_stats_ko = size_stats_bytes // 1024

    # Taille table historical_stats en octets
    query_hist_size = db.execute_sql(
        "SELECT pg_total_relation_size('public.historical_stats')"
    )
    size_hist_bytes = query_hist_size.fetchone()[0]
    size_hist_ko = size_hist_bytes // 1024

    # Date la plus récente dans historical_stats (champ created_at)
    last_backup = (HistoricalStats
                   .select(fn.MAX(HistoricalStats.created_at))
                   .scalar())
    
    # Formatte la date en string lisible si pas None
    last_backup_str = format_date_fr(last_backup)
    db.close()

    return {
        "nb_users": nb_users,
        "nb_profiles": nb_profiles,
        "nb_servers": nb_servers,
        "nb_messages": nb_messages,
        "nb_time": nb_time,
        "size_db_ko": size_db_ko,
        "size_stats_ko": size_stats_ko,
        "size_hist_ko": size_hist_ko,
        "last_backup": last_backup_str
    }