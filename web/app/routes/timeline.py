"""Timeline page (Outils menu): a leaderboard race built by the visitor, and its JSON API."""

import logging

from flask import Blueprint, jsonify, render_template, request

from app.auth import get_current_user
from app.i18n import current_lang
from app.timeline import (
    DEFAULT_TOP, MAX_PICKS, METRICS, TOPS, build_timeline, hidden_user_ids, parse_month, search_members,
    server_exists, timeline_servers,
)

log = logging.getLogger(__name__)

timeline_bp = Blueprint("timeline", __name__)


def _server_arg() -> int | None:
    try:
        server_id = int(request.args.get("srv") or 0)
    except (TypeError, ValueError):
        return None
    return server_id if server_id and server_exists(server_id) else None


def _picks_arg() -> list[int]:
    picks: list[int] = []
    for part in (request.args.get("users") or "").split(","):
        part = part.strip()
        if part.isdigit() and len(part) <= 20 and int(part) not in picks:
            picks.append(int(part))
        if len(picks) >= MAX_PICKS:
            break
    return picks


@timeline_bp.route("/timeline", methods=["GET"])
def timeline():
    """The builder; the settings live in the address (shared links open the same race)."""
    user = get_current_user()
    me = None
    if user and str(user.get("id", "")).isdigit() and int(user["id"]) not in hidden_user_ids():
        me = {"id": str(user["id"]), "name": user.get("username") or "", "avatar": user.get("avatar")}
    return render_template(
        "timeline.html",
        servers=timeline_servers(),
        me=me,
        tops=TOPS,
        default_top=DEFAULT_TOP,
        max_picks=MAX_PICKS,
    )


@timeline_bp.route("/api/timeline", methods=["GET"])
def timeline_data():
    metric = request.args.get("metric", "voice")
    if metric not in METRICS:
        metric = "voice"
    try:
        top = int(request.args.get("top") or DEFAULT_TOP)
    except (TypeError, ValueError):
        top = DEFAULT_TOP
    if top not in TOPS:
        top = DEFAULT_TOP
    server_id = _server_arg()
    picks = _picks_arg() if request.args.get("users") else []
    start, end = parse_month(request.args.get("from")), parse_month(request.args.get("to"))
    if start and end and start > end:
        start, end = end, start
    try:
        data = build_timeline(metric, server_id, picks, top, start, end, current_lang())
    except Exception:
        log.exception("Timeline unavailable")
        return jsonify({"error": "unavailable"}), 500
    return jsonify(dict(data, server=str(server_id) if server_id else None))


@timeline_bp.route("/api/timeline/members", methods=["GET"])
def timeline_members():
    """Members to pick by name (bots and private profiles left out)."""
    try:
        return jsonify({"members": search_members(request.args.get("q", ""), _server_arg())})
    except Exception:
        log.exception("Timeline member search failed")
        return jsonify({"members": []})
