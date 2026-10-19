"""Profile customization page (owner only): color, banner and background color, favorite server, showcase, records and layout."""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.auth import get_current_user
from app.database import Users
from app.gamification import calculate_user_xp_and_level, calculate_user_badges
from app.profile_records import (
    DEFAULT_PINNED_RECORDS,
    MAX_FEATURED_BADGES,
    MAX_PINNED_RECORDS,
    RARITY_ORDER,
    RECORD_CATALOG,
    featured_badges,
)
from app.profile_gallery import BANNERS, banner_url, gallery
from app.routes.user_profile import load_profile_extras, load_user_charts_data, load_user_profile_stats
from app.profile_settings import (
    BACKGROUND_COLORS,
    BACKGROUND_HEX,
    BANNER_MODES,
    DEFAULT_BANNER_IMAGE,
    DISCORD_ACCENT,
    HIDEABLE_BLOCKS,
    PALETTE,
    PALETTE_HEX,
    discord_accent_hex,
    get_profile_settings,
    resolve_layout,
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
    lang = request.cookies.get("lang", "fr")
    stats = load_user_profile_stats(user_id, member.username or user["username"], can_view_presence=False) if member else None
    servers = stats["user_servers_stats"] if stats else []
    badges = calculate_user_badges(stats, lang=lang) if stats else []

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            abort(400)
        if not member:
            return redirect(url_for("customize.customize_profile"))
        values = _validated_form(settings, servers, badges)
        saved = save_profile_settings(user_id, values)
        return redirect(url_for("customize.customize_profile", saved=1 if saved else 0))

    xp = calculate_user_xp_and_level(stats["total_seconds"], stats["total_message"]) if stats else None
    records = {}
    if stats:
        charts = load_user_charts_data(user_id, servers, lang=lang)
        records = load_profile_extras(user_id, stats, charts, lang)["records"]
    favorite_server = next((s for s in servers if s["server_id"] == settings["favorite_server_id"]), None)
    theme = resolve_profile_theme(user_id, settings)
    label = (lambda fr, en: fr if lang == "fr" else en)
    palette = [{"key": k, "hex": h, "label": label(fr, en)} for k, h, fr, en in PALETTE]
    background_colors = [{"key": k, "hex": h, "label": label(fr, en)} for k, h, fr, en in BACKGROUND_COLORS]
    banner_gallery = gallery(BANNERS, banner_url, lang)
    # Names shown next to each setting ("current choice")
    current_accent = next((c["label"] for c in palette if c["key"] == theme["accent_key"]), label("Couleur Discord", "Discord color"))
    current_banner = (next((b["label"] for b in banner_gallery if b["key"] == theme["banner_image"]), "")
                      if theme["banner_mode"] == "image" else label("Aucune", "None"))
    current_background = next((c["label"] for c in background_colors if c["key"] == theme["background_color"]), label("Par défaut", "Default"))
    return render_template(
        "customize_profile.html",
        member=member,
        settings=settings,
        theme=theme,
        palette=palette,
        current_accent=current_accent,
        current_banner=current_banner,
        current_background=current_background,
        discord_accent=discord_accent_hex(settings),
        banner_gallery=banner_gallery,
        background_colors=background_colors,
        servers=servers,
        favorite_server=favorite_server,
        xp=xp,
        # Rarest first: the badges worth showing off are at the top of the picker
        badges=sorted((b for b in badges if b["unlocked"]), key=lambda b: RARITY_ORDER.get(b["rarity"], 0), reverse=True),
        showcase=featured_badges(badges, settings["featured_badges"]),
        records=records,
        pinned_keys=settings["pinned_records"] or [k for k in DEFAULT_PINNED_RECORDS if k in records],
        layout=resolve_layout(settings, is_owner=True),
        block_labels={k: (fr if lang == "fr" else en) for k, (fr, en) in HIDEABLE_BLOCKS.items()},
        max_badges=MAX_FEATURED_BADGES,
        max_records=MAX_PINNED_RECORDS,
        saved=request.args.get("saved"),
    )


def _validated_form(settings: dict, servers: list[dict], badges: list[dict]) -> dict:
    """Keep only values the form is allowed to send; anything unexpected falls back to the current choice."""
    accent = request.form.get("accent_color", "")
    if accent not in PALETTE_HEX and not (accent == DISCORD_ACCENT and discord_accent_hex(settings)):
        accent = settings["accent_color"]

    banner_mode = request.form.get("banner_mode", "")
    if banner_mode not in BANNER_MODES:
        banner_mode = settings["banner_mode"]

    # Gallery pictures: only known keys; choosing the gallery without a picture uses the default one
    banner_image = request.form.get("banner_image") or None
    if banner_image not in BANNERS:
        banner_image = DEFAULT_BANNER_IMAGE if banner_mode == "image" else None
    background_color = request.form.get("background_color") or None
    if background_color not in BACKGROUND_HEX:
        background_color = None

    favorite = request.form.get("favorite_server_id", "")
    allowed_servers = {str(s["server_id"]) for s in servers}
    favorite_server_id = int(favorite) if favorite in allowed_servers else None

    # Order of the form is kept; unknown or locked ids are dropped. An empty list means "automatic".
    unlocked = {b["id"] for b in badges if b["unlocked"]}
    featured = list(dict.fromkeys(i for i in request.form.getlist("featured_badges") if i in unlocked))[:MAX_FEATURED_BADGES]
    pinned = list(dict.fromkeys(k for k in request.form.getlist("pinned_records") if k in RECORD_CATALOG))[:MAX_PINNED_RECORDS]

    visible = set(request.form.getlist("layout_visible"))
    layout = {
        "hidden": [k for k in HIDEABLE_BLOCKS if k not in visible],
        "private": request.form.get("layout_private") == "1",
    }

    return {
        "layout": layout,
        "featured_badges": featured,
        "pinned_records": pinned,
        "accent_color": accent,
        "banner_mode": banner_mode,
        "banner_image": banner_image,
        "background_color": background_color,
        "favorite_server_id": favorite_server_id,
    }
