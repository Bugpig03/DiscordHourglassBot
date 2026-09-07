"""Home dashboard and support routes."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from peewee import fn
from app.database import db, Users, Servers, HistoricalStats, Stats
from app.functions import format_date_heure_localized, ConvertSecondsToTime, _get_activity_delta

home_bp = Blueprint("home", __name__)


@home_bp.route("/", methods=["GET"])
def home():
    """Render the main dashboard with global application metrics, 30-day activity, and database statistics."""
    stats = load_dashboard_stats()
    return render_template("home.html", stats=stats)


@home_bp.route("/supports", methods=["GET"])
def supports():
    """Render the project support and help information page."""
    return render_template("supports.html")


def load_dashboard_stats() -> dict:
    """Collect global metrics: 30-day activity delta, all-time totals, database storage sizes, and last snapshot timestamp."""
    # All-time totals
    nb_users = Users.select().count()
    nb_profiles = Stats.select().count()
    nb_servers = Servers.select().count()
    nb_messages = Stats.select(fn.SUM(Stats.messages)).scalar() or 0
    nb_time = ConvertSecondsToTime(Stats.select(fn.SUM(Stats.seconds)).scalar() or 0)

    # 30-Day Activity Delta & Active Counts
    delta_30d = _get_activity_delta(30)
    time_30d = ConvertSecondsToTime(delta_30d["seconds"])
    messages_30d = delta_30d["messages"]

    now = datetime.utcnow()
    since_30d = now - timedelta(days=30)
    cur = db.execute_sql("""
        SELECT 
            COUNT(DISTINCT user_id) as active_users,
            COUNT(DISTINCT server_id) as active_servers,
            COUNT(DISTINCT (user_id, server_id)) as active_profiles
        FROM historical_stats 
        WHERE created_at >= %s
    """, (since_30d,))
    row_30d = cur.fetchone()
    active_users_30d = row_30d[0] if row_30d else 0
    active_servers_30d = row_30d[1] if row_30d else 0
    active_profiles_30d = row_30d[2] if row_30d else 0

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
        # 30-day activity metrics
        "time_30d": time_30d,
        "seconds_30d": delta_30d["seconds"],
        "messages_30d": messages_30d,
        "active_users_30d": active_users_30d,
        "active_servers_30d": active_servers_30d,
        "active_profiles_30d": active_profiles_30d,
        # All-time global metrics
        "nb_users": nb_users,
        "nb_profiles": nb_profiles,
        "nb_servers": nb_servers,
        "nb_messages": nb_messages,
        "nb_time": nb_time,
        # Infrastructure telemetry
        "size_db_ko": size_db_ko,
        "size_stats_ko": size_stats_ko,
        "size_hist_ko": size_hist_ko,
        "last_backup": last_backup_str
    }