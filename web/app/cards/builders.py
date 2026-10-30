"""Stat cards: data (reusing the website's own computations) and layout, in the language of the Discord member who
asked (French, English, Spanish, Portuguese, Italian, German, Polish, Turkish or Russian; the other site languages
fall back to English until the cards have fonts for their scripts).

Canvas sizes are 2x (1200 px wide); see app.cards.design for the readability rules.
"""

import os
from concurrent.futures import ThreadPoolExecutor

from peewee import fn

from app.cache import TTLCache, cache
from app.cards import design as d
from app.database import Servers, Stats, Users
from app.functions import (
    get_activity_sum_last_X_days,
    get_daily_hours_diff,
    get_global_nb_server,
    get_global_nb_user,
    get_server_avatar_url,
    get_server_live_status,
    get_server_rank,
    get_server_raw_join_date,
    get_total_message_by_server_id,
    get_total_seconds_by_server_id,
    get_user_avatar_url,
    get_user_count_by_server_id,
    get_user_rank_in_server,
    get_user_raw_join_date,
)
from app.gamification import BADGE_DEFS, calculate_user_badges, calculate_user_xp_and_level
from app.i18n import format_number, normalize_lang, tr
from app.profile_records import featured_badges
from app.profile_settings import BACKGROUND_HEX, DEFAULT_ACCENT, PALETTE_HEX, discord_accent_hex, effective_banner_mode, get_profile_settings

W = 1200
M = 48            # outer margin
INNER = W - 2 * M
BANNER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "profile", "banners")
CARD_CACHE_SECONDS = 120
# Cards embed their pictures (100-250 KB each): a small dedicated cache keeps a worker's memory bounded
card_cache = TTLCache(max_entries=48)

# Languages the card fonts can draw (Latin and Cyrillic); Hindi, Japanese and Korean cards are in English
CARD_LANGS = ("fr", "en", "es", "pt", "it", "de", "pl", "tr", "ru")
PERIODS = {"all": "all", "week": "7d", "month": "1m"}
BADGE_ICONS = {key: icon for key, _fr, _en, _wfr, _wen, icon, _kind, _t in BADGE_DEFS}
PIXEL_FOR = {"headphones": "headphones", "chat": "chat", "star": "star", "trophy": "trophy", "globe": "globe", "calendar_check": "calendar_check",
             "hourglass": "hourglass", "flame": "flame", "infinity": "infinity"}


def card_lang(value: str | None) -> str:
    """Card language from a Discord locale or site code ('pt-BR' -> 'pt'); English when the cards cannot draw it."""
    lang = normalize_lang(value) or "en"
    return lang if lang in CARD_LANGS else "en"


def _prefetch(images: list[tuple[str | None, int]]) -> None:
    """Download the avatars of a card in parallel (they are cached, drawing then reuses them)."""
    jobs = [(url, size) for url, size in images if url]
    if len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=min(10, len(jobs))) as pool:
            list(pool.map(lambda job: d.remote_square(*job), jobs))


class CardNotFound(Exception):
    """The member or server is unknown to Hourglass."""


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------
def _theme(user_id: int) -> dict:
    """Colors and banner the member picked on the website (defaults otherwise)."""
    settings = get_profile_settings(user_id)
    key = settings.get("accent_color") or DEFAULT_ACCENT
    accent = discord_accent_hex(settings) if key == "discord" else PALETTE_HEX.get(key)
    banner = None
    if effective_banner_mode(settings.get("banner_mode"), settings.get("banner_image")) == "image":
        path = os.path.join(BANNER_DIR, f"{settings['banner_image']}.webp")
        banner = path if os.path.exists(path) else None
    return {
        "accent": accent or PALETTE_HEX[DEFAULT_ACCENT],
        "bg": BACKGROUND_HEX.get(settings.get("background_color")) or d.BG,
        "banner": banner,
        "featured": settings.get("featured_badges") or [],
    }


def _name(value: str | None, fallback: str) -> str:
    """Display name the card fonts can draw (a name made only of emoji or CJK falls back to a generic one)."""
    return d.clean(value) or fallback


def _footer(h: int, accent: str) -> str:
    y = h - 30
    return (d.icon_block(M, y - 32, 40, "hourglass", accent)
            + d.text(M + 56, y, "HOURGLASS", 26, 700, d.TEXT, spacing=3)
            + d.text(W - M, y, d.SITE, 24, 600, d.DIM, "end", font="body"))


def _tile(x: float, y: float, w: float, h: float, icon: str, caption: str, value: str, color: str, value_size: float = 56) -> str:
    """Key figure tile of the website: colored top edge, icon on a square of its color, caption, big italic value."""
    out = d.panel(x, y, w, h) + d.top_line(x, y, w, d.CUT, color)
    out += d.icon_block(x + 24, y + 26, 46, icon, color)
    cap, cap_size = d.fit_text(caption.upper(), w - 106, 23, 600, 16, spacing=23 * 0.08)
    out += d.caption(x + 84, y + 58, cap, cap_size)
    value, size = d.fit_text(value, w - 48, value_size, 700, 30, italic=True)
    out += d.text(x + 24, y + h - 28, value, size, 700, d.TEXT, italic=True)
    return out


def _rank_block(x_right: float, y: float, caption: str, rank, total: int | None, lang: str) -> str:
    """Rank in gold italic figures with a huge outlined copy behind, as in the website's rankings."""
    out = d.caption(x_right, y, caption, 23, anchor="end")
    if isinstance(rank, int) and rank > 0:
        out = d.ghost(x_right + 12, y + 104, f"#{rank}", 150) + out
        out += d.text(x_right, y + 80, f"#{rank}", 80, 700, d.GOLD, "end", italic=True)
        if total:
            out += d.text(x_right, y + 118, tr("sur {n}", "of {n}", lang, n=d.fmt_int(total, lang)), 25, 600, d.MUTED, "end", font="body")
    else:
        out += d.text(x_right, y + 66, tr("Non classé", "Unranked", lang).upper(), 36, 700, d.MUTED, "end", spacing=2)
    return out


def _int_rank(rank) -> int | None:
    if isinstance(rank, int):
        return rank if rank > 0 else None
    if isinstance(rank, str) and rank.strip().lstrip("#").isdigit():
        return int(rank.strip().lstrip("#"))
    return None


def _tier_paint(badge: dict) -> str:
    return d.HOLO if badge.get("tier_key") == "mythic" else (badge.get("color") or d.MUTED)


# ---------------------------------------------------------------------------
# 1. Member card (/stats on a server, /allstats everywhere)
# ---------------------------------------------------------------------------
def member_card(user_id: int, server_id: int | None = None, lang: str = "en") -> str:
    lang = card_lang(lang)
    key = ("card_member", int(user_id), server_id, lang)
    return card_cache.get_or_set(key, CARD_CACHE_SECONDS, lambda: _member_card(int(user_id), server_id, lang))


def _member_card(user_id: int, server_id: int | None, lang: str) -> str:
    from app.routes.user_profile import load_user_profile_stats  # the profile page's own figures

    user = Users.get_or_none(Users.user_id == user_id)
    if not user:
        raise CardNotFound("member")
    member_label = tr("Membre {id}", "Member {id}", lang, id=user_id)
    profile = load_user_profile_stats(user_id, user.username or member_label, can_view_presence=False)
    name = _name(user.username, member_label)
    theme = _theme(user_id)
    accent = theme["accent"]

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        stat = Stats.get_or_none((Stats.user_id == user_id) & (Stats.server_id == server_id))
        seconds, messages = (stat.seconds or 0, stat.messages or 0) if stat else (0, 0)
        rank, total = get_user_rank_in_server(user_id, server_id), get_user_count_by_server_id(server_id)
        last_30 = get_activity_sum_last_X_days(user_id, 30, server_id=server_id).get("seconds", 0)
        tracked = get_user_raw_join_date(user_id, server_id)  # first activity on this server
        scope = _name(server.servername if server else None, tr("Ce serveur", "This server", lang))
        rank_caption = tr("Rang serveur", "Server rank", lang)
    else:
        seconds, messages = profile["total_seconds"], profile["total_message"] or 0
        rank, total = profile["rank"], profile["total_user"]
        last_30 = profile["total_time_last_30d"]
        tracked = profile["raw_join_date"]  # first activity on any server
        scope = tr("Tous les serveurs", "All servers", lang)
        rank_caption = tr("Rang global", "Global rank", lang)

    xp = calculate_user_xp_and_level(seconds, messages)
    # Badges belong to the member (global figures), like the showcase of the profile page
    showcase = featured_badges(calculate_user_badges(profile, lang=lang), theme["featured"])

    banner = theme["banner"]
    top = 210 if banner else 140          # vertical center of the avatar
    tiles_y = top + 200
    badges_y = tiles_y + 150 + 24
    h = (badges_y + 112 if showcase else tiles_y + 150) + 84

    body = ""
    if banner:
        uri = d.local_cover(banner, W, 220)
        if uri:
            body += (f'<image href="{uri}" x="0" y="0" width="{W}" height="220" preserveAspectRatio="xMidYMid slice"/>'
                     f'<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0.35" stop-color="{theme["bg"]}" stop-opacity="0"/>'
                     f'<stop offset="1" stop-color="{theme["bg"]}" stop-opacity="1"/></linearGradient></defs>'
                     f'<rect x="0" y="0" width="{W}" height="221" fill="url(#fade)"/>')

    # Identity
    av_r = 90
    body += _rank_block(W - M, top - 76, rank_caption, _int_rank(rank), total, lang)
    body += d.avatar(M + av_r + 8, top, av_r, d.remote_square(get_user_avatar_url(user_id), 2 * av_r), name, accent, "av")
    name_x = M + 2 * av_r + 52
    shown, size = d.fit_text(name.upper(), 860 - name_x, 60, 700, 38, spacing=1)
    body += d.text(name_x, top - 14, shown, size, 700, d.TEXT, spacing=1)
    title = tr(xp["title_fr"], xp["title_en"], lang)
    # Level and scope share the line: smaller text first, then the level title is shortened (the scope stays whole)
    room = 930 - name_x   # up to the rank block
    level_text = tr("Niveau {n} · {title}", "Level {n} · {title}", lang, n=xp["level"], title=title)
    for tag_size in (23, 22, 21, 20, 19):
        level_tag, level_w = d.tag(name_x, top + 12, level_text, accent, tag_size, 48, solid=True)
        scope_tag, scope_w = d.tag(0, 0, scope, d.SOFT, tag_size, 48, max_width=room * 0.45)
        if level_w + 12 + scope_w <= room:
            break
    else:
        level_tag, level_w = d.tag(name_x, top + 12, level_text, accent, tag_size, 48, solid=True, max_width=room - scope_w - 12)
    scope_tag, _ = d.tag(name_x + level_w + 12, top + 12, scope, d.SOFT, tag_size, 48, max_width=room * 0.45)
    body += level_tag + scope_tag

    # Progress to the next level
    bar_y = top + 150
    body += d.text(M, bar_y - 16, f"{d.fmt_int(xp['total_xp'], lang)} XP", 28, 700, d.XP, italic=True)
    percent = xp["progress_percent"]
    progress = tr("{p} % vers le niveau {n}", "{p}% to level {n}", lang,
                  p=format_number(percent, 0 if float(percent).is_integer() else 1, lang), n=xp["level"] + 1)
    body += d.text(W - M, bar_y - 16, progress, 24, 600, d.MUTED, "end", font="body")
    body += d.progress(M, bar_y, INNER, 14, xp["progress_percent"] / 100, accent)

    # Key figures (the date needs a wider tile); on a profile everything wears the member's color
    widths = [244, 244, 244, INNER - 3 * 244 - 3 * 20]
    tiles = [
        ("mic", tr("Vocal", "Voice", lang), d.fmt_hours(seconds, lang), accent, 56),
        ("chat", tr("Messages", "Messages", lang), d.fmt_int(messages, lang), accent, 56),
        ("flame", tr("Vocal 30 j", "Voice 30 d", lang), d.fmt_hours(last_30, lang), accent, 56),
        ("calendar", tr("Suivi depuis", "Tracked since", lang), d.fmt_date(tracked, lang), d.MUTED, 40),
    ]
    x = M
    for (icon, caption, value, color, vsize), tw in zip(tiles, widths):
        body += _tile(x, tiles_y, tw, 150, icon, caption, value, color, vsize)
        x += tw + 20

    # Showcase: the badges the member chose (or the highest tiers), in their tier color
    if showcase:
        bw = (INNER - 2 * 20) / 3
        for i, badge in enumerate(showcase[:3]):
            x = M + i * (bw + 20)
            paint = _tier_paint(badge)
            color = badge.get("color") or d.MUTED
            body += d.shape(x, badges_y, bw, 112, color, 0.10, d.CUT, stroke=paint, stroke_opacity=0.6)
            body += d.shape(x + 22, badges_y + 22, 68, 68, paint, 1, d.CUT_S)
            body += d.pixel(PIXEL_FOR.get(BADGE_ICONS.get(badge.get("id")), "star"), x + 36, badges_y + 36, 40, d.BG)
            title_txt, tsize = d.fit_text(badge.get("name", ""), bw - 130, 30, 700, 22)
            body += d.text(x + 110, badges_y + 52, title_txt, tsize, 700, d.TEXT)
            body += d.text(x + 110, badges_y + 86, (badge.get("tier_label") or "").upper(), 22, 700, paint, spacing=2)

    body += _footer(h, accent)
    return d.document(W, h, body, accent, theme["bg"])


# ---------------------------------------------------------------------------
# 2. Versus card (/versus, on this server or everywhere)
# ---------------------------------------------------------------------------
def _rounds(lang: str) -> list[tuple[str, str]]:
    return [("hours", tr("Temps vocal", "Voice time", lang)), ("messages", tr("Messages", "Messages", lang)),
            ("activity_30d", tr("30 derniers jours", "Last 30 days", lang)), ("rank", tr("Rang", "Rank", lang)),
            ("badges", tr("Paliers de badges", "Badge tiers", lang))]


def versus_card(user1_id: int, user2_id: int, server_id: int | None = None, lang: str = "en") -> str:
    lang = card_lang(lang)
    key = ("card_versus", int(user1_id), int(user2_id), server_id, lang)
    return card_cache.get_or_set(key, CARD_CACHE_SECONDS, lambda: _versus_card(int(user1_id), int(user2_id), server_id, lang))


def _versus_card(user1_id: int, user2_id: int, server_id: int | None, lang: str) -> str:
    from app.routes.versus import compare_user_metrics, load_user_versus_data  # the /versus page's own figures

    u1, u2 = Users.get_or_none(Users.user_id == user1_id), Users.get_or_none(Users.user_id == user2_id)
    if not u1 or not u2:
        raise CardNotFound("member")
    p1 = load_user_versus_data(u1, lang=lang, server_id=server_id)
    p2 = load_user_versus_data(u2, lang=lang, server_id=server_id)
    p1["username"] = _name(p1["username"], tr("Joueur 1", "Player 1", lang))
    p2["username"] = _name(p2["username"], tr("Joueur 2", "Player 2", lang))
    metrics = {m["key"]: m for m in compare_user_metrics(p1, p2)["metrics"]}
    rounds = [(metrics[k], caption) for k, caption in _rounds(lang) if k in metrics]
    score1 = sum(1 for m, _ in rounds if m["winner"] == "1")
    score2 = sum(1 for m, _ in rounds if m["winner"] == "2")

    # Each side wears its member's profile color; a second color when both are too alike
    _prefetch([(p1.get("avatar"), 156), (p2.get("avatar"), 156)])
    c1, c2 = _theme(user1_id)["accent"], _theme(user2_id)["accent"]
    if d.color_distance(c1, c2) < 110:
        c2 = d.SERVER if d.color_distance(c1, d.SERVER) >= 110 else d.MESSAGES

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        scope = tr("Sur {server}", "On {server}", lang, server=_name(server.servername if server else None, tr("ce serveur", "this server", lang)))
    else:
        scope = tr("Tous les serveurs", "All servers", lang)

    row_h, rows_y = 92, 420
    h = rows_y + len(rounds) * row_h + 92
    body = ""
    # Two halves tinted with the players' colors
    body += (f'<defs><linearGradient id="sides" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{c1}" stop-opacity="0.18"/><stop offset="0.5" stop-color="{c1}" stop-opacity="0"/>'
             f'<stop offset="0.5" stop-color="{c2}" stop-opacity="0"/><stop offset="1" stop-color="{c2}" stop-opacity="0.18"/>'
             f'</linearGradient></defs><rect width="{W}" height="300" fill="url(#sides)"/>')
    scope_tag, _ = d.tag(W / 2, 34, scope, d.SOFT, 23, 46, "middle", 560)
    body += scope_tag

    av_r = 78
    for side, (p, color) in enumerate(((p1, c1), (p2, c2))):
        cx = M + av_r + 10 if side == 0 else W - M - av_r - 10
        body += d.avatar(cx, 186, av_r, d.remote_square(p.get("avatar"), 2 * av_r), p["username"], color, f"v{side}")
        anchor = "start" if side == 0 else "end"
        tx = cx + av_r + 32 if side == 0 else cx - av_r - 32
        shown, size = d.fit_text(p["username"].upper(), 320, 46, 700, 28, spacing=1)
        body += d.text(tx, 180, shown, size, 700, d.TEXT, anchor, spacing=1)
        body += d.text(tx, 226, tr("Niveau {n}", "Level {n}", lang, n=p["level"]).upper(), 28, 700, color, anchor, spacing=2)

    body += d.shape(W / 2 - 56, 130, 112, 112, d.PANEL, 1, d.CUT, stroke=d.LINE)
    body += d.text(W / 2, 205, "VS", 52, 700, d.TEXT, "middle", italic=True)

    # Verdict
    if score1 != score2:
        winner, color = (p1, c1) if score1 > score2 else (p2, c2)
        verdict = tr("{name} gagne {a}–{b}", "{name} wins {a}–{b}", lang, name=winner["username"], a=max(score1, score2), b=min(score1, score2))
    else:
        color, verdict = d.SOFT, tr("Égalité {a}–{b}", "It's a tie {a}–{b}", lang, a=score1, b=score2)
    body += d.shape(M, 300, INNER, 88, color, 0.12, d.CUT, stroke=color, stroke_opacity=0.6)
    verdict, vsize = d.fit_text(verdict.upper(), INNER - 160, 40, 700, 28, spacing=2)
    vw = d.text_width(verdict, vsize, 700) + 2 * len(verdict)
    left = W / 2 - (vw + 60) / 2   # crown + gap + text, centered together
    body += d.pixel("crown", left, 324, 40, color)
    body += d.text(left + 60, 358, verdict, vsize, 700, color, spacing=2)

    # Rounds: values on each side, winner highlighted, bar split by share
    for i, (m, caption) in enumerate(rounds):
        y = rows_y + i * row_h
        v1, v2 = m["v1"], m["v2"]
        if m["key"] == "rank":
            r1, r2 = _int_rank(v1), _int_rank(v2)
            s1, s2 = (f"#{r1}" if r1 else "—"), (f"#{r2}" if r2 else "—")
            share = (r2 / (r1 + r2)) if r1 and r2 else (1.0 if r1 else 0.0 if r2 else 0.5)  # lower is better
        else:
            fmt = (lambda v: d.fmt_hours(v * 3600, lang)) if m["key"] in ("hours", "activity_30d") else (lambda v: d.fmt_int(v, lang))
            s1, s2 = fmt(v1), fmt(v2)
            share = v1 / (v1 + v2) if (v1 or 0) + (v2 or 0) > 0 else 0.5
        w1, w2 = m["winner"] == "1", m["winner"] == "2"
        body += d.caption(W / 2, y + 30, caption, 23, anchor="middle")
        body += d.text(M, y + 36, s1, 40, 700, c1 if w1 else d.SOFT, opacity=None if w1 or not w2 else 0.5, italic=True)
        body += d.text(W - M, y + 36, s2, 40, 700, c2 if w2 else d.SOFT, "end", opacity=None if w2 or not w1 else 0.5, italic=True)
        share = max(0.03, min(0.97, share))
        bar_y = y + 54
        split = M + INNER * share
        body += (f'<rect x="{M}" y="{bar_y}" width="{split - M - 3:.1f}" height="12" fill="{c1}" fill-opacity="{1 if not w2 else 0.35}"/>'
                 f'<rect x="{split + 3:.1f}" y="{bar_y}" width="{M + INNER - split - 3:.1f}" height="12" fill="{c2}" fill-opacity="{1 if not w1 else 0.35}"/>')

    body += _footer(h, c1)
    return d.document(W, h, body, c1, halo=c2)


# ---------------------------------------------------------------------------
# 3. Leaderboard card (/top on a server, /alltop everywhere)
# ---------------------------------------------------------------------------
def top_card(metric: str = "voice", period: str = "all", server_id: int | None = None, lang: str = "en") -> str:
    metric = "messages" if metric == "messages" else "voice"
    period = period if period in PERIODS else "all"
    lang = card_lang(lang)
    key = ("card_top", metric, period, server_id, lang)
    return card_cache.get_or_set(key, CARD_CACHE_SECONDS, lambda: _top_card(metric, period, server_id, lang))


def _period_label(period: str, lang: str) -> str:
    return {"all": tr("Toujours", "All time", lang), "week": tr("7 derniers jours", "Last 7 days", lang),
            "month": tr("30 derniers jours", "Last 30 days", lang)}[period]


def _top_card(metric: str, period: str, server_id: int | None, lang: str) -> str:
    from app.routes.top import RANKING_CACHE_SECONDS, _compute_user_ranking, without_bots  # the /members ranking

    site_period = PERIODS[period]
    scope_key = str(server_id) if server_id else "all"
    rows = cache.get_or_set(("members", site_period, scope_key), RANKING_CACHE_SECONDS,
                            lambda: _compute_user_ranking(site_period, scope_key))
    rows = without_bots(rows)  # real members only, like the default view of the Members page
    field = "messages" if metric == "messages" else "seconds"
    top = sorted((r for r in rows if (r.get(field) or 0) > 0), key=lambda r: -r[field])[:10]
    color = d.MESSAGES if metric == "messages" else d.VOICE
    fmt = (lambda v: d.fmt_int(v, lang)) if metric == "messages" else (lambda v: d.fmt_hours(v, lang))

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        scope = _name(server.servername if server else None, tr("Ce serveur", "This server", lang))
    else:
        scope = tr("Tous les serveurs", "All servers", lang)

    _prefetch([(r.get("avatar_url"), 128 if i < 3 else 44) for i, r in enumerate(top)])
    rest = top[3:]
    list_rows = (len(rest) + 1) // 2
    h = 560 + (list_rows * 76 + 20 if rest else 0) + 84
    if not top:
        h = 420

    body = d.icon_block(M, 48, 60, "trophy", d.GOLD)
    title = tr("Top 10 · Messages", "Top 10 · Messages", lang) if metric == "messages" else tr("Top 10 · Vocal", "Top 10 · Voice", lang)
    period_tag, pw = d.tag(W - M, 54, _period_label(period, lang), color, 23, 48, "end", solid=True)
    scope_tag, sw = d.tag(W - M - pw - 12, 54, scope, d.SOFT, 23, 48, "end", 400)
    title_txt, tsize = d.fit_text(title.upper(), W - M - pw - sw - 24 - (M + 82) - 16, 50, 700, 32, spacing=2)
    body += d.text(M + 82, 96, title_txt, tsize, 700, d.TEXT, spacing=2)
    body += period_tag + scope_tag

    if not top:
        body += d.panel(M, 160, INNER, 160)
        body += d.text(W / 2, 255, tr("Pas encore d’activité sur cette période", "No activity in this period yet", lang), 34, 600, d.MUTED, "middle", font="body")
        body += _footer(h, color)
        return d.document(W, h, body, color)

    # Podium: 2nd, 1st (raised), 3rd, in gold, silver and bronze with their number huge behind
    medals = {1: d.GOLD, 2: d.SILVER, 3: d.BRONZE}
    col_w = (INNER - 2 * 24) / 3
    for slot, place in enumerate((2, 1, 3)):
        if place > len(top):
            continue
        r = top[place - 1]
        x = M + slot * (col_w + 24)
        y = 160 if place == 1 else 196
        medal = medals[place]
        body += d.shape(x, y, col_w, 520 - y, medal, 0.10 if place == 1 else 0.06, d.CUT, stroke=medal, stroke_opacity=0.45 if place == 1 else 0.3)
        body += d.top_line(x, y, col_w, d.CUT, medal)
        body += d.ghost(x + col_w - 14, 520 - 18, str(place), 230, opacity=0.09)
        cx = x + col_w / 2
        body += d.avatar(cx, y + 104, 62, d.remote_square(r.get("avatar_url"), 124), r.get("username"), medal, f"t{place}", 6)
        num, _ = d.tag(cx + 44, y + 34, str(place), medal, 26, 44, solid=True)
        body += num
        name, size = d.fit_text(_name(r.get("username"), tr("Membre", "Member", lang)), col_w - 40, 34, 700, 24)
        body += d.text(cx, y + 222, name, size, 700, d.TEXT, "middle")
        body += d.text(cx, y + 282, fmt(r[field]), 48, 700, color, "middle", italic=True)

    # Places 4 to 10, in two columns
    half = (INNER - 24) / 2
    for i, r in enumerate(rest):
        col, row = (0, i) if i < list_rows else (1, i - list_rows)
        x, y = M + col * (half + 24), 560 + row * 76
        body += d.panel(x, y, half, 64, d.CUT_S)
        body += d.text(x + 36, y + 44, str(i + 4), 30, 700, d.MUTED, "middle", italic=True)
        body += d.avatar(x + 94, y + 32, 22, d.remote_square(r.get("avatar_url"), 44), r.get("username"), d.LINE, f"l{i}", 2)
        value = fmt(r[field])
        vw = d.text_width(value, 30, 700, italic=True)
        name, size = d.fit_text(_name(r.get("username"), tr("Membre", "Member", lang)), half - 160 - vw - 24, 28, 600, 22, font="body")
        body += d.text(x + 130, y + 42, name, size, 600, d.TEXT, font="body")
        body += d.text(x + half - 22, y + 44, value, 30, 700, color, "end", italic=True)

    body += _footer(h, color)
    return d.document(W, h, body, color, halo=d.GOLD)


# ---------------------------------------------------------------------------
# 4. Server card (/server)
# ---------------------------------------------------------------------------
def server_card(server_id: int, lang: str = "en") -> str:
    lang = card_lang(lang)
    return card_cache.get_or_set(("card_server", int(server_id), lang), CARD_CACHE_SECONDS, lambda: _server_card(int(server_id), lang))


def _server_card(server_id: int, lang: str) -> str:
    server = Servers.get_or_none(Servers.server_id == server_id)
    if not server:
        raise CardNotFound("server")
    name = _name(server.servername, tr("Serveur {id}", "Server {id}", lang, id=server_id))
    seconds = get_total_seconds_by_server_id(server_id) or 0
    messages = get_total_message_by_server_id(server_id) or 0
    members = get_user_count_by_server_id(server_id) or 0
    live = get_server_live_status(server_id)
    daily = get_daily_hours_diff(server_id=server_id, days=30)
    accent = d.SERVER

    h = 728
    top = 150
    body = _rank_block(W - M, top - 76, tr("Rang serveur", "Server rank", lang), get_server_rank(server_id), get_global_nb_server(), lang)
    body += d.server_icon(M + 6, top - 80, 160, d.remote_square(get_server_avatar_url(server_id), 160), name, accent, "srv")
    name_x = M + 6 + 160 + 44
    shown, size = d.fit_text(name.upper(), 860 - name_x, 58, 700, 36, spacing=1)
    body += d.text(name_x, top - 12, shown, size, 700, d.TEXT, spacing=1)
    tracked = get_server_raw_join_date(server_id)
    since = tr("Suivi depuis le {date}", "Tracked since {date}", lang, date=d.fmt_date(tracked, lang)) if tracked \
        else tr("Suivi par Hourglass", "Tracked by Hourglass", lang)
    since_tag, _ = d.tag(name_x, top + 14, since, d.SOFT, 23, 48, max_width=860 - name_x)
    body += since_tag

    tiles_y = top + 120
    tw = (INNER - 3 * 20) / 4
    voice_now = int(live.get("voice_count") or 0)
    tiles = [
        ("mic", tr("Vocal", "Voice", lang), d.fmt_hours(seconds, lang), d.VOICE),
        ("chat", tr("Messages", "Messages", lang), d.fmt_int(messages, lang), d.MESSAGES),
        ("users", tr("Membres", "Members", lang), d.fmt_int(members, lang), d.MEMBER),
        ("headphones", tr("En vocal", "In voice", lang), d.fmt_int(voice_now, lang), d.SERVER),
    ]
    for i, (icon, caption, value, color) in enumerate(tiles):
        body += _tile(M + i * (tw + 20), tiles_y, tw, 150, icon, caption, value, color)

    # Voice hours per day over 30 days
    chart_y, chart_h = tiles_y + 174, 210
    body += d.panel(M, chart_y, INNER, chart_h)
    values = [float(r.get("hours_this_day") or 0) for r in daily]
    total_30 = sum(values)
    body += d.caption(M + 28, chart_y + 46, tr("Vocal · 30 derniers jours", "Voice · last 30 days", lang), 23)
    body += d.text(W - M - 28, chart_y + 46, tr("{h} au total", "{h} in total", lang, h=d.fmt_hours(int(total_30 * 3600), lang)),
                   26, 700, d.VOICE, "end", italic=True)
    if values and max(values) > 0:
        x0, x1, y0, y1 = M + 28, W - M - 28, chart_y + 76, chart_y + chart_h - 26
        step = (x1 - x0) / max(1, len(values) - 1)
        peak = max(values)
        pts = [(x0 + i * step, y1 - (v / peak) * (y1 - y0)) for i, v in enumerate(values)]
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        body += (f'<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{d.VOICE}" stop-opacity="0.35"/>'
                 f'<stop offset="1" stop-color="{d.VOICE}" stop-opacity="0"/></linearGradient></defs>'
                 f'<polygon points="{x0},{y1} {line} {x1:.1f},{y1}" fill="url(#area)"/>'
                 f'<polyline points="{line}" fill="none" stroke="{d.VOICE}" stroke-width="5" stroke-linejoin="miter"/>')
    else:
        body += d.text(W / 2, chart_y + 150, tr("Aucune activité vocale ces 30 derniers jours", "No voice activity in the last 30 days", lang),
                       28, 600, d.MUTED, "middle", font="body")

    body += _footer(h, accent)
    return d.document(W, h, body, accent, halo=d.VOICE)


# ---------------------------------------------------------------------------
# 5. Help and error cards (embeddable SVG only; the bot answers /help with text)
# ---------------------------------------------------------------------------
def _help_commands(lang: str) -> list[tuple[str, str]]:
    return [
        ("/stats [user]", tr("Tes statistiques sur ce serveur", "Your stats on this server", lang)),
        ("/allstats [user]", tr("Tes statistiques sur tous les serveurs", "Your stats across every server", lang)),
        ("/top [type] [period] [scope]", tr("Top 10 de ce serveur", "Top 10 of this server", lang)),
        ("/alltop", tr("Top 10 de tous les serveurs", "Top 10 of every server", lang)),
        ("/versus <p1> <p2> [scope]", tr("Duel entre deux membres", "Head-to-head duel between two members", lang)),
        ("/server", tr("Statistiques de ce serveur", "Statistics of this server", lang)),
        ("/help", tr("Toutes les commandes", "Every command", lang)),
    ]


def help_card(lang: str = "en") -> str:
    lang = card_lang(lang)
    commands = _help_commands(lang)
    h = 150 + len(commands) * 76 + 78
    body = d.icon_block(M, 48, 60, "hourglass", d.ACCENT)
    body += d.text(M + 82, 96, tr("Commandes Hourglass", "Hourglass commands", lang).upper(), 50, 700, d.TEXT, spacing=2)
    for i, (cmd, desc) in enumerate(commands):
        y = 150 + i * 76
        body += d.panel(M, y, INNER, 64, d.CUT_S)
        body += d.text(M + 26, y + 43, cmd, 30, 700, d.ACCENT)
        desc, size = d.fit_text(desc, INNER - 520, 28, 400, 22, font="body")
        body += d.text(W - M - 26, y + 43, desc, size, 400, d.SOFT, "end", font="body")
    body += _footer(h, d.ACCENT)
    return d.document(W, h, body, d.ACCENT)


def error_card(title: str, message: str) -> str:
    h = 300
    color = d.DANGER
    body = d.shape(M, h / 2 - 66, 112, 112, color, 0.14, d.CUT, stroke=color, stroke_opacity=0.6)
    body += d.pixel("alert", M + 26, h / 2 - 40, 60, color)
    title, size = d.fit_text(title.upper(), INNER - 170, 42, 700, 28, spacing=1)
    body += d.text(M + 150, h / 2 - 16, title, size, 700, d.TEXT, spacing=1)
    message, msize = d.fit_text(message, INNER - 170, 28, 400, 22, font="body")
    body += d.text(M + 150, h / 2 + 30, message, msize, 400, d.MUTED, font="body")
    body += _footer(h, color)
    return d.document(W, h, body, color)


def not_found_card(what: str, lang: str = "en") -> str:
    """Error card of the embeddable SVG links, in the requested language."""
    lang = card_lang(lang)
    if what == "server":
        return error_card(tr("Serveur introuvable", "Server not found", lang),
                          tr("Hourglass n’a encore aucune activité enregistrée pour ce serveur.", "Hourglass has no activity recorded for this server yet.", lang))
    return error_card(tr("Membre introuvable", "Member not found", lang),
                      tr("Hourglass n’a encore aucune activité enregistrée pour ce membre.", "Hourglass has no activity recorded for this member yet.", lang))


def resolve_user_id(identifier: str) -> int | None:
    """Member by id or username (the embeddable cards accept both)."""
    raw = str(identifier or "").strip()
    user = Users.get_or_none(Users.user_id == int(raw)) if raw.isdigit() else None
    if not user:
        user = Users.select().where(Users.username == raw).first() or \
            Users.select().where(fn.LOWER(Users.username) == raw.lower()).first()
    return int(user.user_id) if user else None
