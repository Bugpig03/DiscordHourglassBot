"""Home dashboard and support routes."""

from flask import Blueprint, render_template, request
from peewee import fn
from app.database import db, Users, Servers, HistoricalStats, Stats
from app.functions import format_date_heure_localized, ConvertSecondsToTime

home_bp = Blueprint("home", __name__)


@home_bp.route("/", methods=["GET"])
def home():
    """Render the main dashboard with global application metrics and database statistics."""
    stats = load_dashboard_stats()
    return render_template("home.html", stats=stats)


@home_bp.route("/supports", methods=["GET"])
def supports():
    """Render the project support and help information page."""
    return render_template("supports.html")


def load_dashboard_stats() -> dict:
    """Collect global metrics: counts, totals, database storage sizes, and last snapshot timestamp."""
    nb_users = Users.select().count()
    nb_profiles = Stats.select().count()
    nb_servers = Servers.select().count()
    nb_messages = Stats.select(fn.SUM(Stats.messages)).scalar() or 0
    nb_time = ConvertSecondsToTime(Stats.select(fn.SUM(Stats.seconds)).scalar() or 0)

    # Database total size in KB
    query_db_size = db.execute_sql("SELECT pg_database_size(current_database())")
    size_db_bytes = query_db_size.fetchone()[0]
    size_db_ko = size_db_bytes // 1024

    # Table sizes in KB
    query_stats_size = db.execute_sql("SELECT pg_total_relation_size('public.stats')")
    size_stats_bytes = query_stats_size.fetchone()[0]
    size_stats_ko = size_stats_bytes // 1024

    query_hist_size = db.execute_sql("SELECT pg_total_relation_size('public.historical_stats')")
    size_hist_bytes = query_hist_size.fetchone()[0]
    size_hist_ko = size_hist_bytes // 1024

    # Most recent snapshot timestamp in historical_stats
    last_backup = HistoricalStats.select(fn.MAX(HistoricalStats.created_at)).scalar()
    lang = request.cookies.get("lang", "fr")
    last_backup_str = format_date_heure_localized(last_backup, lang=lang)

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