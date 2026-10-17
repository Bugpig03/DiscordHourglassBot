"""Profile customization stored in user_profile_settings: accent color, banner, favorite server,
featured badges, pinned records and block visibility (per block or private mode).

Reads never fail a page: if the table is missing (migration not applied yet) or the query errors,
the profile falls back to the default look.
"""

import json
import logging
from datetime import datetime, timezone

from peewee import DatabaseError

from app.database import db, UserProfileSettings

log = logging.getLogger(__name__)

# Accent palette tuned for the dark theme (every color stays readable on #0f1722 cards)
PALETTE = [
    ("sky", "#38bdf8", "Ciel", "Sky"),
    ("indigo", "#818cf8", "Indigo", "Indigo"),
    ("violet", "#a78bfa", "Violet", "Violet"),
    ("pink", "#f472b6", "Rose", "Pink"),
    ("red", "#f87171", "Rouge", "Red"),
    ("orange", "#fb923c", "Orange", "Orange"),
    ("amber", "#fbbf24", "Ambre", "Amber"),
    ("lime", "#a3e635", "Citron vert", "Lime"),
    ("emerald", "#34d399", "Émeraude", "Emerald"),
    ("teal", "#2dd4bf", "Turquoise", "Teal"),
]
PALETTE_HEX = {key: hex_ for key, hex_, _, _ in PALETTE}
DEFAULT_ACCENT = "sky"
DISCORD_ACCENT = "discord"  # the accent color of the member's Discord profile

BANNER_MODES = ("auto", "gradient", "none")  # auto = Discord banner when known, else gradient

# Sections of the "Activité" tab, in display order
ACTIVITY_BLOCKS = ["streaks", "heatmap", "hourly", "companions"]
# Blocks the member can hide from visitors (key: label fr, label en)
HIDEABLE_BLOCKS = {
    "showcase": ("Vitrine de badges", "Badge showcase"),
    "records": ("Records épinglés", "Pinned records"),
    "streaks": ("Séries et assiduité", "Streaks and consistency"),
    "heatmap": ("Calendrier d’activité", "Activity calendar"),
    "hourly": ("Rythme horaire", "Hourly rhythm"),
    "companions": ("Compagnons vocaux", "Voice companions"),
    "tab_charts": ("Graphiques", "Charts"),
    "tab_servers": ("Serveurs fréquentés", "Servers"),
    "tab_badges": ("Badges", "Badges"),
}

DEFAULTS = {
    "accent_color": DEFAULT_ACCENT,
    "banner_mode": "auto",
    "discord_banner": None,
    "discord_accent": None,
    "favorite_server_id": None,
    "featured_badges": [],
    "pinned_records": [],
    "layout": {},
}


def ensure_table() -> None:
    """Create the settings table when the migration was not run (CREATE TABLE IF NOT EXISTS, harmless)."""
    try:
        with db.connection_context():
            db.create_tables([UserProfileSettings], safe=True)
    except DatabaseError as e:
        log.warning("user_profile_settings table unavailable, profile customization disabled: %s", e)


def get_profile_settings(user_id: int | str) -> dict:
    """Saved customization of a member merged over the defaults."""
    settings = dict(DEFAULTS)
    try:
        row = UserProfileSettings.get_or_none(UserProfileSettings.user_id == int(user_id))
    except (DatabaseError, ValueError) as e:
        _rollback()
        log.warning("Could not read profile settings of %s: %s", user_id, e)
        return settings
    if row:
        settings.update({
            "accent_color": row.accent_color or DEFAULT_ACCENT,
            "banner_mode": row.banner_mode if row.banner_mode in BANNER_MODES else "auto",
            "discord_banner": row.discord_banner,
            "discord_accent": row.discord_accent,
            "favorite_server_id": row.favorite_server_id,
            "featured_badges": _json_list(row.featured_badges),
            "pinned_records": _json_list(row.pinned_records),
            "layout": _json_dict(row.layout),
        })
    return settings


def _json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [str(v) for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _json_dict(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def save_profile_settings(user_id: int, values: dict) -> bool:
    """Insert or update the member's choices (values are validated by the caller)."""
    fields = {
        getattr(UserProfileSettings, key): json.dumps(value) if isinstance(value, (list, dict)) else value
        for key, value in values.items()
    }
    fields[UserProfileSettings.updated_at] = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        (UserProfileSettings
         .insert(user_id=user_id, **{f.name: v for f, v in fields.items()})
         .on_conflict(conflict_target=[UserProfileSettings.user_id], update=fields)
         .execute())
        return True
    except DatabaseError as e:
        _rollback()
        log.error("Could not save profile settings of %s: %s", user_id, e)
        return False


def remember_discord_identity(user_id: int | str, banner: str | None, accent: int | None) -> None:
    """Keep the Discord banner and profile color seen at login (the bot does not collect them)."""
    if banner is not None and (len(banner) > 64 or not banner.replace("_", "").isalnum()):
        banner = None
    save_profile_settings(int(user_id), {"discord_banner": banner, "discord_accent": accent})


def _rollback() -> None:
    try:
        db.rollback()
    except Exception:
        pass


# ------------------------------------------------------------------------------
# Rendering helpers
# ------------------------------------------------------------------------------

def _hex_to_rgb(hex_: str) -> tuple[int, int, int]:
    hex_ = hex_.lstrip("#")
    return int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)


def _readable_on_dark(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Lighten a too-dark Discord color so text and bars stay visible on the dark cards."""
    def luminance(c):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2])

    for _ in range(8):
        if luminance(rgb) >= 0.22:
            break
        rgb = tuple(round(v + (255 - v) * 0.2) for v in rgb)
    return rgb


def discord_accent_hex(settings: dict) -> str | None:
    accent = settings.get("discord_accent")
    if accent is None:
        return None
    try:
        accent = int(accent)
    except (TypeError, ValueError):
        return None
    if not 0 <= accent <= 0xFFFFFF:
        return None
    rgb = _readable_on_dark(((accent >> 16) & 255, (accent >> 8) & 255, accent & 255))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def resolve_profile_theme(user_id: int | str, settings: dict) -> dict:
    """Colors and banner the profile page renders with."""
    key = settings.get("accent_color") or DEFAULT_ACCENT
    hex_ = discord_accent_hex(settings) if key == DISCORD_ACCENT else PALETTE_HEX.get(key)
    if not hex_:
        key, hex_ = DEFAULT_ACCENT, PALETTE_HEX[DEFAULT_ACCENT]
    r, g, b = _hex_to_rgb(hex_)

    mode = settings.get("banner_mode") or "auto"
    banner = settings.get("discord_banner")
    discord_banner_url = None
    if banner:
        ext = "gif" if banner.startswith("a_") else "png"
        discord_banner_url = f"https://cdn.discordapp.com/banners/{int(user_id)}/{banner}.{ext}?size=1024"
    banner_url = discord_banner_url if mode == "auto" else None

    return {
        "accent_key": key,
        "accent_hex": hex_,
        "accent_rgb": f"{r}, {g}, {b}",
        "is_custom": key != DEFAULT_ACCENT,
        "banner_mode": mode,
        "banner_url": banner_url,
        "discord_banner_url": discord_banner_url,
        "show_banner": mode != "none",
    }


def resolve_layout(settings: dict, is_owner: bool) -> dict:
    """Visibility of the profile blocks for this viewer.

    The owner always sees every block (hidden ones are tagged "hidden from visitors"); visitors do not
    receive hidden blocks at all, not even their data. Private mode hides every block below the totals.
    """
    layout = settings.get("layout") or {}
    private = bool(layout.get("private"))
    hidden = set(HIDEABLE_BLOCKS) if private else {k for k in layout.get("hidden", []) if k in HIDEABLE_BLOCKS}
    return {
        "order": ACTIVITY_BLOCKS,
        "hidden": {k: k in hidden for k in HIDEABLE_BLOCKS},
        "visible": {k: is_owner or k not in hidden for k in HIDEABLE_BLOCKS},
        "private": private,
        "private_view": private and not is_owner,
        "is_owner": is_owner,
    }
