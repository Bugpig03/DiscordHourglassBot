"""Hover cards: the small player / server card shown when the pointer rests on a ranking row (desktop).

Only figures already public on the profile and server pages are returned, and the badge showcase follows
the member's own visibility choice (hidden or private profile = no badges on the card).
"""

from flask import Blueprint, jsonify

from app.cache import cache
from app.database import Servers, Users
from app.functions import (
    format_date_localized,
    get_global_nb_server,
    get_server_activity_sum_last_X_days,
    get_server_live_status,
    get_server_rank,
    get_server_raw_join_date,
    get_total_message_by_server_id,
    get_total_seconds_by_server_id,
    get_user_count_by_server_id,
)
from app.gamification import calculate_user_badges, calculate_user_xp_and_level
from app.profile_records import featured_badges
from app.profile_settings import get_profile_settings, resolve_layout, resolve_profile_theme
from app.i18n import current_lang, tr

hovercard_bp = Blueprint("hovercard", __name__)

HOVER_CACHE_SECONDS = 120


def _lang() -> str:
    return current_lang()


def _user_card(user_id: int, lang: str) -> dict | None:
    from app.routes.user_profile import load_user_profile_stats  # the profile page's own figures

    user = Users.get_or_none(Users.user_id == user_id)
    if not user:
        return None
    stats = load_user_profile_stats(user_id, user.username or tr("Membre {id}", "Member {id}", lang, id=user_id), can_view_presence=False)
    xp = calculate_user_xp_and_level(stats["total_seconds"], stats["total_message"] or 0)
    settings = get_profile_settings(user_id)
    theme = resolve_profile_theme(user_id, settings)
    layout = resolve_layout(settings, is_owner=False)
    badges = calculate_user_badges(stats, lang=lang)
    showcase = featured_badges(badges, settings.get("featured_badges") or []) if layout["visible"]["showcase"] else []
    rank = stats["rank"] if isinstance(stats["rank"], int) else None
    return {
        "kind": "user",
        "name": user.username or tr("Membre {id}", "Member {id}", lang, id=user_id),
        "avatar": stats["avatar_url"],
        "accent": theme["accent_hex"],
        "level": xp["level"],
        "title": tr(xp["title_fr"], xp["title_en"], lang),
        "progress": xp["progress_percent"],
        "rank": rank,
        "rank_total": stats["total_user"],
        "hours": round((stats["total_seconds"] or 0) / 3600, 1),
        "hours_30d": round((stats["total_time_last_30d"] or 0) / 3600, 1),
        "messages": stats["total_message"] or 0,
        "badges": sum(b["tier"] for b in badges),
        "badges_total": sum(b["tier_count"] for b in badges),
        "showcase": [{"name": f"{b['name']} · {b['tier_label']}", "color": b["color"], "icon": b["icon"]} for b in showcase],
        "since": format_date_localized(stats["raw_join_date"], lang=lang) if stats["raw_join_date"] else None,
    }


def _server_card(server_id: int, lang: str) -> dict | None:
    server = Servers.get_or_none(Servers.server_id == server_id)
    if not server:
        return None
    live = get_server_live_status(server_id) or {}
    since = get_server_raw_join_date(server_id)
    return {
        "kind": "server",
        "name": server.servername or tr("Serveur {id}", "Server {id}", lang, id=server_id),
        "avatar": server.avatar,
        "rank": get_server_rank(server_id),
        "rank_total": get_global_nb_server(),
        "hours": round((get_total_seconds_by_server_id(server_id) or 0) / 3600, 1),
        "hours_30d": round((get_server_activity_sum_last_X_days(server_id, 30).get("seconds") or 0) / 3600, 1),
        "messages": get_total_message_by_server_id(server_id),
        "members": get_user_count_by_server_id(server_id),
        "in_voice": live.get("voice_count", 0),
        "bot_present": server.is_bot_present is not False,
        "since": format_date_localized(since, lang=lang) if since else None,
    }


@hovercard_bp.route("/api/hover/user/<int:user_id>", methods=["GET"])
def hover_user(user_id: int):
    lang = _lang()
    data = cache.get_or_set(("hover_user", user_id, lang), HOVER_CACHE_SECONDS, lambda: _user_card(user_id, lang))
    return (jsonify(data), 200) if data else (jsonify({"error": "not_found"}), 404)


@hovercard_bp.route("/api/hover/server/<int:server_id>", methods=["GET"])
def hover_server(server_id: int):
    lang = _lang()
    data = cache.get_or_set(("hover_server", server_id, lang), HOVER_CACHE_SECONDS, lambda: _server_card(server_id, lang))
    return (jsonify(data), 200) if data else (jsonify({"error": "not_found"}), 404)
