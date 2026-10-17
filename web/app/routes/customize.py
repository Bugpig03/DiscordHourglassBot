"""Profile customization page (owner only): accent color, banner and favorite server."""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.auth import get_current_user
from app.database import Users
from app.functions import get_user_servers_stats, get_total_seconds_by_user_id, get_total_message_by_user_id
from app.gamification import calculate_user_xp_and_level
from app.profile_settings import (
    BANNER_MODES,
    DISCORD_ACCENT,
    PALETTE,
    PALETTE_HEX,
    discord_accent_hex,
    get_profile_settings,
    resolve_profile_theme,
    save_profile_settings,
)
from app.security import valid_csrf

customize_bp = Blueprint("customize", __name__)


@customize_bp.route("/me/profile", methods=["GET", "POST"])
def customize_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login", next=request.path))
    user_id = int(user["id"])
    member = Users.get_or_none(Users.user_id == user_id)
    settings = get_profile_settings(user_id)
    servers = get_user_servers_stats(user_id) if member else []

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            abort(400)
        if not member:
            return redirect(url_for("customize.customize_profile"))
        values = _validated_form(settings, servers)
        saved = save_profile_settings(user_id, values)
        return redirect(url_for("customize.customize_profile", saved=1 if saved else 0))

    lang = request.cookies.get("lang", "fr")
    xp = calculate_user_xp_and_level(
        get_total_seconds_by_user_id(user_id) or 0, get_total_message_by_user_id(user_id) or 0
    ) if member else None
    favorite_server = next((s for s in servers if s["server_id"] == settings["favorite_server_id"]), None)
    return render_template(
        "customize_profile.html",
        member=member,
        settings=settings,
        theme=resolve_profile_theme(user_id, settings),
        palette=[{"key": k, "hex": h, "label": fr if lang == "fr" else en} for k, h, fr, en in PALETTE],
        discord_accent=discord_accent_hex(settings),
        has_discord_banner=bool(settings.get("discord_banner")),
        servers=servers,
        favorite_server=favorite_server,
        xp=xp,
        saved=request.args.get("saved"),
    )


def _validated_form(settings: dict, servers: list[dict]) -> dict:
    """Keep only values the form is allowed to send; anything unexpected falls back to the current choice."""
    accent = request.form.get("accent_color", "")
    if accent not in PALETTE_HEX and not (accent == DISCORD_ACCENT and discord_accent_hex(settings)):
        accent = settings["accent_color"]

    banner_mode = request.form.get("banner_mode", "")
    if banner_mode not in BANNER_MODES:
        banner_mode = settings["banner_mode"]

    favorite = request.form.get("favorite_server_id", "")
    allowed_servers = {str(s["server_id"]) for s in servers}
    favorite_server_id = int(favorite) if favorite in allowed_servers else None

    return {
        "accent_color": accent,
        "banner_mode": banner_mode,
        "favorite_server_id": favorite_server_id,
    }
