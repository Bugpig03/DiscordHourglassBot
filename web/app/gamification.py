"""Gamification system for Hourglass Web: XP, Levels, and Real-time Badges computed purely in memory."""

from datetime import datetime, timezone
from typing import Any

from app.i18n import format_number, tr
from app.pixel_icons import pixel_svg


# Titles by level (v3.30.0): (from level, French, English, color group). Round levels, ranking words of
# competitive games; the top two are Hourglass's own (the hourglass, time).
LEVEL_TITLES = [
    (1, "Recrue", "Rookie", "rookie"),
    (5, "Habitué", "Regular", "rookie"),
    (10, "Confirmé", "Seasoned", "adept"),
    (20, "Vétéran", "Veteran", "adept"),
    (30, "Champion", "Champion", "master"),
    (40, "Maître", "Master", "master"),
    (50, "Grand Maître", "Grandmaster", "master"),
    (60, "Icône", "Icon", "legend"),
    (70, "Immortel", "Immortal", "legend"),
    (80, "Titan", "Titan", "legend"),
    (90, "Gardien du Sablier", "Hourglass Keeper", "legend"),
    (100, "Maître du Temps", "Timekeeper", "legend"),
]


def level_title(level: int) -> tuple:
    """(from level, French, English, color group) of the title worn at this level."""
    return next((t for t in reversed(LEVEL_TITLES) if level >= t[0]), LEVEL_TITLES[0])


# Each vote for Hourglass on top.gg (one per 12 h) awards this XP, to the member's global level
XP_PER_VOTE = 100


def xp_for_level(level: int) -> int:
    """XP needed to reach a level (curve of calculate_user_xp_and_level)."""
    return ((max(1, level) - 1) ** 2) * 100


def title_ladder(lang: str = "fr") -> list[dict]:
    """Help page: every title with its level, the XP it takes and the voice time that is (1 XP per minute)."""
    return [{
        "level": lvl,
        "title": tr(fr, en, lang),
        "group": group,
        "xp": xp_for_level(lvl),
        "hours": _round_hours(xp_for_level(lvl) / 60),
    } for lvl, fr, en, group in LEVEL_TITLES]


def _round_hours(hours: float) -> int:
    """About this many hours, in a round figure: 27, 140, 600, 1 400, 16 300."""
    step = 1 if hours < 100 else 10 if hours < 1000 else 100
    return int(round(hours / step) * step)


def badge_ladders(lang: str = "fr") -> list[dict]:
    """Help page: every badge and what each of its 7 tiers asks."""
    out = []
    for key, name_fr, name_en, what_fr, what_en, icon, kind, thresholds in BADGE_DEFS:
        out.append({
            "id": key,
            "name": tr(name_fr, name_en, lang),
            "what": tr(what_fr, what_en, lang),
            "icon": str(pixel_svg(icon, 18)),
            "tiers": [{"key": TIERS[i][0], "label": tr(TIERS[i][1], TIERS[i][2], lang), "color": TIERS[i][3],
                       "threshold": _threshold_text(kind, threshold, lang)} for i, threshold in enumerate(thresholds)],
        })
    return out


def calculate_user_xp_and_level(total_seconds: int, total_messages: int, votes: int = 0) -> dict[str, Any]:
    """Calculate user XP, level, title, and progress percentage based on voice time, messages and votes.

    Formula:
      - 1 minute in voice = 1 XP
      - 1 text message = 1 XP (5 XP before v3.26.0)
      - 1 vote for Hourglass on top.gg = 100 XP (v3.34.0; global level only, votes belong to no server)
      - Level curve: quadratic progression where Level = int((XP / 100) ** 0.5) + 1
    """
    total_seconds = max(0, total_seconds or 0)
    total_messages = max(0, total_messages or 0)
    votes = max(0, int(votes or 0))

    voice_minutes = int(total_seconds) // 60
    total_xp = voice_minutes + int(total_messages) + votes * XP_PER_VOTE

    level = int((total_xp / 100) ** 0.5) + 1
    current_level_base_xp = ((level - 1) ** 2) * 100
    next_level_target_xp = (level ** 2) * 100
    xp_needed_for_level = next_level_target_xp - current_level_base_xp
    xp_progress_in_level = total_xp - current_level_base_xp

    if xp_needed_for_level > 0:
        progress_percent = min(100.0, max(0.0, round((xp_progress_in_level / xp_needed_for_level) * 100, 1)))
    else:
        progress_percent = 100.0

    title = level_title(level)
    return {
        "total_xp": total_xp,
        "vote_xp": votes * XP_PER_VOTE,
        "level": level,
        "title_fr": title[1],
        "title_en": title[2],
        "title_group": title[3],
        "current_level_base_xp": current_level_base_xp,
        "next_level_target_xp": next_level_target_xp,
        "xp_progress_in_level": xp_progress_in_level,
        "xp_needed_for_level": xp_needed_for_level,
        "progress_percent": progress_percent,
    }


def calculate_user_badges(stats: dict[str, Any], lang: str = "fr") -> list[dict[str, Any]]:
    """The member's 10 badges, computed live from their statistics (nothing is stored).

    One badge per family (voice, messages, level, ranking, servers, loyalty, monthly activity, streak, versatility,
    top.gg votes),
    levelled up through 7 tiers: Bronze, Silver, Gold, Platinum, Diamond, Legend, Mythic. tier is 0 until the
    first one is reached; the tier color is the badge color everywhere (see TIERS).
    """
    values, records = badge_values(stats)
    badges = []
    for definition in BADGE_DEFS:
        badge = _family_badge(definition, values[definition[0]], lang)
        note = _record_text(definition[0], records, lang) if records else None
        if note:
            badge["record"] = note
            badge["description"] = f"{badge['description']} {note}"
        badges.append(badge)
    return badges


def badge_values(stats: dict[str, Any]) -> tuple[dict[str, Any], dict | None]:
    """What each badge measures for the member ({badge id: value}) and their stored records.

    Shared by the profile (calculate_user_badges) and the badge pages (badge_stats), so both always give the
    same tier. Every figure can be given in stats; what is missing is read for the member.
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
    user_xp_info = calculate_user_xp_and_level(total_seconds, total_messages, _vote_count(stats))
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

    # Longest run of consecutive active days ever (a tier once reached stays): given by the caller, or read
    # from the database for the member (cached, see functions.get_user_best_streak)
    best_streak = stats.get("best_streak")
    if best_streak is None and str(stats.get("user_id") or "").isdigit():
        from app.functions import get_user_best_streak
        best_streak = get_user_best_streak(int(stats["user_id"]))

    values = {
        "voice": total_hours,
        "messages": total_messages,
        "level": user_level,
        "rank": (rank, total_hours),
        "servers": server_count,
        "loyalty": days_since_join,
        "activity": last_30d_hours,
        "streak": int(best_streak or 0),
        "hybrid": (total_hours, total_messages),
        "votes": _vote_count(stats),
    }
    # Ranking and Activity can go down (someone overtakes you, a quiet month): the best rank and the best 30 days
    # ever reached are stored (best_records), and the badge keeps the higher tier of now and of that record
    records = stats.get("best_records")
    if records is None and str(stats.get("user_id") or "").isdigit():
        from app.best_records import get_best_records
        records = get_best_records(int(stats["user_id"]))
    if records:
        # Best of now and of the record: a better (lower) spot wins, at the same spot the most hours count
        best_rank = records.get("best_rank")
        if best_rank:
            best_hours = float(records.get("best_rank_hours") or 0)
            if rank is None or best_rank < rank:
                values["rank"] = (int(best_rank), best_hours)
            elif best_rank == rank:
                values["rank"] = (rank, max(total_hours, best_hours))
        if records.get("best_30d_hours"):
            values["activity"] = max(last_30d_hours, float(records["best_30d_hours"]))
    return values, records


def member_votes(user_id) -> int:
    """Votes of a member for Hourglass on top.gg (cached a few seconds), for their global XP."""
    return _vote_count({"user_id": user_id})


def _vote_count(stats: dict) -> int:
    """Votes for Hourglass on top.gg: given by the caller, or read for the member (cached)."""
    if stats.get("votes_total") is not None:
        return int(stats["votes_total"])
    if str(stats.get("user_id") or "").isdigit():
        from app.topgg_votes import user_votes
        return user_votes(int(stats["user_id"]))["total"]
    return 0


def _record_text(key: str, records: dict, lang: str) -> str | None:
    """"Best spot: #3, on 12 Mar 2026." / "Record: 152 h, from 6 May to 4 Jun 2026." (dates in the visitor's language)"""
    from app.i18n import day_month_year

    def short(d):
        return day_month_year(d.day, d.month, d.year, lang) if d else ""

    if key == "rank" and records.get("best_rank"):
        when = records.get("best_rank_on")
        if when:
            return tr("Meilleure place : #{rank}, le {date}.", "Best spot: #{rank}, on {date}.", lang,
                      rank=records["best_rank"], date=short(when))
        return tr("Meilleure place : #{rank}.", "Best spot: #{rank}.", lang, rank=records["best_rank"])
    if key == "activity" and records.get("best_30d_hours"):
        hours = format_number(records["best_30d_hours"], 1, lang)
        if records.get("best_30d_end"):
            return tr("Record : {hours} h, du {start} au {end}.", "Record: {hours} h, from {start} to {end}.", lang,
                      hours=hours, start=short(records.get("best_30d_start")), end=short(records["best_30d_end"]))
        return tr("Record : {hours} h sur 30 jours.", "Record: {hours} h over 30 days.", lang, hours=hours)
    return None


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
    "calendar_check": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4"/><path d="M3 10h18"/><path d="m9 16 2 2 4-4"/>',
    "infinity": '<path d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-4.585 0-4.585 8 0 8 5.606 0 7.644-8 12.74-8z"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
}

# (key, name fr, name en, what it measures fr, en, icon, kind, thresholds from Bronze to Mythic)
BADGE_DEFS = [
    ("voice", "Vocal", "Voice", "Temps passé en vocal", "Time spent in voice", "headphones", "hours", [1, 10, 100, 500, 1000, 2500, 5000]),
    ("messages", "Messages", "Messages", "Messages envoyés", "Messages sent", "chat", "messages", [25, 250, 1000, 5000, 10000, 25000, 50000]),
    ("level", "Niveau", "Level", "Niveau atteint", "Level reached", "star", "level", [5, 10, 20, 30, 50, 70, 90]),
    ("rank", "Classement", "Ranking", "Meilleure place au classement vocal global", "Best spot in the global voice ranking", "trophy", "rank",
     [100, 50, 25, 10, 5, 3, 1]),
    ("servers", "Serveurs", "Servers", "Serveurs fréquentés", "Servers joined", "globe", "servers", [2, 3, 4, 6, 8, 12, 20]),
    ("loyalty", "Fidélité", "Loyalty", "Ancienneté depuis la première activité", "Time since the first activity", "hourglass", "days", [30, 60, 120, 250, 365, 730, 1095]),
    ("activity", "Activité", "Activity", "Meilleur total de vocal sur 30 jours", "Best voice total over 30 days", "flame", "hours30",
     [5, 15, 40, 80, 120, 200, 300]),
    ("streak", "Série", "Streak", "Plus longue série de jours actifs d’affilée", "Longest run of active days in a row", "calendar_check", "days",
     [5, 10, 30, 60, 100, 250, 365]),
    ("hybrid", "Polyvalence", "Versatility", "Vocal et messages à la fois", "Voice and messages together", "infinity", "hybrid",
     [(10, 100), (50, 500), (100, 1000), (250, 2500), (500, 5000), (1000, 10000), (2500, 25000)]),
    # Votes for Hourglass on top.gg (one vote every 12 h; a weekend vote counts once here)
    ("votes", "Soutien", "Supporter", "Votes pour Hourglass sur top.gg", "Votes for Hourglass on top.gg", "heart", "votes",
     [1, 5, 10, 25, 50, 100, 200]),
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
    if kind == "votes":
        return tr("{n} vote(s)", "{n} vote(s)", lang, n=_fmt_number(threshold, lang))
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
    if kind == "votes":
        return tr("{n} vote(s)", "{n} vote(s)", lang, n=_fmt_number(value or 0, lang))
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
            # Ranking and Activity: the stored record and its date show when hovering any tier of the ladder
            "description": tr("{badge} · {tier} : {goal}", "{badge} · {tier}: {goal}", lang, badge=b["name"], tier=t["label"], goal=t["threshold"])
                           + (f". {b['record']}" if b.get("record") else ""),
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
