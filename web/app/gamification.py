"""Gamification system for Hourglass Web: XP, Levels, and Real-time Badges computed purely in memory."""

from datetime import datetime, timezone
from typing import Any

from app.i18n import format_number, tr
from app.pixel_icons import pixel_svg


def calculate_user_xp_and_level(total_seconds: int, total_messages: int) -> dict[str, Any]:
    """Calculate user XP, level, title, and progress percentage based on voice time and messages.
    
    Formula:
      - 1 minute in voice = 1 XP
      - 1 text message = 5 XP
      - Level curve: quadratic progression where Level = int((XP / 100) ** 0.5) + 1
    """
    total_seconds = max(0, total_seconds or 0)
    total_messages = max(0, total_messages or 0)

    voice_minutes = total_seconds // 60
    total_xp = voice_minutes + (total_messages * 5)

    level = int((total_xp / 100) ** 0.5) + 1
    current_level_base_xp = ((level - 1) ** 2) * 100
    next_level_target_xp = (level ** 2) * 100
    xp_needed_for_level = next_level_target_xp - current_level_base_xp
    xp_progress_in_level = total_xp - current_level_base_xp

    if xp_needed_for_level > 0:
        progress_percent = min(100.0, max(0.0, round((xp_progress_in_level / xp_needed_for_level) * 100, 1)))
    else:
        progress_percent = 100.0

    # Dynamic honor titles depending on level
    titles = {
        "fr": [
            (50, "Légende Hourglass"),
            (40, "Grand Maître"),
            (30, "Vétéran de l'Éther"),
            (20, "Expert des Ondes"),
            (10, "Membre Confirmé"),
            (5, "Initié Actif"),
            (1, "Novice Curieux"),
        ],
        "en": [
            (50, "Hourglass Legend"),
            (40, "Grandmaster"),
            (30, "Aether Veteran"),
            (20, "Voice Expert"),
            (10, "Senior Member"),
            (5, "Active Initiate"),
            (1, "Curious Novice"),
        ]
    }

    def get_title(lang: str = "fr") -> str:
        lang_titles = titles.get(lang, titles["fr"])
        for min_lvl, title_name in lang_titles:
            if level >= min_lvl:
                return title_name
        return "Membre" if lang == "fr" else "Member"

    return {
        "total_xp": total_xp,
        "level": level,
        "title_fr": get_title("fr"),
        "title_en": get_title("en"),
        "current_level_base_xp": current_level_base_xp,
        "next_level_target_xp": next_level_target_xp,
        "xp_progress_in_level": xp_progress_in_level,
        "xp_needed_for_level": xp_needed_for_level,
        "progress_percent": progress_percent,
    }


def calculate_user_badges(stats: dict[str, Any], lang: str = "fr") -> list[dict[str, Any]]:
    """The member's 8 badges, computed live from their statistics (nothing is stored).

    One badge per family (voice, messages, level, ranking, servers, loyalty, monthly activity, versatility),
    levelled up through 7 tiers: Bronze, Silver, Gold, Platinum, Diamond, Legend, Mythic. tier is 0 until the
    first one is reached; the tier color is the badge color everywhere (see TIERS).
    """

    try:
        total_seconds = float(stats.get("total_seconds") or 0)
    except (ValueError, TypeError):
        total_seconds = 0.0
    total_hours = total_seconds / 3600.0

    try:
        total_messages = int(stats.get("total_message") or 0)
    except (ValueError, TypeError):
        total_messages = 0

    raw_rank = stats.get("rank")
    rank: int | None = None
    if isinstance(raw_rank, int) and raw_rank > 0:
        rank = raw_rank
    elif isinstance(raw_rank, str) and raw_rank.strip().isdigit():
        rank = int(raw_rank.strip())

    servers = stats.get("user_servers_stats")
    server_count = len(servers) if isinstance(servers, list) else 0

    try:
        last_30d_seconds = float(stats.get("total_time_last_30d") or 0)
    except (ValueError, TypeError):
        last_30d_seconds = 0.0
    last_30d_hours = last_30d_seconds / 3600.0
    join_source = stats.get("raw_join_date") or stats.get("join_date")

    # Real-time level calculation from gamification engine
    user_xp_info = calculate_user_xp_and_level(total_seconds, total_messages)
    user_level = user_xp_info["level"]

    # Calculate days since earliest recorded activity
    days_since_join = 0
    if join_source:
        now_utc = datetime.now(timezone.utc)
        if isinstance(join_source, datetime):
            dt = join_source if join_source.tzinfo else join_source.replace(tzinfo=timezone.utc)
            days_since_join = max(0, (now_utc - dt).days)
        elif isinstance(join_source, str):
            try:
                dt = datetime.fromisoformat(join_source)
                dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                days_since_join = max(0, (now_utc - dt).days)
            except Exception:
                days_since_join = 0

    values = {
        "voice": total_hours,
        "messages": total_messages,
        "level": user_level,
        "rank": (rank, total_hours),
        "servers": server_count,
        "loyalty": days_since_join,
        "activity": last_30d_hours,
        "hybrid": (total_hours, total_messages),
    }
    return [_family_badge(definition, values[definition[0]], lang) for definition in BADGE_DEFS]


# ------------------------------------------------------------------------------
# Badges (v3.24.0): one badge per family, levelled up through 7 tiers shown by color
# ------------------------------------------------------------------------------
# (key, label fr, label en, color)
TIERS = [
    ("bronze", "Bronze", "Bronze", "#d08a4f"),
    ("silver", "Argent", "Silver", "#c9ced6"),
    ("gold", "Or", "Gold", "#f5c542"),
    ("platinum", "Platine", "Platinum", "#4fd8c4"),
    ("diamond", "Diamant", "Diamond", "#6fb6ff"),
    ("legend", "Légende", "Legend", "#b07cff"),
    ("mythic", "Mythique", "Mythic", "#ff8ad8"),  # holographic on the website (arene.css)
]

# Line drawings of the family icons, used by the bot cards (the website shows the pixel versions)
_SVG = {
    "headphones": '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H8v4h8v-4h-1c-.55 0-1-.45-1-1v-2.34"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "hourglass": '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "infinity": '<path d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-4.585 0-4.585 8 0 8 5.606 0 7.644-8 12.74-8z"/>',
}

# (key, name fr, name en, what it measures fr, en, icon, kind, thresholds from Bronze to Mythic)
BADGE_DEFS = [
    ("voice", "Vocal", "Voice", "Temps passé en vocal", "Time spent in voice", "headphones", "hours", [1, 10, 100, 500, 1000, 2500, 5000]),
    ("messages", "Messages", "Messages", "Messages envoyés", "Messages sent", "chat", "messages", [25, 250, 1000, 5000, 10000, 25000, 50000]),
    ("level", "Niveau", "Level", "Niveau atteint", "Level reached", "star", "level", [5, 10, 20, 30, 50, 70, 90]),
    ("rank", "Classement", "Ranking", "Place au classement vocal global", "Spot in the global voice ranking", "trophy", "rank", [100, 50, 25, 10, 3, 1, (1, 5000)]),
    ("servers", "Serveurs", "Servers", "Serveurs fréquentés", "Servers joined", "globe", "servers", [2, 3, 4, 6, 8, 12, 20]),
    ("loyalty", "Fidélité", "Loyalty", "Ancienneté depuis la première activité", "Time since the first activity", "hourglass", "days", [30, 60, 120, 250, 365, 730, 1095]),
    ("activity", "Activité", "Activity", "Heures en vocal sur les 30 derniers jours", "Voice hours over the last 30 days", "flame", "hours30", [5, 15, 40, 80, 120, 200, 300]),
    ("hybrid", "Polyvalence", "Versatility", "Vocal et messages à la fois", "Voice and messages together", "infinity", "hybrid",
     [(10, 100), (50, 500), (100, 1000), (250, 2500), (500, 5000), (1000, 10000), (2500, 25000)]),
]
BADGE_IDS = [d[0] for d in BADGE_DEFS]

# Badges saved in a showcase before v3.24.0 were single tiers: they now point to their family's badge
_OLD_PREFIXES = (("voice_", "voice"), ("msg_", "messages"), ("level_", "level"), ("rank_", "rank"), ("social_", "servers"),
                 ("loyalty_", "loyalty"), ("activity_", "activity"))
_OLD_HYBRID = {"versatile", "hybrid_master", "all_rounder"}


def normalize_badge_ids(ids: list[str]) -> list[str]:
    """Current badge ids of a saved list (former tier ids mapped to their family), duplicates removed."""
    out = []
    for badge_id in ids or []:
        if badge_id in BADGE_IDS:
            key = badge_id
        elif badge_id in _OLD_HYBRID:
            key = "hybrid"
        else:
            key = next((fam for prefix, fam in _OLD_PREFIXES if badge_id.startswith(prefix)), None)
        if key and key not in out:
            out.append(key)
    return out


def _fmt_number(value, lang: str) -> str:
    """1234.5 -> '1 234,5' (fr) / '1,234.5' (en) / '1.234,5' (de); whole numbers lose their decimals."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return format_number(value, 0 if isinstance(value, int) else 1, lang)


def _met(kind: str, value, threshold) -> bool:
    if kind == "rank":
        place, hours = threshold if isinstance(threshold, tuple) else (threshold, 0)
        return isinstance(value[0], int) and value[0] <= place and value[1] >= hours
    if kind == "hybrid":
        return value[0] >= threshold[0] and value[1] >= threshold[1]
    return (value or 0) >= threshold


def _ratio(kind: str, value, threshold) -> float:
    """How far the value is toward a threshold, 0 to 1."""
    if kind == "rank":
        place, hours = threshold if isinstance(threshold, tuple) else (threshold, 0)
        if not isinstance(value[0], int) or value[0] <= 0:
            return 0.0
        return min(1.0, place / value[0], value[1] / hours if hours else 1.0)
    if kind == "hybrid":
        return min(value[0] / threshold[0], value[1] / threshold[1], 1.0)
    return min(1.0, (value or 0) / threshold) if threshold else 0.0


def _threshold_text(kind: str, threshold, lang: str) -> str:
    """What a tier asks for, written for people: '500 h', 'Niveau 30', 'Top 10', '50 h + 500 messages'."""
    if kind == "hours":
        return f"{_fmt_number(threshold, lang)} h"
    if kind == "hours30":
        return tr("{n} h sur 30 j", "{n} h in 30 d", lang, n=_fmt_number(threshold, lang))
    if kind == "messages":
        return tr("{n} messages", "{n} messages", lang, n=_fmt_number(threshold, lang))
    if kind == "level":
        return tr("Niveau {n}", "Level {n}", lang, n=threshold)
    if kind == "rank":
        if isinstance(threshold, tuple):
            return tr("N°1 + {n} h", "No. 1 + {n} h", lang, n=_fmt_number(threshold[1], lang))
        return tr("N°1", "No. 1", lang) if threshold == 1 else tr("Top {n}", "Top {n}", lang, n=threshold)
    if kind == "servers":
        return tr("{n} serveurs", "{n} servers", lang, n=threshold)
    if kind == "days":
        return tr("{n} jours", "{n} days", lang, n=_fmt_number(threshold, lang))
    return tr("{h} h + {m} messages", "{h} h + {m} messages", lang, h=_fmt_number(threshold[0], lang), m=_fmt_number(threshold[1], lang))


def _current_text(kind: str, value, lang: str) -> str:
    if kind in ("hours", "hours30"):
        return f"{_fmt_number(round(value or 0, 1), lang)} h"
    if kind == "messages":
        return tr("{n} messages", "{n} messages", lang, n=_fmt_number(value or 0, lang))
    if kind == "level":
        return tr("Niveau {n}", "Level {n}", lang, n=value)
    if kind == "rank":
        return f"#{value[0]}" if isinstance(value[0], int) else tr("non classé", "unranked", lang)
    if kind == "servers":
        return tr("{n} serveurs", "{n} servers", lang, n=value)
    if kind == "days":
        return tr("{n} jours", "{n} days", lang, n=_fmt_number(value or 0, lang))
    return tr("{h} h + {m} messages", "{h} h + {m} messages", lang, h=_fmt_number(round(value[0], 1), lang), m=_fmt_number(value[1], lang))


def _family_badge(definition: tuple, value, lang: str) -> dict[str, Any]:
    key, name_fr, name_en, what_fr, what_en, icon, kind, thresholds = definition
    tier = 0
    for threshold in thresholds:
        if not _met(kind, value, threshold):
            break
        tier += 1
    tiers = []
    for i, threshold in enumerate(thresholds):
        t_key, t_fr, t_en, color = TIERS[i]
        state = "unlocked" if i < tier else "next" if i == tier else "locked"
        tiers.append({
            "key": t_key,
            "label": tr(t_fr, t_en, lang),
            "color": color,
            "threshold": _threshold_text(kind, threshold, lang),
            "state": state,
            "progress_percent": 100.0 if state == "unlocked" else round(min(99.0, _ratio(kind, value, threshold) * 100), 1) if state == "next" else 0.0,
        })
    current = _current_text(kind, value, lang)
    reached = tiers[tier - 1] if tier else None
    nxt = tiers[tier] if tier < len(tiers) else None
    if nxt:
        goal = tr("Prochain palier : {tier} ({goal}).", "Next tier: {tier} ({goal}).", lang, tier=nxt["label"], goal=nxt["threshold"])
    else:
        goal = tr("Palier maximum atteint.", "Highest tier reached.", lang)
    what = tr(what_fr, what_en, lang)
    return {
        "id": key,
        "name": tr(name_fr, name_en, lang),
        "what": what,
        "description": tr("{what} : {current}. {goal}", "{what}: {current}. {goal}", lang, what=what, current=current, goal=goal),
        "icon": str(pixel_svg(icon, 24)),
        "svg_path": _SVG[icon],
        "kind": kind,
        "tier": tier,
        "tier_count": len(tiers),
        "tier_key": reached["key"] if reached else "locked",
        "tier_label": reached["label"] if reached else tr("Verrouillé", "Locked", lang),
        "color": reached["color"] if reached else "#72767d",
        # rarity is the tier key, so the existing rarity-* classes and the bot cards color the badge
        "rarity": reached["key"] if reached else "locked",
        "unlocked": tier > 0,
        "current": current,
        "next_label": nxt["label"] if nxt else None,
        "next_threshold": nxt["threshold"] if nxt else None,
        "progress_percent": 100.0 if not nxt else nxt["progress_percent"],
        "tiers": tiers,
    }


def build_badge_overview(badges: list[dict], lang: str = "fr") -> dict:
    """Badges tab: one ladder of 7 tiers per badge, a summary and how many badges reached each tier."""
    families = []
    for b in badges:
        tiers = [{
            **t,
            "name": t["label"],
            "rarity": t["key"],
            "icon": b["icon"],
            "description": tr("{badge} · {tier} : {goal}", "{badge} · {tier}: {goal}", lang, badge=b["name"], tier=t["label"], goal=t["threshold"]),
            "progress_text": b["current"] if t["state"] == "next" else "",
        } for t in b["tiers"]]
        families.append({
            "key": b["id"],
            "label": b["name"],
            "what": b["what"],
            "tiers": tiers,
            "unlocked": b["tier"],
            "total": b["tier_count"],
            "complete": b["tier"] == b["tier_count"],
            "icon": b["icon"],
            "tier_key": b["tier_key"],
            "tier_label": b["tier_label"],
        })
    done = sum(b["tier"] for b in badges)
    total = sum(b["tier_count"] for b in badges)
    rarity = [{
        "rarity": t_key,
        "label": tr(t_fr, t_en, lang),
        "unlocked": sum(1 for b in badges if b["tier"] > i),
        "total": len(badges),
    } for i, (t_key, t_fr, t_en, _) in enumerate(TIERS)]
    return {
        "families": families,
        "rarity": rarity,
        "unlocked": sum(1 for b in badges if b["unlocked"]),
        "total": len(badges),
        "tiers_done": done,
        "tiers_total": total,
        "percent": round(done / total * 100) if total else 0,
    }
