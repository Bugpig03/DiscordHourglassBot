"""Top leaderboard routes for users and servers."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from peewee import fn
from app.database import Users, Stats, Servers, HistoricalStats
from app.gamification import calculate_user_xp_and_level

top_bp = Blueprint("top", __name__)

USERS_PER_PAGE = 20
SERVERS_PER_PAGE = 20

PERIOD_MAP = {
    "24h": 1,
    "7d": 7,
    "15d": 15,
    "1m": 30,
    "6m": 182,
    "1y": 365
}


@top_bp.route("/top/users", methods=["GET"])
def top_users():
    """Render the user leaderboard with filtering by period, server, and sorting criterion."""
    users, total_pages = load_users()
    servers = Servers.select().order_by(Servers.servername)
    return render_template("top_users.html", users=users, servers=servers, total_pages=total_pages)


@top_bp.route("/top/servers", methods=["GET"])
def top_servers():
    """Render the server leaderboard with filtering by period and sorting criterion."""
    servers, total_pages = load_servers()
    return render_template("top_servers.html", servers=servers, total_pages=total_pages)


def load_users() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate users based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    server_id = request.args.get("server_id", "all")
    page = request.args.get("page", 1, type=int)

    search_day = PERIOD_MAP.get(period)

    # Base query for all users tracked in stats
    query = (
        Users
        .select(Users.user_id, Users.username, Users.avatar)
        .join(Stats, on=(Users.user_id == Stats.user_id))
    )

    if server_id != "all":
        query = query.where(Stats.server_id == int(server_id))

    query = query.group_by(Users.user_id)

    # Fast batch aggregation when a period filter is requested
    if search_day:
        now = datetime.utcnow()
        since_days = now - timedelta(days=search_day)

        hist_base = (HistoricalStats.created_at >= since_days) & (HistoricalStats.created_at <= now)
        if server_id != "all":
            hist_base &= (HistoricalStats.server_id == int(server_id))

        oldest_record = (
            HistoricalStats.select(HistoricalStats.created_at)
            .where(hist_base)
            .order_by(HistoricalStats.created_at.asc())
            .first()
        )

        hist_map = {}
        if oldest_record:
            oldest_date = oldest_record.created_at.date()
            hist_cond = (fn.DATE(HistoricalStats.created_at) == oldest_date)
            if server_id != "all":
                hist_cond &= (HistoricalStats.server_id == int(server_id))

            hist_data = (
                HistoricalStats
                .select(
                    HistoricalStats.user_id,
                    fn.SUM(HistoricalStats.seconds).alias("hist_sec"),
                    fn.SUM(HistoricalStats.messages).alias("hist_msg")
                )
                .where(hist_cond)
                .group_by(HistoricalStats.user_id)
            )
            hist_map = {row.user_id: (row.hist_sec or 0, row.hist_msg or 0) for row in hist_data}

        # Fetch current totals for all users in one query
        curr_cond = (Stats.server_id == int(server_id)) if server_id != "all" else None
        curr_query = (
            Stats
            .select(
                Stats.user_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
        )
        if curr_cond is not None:
            curr_query = curr_query.where(curr_cond)
        curr_data = curr_query.group_by(Stats.user_id)
        curr_map = {row.user_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = []
        for user in query:
            curr_sec, curr_msg = curr_map.get(user.user_id, (0, 0))
            hist_sec, hist_msg = hist_map.get(user.user_id, (0, 0))
            results.append({
                "username": user.username,
                "avatar_url": user.avatar,
                "seconds": max(0, curr_sec - hist_sec),
                "messages": max(0, curr_msg - hist_msg)
            })
    else:
        # All-time stats queried in bulk
        curr_cond = (Stats.server_id == int(server_id)) if server_id != "all" else None
        curr_query = (
            Stats
            .select(
                Stats.user_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
        )
        if curr_cond is not None:
            curr_query = curr_query.where(curr_cond)
        curr_data = curr_query.group_by(Stats.user_id)
        curr_map = {row.user_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = [
            {
                "username": user.username,
                "avatar_url": user.avatar,
                "seconds": curr_map.get(user.user_id, (0, 0))[0],
                "messages": curr_map.get(user.user_id, (0, 0))[1]
            }
            for user in query
        ]

    # Compute XP and level for all users
    for r in results:
        xp_info = calculate_user_xp_and_level(r["seconds"], r["messages"])
        r["xp"] = xp_info["total_xp"]
        r["level"] = xp_info["level"]

    # Sort results
    if sort_by in ("xp", "level"):
        results.sort(key=lambda x: (x["xp"], x["seconds"], x["messages"]), reverse=True)
    elif sort_by == "messages":
        results.sort(key=lambda x: (x["messages"], x["seconds"]), reverse=True)
    else:
        results.sort(key=lambda x: (x["seconds"], x["messages"]), reverse=True)

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * USERS_PER_PAGE: page * USERS_PER_PAGE]
    return paginated_results, total_pages


def load_servers() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate servers based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    page = request.args.get("page", 1, type=int)

    search_day = PERIOD_MAP.get(period)

    # Base query for all active servers
    query = (
        Servers
        .select(Servers.server_id, Servers.servername, Servers.avatar)
        .join(Stats, on=(Servers.server_id == Stats.server_id))
        .group_by(Servers.server_id)
    )

    if search_day:
        now = datetime.utcnow()
        since_days = now - timedelta(days=search_day)

        oldest_record = (
            HistoricalStats.select(HistoricalStats.created_at)
            .where((HistoricalStats.created_at >= since_days) & (HistoricalStats.created_at <= now))
            .order_by(HistoricalStats.created_at.asc())
            .first()
        )

        hist_map = {}
        if oldest_record:
            oldest_date = oldest_record.created_at.date()
            hist_data = (
                HistoricalStats
                .select(
                    HistoricalStats.server_id,
                    fn.SUM(HistoricalStats.seconds).alias("hist_sec"),
                    fn.SUM(HistoricalStats.messages).alias("hist_msg")
                )
                .where(fn.DATE(HistoricalStats.created_at) == oldest_date)
                .group_by(HistoricalStats.server_id)
            )
            hist_map = {row.server_id: (row.hist_sec or 0, row.hist_msg or 0) for row in hist_data}

        curr_data = (
            Stats
            .select(
                Stats.server_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
            .group_by(Stats.server_id)
        )
        curr_map = {row.server_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = []
        for server in query:
            curr_sec, curr_msg = curr_map.get(server.server_id, (0, 0))
            hist_sec, hist_msg = hist_map.get(server.server_id, (0, 0))
            results.append({
                "server_id": server.server_id,
                "servername": server.servername,
                "avatar_url": server.avatar,
                "seconds": max(0, curr_sec - hist_sec),
                "messages": max(0, curr_msg - hist_msg)
            })
    else:
        curr_data = (
            Stats
            .select(
                Stats.server_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
            .group_by(Stats.server_id)
        )
        curr_map = {row.server_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = [
            {
                "server_id": server.server_id,
                "servername": server.servername,
                "avatar_url": server.avatar,
                "seconds": curr_map.get(server.server_id, (0, 0))[0],
                "messages": curr_map.get(server.server_id, (0, 0))[1]
            }
            for server in query
        ]

    # Sort results
    if sort_by == "messages":
        results.sort(key=lambda x: x["messages"], reverse=True)
    else:
        results.sort(key=lambda x: x["seconds"], reverse=True)

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + SERVERS_PER_PAGE - 1) // SERVERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * SERVERS_PER_PAGE: page * SERVERS_PER_PAGE]
    return paginated_results, total_pages
