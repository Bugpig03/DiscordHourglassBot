"""Stat card endpoints.

- /internal/card/<kind>.png: PNG images for the Discord bot, protected by the CARD_TOKEN shared secret
  (header X-Card-Token). Disabled (404) while CARD_TOKEN is not configured.
- /api/card/...: the same cards as embeddable SVG (public, rate limited like the rest of /api/card/).
"""

import hmac
import logging

from flask import Blueprint, Response, abort, current_app, jsonify, request

from app.cards import builders
from app.cards.design import to_png

cards_bp = Blueprint("cards", __name__)
log = logging.getLogger(__name__)

PNG_CACHE_SECONDS = 120


def _int_arg(name: str) -> int | None:
    value = (request.args.get(name) or "").strip()
    return int(value) if value.isdigit() else None


# ---------------------------------------------------------------------------
# PNG for the bot
# ---------------------------------------------------------------------------
def _check_token() -> None:
    expected = current_app.config.get("CARD_TOKEN") or ""
    given = request.headers.get("X-Card-Token", "")
    if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
        abort(404)


def _png(key: tuple, build) -> Response:
    try:
        png = builders.card_cache.get_or_set(("card_png",) + key, PNG_CACHE_SECONDS, lambda: to_png(build()))
    except builders.CardNotFound as e:
        return jsonify({"error": "not_found", "what": str(e)}), 404
    resp = Response(png, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@cards_bp.route("/internal/card/member.png")
def internal_member_card():
    _check_token()
    user_id, server_id = _int_arg("user"), _int_arg("server")
    if not user_id:
        abort(400)
    return _png(("member", user_id, server_id), lambda: builders.member_card(user_id, server_id))


@cards_bp.route("/internal/card/versus.png")
def internal_versus_card():
    _check_token()
    u1, u2, server_id = _int_arg("u1"), _int_arg("u2"), _int_arg("server")
    if not u1 or not u2:
        abort(400)
    return _png(("versus", u1, u2, server_id), lambda: builders.versus_card(u1, u2, server_id))


@cards_bp.route("/internal/card/top.png")
def internal_top_card():
    _check_token()
    metric, period, server_id = request.args.get("type", "voice"), request.args.get("period", "all"), _int_arg("server")
    return _png(("top", metric, period, server_id), lambda: builders.top_card(metric, period, server_id))


@cards_bp.route("/internal/card/server.png")
def internal_server_card():
    _check_token()
    server_id = _int_arg("server")
    if not server_id:
        abort(400)
    return _png(("server", server_id), lambda: builders.server_card(server_id))


# ---------------------------------------------------------------------------
# Embeddable SVG (same URLs as before v3.19.0)
# ---------------------------------------------------------------------------
def _svg(build, max_age: int = 180) -> Response:
    try:
        svg, status = build(), 200
    except builders.CardNotFound as e:
        what = "Server" if str(e) == "server" else "Member"
        svg, status = builders.error_card(f"{what} not found", f"Hourglass has no activity recorded for this {what.lower()} yet."), 404
    resp = Response(svg, mimetype="image/svg+xml", status=status)
    resp.headers["Cache-Control"] = f"public, max-age={max_age}" if status == 200 else "no-store"
    return resp


def _user_or_404(identifier: str) -> int:
    user_id = builders.resolve_user_id(identifier)
    if user_id is None:
        raise builders.CardNotFound("member")
    return user_id


@cards_bp.route("/api/card/user/<username>")
@cards_bp.route("/api/card/allstats/<username>")
def svg_member_card(username: str):
    return _svg(lambda: builders.member_card(_user_or_404(username)))


@cards_bp.route("/api/card/user/<username>/server/<int:server_id>")
@cards_bp.route("/api/card/stats/<username>/<int:server_id>")
def svg_member_server_card(username: str, server_id: int):
    return _svg(lambda: builders.member_card(_user_or_404(username), server_id))


@cards_bp.route("/api/card/versus/<user1>/<user2>")
def svg_versus_card(user1: str, user2: str):
    return _svg(lambda: builders.versus_card(_user_or_404(user1), _user_or_404(user2), _int_arg("server")))


@cards_bp.route("/api/card/top/server/<int:server_id>")
@cards_bp.route("/api/card/server/<int:server_id>/top")
def svg_server_top_card(server_id: int):
    return _svg(lambda: builders.top_card(request.args.get("type", "voice"), request.args.get("period", "all"), server_id))


@cards_bp.route("/api/card/top")
@cards_bp.route("/api/card/top/global")
@cards_bp.route("/api/card/alltop")
def svg_global_top_card():
    return _svg(lambda: builders.top_card(request.args.get("type", "voice"), request.args.get("period", "all")))


@cards_bp.route("/api/card/server/<int:server_id>")
def svg_server_card(server_id: int):
    return _svg(lambda: builders.server_card(server_id))


@cards_bp.route("/api/card/commands")
@cards_bp.route("/api/card/help")
@cards_bp.route("/api/card/aide")
def svg_help_card():
    return _svg(builders.help_card, max_age=3600)
