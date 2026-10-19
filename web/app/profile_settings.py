"""Profile customization stored in user_profile_settings: accent color, banner and page background color
(Discord, gradient or gallery image), favorite server, featured badges, pinned records and block visibility.

Reads never fail a page: if the table is missing (migration not applied yet) or the query errors,
the profile falls back to the default look.
"""

import json
import logging
from datetime import datetime, timezone

from peewee import DatabaseError

from app.database import db, UserProfileSettings
from app.profile_gallery import BANNERS, banner_url as gallery_banner_url

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
    ("blue", "#60a5fa", "Bleu", "Blue"),
    ("cyan", "#22d3ee", "Cyan", "Cyan"),
    ("purple", "#c084fc", "Pourpre", "Purple"),
    ("fuchsia", "#e879f9", "Fuchsia", "Fuchsia"),
    ("coral", "#fb7185", "Corail", "Coral"),
    ("peach", "#fdba74", "Pêche", "Peach"),
    ("yellow", "#facc15", "Jaune", "Yellow"),
    ("green", "#4ade80", "Vert", "Green"),
    ("mint", "#6ee7b7", "Menthe", "Mint"),
    ("silver", "#cbd5e1", "Argent", "Silver"),
]
PALETTE_HEX = {key: hex_ for key, hex_, _, _ in PALETTE}
DEFAULT_ACCENT = "sky"
DISCORD_ACCENT = "discord"  # the accent color of the member's Discord profile

# image = picture from the gallery; none = no banner. Older modes ("auto" = Discord banner until v3.16,
# "gradient" until v3.15) are still read from old rows and shown as the gallery picture.
BANNER_MODES = ("image", "none")
DEFAULT_BANNER_IMAGE = "aurora"

# Solid page backgrounds (key, hex, label fr, label en): dark shades so the cards and text stay readable
BACKGROUND_COLORS = [
    ("midnight", "#0b1220", "Minuit", "Midnight"),
    ("navy", "#0c1a33", "Marine", "Navy"),
    ("indigo", "#17153d", "Indigo", "Indigo"),
    ("violet", "#241538", "Violet", "Violet"),
    ("plum", "#2b122b", "Prune", "Plum"),
    ("wine", "#2c0f18", "Bordeaux", "Wine"),
    ("rust", "#2b1a0e", "Rouille", "Rust"),
    ("olive", "#1d2110", "Olive", "Olive"),
    ("forest", "#0e2117", "Forêt", "Forest"),
    ("teal", "#0b2327", "Sarcelle", "Teal"),
    ("slate", "#1a1f28", "Ardoise", "Slate"),
    ("black", "#050608", "Noir", "Black"),
]
BACKGROUND_HEX = {k: h for k, h, _, _ in BACKGROUND_COLORS}

# Sections of the "Activité" tab, in display order
ACTIVITY_BLOCKS = ["streaks", "heatmap", "companions"]
# Blocks the member can hide from visitors (key: label fr, label en)
HIDEABLE_BLOCKS = {
    "showcase": ("Vitrine de badges", "Badge showcase"),
    "records": ("Records épinglés", "Pinned records"),
    "streaks": ("Séries et assiduité", "Streaks and consistency"),
    "heatmap": ("Calendrier d’activité", "Activity calendar"),
    "companions": ("Compagnons vocaux", "Voice companions"),
    "tab_charts": ("Graphiques", "Charts"),
    "tab_servers": ("Serveurs fréquentés", "Servers"),
    "tab_badges": ("Badges", "Badges"),
}

DEFAULTS = {
    "accent_color": DEFAULT_ACCENT,
    "banner_mode": "image",
    "discord_banner": None,
    "discord_accent": None,
    "favorite_server_id": None,
    "banner_image": None,
    "background_color": None,
    "featured_badges": [],
    "pinned_records": [],
    "layout": {},
}


# Columns added after the table was first created (v3.9.0): added on startup when missing
LATER_COLUMNS = {
    "banner_image": "VARCHAR(32)",
    "background_image": "VARCHAR(32)",
    "background_color": "VARCHAR(16)",
}


def ensure_table() -> None:
    """Create the settings table and its newer columns when the migrations were not run (IF NOT EXISTS, harmless)."""
    try:
        with db.connection_context():
            db.create_tables([UserProfileSettings], safe=True)
            for column, sql_type in LATER_COLUMNS.items():
                db.execute_sql(f"ALTER TABLE user_profile_settings ADD COLUMN IF NOT EXISTS {column} {sql_type}")
    except DatabaseError as e:
        log.warning("user_profile_settings table unavailable or outdated, run the web migrations: %s", e)


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
            "banner_mode": row.banner_mode if row.banner_mode in BANNER_MODES else "image",
            "discord_banner": row.discord_banner,
            "discord_accent": row.discord_accent,
            "favorite_server_id": row.favorite_server_id,
            "banner_image": row.banner_image if row.banner_image in BANNERS else None,
            "background_color": row.background_color if row.background_color in BACKGROUND_HEX else None,
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
    """Colors, banner and page background color the profile page renders with."""
    key = settings.get("accent_color") or DEFAULT_ACCENT
    hex_ = discord_accent_hex(settings) if key == DISCORD_ACCENT else PALETTE_HEX.get(key)
    if not hex_:
        key, hex_ = DEFAULT_ACCENT, PALETTE_HEX[DEFAULT_ACCENT]
    r, g, b = _hex_to_rgb(hex_)

    # Old "auto" (Discord banner) and "gradient" choices: the gallery picture, the default one if none was picked
    mode = settings.get("banner_mode") if settings.get("banner_mode") in BANNER_MODES else "image"
    banner_image = settings.get("banner_image") or DEFAULT_BANNER_IMAGE
    if not gallery_banner_url(banner_image):
        banner_image = DEFAULT_BANNER_IMAGE
    banner_url = gallery_banner_url(banner_image) if mode == "image" else None

    return {
        "accent_key": key,
        "accent_hex": hex_,
        "accent_rgb": f"{r}, {g}, {b}",
        "is_custom": key != DEFAULT_ACCENT,
        "banner_mode": mode,
        "banner_url": banner_url,
        "show_banner": mode != "none",
        "banner_image": banner_image,
        "background_color": settings.get("background_color"),
        "background_hex": BACKGROUND_HEX.get(settings.get("background_color")),
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
