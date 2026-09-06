"""Utility functions and statistics query helpers for the Hourglass web application."""

from datetime import datetime, timedelta
from peewee import fn, SQL, JOIN
from app.database import Users, Stats, HistoricalStats, Servers

FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

ENGLISH_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

FR_MONTH_ABBR = {
    1: "Janv", 2: "Fév", 3: "Mars", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Août",
    9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc"
}

EN_MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}


def get_month_abbr(month: int, lang: str = "fr") -> str:
    """Return 3-4 letter localized month abbreviation."""
    if lang == "en":
        return EN_MONTH_ABBR.get(month, "")
    return FR_MONTH_ABBR.get(month, "")


def ConvertSecondsToTime(seconds: int) -> str:
    """Format an integer number of seconds into human-readable hours, minutes, and seconds with space separators."""
    seconds = int(seconds or 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    formatted_hours = f"{hours:,}".replace(",", " ")
    return f"{formatted_hours} h {minutes} min {secs} s"


def ConvertSecondsToHours(seconds: int) -> str:
    """Convert an integer number of seconds into decimal hours with one decimal place."""
    seconds = int(seconds or 0)
    hours = round(seconds / 3600, 1)
    return f"{hours} h"


def format_date_heure_localized(dt: datetime | None, lang: str = "fr") -> str:
    """Format a datetime object into a localized French or English date and time string."""
    if dt is None:
        return " "
    if lang == "en":
        return f"{ENGLISH_MONTHS[dt.month - 1]} {dt.day}, {dt.year} at {dt.strftime('%H:%M:%S')}"
    return f"{dt.day} {FRENCH_MONTHS[dt.month - 1]} {dt.year} à {dt.strftime('%H:%M:%S')}"


def format_date_localized(dt: datetime | None, lang: str = "fr") -> str:
    """Format a datetime object into a localized French or English date string."""
    if dt is None:
        return " "
    if lang == "en":
        return f"{ENGLISH_MONTHS[dt.month - 1]} {dt.day}, {dt.year}"
    return f"{dt.day} {FRENCH_MONTHS[dt.month - 1]} {dt.year}"


def format_date_heure_fr(dt: datetime | None) -> str:
    """Format a datetime object into a French date and time string (backward compatibility)."""
    return format_date_heure_localized(dt, lang="fr")


def format_date_fr(dt: datetime | None) -> str:
    """Format a datetime object into a French date string (backward compatibility)."""
    return format_date_localized(dt, lang="fr")


def get_user_id_by_username(username: str) -> int | None:
    """Retrieve a user ID by exact username lookup."""
    user = Users.select(Users.user_id).where(Users.username == username).first()
    return user.user_id if user else None


def get_servername_by_server_id(server_id: int | str) -> str | None:
    """Retrieve a server name by its Discord server ID."""
    if isinstance(server_id, str):
        if not server_id.isdigit():
            return None
        server_id = int(server_id)
    elif not isinstance(server_id, int):
        return None

    server = Servers.select(Servers.servername).where(Servers.server_id == server_id).first()
    return server.servername if server else None


# Alias for backward compatibility
get_server_name_by_id = get_servername_by_server_id


def get_total_seconds_by_user_id(user_id: int) -> int:
    """Compute the cumulative voice seconds for a specific user across all servers."""
    result = Stats.select(fn.SUM(Stats.seconds)).where(Stats.user_id == user_id).scalar()
    return result or 0


def get_total_seconds_by_server_id(server_id: int) -> int:
    """Compute the cumulative voice seconds for a specific server across all users."""
    result = Stats.select(fn.SUM(Stats.seconds)).where(Stats.server_id == server_id).scalar()
    return result or 0


def get_total_message_by_user_id(user_id: int) -> int:
    """Compute the cumulative message count for a specific user across all servers."""
    result = Stats.select(fn.SUM(Stats.messages)).where(Stats.user_id == user_id).scalar()
    return result or 0


def get_total_message_by_server_id(server_id: int) -> int:
    """Compute the cumulative message count for a specific server across all users."""
    result = Stats.select(fn.SUM(Stats.messages)).where(Stats.server_id == server_id).scalar()
    return result or 0


def get_global_rank_by_user_id_seconds(user_id: int) -> int | str:
    """Determine the global rank of a user based on total voice seconds across all servers."""
    user_total = Stats.select(fn.SUM(Stats.seconds)).where(Stats.user_id == user_id).scalar() or 0
    if user_total == 0:
        return "Non classé"

    # Count how many users have more total seconds than the target user
    higher_count = (
        Stats
        .select(Stats.user_id)
        .group_by(Stats.user_id)
        .having(fn.SUM(Stats.seconds) > user_total)
        .count()
    )
    return higher_count + 1


def get_global_nb_user() -> int:
    """Count the total number of registered users."""
    return Users.select(fn.COUNT(Users.user_id)).scalar() or 0


def get_global_nb_server() -> int:
    """Count the total number of registered servers."""
    return Servers.select(fn.COUNT(Servers.server_id)).scalar() or 0


def _get_activity_delta(days: int, user_id: int | None = None, server_id: int | None = None) -> dict[str, int]:
    """Calculate the activity delta (seconds and messages) over the last X days.

    Finds the earliest snapshot record within the window and subtracts it from current stats.
    """
    now = datetime.utcnow()
    since_days = now - timedelta(days=days)

    base_condition = (HistoricalStats.created_at >= since_days) & (HistoricalStats.created_at <= now)
    if user_id is not None:
        base_condition &= (HistoricalStats.user_id == user_id)
    if server_id is not None:
        base_condition &= (HistoricalStats.server_id == server_id)

    oldest_record = (
        HistoricalStats.select(HistoricalStats.created_at)
        .where(base_condition)
        .order_by(HistoricalStats.created_at.asc())
        .first()
    )

    if not oldest_record:
        return {"seconds": 0, "messages": 0}

    oldest_date = oldest_record.created_at.date()

    hist_condition = fn.DATE(HistoricalStats.created_at) == oldest_date
    curr_condition = None

    if user_id is not None:
        hist_condition &= (HistoricalStats.user_id == user_id)
        curr_condition = (Stats.user_id == user_id)
    if server_id is not None:
        hist_condition &= (HistoricalStats.server_id == server_id)
        if curr_condition is not None:
            curr_condition &= (Stats.server_id == server_id)
        else:
            curr_condition = (Stats.server_id == server_id)

    hist_query = HistoricalStats.select(
        fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
        fn.SUM(HistoricalStats.messages).alias("total_messages")
    ).where(hist_condition).dicts().first()

    curr_query = Stats.select(
        fn.SUM(Stats.seconds).alias("total_seconds"),
        fn.SUM(Stats.messages).alias("total_messages")
    )
    if curr_condition is not None:
        curr_query = curr_query.where(curr_condition)
    curr_data = curr_query.dicts().first()

    curr_seconds = curr_data.get("total_seconds") or 0 if curr_data else 0
    curr_messages = curr_data.get("total_messages") or 0 if curr_data else 0
    hist_seconds = hist_query.get("total_seconds") or 0 if hist_query else 0
    hist_messages = hist_query.get("total_messages") or 0 if hist_query else 0

    return {
        "seconds": max(0, curr_seconds - hist_seconds),
        "messages": max(0, curr_messages - hist_messages)
    }


def get_activity_sum_last_X_days(user_id: int, days: int, server_id: int | None = None) -> dict[str, int]:
    """Calculate user activity delta over the last X days, optionally restricted to a specific server."""
    return _get_activity_delta(days=days, user_id=user_id, server_id=server_id)


def get_server_activity_sum_last_X_days(server_id: int, days: int) -> dict[str, int]:
    """Calculate server-wide activity delta over the last X days."""
    return _get_activity_delta(days=days, server_id=server_id)


def get_user_avatar_url(user_id: int) -> str | None:
    """Fetch avatar URL for a given user ID."""
    user = Users.select(Users.avatar).where(Users.user_id == user_id).first()
    return user.avatar if user else None


def get_server_avatar_url(server_id: int) -> str | None:
    """Fetch avatar icon URL for a given server ID."""
    server = Servers.select(Servers.avatar).where(Servers.server_id == server_id).first()
    return server.avatar if server else None


def get_user_count_by_server_id(server_id: int) -> int:
    """Return the number of unique active users tracked on a server."""
    return Stats.select(Stats.user_id).where(Stats.server_id == server_id).distinct().count()


def get_user_rank_in_server(user_id: int, server_id: int) -> int | None:
    """Calculate a user's voice activity rank on a specific server using SQL window functions."""
    ranked_stats = (
        Stats
        .select(
            Stats.user_id,
            Stats.server_id,
            fn.RANK().over(
                partition_by=[Stats.server_id],
                order_by=[Stats.seconds.desc()]
            ).alias("rank")
        )
        .where(Stats.server_id == server_id)
        .alias("ranked_stats")
    )

    query = (
        Stats
        .select(ranked_stats.c.rank)
        .from_(ranked_stats)
        .where(ranked_stats.c.user_id == user_id)
    )
    return query.scalar()


def get_server_rank(server_id: int) -> int | None:
    """Calculate a server's rank based on aggregate voice seconds across all servers."""
    query = (
        Stats
        .select(Stats.server_id, fn.SUM(Stats.seconds).alias("total_seconds"))
        .group_by(Stats.server_id)
        .order_by(fn.SUM(Stats.seconds).desc())
    )
    for idx, row in enumerate(query, start=1):
        if int(row.server_id) == int(server_id):
            return idx
    return None


def get_user_servers_stats(user_id: int) -> list[dict]:
    """Retrieve activity stats and ranking for a user on every server they belong to."""
    query = (
        Stats
        .select(
            Stats.server_id,
            Servers.servername,
            Servers.avatar,
            Stats.seconds,
            Stats.messages,
            Stats.date_creation
        )
        .join(Servers, on=(Stats.server_id == Servers.server_id))
        .where(Stats.user_id == user_id)
        .order_by(Stats.seconds.desc())
    )

    return [
        {
            "server_id": stat.server_id,
            "server_name": stat.servers.servername if (hasattr(stat, 'servers') and stat.servers and stat.servers.servername) else str(stat.server_id),
            "avatar": stat.servers.avatar if (hasattr(stat, 'servers') and stat.servers) else None,
            "nb_user": get_user_count_by_server_id(stat.server_id),
            "time_spent": round((stat.seconds or 0) / 3600, 1),
            "messages_count": stat.messages,
            "rank": get_user_rank_in_server(user_id, stat.server_id),
            "joined_at": format_date_fr(stat.date_creation)
        }
        for stat in query
    ]


def get_first_of_month_hours_sum(server_id: int | None = None, user_id: int | None = None) -> list[dict]:
    """Sum voice hours on the first day of each month for cumulative trend charting."""
    query = (
        HistoricalStats
        .select(
            fn.DATE_TRUNC("month", HistoricalStats.created_at).alias("month_start"),
            fn.SUM(HistoricalStats.seconds).alias("total_seconds")
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC("month", HistoricalStats.created_at)).order_by(
        fn.DATE_TRUNC("month", HistoricalStats.created_at)
    )

    result = [
        {
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_hours": round((row.total_seconds or 0) / 3600, 1)
        }
        for row in query
    ]

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Add baseline according to entity scope (user, server, or global bot)
    if user_id:
        start_date = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.user_id == user_id).scalar()
        if start_date:
            start_date_str = start_date.strftime("%Y-%m-%d")
            result = [r for r in result if r["month"] >= start_date_str]
            if start_date_str < today_str and not any(r["month"] == start_date_str for r in result):
                result.append({"month": start_date_str, "total_hours": 0.0})
    elif server_id:
        server_min = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.server_id == server_id).scalar()
        if server_min:
            start_date_str = server_min.strftime("%Y-%m-%d")
            result = [r for r in result if r["month"] >= start_date_str]
            if start_date_str < today_str and not any(r["month"] == start_date_str for r in result):
                result.append({"month": start_date_str, "total_hours": 0.0})
    else:
        # Add bot origin baseline if not already present
        if not any(r["month"] == "2024-04-28" for r in result):
            result.append({"month": "2024-04-28", "total_hours": 0.0})

    # Add latest current total value
    curr_query = Stats.select(fn.SUM(Stats.seconds))
    if server_id:
        curr_query = curr_query.where(Stats.server_id == server_id)
    if user_id:
        curr_query = curr_query.where(Stats.user_id == user_id)
    current_total = curr_query.scalar() or 0

    if any(r["month"] == today_str for r in result):
        for r in result:
            if r["month"] == today_str:
                r["total_hours"] = round(current_total / 3600, 1)
                break
    else:
        result.append({
            "month": today_str,
            "total_hours": round(current_total / 3600, 1)
        })

    return sorted(result, key=lambda x: x["month"])


def get_first_of_month_messages_sum(server_id: int | None = None, user_id: int | None = None) -> list[dict]:
    """Sum total message count on the first day of each month for cumulative trend charting."""
    query = (
        HistoricalStats
        .select(
            fn.DATE_TRUNC("month", HistoricalStats.created_at).alias("month_start"),
            fn.SUM(HistoricalStats.messages).alias("total_messages")
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC("month", HistoricalStats.created_at)).order_by(
        fn.DATE_TRUNC("month", HistoricalStats.created_at)
    )

    result = [
        {
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_messages": int(row.total_messages or 0)
        }
        for row in query
    ]

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Add baseline according to entity scope (user, server, or global bot)
    if user_id:
        start_date = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.user_id == user_id).scalar()
        if start_date:
            start_date_str = start_date.strftime("%Y-%m-%d")
            result = [r for r in result if r["month"] >= start_date_str]
            if start_date_str < today_str and not any(r["month"] == start_date_str for r in result):
                result.append({"month": start_date_str, "total_messages": 0})
    elif server_id:
        server_min = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.server_id == server_id).scalar()
        if server_min:
            start_date_str = server_min.strftime("%Y-%m-%d")
            result = [r for r in result if r["month"] >= start_date_str]
            if start_date_str < today_str and not any(r["month"] == start_date_str for r in result):
                result.append({"month": start_date_str, "total_messages": 0})
    else:
        # Add bot origin baseline if not already present
        if not any(r["month"] == "2024-04-28" for r in result):
            result.append({"month": "2024-04-28", "total_messages": 0})

    # Add latest current total value from Stats table
    curr_query = Stats.select(fn.SUM(Stats.messages))
    if server_id:
        curr_query = curr_query.where(Stats.server_id == server_id)
    if user_id:
        curr_query = curr_query.where(Stats.user_id == user_id)
    current_total = curr_query.scalar() or 0

    if any(r["month"] == today_str for r in result):
        for r in result:
            if r["month"] == today_str:
                r["total_messages"] = int(current_total)
                break
    else:
        result.append({
            "month": today_str,
            "total_messages": int(current_total)
        })

    return sorted(result, key=lambda x: x["month"])


def get_monthly_hours_diff(server_id: int | None = None, user_id: int | None = None) -> list[dict]:
    """Calculate the incremental hours spent each month by computing the difference between month-start totals."""
    # Retrieve month-start totals from HistoricalStats
    query = (
        HistoricalStats
        .select(
            fn.DATE_TRUNC("month", HistoricalStats.created_at).alias("month_start"),
            fn.SUM(HistoricalStats.seconds).alias("total_seconds")
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC("month", HistoricalStats.created_at)).order_by(
        fn.DATE_TRUNC("month", HistoricalStats.created_at)
    )

    monthly_data = [
        {
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_hours": round((row.total_seconds or 0) / 3600, 1)
        }
        for row in query
    ]

    # Baseline for user/server join month
    if user_id:
        start_date = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.user_id == user_id).scalar()
        if start_date:
            start_month_str = start_date.strftime("%Y-%m-01")
            monthly_data = [r for r in monthly_data if r["month"] >= start_month_str]
            if not any(r["month"] == start_month_str for r in monthly_data):
                monthly_data.append({"month": start_month_str, "total_hours": 0.0})
    elif server_id:
        server_min = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.server_id == server_id).scalar()
        if server_min:
            start_month_str = server_min.strftime("%Y-%m-01")
            monthly_data = [r for r in monthly_data if r["month"] >= start_month_str]
            if not any(r["month"] == start_month_str for r in monthly_data):
                monthly_data.append({"month": start_month_str, "total_hours": 0.0})

    # Append current total for today
    curr_query = Stats.select(fn.SUM(Stats.seconds))
    if server_id:
        curr_query = curr_query.where(Stats.server_id == server_id)
    if user_id:
        curr_query = curr_query.where(Stats.user_id == user_id)
    current_total = curr_query.scalar() or 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    if any(r["month"] == today_str for r in monthly_data):
        for r in monthly_data:
            if r["month"] == today_str:
                r["total_hours"] = round(current_total / 3600, 1)
                break
    else:
        monthly_data.append({
            "month": today_str,
            "total_hours": round(current_total / 3600, 1)
        })

    monthly_data = sorted(monthly_data, key=lambda x: x["month"])

    # Compute differences between consecutive points
    monthly_differences = []
    for i in range(1, len(monthly_data)):
        prev = monthly_data[i - 1]
        curr = monthly_data[i]
        diff = round(curr["total_hours"] - prev["total_hours"], 1)
        monthly_differences.append({
            "month": prev["month"],
            "hours_this_month": max(diff, 0.0)
        })

    return monthly_differences


def get_user_join_date(user_id: int, server_id: int | None = None, lang: str = "fr") -> str:
    """Return the earliest recorded activity date for a user (overall or on a specific server)."""
    min_date = get_user_raw_join_date(user_id, server_id)
    return format_date_localized(min_date, lang=lang)


def get_user_raw_join_date(user_id: int, server_id: int | None = None):
    """Return the raw earliest recorded activity datetime for a user."""
    query = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.user_id == user_id)
    if server_id:
        query = query.where(Stats.server_id == server_id)
    min_date = query.scalar()
    if not min_date:
        hist_query = HistoricalStats.select(fn.MIN(HistoricalStats.created_at)).where(HistoricalStats.user_id == user_id)
        if server_id:
            hist_query = hist_query.where(HistoricalStats.server_id == server_id)
        min_date = hist_query.scalar()
    return min_date


def get_server_raw_join_date(server_id: int | str):
    """Return the raw earliest recorded activity datetime for a server (oldest registered user on the server)."""
    int_server_id = int(server_id)
    min_date = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.server_id == int_server_id).scalar()
    if not min_date:
        min_date = HistoricalStats.select(fn.MIN(HistoricalStats.created_at)).where(HistoricalStats.server_id == int_server_id).scalar()
    return min_date


def get_server_join_date(server_id: int | str, lang: str = "fr") -> str:
    """Return the formatted localized earliest activity date for a server."""
    min_date = get_server_raw_join_date(server_id)
    if not min_date:
        return ""
    return format_date_localized(min_date, lang=lang)


def get_monthly_messages_diff(server_id: int | None = None, user_id: int | None = None) -> list[dict]:
    """Calculate incremental messages sent each month by computing the difference between month-start totals."""
    query = (
        HistoricalStats
        .select(
            fn.DATE_TRUNC("month", HistoricalStats.created_at).alias("month_start"),
            fn.SUM(HistoricalStats.messages).alias("total_messages")
        )
        .where(SQL("EXTRACT(DAY FROM created_at) = 1"))
    )

    if server_id:
        query = query.where(HistoricalStats.server_id == server_id)
    if user_id:
        query = query.where(HistoricalStats.user_id == user_id)

    query = query.group_by(fn.DATE_TRUNC("month", HistoricalStats.created_at)).order_by(
        fn.DATE_TRUNC("month", HistoricalStats.created_at)
    )

    monthly_data = [
        {
            "month": row.month_start.strftime("%Y-%m-%d"),
            "total_messages": int(row.total_messages or 0)
        }
        for row in query
    ]

    # Baseline for user/server join month
    if user_id:
        start_date = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.user_id == user_id).scalar()
        if start_date:
            start_month_str = start_date.strftime("%Y-%m-01")
            monthly_data = [r for r in monthly_data if r["month"] >= start_month_str]
            if not any(r["month"] == start_month_str for r in monthly_data):
                monthly_data.append({"month": start_month_str, "total_messages": 0})
    elif server_id:
        server_min = Stats.select(fn.MIN(Stats.date_creation)).where(Stats.server_id == server_id).scalar()
        if server_min:
            start_month_str = server_min.strftime("%Y-%m-01")
            monthly_data = [r for r in monthly_data if r["month"] >= start_month_str]
            if not any(r["month"] == start_month_str for r in monthly_data):
                monthly_data.append({"month": start_month_str, "total_messages": 0})

    curr_query = Stats.select(fn.SUM(Stats.messages))
    if server_id:
        curr_query = curr_query.where(Stats.server_id == server_id)
    if user_id:
        curr_query = curr_query.where(Stats.user_id == user_id)
    current_total = curr_query.scalar() or 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    if any(r["month"] == today_str for r in monthly_data):
        for r in monthly_data:
            if r["month"] == today_str:
                r["total_messages"] = int(current_total)
                break
    else:
        monthly_data.append({
            "month": today_str,
            "total_messages": int(current_total)
        })

    monthly_data = sorted(monthly_data, key=lambda x: x["month"])

    monthly_differences = []
    for i in range(1, len(monthly_data)):
        prev = monthly_data[i - 1]
        curr = monthly_data[i]
        diff = curr["total_messages"] - prev["total_messages"]
        monthly_differences.append({
            "month": prev["month"],
            "messages_this_month": max(diff, 0)
        })

    return monthly_differences


def get_daily_activity_last_30_days() -> list[dict]:
    """Calculate day-by-day incremental voice hours and messages over the last 30 days."""
    cutoff = datetime.now() - timedelta(days=32)
    query = (
        HistoricalStats
        .select(
            fn.DATE(HistoricalStats.created_at).alias("day_date"),
            fn.SUM(HistoricalStats.seconds).alias("total_seconds"),
            fn.SUM(HistoricalStats.messages).alias("total_messages")
        )
        .where(HistoricalStats.created_at >= cutoff)
        .group_by(fn.DATE(HistoricalStats.created_at))
        .order_by(fn.DATE(HistoricalStats.created_at))
    )

    daily_cumulative = [
        {
            "date": row.day_date.strftime("%Y-%m-%d"),
            "seconds": int(row.total_seconds or 0),
            "messages": int(row.total_messages or 0)
        }
        for row in query
    ]

    today_str = datetime.now().strftime("%Y-%m-%d")
    curr_s = Stats.select(fn.SUM(Stats.seconds)).scalar() or 0
    curr_m = Stats.select(fn.SUM(Stats.messages)).scalar() or 0
    if not daily_cumulative or daily_cumulative[-1]["date"] != today_str:
        daily_cumulative.append({
            "date": today_str,
            "seconds": int(curr_s),
            "messages": int(curr_m)
        })

    daily_activity = []
    for i in range(1, len(daily_cumulative)):
        prev = daily_cumulative[i - 1]
        curr = daily_cumulative[i]
        diff_hours = round(max(curr["seconds"] - prev["seconds"], 0) / 3600, 1)
        diff_msgs = max(curr["messages"] - prev["messages"], 0)
        daily_activity.append({
            "date": curr["date"],
            "hours": diff_hours,
            "messages": diff_msgs
        })

    return daily_activity[-30:]


def get_top_10_users_by_hours() -> list[dict]:
    """Retrieve the top 10 most active members by total voice hours across all servers (excluding bot)."""
    HOURGLASS_BOT_ID = 1210665993328926750
    query = (
        Stats
        .select(
            Stats.user_id,
            Users.username,
            fn.SUM(Stats.seconds).alias("total_seconds"),
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .join(Users, JOIN.LEFT_OUTER, on=(Stats.user_id == Users.user_id))
        .where(Stats.user_id != HOURGLASS_BOT_ID)
        .group_by(Stats.user_id, Users.username)
        .order_by(fn.SUM(Stats.seconds).desc())
        .limit(10)
        .dicts()
    )

    top_users = []
    for row in query:
        name = row["username"] if row["username"] else f"Membre {row['user_id']}"
        top_users.append({
            "user_id": row["user_id"],
            "username": name,
            "hours": round((row["total_seconds"] or 0) / 3600, 1),
            "messages": int(row["total_messages"] or 0)
        })
    return top_users


def get_vocal_vs_messages_scatter(limit: int = 40) -> list[dict]:
    """Retrieve top active members formatted as (x: vocal hours, y: messages) for scatter plot analysis."""
    HOURGLASS_BOT_ID = 1210665993328926750
    query = (
        Stats
        .select(
            Stats.user_id,
            Users.username,
            fn.SUM(Stats.seconds).alias("total_seconds"),
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .join(Users, JOIN.LEFT_OUTER, on=(Stats.user_id == Users.user_id))
        .where(Stats.user_id != HOURGLASS_BOT_ID)
        .group_by(Stats.user_id, Users.username)
        .order_by((fn.SUM(Stats.seconds) + fn.SUM(Stats.messages) * 60).desc())
        .limit(limit)
        .dicts()
    )

    scatter_data = []
    for row in query:
        name = row["username"] if row["username"] else f"Membre {row['user_id']}"
        scatter_data.append({
            "username": name,
            "x": round((row["total_seconds"] or 0) / 3600, 1),
            "y": int(row["total_messages"] or 0)
        })
    return scatter_data


def get_monthly_new_users_growth() -> list[dict]:
    """Group users by the month of their earliest recorded activity to show community growth cohorts."""
    HOURGLASS_BOT_ID = 1210665993328926750
    user_first_seen = (
        Stats
        .select(
            Stats.user_id,
            fn.DATE_TRUNC("month", fn.MIN(Stats.date_creation)).alias("join_month")
        )
        .where(Stats.user_id != HOURGLASS_BOT_ID)
        .group_by(Stats.user_id)
        .alias("user_first_seen")
    )

    query = (
        Stats
        .select(
            user_first_seen.c.join_month,
            fn.COUNT(user_first_seen.c.user_id).alias("new_users")
        )
        .from_(user_first_seen)
        .group_by(user_first_seen.c.join_month)
        .order_by(user_first_seen.c.join_month)
    )

    cohorts = []
    for row in query:
        if row.join_month:
            cohorts.append({
                "month": row.join_month.strftime("%Y-%m-%d"),
                "new_users": int(row.new_users)
            })
    return cohorts