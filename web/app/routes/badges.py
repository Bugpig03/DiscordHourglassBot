"""Badge pages (/badge/<id>): how rare each tier is, who holds it and since when, the latest unlocks and who is
about to climb. Opened from a badge on a profile; reads the tables filled every hour by app.badge_stats.

Members with a private profile or hidden badges count in the rarity but are never named.
"""

import json
from datetime import date

from flask import Blueprint, abort, render_template, request

from app.badge_stats import DEFS, IMPORT_DAY, enabled
from app.cache import cache
from app.database import db
from app.gamification import TIERS, _current_text, _threshold_text, pixel_svg
from app.i18n import current_lang, day_month_year, tr
from app.profile_settings import resolve_layout

badges_bp = Blueprint("badges", __name__)

PER_PAGE = 25
CACHE_SECONDS = 300
RECENT = 20
ALMOST = 10
ALMOST_PERCENT = 80.0


def _scope(server_id: int | None) -> tuple[str, tuple]:
    """SQL filter on v.user_id: everyone, or the members with activity on one server."""
    if server_id is None:
        return "", ()
    return " AND v.user_id IN (SELECT user_id FROM stats WHERE server_id = %s)", (server_id,)


def _hidden_ids(user_ids) -> set[int]:
    """Members whose badges visitors do not see (private profile or Badges tab hidden): read live, not cached."""
    ids = [int(u) for u in user_ids]
    if not ids:
        return set()
    hidden = set()
    for uid, layout in db.execute_sql("SELECT user_id, layout FROM user_profile_settings WHERE user_id = ANY(%s)", (ids,)).fetchall():
        try:
            layout = json.loads(layout) if isinstance(layout, str) else (layout or {})
        except ValueError:
            layout = {}
        if not resolve_layout({"layout": layout}, is_owner=False)["visible"]["tab_badges"]:
            hidden.add(int(uid))
    return hidden


def _value(kind: str, v1, v2):
    """The badge value as gamification shows it, back from the stored columns."""
    if kind == "rank":
        return (int(v1) if v1 is not None else None, v2 or 0)
    if kind == "hybrid":
        return (v1 or 0, int(v2 or 0))
    if kind in ("messages", "level", "servers", "days", "votes"):
        return int(v1 or 0)
    return v1 or 0


def _day(d: date | None, before: bool, lang: str) -> str:
    if before:
        return tr("avant oct. 2024", "before Oct 2024", lang)
    return day_month_year(d.day, d.month, d.year, lang) if d else "—"


def _order(kind: str) -> str:
    """Best holders first: highest tier, then the best value (a lower place for the ranking)."""
    if kind == "rank":
        return "v.tier DESC, v.value ASC NULLS LAST, v.value2 DESC"
    if kind == "hybrid":
        return "v.tier DESC, v.progress DESC, v.value DESC"
    return "v.tier DESC, v.value DESC"


def label(fr: str, en: str) -> tuple[str, str]:
    """A French / English pair of a data table (found by scripts/i18n_extract.py, like tr())."""
    return fr, en


# What counts for each badge, in a sentence (shown with the tiers to unlock)
HOW = {
    "voice": label("Toutes les heures passées en vocal, sur tous les serveurs suivis.", "Every hour spent in voice, on every tracked server."),
    "messages": label("Tous les messages envoyés dans les salons textuels suivis.", "Every message sent in the tracked text channels."),
    "level": label("Le niveau global : 1 XP par minute en vocal, 1 XP par message et 100 XP par vote sur top.gg.",
                   "The global level: 1 XP per voice minute, 1 XP per message and 100 XP per top.gg vote."),
    "rank": label("La meilleure place jamais atteinte au classement vocal global. Une place perdue ensuite ne fait pas redescendre le palier.",
                  "The best spot ever reached in the global voice ranking. Losing it later never takes the tier away."),
    "servers": label("Le nombre de serveurs suivis par Hourglass sur lesquels le membre a été actif.", "How many servers tracked by Hourglass the member has been active on."),
    "loyalty": label("Le nombre de jours depuis la première activité vue par Hourglass.", "Days since the first activity seen by Hourglass."),
    "activity": label("Le meilleur total de vocal sur 30 jours glissants. Le record reste acquis, même après un mois calme.",
                      "The best voice total over 30 sliding days. The record stays, even after a quiet month."),
    "streak": label("La plus longue série de jours actifs d’affilée (vocal ou messages). La série record reste acquise.",
                    "The longest run of active days in a row (voice or messages). The record run stays."),
    "hybrid": label("Les deux à la fois : des heures en vocal et des messages, chaque palier demande les deux seuils.",
                    "Both at once: voice hours and messages, each tier asks for both thresholds."),
    "votes": label("Les votes pour Hourglass sur top.gg, un toutes les 12 heures (un vote du week-end compte une fois).",
                   "Votes for Hourglass on top.gg, one every 12 hours (a weekend vote counts once)."),
}


def _nav(server_id: int | None, lang: str) -> list[dict]:
    """The 10 badges of the side menu, with how many members hold each one in the scope."""
    def load():
        where, params = _scope(server_id)
        return dict(db.execute_sql(f"SELECT v.badge, COUNT(*) FROM user_badge_values v WHERE v.tier > 0{where} GROUP BY v.badge",
                                   params).fetchall())
    counts = cache.get_or_set(("badge_nav", server_id), CACHE_SECONDS, load)
    return [{"id": d[0], "name": tr(d[1], d[2], lang), "icon": str(pixel_svg(d[5], 18)), "holders": int(counts.get(d[0], 0))}
            for d in DEFS.values()]


def _summary(badge: str, server_id: int | None) -> dict:
    """Counts per tier and the members in scope (cached 5 min; the tables change once an hour)."""
    def load():
        where, params = _scope(server_id)
        rows = db.execute_sql(f"SELECT v.tier, COUNT(*) FROM user_badge_values v WHERE v.badge = %s{where} GROUP BY v.tier",
                              (badge,) + params).fetchall()
        per_tier = {int(t): int(n) for t, n in rows}
        updated = db.execute_sql("SELECT MAX(updated_at) FROM user_badge_values").fetchone()[0]
        return {"per_tier": per_tier, "members": sum(per_tier.values()), "updated": updated}
    return cache.get_or_set(("badge_summary", badge, server_id), CACHE_SECONDS, load)


def _firsts(badge: str, server_id: int | None, hidden: set[int]) -> dict:
    """First member named for each tier (earliest day; members already there before Oct 2024 are counted apart)."""
    where, params = _scope(server_id)
    rows = db.execute_sql(
        f"SELECT v.tier, v.reached_on, v.before_tracking, v.user_id, u.username FROM user_badge_tiers v "
        f"LEFT JOIN users u ON u.user_id = v.user_id WHERE v.badge = %s{where} ORDER BY v.tier, v.reached_on, v.user_id",
        (badge,) + params).fetchall()
    out = {}
    for tier, day, before, uid, name in rows:
        entry = out.setdefault(int(tier), {"first": None, "before": 0})
        if before:
            entry["before"] += 1
        elif entry["first"] is None and int(uid) not in hidden:
            entry["first"] = {"day": day, "user_id": int(uid), "name": name or str(uid)}
    return out


@badges_bp.route("/badge/<badge_id>", methods=["GET"])
def badge_page(badge_id: str):
    definition = DEFS.get(badge_id)
    if not definition or not enabled():
        abort(404)
    key, name_fr, name_en, what_fr, what_en, icon, kind, thresholds = definition
    lang = current_lang()
    server_id = request.args.get("srv", type=int)
    tier_filter = max(1, min(7, request.args.get("tier", 1, type=int)))
    page = max(1, request.args.get("page", 1, type=int))
    search = (request.args.get("q") or "").strip()[:40]

    servers = cache.get_or_set(("badge_servers",), CACHE_SECONDS, lambda: [
        {"id": int(sid), "name": name or str(sid)} for sid, name in db.execute_sql(
            "SELECT server_id, servername FROM servers WHERE server_id IN (SELECT DISTINCT server_id FROM stats) "
            "ORDER BY LOWER(servername)").fetchall()])
    if server_id is not None and not any(s["id"] == server_id for s in servers):
        server_id = None

    summary = _summary(key, server_id)
    where, params = _scope(server_id)

    # Holders of the chosen tier or better, best first; hidden members are left out of the list
    search_sql = " AND u.username ILIKE %s" if search else ""
    search_params = (f"%{search.replace('%', '').replace('_', '')}%",) if search else ()
    rows = db.execute_sql(
        f"SELECT v.user_id, v.tier, v.value, v.value2, v.progress, u.username, u.avatar FROM user_badge_values v "
        f"LEFT JOIN users u ON u.user_id = v.user_id WHERE v.badge = %s AND v.tier >= %s{where}{search_sql} ORDER BY {_order(kind)}",
        (key, tier_filter) + params + search_params).fetchall()
    hidden = _hidden_ids(r[0] for r in rows)
    listed = [r for r in rows if int(r[0]) not in hidden]
    total_pages = max(1, -(-len(listed) // PER_PAGE))
    page = min(page, total_pages)
    page_rows = listed[(page - 1) * PER_PAGE: page * PER_PAGE]

    # Day of every tier of the members shown (their timeline)
    timelines = {}
    if page_rows:
        for uid, tier, day, before in db.execute_sql(
                "SELECT user_id, tier, reached_on, before_tracking FROM user_badge_tiers WHERE badge = %s AND user_id = ANY(%s)",
                (key, [int(r[0]) for r in page_rows])).fetchall():
            timelines.setdefault(int(uid), {})[int(tier)] = (day, before)

    def tier_meta(i: int) -> dict:
        t_key, t_fr, t_en, color = TIERS[i]
        return {"n": i + 1, "key": t_key, "label": tr(t_fr, t_en, lang), "color": color,
                "threshold": _threshold_text(kind, thresholds[i], lang)}

    tiers = [tier_meta(i) for i in range(len(thresholds))]
    holders = []
    for uid, tier, v1, v2, progress, username, avatar in page_rows:
        uid, tier = int(uid), int(tier)
        line = timelines.get(uid, {})
        reached = line.get(tier, (None, False))
        holders.append({
            "user_id": uid, "name": username or tr("Membre {id}", "Member {id}", lang, id=uid), "avatar": avatar,
            "tier": tiers[tier - 1], "value": _current_text(kind, _value(kind, v1, v2), lang),
            "reached": _day(reached[0], reached[1], lang), "reached_before": bool(reached[1]),
            "timeline": [{**t, "done": t["n"] <= tier,
                          "day": _day(*line.get(t["n"], (None, False)), lang) if t["n"] <= tier else None} for t in tiers],
        })

    # Rarity: members who reached each tier (or better), first one named, those already there before Oct 2024
    members = summary["members"]
    firsts = _firsts(key, server_id, _hidden_ids_cached(key, server_id))
    rarity = []
    for t in tiers:
        count = sum(n for tier, n in summary["per_tier"].items() if tier >= t["n"])
        first = firsts.get(t["n"], {})
        rarity.append({**t, "count": count, "percent": round(count / members * 100, 1) if members else 0.0,
                       "first": first.get("first") and {**first["first"], "day": _day(first["first"]["day"], False, lang)},
                       "before": first.get("before", 0)})
    rarest = max((r for r in rarity if r["count"]), key=lambda r: r["n"], default=None)

    # Latest unlocks and members about to climb (named members only)
    recent_rows = db.execute_sql(
        f"SELECT v.user_id, v.tier, v.reached_on, u.username, u.avatar FROM user_badge_tiers v LEFT JOIN users u ON u.user_id = v.user_id "
        f"WHERE v.badge = %s AND NOT v.before_tracking{where} ORDER BY v.reached_on DESC, v.tier DESC LIMIT %s",
        (key,) + params + (RECENT * 3,)).fetchall()
    almost_rows = db.execute_sql(
        f"SELECT v.user_id, v.tier, v.value, v.value2, v.progress, u.username, u.avatar FROM user_badge_values v "
        f"LEFT JOIN users u ON u.user_id = v.user_id WHERE v.badge = %s AND v.tier < %s AND v.progress >= %s{where} "
        f"ORDER BY v.progress DESC, v.tier DESC LIMIT %s",
        (key, len(thresholds), ALMOST_PERCENT) + params + (ALMOST * 3,)).fetchall()
    shy = _hidden_ids({r[0] for r in recent_rows} | {r[0] for r in almost_rows})
    recent = [{"user_id": int(u), "name": n or str(u), "avatar": a, "tier": tiers[int(t) - 1], "day": _day(d, False, lang)}
              for u, t, d, n, a in recent_rows if int(u) not in shy][:RECENT]
    almost = [{"user_id": int(u), "name": n or str(u), "avatar": a, "tier": tiers[int(t) - 1] if t else None,
               "next": tiers[int(t)], "progress": round(float(p), 1), "value": _current_text(kind, _value(kind, v1, v2), lang)}
              for u, t, v1, v2, p, n, a in almost_rows if int(u) not in shy][:ALMOST]

    return render_template(
        "badge.html",
        badge={"id": key, "name": tr(name_fr, name_en, lang), "what": tr(what_fr, what_en, lang), "icon": str(pixel_svg(icon, 34)),
               "how": tr(*HOW[key], lang) if key in HOW else ""},
        nav=_nav(server_id, lang),
        tiers=tiers, rarity=rarity, rarest=rarest, members=members, holders=holders, listed_count=len(listed),
        hidden_count=len(rows) - len(listed), tier_filter=tier_filter, page=page, total_pages=total_pages,
        recent=recent, almost=almost, servers=servers, server_id=server_id, search=search,
        updated=summary["updated"], import_day=IMPORT_DAY,
    )


def _hidden_ids_cached(badge: str, server_id: int | None) -> set[int]:
    """Hidden holders of any tier, for naming the first holder of each tier."""
    where, params = _scope(server_id)
    ids = [r[0] for r in db.execute_sql(f"SELECT v.user_id FROM user_badge_values v WHERE v.badge = %s AND v.tier > 0{where}",
                                        (badge,) + params).fetchall()]
    return _hidden_ids(ids)
