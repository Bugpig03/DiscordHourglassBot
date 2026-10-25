"""Personal records a member can pin on the profile, and the featured badge showcase."""

from datetime import datetime

from app.database import Servers, VoiceSessions
from app.pixel_icons import name_for_lucide, pixel_svg
from app.i18n import day_month_year, format_number, month_year, tr
from app.functions import (
    get_month_abbr,
    get_monthly_hours_diff,
    get_monthly_messages_diff,
    to_user_timezone,
)

MAX_PINNED_RECORDS = 4
DEFAULT_PINNED_RECORDS = ["longest_session", "best_month_voice", "best_month_messages", "top_companion"]
MAX_FEATURED_BADGES = 3

_ICONS = {
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "server": '<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "check": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="m9 15 2 2 4-4"/>',
}

# key: (icon, label fr, label en)
RECORD_CATALOG = {
    "longest_session": ("clock", "Plus longue session", "Longest session"),
    "best_day": ("sun", "Meilleure journée", "Best day"),
    "max_streak": ("flame", "Plus longue série", "Longest streak"),
    "best_month_voice": ("calendar", "Meilleur mois en vocal", "Best voice month"),
    "best_month_messages": ("message", "Meilleur mois en messages", "Best message month"),
    "top_server": ("server", "Serveur principal", "Main server"),
    "top_companion": ("users", "Meilleur compagnon vocal", "Top voice companion"),
    "peak_hour": ("moon", "Heure de pointe en vocal", "Peak voice hour"),
    "active_days": ("check", "Jours actifs sur un an", "Active days in a year"),
}


def _svg(name: str) -> str:
    """Record icon on the website: the pixel-art version of the drawing."""
    pixel = name_for_lucide(_ICONS[name])
    if pixel:
        return str(pixel_svg(pixel, 18))
    return (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round">{_ICONS[name]}</svg>'
    )


def _month_label(month: str, lang: str) -> str:
    dt = datetime.strptime(month, "%Y-%m-%d")
    return month_year(dt.month, dt.year, lang)


def _duration(seconds: int, lang: str) -> str:
    hours, minutes = divmod(int(seconds) // 60, 60)
    if hours and minutes:
        return f"{hours} h {minutes:02d}"
    return f"{hours} h" if hours else f"{minutes} min"


def query_record_sources(user_id: int) -> dict:
    """Database part of the records (cached by the caller, identical for every visitor)."""
    longest = (
        VoiceSessions
        .select(VoiceSessions.duration_seconds, VoiceSessions.joined_at, Servers.servername)
        .join(Servers, on=(VoiceSessions.server_id == Servers.server_id))
        .where(
            (VoiceSessions.user_id == user_id)
            & (VoiceSessions.is_legacy == False)  # noqa: E712 - legacy rows are daily snapshots, not sessions
            & (VoiceSessions.left_at.is_null(False))
        )
        .order_by(VoiceSessions.duration_seconds.desc())
        .first()
    )
    months_voice = [m for m in get_monthly_hours_diff(user_id=user_id) if m["hours_this_month"] > 0]
    months_msgs = [m for m in get_monthly_messages_diff(user_id=user_id) if m["messages_this_month"] > 0]
    return {
        "longest": {
            "seconds": int(longest.duration_seconds or 0),
            "joined_at": longest.joined_at,
            "server": longest.servers.servername if longest.servers else None,
        } if longest and longest.duration_seconds else None,
        "best_month_voice": max(months_voice, key=lambda m: m["hours_this_month"]) if months_voice else None,
        "best_month_messages": max(months_msgs, key=lambda m: m["messages_this_month"]) if months_msgs else None,
    }


def build_records(sources: dict, stats: dict, heatmap: dict, companions: list, peak_voice_hour: str, lang: str) -> dict:
    """Every record the member has data for, keyed like RECORD_CATALOG (records without data are left out)."""
    values: dict[str, dict] = {}

    longest = sources.get("longest")
    if longest:
        joined = to_user_timezone(longest["joined_at"])
        if not joined:
            sub = ""
        elif lang == "fr":
            sub = f"{joined.day} {get_month_abbr(joined.month, lang).lower()} {joined.year}"
        else:
            sub = day_month_year(joined.day, joined.month, joined.year, lang)
        if longest["server"]:
            sub = f"{sub} · {longest['server']}" if sub else longest["server"]
        values["longest_session"] = {"value": _duration(longest["seconds"], lang), "sub": sub}

    best_day = heatmap.get("best_day") if heatmap else None
    if best_day and best_day.get("hours"):
        values["best_day"] = {"value": best_day["hours"], "decimals": 1, "unit": "h", "sub": best_day["label"]}

    if heatmap and heatmap.get("max_streak"):
        streak = heatmap["max_streak"]
        values["max_streak"] = {
            "value": streak, "unit": tr("jour", "day", lang) if streak <= 1 else tr("jours", "days", lang),
            "sub": tr("jours actifs d’affilée", "active days in a row", lang),
        }

    month = sources.get("best_month_voice")
    if month:
        values["best_month_voice"] = {"value": month["hours_this_month"], "decimals": 1, "unit": "h", "sub": _month_label(month["month"], lang)}

    month = sources.get("best_month_messages")
    if month:
        values["best_month_messages"] = {"value": month["messages_this_month"], "unit": tr("messages", "messages", lang), "sub": _month_label(month["month"], lang)}

    servers = stats.get("user_servers_stats") or []
    if servers and servers[0]["time_spent"] > 0:
        top = servers[0]
        values["top_server"] = {"value": top["server_name"], "sub": f"{format_number(top['time_spent'], 1, lang)} h · #{top['rank']}"}

    if companions:
        buddy = companions[0]
        hours = format_number(buddy["shared_hours"], 1, lang)
        values["top_companion"] = {"value": buddy["username"], "sub": tr("{h} h ensemble", "{h} h together", lang, h=hours)}

    if peak_voice_hour and peak_voice_hour != "-":
        values["peak_hour"] = {"value": peak_voice_hour, "sub": tr("créneau le plus actif", "most active time slot", lang)}

    if heatmap and heatmap.get("total_active_days"):
        values["active_days"] = {"value": heatmap["total_active_days"], "unit": "/ 365", "sub": tr("jours avec de l’activité", "days with activity", lang)}

    records = {}
    for key, (icon, label_fr, label_en) in RECORD_CATALOG.items():
        if key in values:
            records[key] = {"key": key, "icon": _svg(icon), "label": tr(label_fr, label_en, lang), "decimals": 0, "unit": "", **values[key]}
    return records


def pinned_records(records: dict, chosen: list[str]) -> list[dict]:
    """Records to show: the member's choice, or the default selection when nothing was chosen."""
    keys = chosen or DEFAULT_PINNED_RECORDS
    return [records[k] for k in keys if k in records][:MAX_PINNED_RECORDS]


def featured_badges(badges: list[dict], chosen: list[str]) -> list[dict]:
    """Badges of the showcase: the member's choice (still unlocked), or the highest tiers by default."""
    unlocked = [b for b in badges if b["unlocked"]]
    if chosen:
        by_id = {b["id"]: b for b in unlocked}
        return [by_id[i] for i in chosen if i in by_id][:MAX_FEATURED_BADGES]
    return sorted(unlocked, key=lambda b: b["tier"], reverse=True)[:MAX_FEATURED_BADGES]
