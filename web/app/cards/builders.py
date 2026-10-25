"""Stat cards: data (reusing the website's own computations) and layout. English only, for every community.

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
from app.gamification import calculate_user_badges, calculate_user_xp_and_level
from app.profile_records import featured_badges
from app.profile_settings import BACKGROUND_HEX, DEFAULT_ACCENT, PALETTE_HEX, discord_accent_hex, effective_banner_mode, get_profile_settings

W = 1200
M = 48            # outer margin
INNER = W - 2 * M
BANNER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "profile", "banners")
CARD_CACHE_SECONDS = 120
# Cards embed their pictures (100-250 KB each): a small dedicated cache keeps a worker's memory bounded
card_cache = TTLCache(max_entries=48)

PERIODS = {"all": ("all", "All time"), "week": ("7d", "Last 7 days"), "month": ("1m", "Last 30 days")}


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


def _name(value: str | None, fallback: str = "Member") -> str:
    """Display name drawable with Inter (a name made only of emoji or CJK falls back to a generic one)."""
    return d.clean(value) or fallback


def _footer(h: int) -> str:
    y = h - 30
    return (d.icon(d.ICONS["hourglass"], M, y - 24, 30, d.DIM, 2.2)
            + d.text(M + 42, y, "HOURGLASS", 24, 800, d.DIM, spacing=2)
            + d.text(W - M, y, d.SITE, 24, 700, d.DIM, "end"))


def _tile(x: float, y: float, w: float, h: float, icon_key: str, caption: str, value: str, color: str, value_size: float = 54) -> str:
    out = d.panel(x, y, w, h, 24)
    out += d.icon(d.ICONS[icon_key], x + 26, y + 26, 30, color, 2.4)
    cap, cap_size = caption.upper(), 23.0
    while cap_size > 18 and d.text_width(cap, cap_size, 700) + 1.5 * len(cap) > w - 94:
        cap_size -= 1
    out += d.label(x + 68, y + 51, caption, cap_size)
    value, size = d.fit_text(value, w - 52, value_size, 900, 30)
    out += d.text(x + 26, y + h - 30, value, size, 900, d.TEXT)
    return out


def _rank_block(x_right: float, y: float, caption: str, rank, total: int | None, color: str) -> str:
    out = d.label(x_right, y, caption, 23, anchor="end")
    if isinstance(rank, int) and rank > 0:
        out += d.text(x_right, y + 76, f"#{rank}", 76, 900, color, "end")
    else:
        out += d.text(x_right, y + 66, "Unranked", 40, 900, d.MUTED, "end")
    if total:
        out += d.text(x_right, y + 114, f"of {d.fmt_int(total)}", 25, 600, d.MUTED, "end")
    return out


def _int_rank(rank) -> int | None:
    if isinstance(rank, int):
        return rank if rank > 0 else None
    if isinstance(rank, str) and rank.strip().lstrip("#").isdigit():
        return int(rank.strip().lstrip("#"))
    return None


# ---------------------------------------------------------------------------
# 1. Member card (/stats on a server, /allstats everywhere)
# ---------------------------------------------------------------------------
def member_card(user_id: int, server_id: int | None = None) -> str:
    return card_cache.get_or_set(("card_member", int(user_id), server_id), CARD_CACHE_SECONDS, lambda: _member_card(int(user_id), server_id))


def _member_card(user_id: int, server_id: int | None) -> str:
    from app.routes.user_profile import load_user_profile_stats  # the profile page's own figures

    user = Users.get_or_none(Users.user_id == user_id)
    if not user:
        raise CardNotFound("member")
    profile = load_user_profile_stats(user_id, user.username or f"User {user_id}", can_view_presence=False)
    name = _name(user.username)
    theme = _theme(user_id)
    accent = theme["accent"]

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        stat = Stats.get_or_none((Stats.user_id == user_id) & (Stats.server_id == server_id))
        seconds, messages = (stat.seconds or 0, stat.messages or 0) if stat else (0, 0)
        rank, total = get_user_rank_in_server(user_id, server_id), get_user_count_by_server_id(server_id)
        last_30 = get_activity_sum_last_X_days(user_id, 30, server_id=server_id).get("seconds", 0)
        tracked = get_user_raw_join_date(user_id, server_id)  # first activity on this server
        scope = _name(server.servername if server else None, "This server")
        rank_caption = "Server rank"
    else:
        seconds, messages = profile["total_seconds"], profile["total_message"] or 0
        rank, total = profile["rank"], profile["total_user"]
        last_30 = profile["total_time_last_30d"]
        tracked = profile["raw_join_date"]  # first activity on any server
        scope = "All servers"
        rank_caption = "Global rank"

    xp = calculate_user_xp_and_level(seconds, messages)
    # Badges belong to the member (global figures), like the showcase of the profile page
    showcase = featured_badges(calculate_user_badges(profile, lang="en"), theme["featured"])

    banner = theme["banner"]
    top = 210 if banner else 140          # vertical center of the avatar
    tiles_y = top + 200
    badges_y = tiles_y + 150 + 24
    h = (badges_y + 112 if showcase else tiles_y + 150) + 76

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
    av_r = 92
    body += d.avatar(M + av_r + 8, top, av_r, d.remote_square(get_user_avatar_url(user_id), 2 * av_r), name, accent, "av")
    name_x = M + 2 * av_r + 52
    shown, size = d.fit_text(name, 860 - name_x, 62, 900, 40)
    body += d.text(name_x, top - 12, shown, size, 900, d.TEXT)
    level_pill, level_w = d.pill(name_x, top + 14, f"Level {xp['level']} · {xp['title_en']}", accent, 26, 50)
    scope_pill, _ = d.pill(name_x + level_w + 14, top + 14, scope, d.SOFT, 26, 50, weight=700, max_width=860 - name_x - level_w - 14)
    body += level_pill + scope_pill
    body += _rank_block(W - M, top - 76, rank_caption, _int_rank(rank), total, accent)

    # Progress to the next level
    bar_y = top + 150
    body += d.text(M, bar_y - 14, f"{d.fmt_int(xp['total_xp'])} XP", 26, 800, d.SOFT)
    body += d.text(W - M, bar_y - 14, f"{xp['progress_percent']:g}% to level {xp['level'] + 1}", 24, 600, d.MUTED, "end")
    body += d.progress(M, bar_y, INNER, 16, xp["progress_percent"] / 100, accent, d.MESSAGES, "xpbar")

    # Key figures (the date needs a wider tile)
    widths = [244, 244, 244, INNER - 3 * 244 - 3 * 20]
    tiles = [
        ("mic", "Voice", d.fmt_hours(seconds), accent, 54),
        ("message", "Messages", d.fmt_int(messages), d.MESSAGES, 54),
        ("activity", "Last 30 days", d.fmt_hours(last_30), accent, 54),
        ("calendar", "Tracked since", d.fmt_date(tracked), d.MUTED, 42),
    ]
    x = M
    for (key, caption, value, color, vsize), tw in zip(tiles, widths):
        body += _tile(x, tiles_y, tw, 150, key, caption, value, color, vsize)
        x += tw + 20

    # Showcase: the badges the member chose (or the highest tiers), large and in their tier color
    if showcase:
        bw = (INNER - 2 * 20) / 3
        for i, badge in enumerate(showcase[:3]):
            x = M + i * (bw + 20)
            color = badge.get("color") or d.MUTED
            body += d.rect(x, badges_y, bw, 112, 24, color, 0.09, stroke=color, stroke_opacity=0.4)
            body += f'<circle cx="{x + 60}" cy="{badges_y + 56}" r="38" fill="{color}" fill-opacity="0.16"/>'
            body += d.icon(badge.get("svg_path", ""), x + 38, badges_y + 34, 44, color, 2.2)
            title, tsize = d.fit_text(badge.get("name", ""), bw - 130, 30, 800, 22)
            body += d.text(x + 114, badges_y + 52, title, tsize, 800, d.TEXT)
            body += d.text(x + 114, badges_y + 86, (badge.get("tier_label") or "").upper(), 22, 800, color, spacing=1.5)

    body += _footer(h)
    return d.document(W, h, body, theme["bg"], glow=None if banner else accent)


# ---------------------------------------------------------------------------
# 2. Versus card (/versus, on this server or everywhere)
# ---------------------------------------------------------------------------
ROUNDS = [("hours", "Voice time"), ("messages", "Messages"), ("activity_30d", "Last 30 days"), ("rank", "Rank"), ("badges", "Badges")]


def versus_card(user1_id: int, user2_id: int, server_id: int | None = None) -> str:
    key = ("card_versus", int(user1_id), int(user2_id), server_id)
    return card_cache.get_or_set(key, CARD_CACHE_SECONDS, lambda: _versus_card(int(user1_id), int(user2_id), server_id))


def _versus_card(user1_id: int, user2_id: int, server_id: int | None) -> str:
    from app.routes.versus import compare_user_metrics, load_user_versus_data  # the /versus page's own figures

    u1, u2 = Users.get_or_none(Users.user_id == user1_id), Users.get_or_none(Users.user_id == user2_id)
    if not u1 or not u2:
        raise CardNotFound("member")
    p1 = load_user_versus_data(u1, lang="en", server_id=server_id)
    p2 = load_user_versus_data(u2, lang="en", server_id=server_id)
    p1["username"], p2["username"] = _name(p1["username"], "Player 1"), _name(p2["username"], "Player 2")
    metrics = {m["key"]: m for m in compare_user_metrics(p1, p2)["metrics"]}
    rounds = [(metrics[k], caption) for k, caption in ROUNDS if k in metrics]
    score1 = sum(1 for m, _ in rounds if m["winner"] == "1")
    score2 = sum(1 for m, _ in rounds if m["winner"] == "2")

    # Each side wears its member's profile color; a second color when both are too alike
    _prefetch([(p1.get("avatar"), 156), (p2.get("avatar"), 156)])
    c1, c2 = _theme(user1_id)["accent"], _theme(user2_id)["accent"]
    if d.color_distance(c1, c2) < 110:
        c2 = "#c084fc" if d.color_distance(c1, "#c084fc") >= 110 else "#38bdf8"

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        scope = f"On {_name(server.servername if server else None, 'this server')}"
    else:
        scope = "All servers"

    row_h, rows_y = 92, 420
    h = rows_y + len(rounds) * row_h + 84
    body = ""
    # Two halves tinted with the players' colors
    body += (f'<defs><linearGradient id="sides" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{c1}" stop-opacity="0.16"/><stop offset="0.5" stop-color="{c1}" stop-opacity="0"/>'
             f'<stop offset="0.5" stop-color="{c2}" stop-opacity="0"/><stop offset="1" stop-color="{c2}" stop-opacity="0.16"/>'
             f'</linearGradient></defs><rect width="{W}" height="300" fill="url(#sides)"/>')
    scope_pill, _ = d.pill(W / 2, 34, scope, d.SOFT, 25, 48, "middle", 700, 560)
    body += scope_pill

    av_r = 78
    for side, (p, color) in enumerate(((p1, c1), (p2, c2))):
        cx = M + av_r + 10 if side == 0 else W - M - av_r - 10
        body += d.avatar(cx, 186, av_r, d.remote_square(p.get("avatar"), 2 * av_r), p["username"], color, f"v{side}")
        anchor = "start" if side == 0 else "end"
        tx = cx + av_r + 32 if side == 0 else cx - av_r - 32
        shown, size = d.fit_text(p["username"], 330, 48, 900, 30)
        body += d.text(tx, 180, shown, size, 900, d.TEXT, anchor)
        body += d.text(tx, 226, f"Level {p['level']}", 30, 800, color, anchor)

    body += f'<circle cx="{W / 2}" cy="186" r="54" fill="{d.BG}" stroke="{d.LINE}" stroke-opacity="0.18" stroke-width="2"/>'
    body += d.text(W / 2, 202, "VS", 44, 900, d.TEXT, "middle")

    # Verdict
    if score1 != score2:
        winner, color = (p1, c1) if score1 > score2 else (p2, c2)
        verdict = f"{winner['username']} wins {max(score1, score2)}–{min(score1, score2)}"
    else:
        color, verdict = d.SOFT, f"It's a tie {score1}–{score2}"
    body += d.rect(M, 300, INNER, 88, 24, color, 0.12, stroke=color, stroke_opacity=0.45)
    verdict, vsize = d.fit_text(verdict, INNER - 160, 44, 900, 30)
    vw = d.text_width(verdict, vsize, 900)
    left = W / 2 - (vw + 58) / 2   # crown + gap + text, centered together
    body += d.icon(d.ICONS["crown"], left, 323, 42, color, 2.4)
    body += d.text(left + 58, 360, verdict, vsize, 900, color)

    # Rounds: values on each side, winner highlighted, bar split by share
    for i, (m, caption) in enumerate(rounds):
        y = rows_y + i * row_h
        v1, v2 = m["v1"], m["v2"]
        if m["key"] == "rank":
            r1, r2 = _int_rank(v1), _int_rank(v2)
            s1, s2 = (f"#{r1}" if r1 else "—"), (f"#{r2}" if r2 else "—")
            share = (r2 / (r1 + r2)) if r1 and r2 else (1.0 if r1 else 0.0 if r2 else 0.5)  # lower is better
        else:
            fmt = (lambda v: d.fmt_hours(v * 3600)) if m["key"] in ("hours", "activity_30d") else d.fmt_int
            s1, s2 = fmt(v1), fmt(v2)
            share = v1 / (v1 + v2) if (v1 or 0) + (v2 or 0) > 0 else 0.5
        w1, w2 = m["winner"] == "1", m["winner"] == "2"
        body += d.label(W / 2, y + 30, caption, 24, anchor="middle")
        body += d.text(M, y + 36, s1, 40, 900, c1 if w1 else d.SOFT, opacity=None if w1 or not w2 else 0.55)
        body += d.text(W - M, y + 36, s2, 40, 900, c2 if w2 else d.SOFT, "end", opacity=None if w2 or not w1 else 0.55)
        share = max(0.03, min(0.97, share))
        bar_y, bar_w = y + 54, INNER
        split = M + bar_w * share
        body += f'<clipPath id="bar{i}"><rect x="{M}" y="{bar_y}" width="{bar_w}" height="14" rx="7"/></clipPath>'
        body += (f'<g clip-path="url(#bar{i})"><rect x="{M}" y="{bar_y}" width="{split - M:.1f}" height="14" fill="{c1}" fill-opacity="{1 if not w2 else 0.4}"/>'
                 f'<rect x="{split:.1f}" y="{bar_y}" width="{M + bar_w - split:.1f}" height="14" fill="{c2}" fill-opacity="{1 if not w1 else 0.4}"/></g>')

    body += _footer(h)
    return d.document(W, h, body)


# ---------------------------------------------------------------------------
# 3. Leaderboard card (/top on a server, /alltop everywhere)
# ---------------------------------------------------------------------------
def top_card(metric: str = "voice", period: str = "all", server_id: int | None = None) -> str:
    metric = "messages" if metric == "messages" else "voice"
    period = period if period in PERIODS else "all"
    key = ("card_top", metric, period, server_id)
    return card_cache.get_or_set(key, CARD_CACHE_SECONDS, lambda: _top_card(metric, period, server_id))


def _top_card(metric: str, period: str, server_id: int | None) -> str:
    from app.routes.top import RANKING_CACHE_SECONDS, _compute_user_ranking  # the /members ranking

    site_period, period_label = PERIODS[period]
    scope_key = str(server_id) if server_id else "all"
    rows = cache.get_or_set(("members", site_period, scope_key), RANKING_CACHE_SECONDS,
                            lambda: _compute_user_ranking(site_period, scope_key))
    field = "messages" if metric == "messages" else "seconds"
    top = sorted((r for r in rows if (r.get(field) or 0) > 0), key=lambda r: -r[field])[:10]
    color = d.MESSAGES if metric == "messages" else d.VOICE
    fmt = d.fmt_int if metric == "messages" else d.fmt_hours

    if server_id:
        server = Servers.get_or_none(Servers.server_id == server_id)
        scope = _name(server.servername if server else None, "This server")
    else:
        scope = "All servers"

    _prefetch([(r.get("avatar_url"), 128 if i < 3 else 44) for i, r in enumerate(top)])
    rest = top[3:]
    list_rows = (len(rest) + 1) // 2
    h = 560 + (list_rows * 76 + 20 if rest else 0) + 76
    if not top:
        h = 420

    body = d.icon(d.ICONS["trophy"], M, 52, 50, d.GOLD, 2.4)
    body += d.text(M + 70, 96, f"Top 10 · {'Messages' if metric == 'messages' else 'Voice'}", 56, 900, d.TEXT)
    period_pill, pw = d.pill(W - M, 54, period_label, color, 26, 50, "end")
    scope_pill, _ = d.pill(W - M - pw - 14, 54, scope, d.SOFT, 26, 50, "end", 700, 420)
    body += period_pill + scope_pill

    if not top:
        body += d.panel(M, 160, INNER, 160)
        body += d.text(W / 2, 255, "No activity in this period yet", 36, 800, d.MUTED, "middle")
        body += _footer(h)
        return d.document(W, h, body, glow=color)

    # Podium: 2nd, 1st (raised), 3rd
    medals = {1: d.GOLD, 2: d.SILVER, 3: d.BRONZE}
    col_w = (INNER - 2 * 24) / 3
    for slot, place in enumerate((2, 1, 3)):
        if place > len(top):
            continue
        r = top[place - 1]
        x = M + slot * (col_w + 24)
        y = 160 if place == 1 else 196
        medal = medals[place]
        body += d.rect(x, y, col_w, 520 - y, 28, medal, 0.08 if place == 1 else 0.05, stroke=medal, stroke_opacity=0.35 if place == 1 else 0.2)
        cx = x + col_w / 2
        body += d.avatar(cx, y + 104, 64, d.remote_square(r.get("avatar_url"), 128), r.get("username"), medal, f"t{place}", 6)
        body += f'<circle cx="{cx + 52}" cy="{y + 54}" r="24" fill="{medal}"/>'
        body += d.text(cx + 52, y + 64, str(place), 28, 900, d.BG, "middle")
        name, size = d.fit_text(_name(r.get("username")), col_w - 40, 34, 800, 24)
        body += d.text(cx, y + 222, name, size, 800, d.TEXT, "middle")
        body += d.text(cx, y + 280, fmt(r[field]), 46, 900, color, "middle")

    # Places 4 to 10, in two columns
    half = (INNER - 24) / 2
    for i, r in enumerate(rest):
        col, row = (0, i) if i < list_rows else (1, i - list_rows)
        x, y = M + col * (half + 24), 560 + row * 76
        body += d.panel(x, y, half, 64, 18)
        body += d.text(x + 34, y + 43, str(i + 4), 28, 900, d.MUTED, "middle")
        body += d.avatar(x + 92, y + 32, 22, d.remote_square(r.get("avatar_url"), 44), r.get("username"), d.LINE, f"l{i}", 0)
        value = fmt(r[field])
        vw = d.text_width(value, 30, 900)
        name, size = d.fit_text(_name(r.get("username")), half - 160 - vw - 24, 28, 700, 22)
        body += d.text(x + 128, y + 42, name, size, 700, d.TEXT)
        body += d.text(x + half - 22, y + 43, value, 30, 900, color, "end")

    body += _footer(h)
    return d.document(W, h, body, glow=color)



# ---------------------------------------------------------------------------
# 4. Server card (/server)
# ---------------------------------------------------------------------------
def server_card(server_id: int) -> str:
    return card_cache.get_or_set(("card_server", int(server_id)), CARD_CACHE_SECONDS, lambda: _server_card(int(server_id)))


def _server_card(server_id: int) -> str:
    server = Servers.get_or_none(Servers.server_id == server_id)
    if not server:
        raise CardNotFound("server")
    name = _name(server.servername, f"Server {server_id}")
    seconds = get_total_seconds_by_server_id(server_id) or 0
    messages = get_total_message_by_server_id(server_id) or 0
    members = get_user_count_by_server_id(server_id) or 0
    live = get_server_live_status(server_id)
    daily = get_daily_hours_diff(server_id=server_id, days=30)
    accent = d.VOICE

    h = 720
    top = 150
    body = d.avatar(M + 88, top, 80, d.remote_square(get_server_avatar_url(server_id), 160), name, accent, "srv")
    name_x = M + 2 * 88 + 44
    shown, size = d.fit_text(name, 860 - name_x, 62, 900, 38)
    body += d.text(name_x, top - 10, shown, size, 900, d.TEXT)
    tracked = get_server_raw_join_date(server_id)
    since_pill, _ = d.pill(name_x, top + 16, f"Tracked since {d.fmt_date(tracked)}" if tracked else "Tracked by Hourglass", d.SOFT, 26, 50, weight=700)
    body += since_pill
    body += _rank_block(W - M, top - 76, "Server rank", get_server_rank(server_id), get_global_nb_server(), accent)

    tiles_y = top + 120
    tw = (INNER - 3 * 20) / 4
    voice_now = int(live.get("voice_count") or 0)
    tiles = [
        ("mic", "Voice", d.fmt_hours(seconds), accent),
        ("message", "Messages", d.fmt_int(messages), d.MESSAGES),
        ("users", "Members", d.fmt_int(members), d.WIN),
        ("headphones", "In voice now", d.fmt_int(voice_now), accent),
    ]
    for i, (key, caption, value, color) in enumerate(tiles):
        body += _tile(M + i * (tw + 20), tiles_y, tw, 150, key, caption, value, color)

    # Voice hours per day over 30 days
    chart_y, chart_h = tiles_y + 174, 210
    body += d.panel(M, chart_y, INNER, chart_h, 24)
    values = [float(r.get("hours_this_day") or 0) for r in daily]
    total_30 = sum(values)
    body += d.label(M + 28, chart_y + 46, "Voice · last 30 days", 23)
    body += d.text(W - M - 28, chart_y + 46, f"{d.fmt_hours(int(total_30 * 3600))} in total", 26, 800, accent, "end")
    if values and max(values) > 0:
        x0, x1, y0, y1 = M + 28, W - M - 28, chart_y + 76, chart_y + chart_h - 26
        step = (x1 - x0) / max(1, len(values) - 1)
        peak = max(values)
        pts = [(x0 + i * step, y1 - (v / peak) * (y1 - y0)) for i, v in enumerate(values)]
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        body += (f'<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{accent}" stop-opacity="0.35"/>'
                 f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></linearGradient></defs>'
                 f'<polygon points="{x0},{y1} {line} {x1:.1f},{y1}" fill="url(#area)"/>'
                 f'<polyline points="{line}" fill="none" stroke="{accent}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>')
    else:
        body += d.text(W / 2, chart_y + 150, "No voice activity in the last 30 days", 28, 700, d.MUTED, "middle")

    body += _footer(h)
    return d.document(W, h, body, glow=accent)


# ---------------------------------------------------------------------------
# 5. Help and error cards (embeddable SVG only; the bot answers /help with text)
# ---------------------------------------------------------------------------
HELP_COMMANDS = [
    ("/stats [user]", "Your stats on this server"),
    ("/allstats [user]", "Your stats across every server"),
    ("/top [type] [period] [scope]", "Top 10 of this server"),
    ("/alltop", "Top 10 of every server"),
    ("/versus <p1> <p2> [scope]", "Head-to-head duel between two members"),
    ("/server", "Statistics of this server"),
    ("/help", "Every command"),
]


def help_card() -> str:
    h = 150 + len(HELP_COMMANDS) * 76 + 70
    body = d.icon(d.ICONS["hourglass"], M, 52, 50, d.VOICE, 2.4)
    body += d.text(M + 70, 96, "Hourglass commands", 56, 900, d.TEXT)
    for i, (cmd, desc) in enumerate(HELP_COMMANDS):
        y = 150 + i * 76
        body += d.panel(M, y, INNER, 64, 18)
        body += d.text(M + 26, y + 43, cmd, 30, 800, d.VOICE)
        desc, size = d.fit_text(desc, INNER - 520, 28, 600, 22)
        body += d.text(W - M - 26, y + 43, desc, size, 600, d.SOFT, "end")
    body += _footer(h)
    return d.document(W, h, body, glow=d.VOICE)


def error_card(title: str, message: str) -> str:
    h = 300
    color = "#f87171"
    body = f'<circle cx="{M + 60}" cy="{h / 2 - 10}" r="52" fill="{color}" fill-opacity="0.14" stroke="{color}" stroke-opacity="0.5" stroke-width="3"/>'
    body += d.text(M + 60, h / 2 + 8, "!", 56, 900, color, "middle")
    title, size = d.fit_text(title, INNER - 170, 44, 900, 30)
    body += d.text(M + 150, h / 2 - 16, title, size, 900, d.TEXT)
    message, msize = d.fit_text(message, INNER - 170, 28, 600, 22)
    body += d.text(M + 150, h / 2 + 30, message, msize, 600, d.MUTED)
    body += _footer(h)
    return d.document(W, h, body)


def resolve_user_id(identifier: str) -> int | None:
    """Member by id or username (the embeddable cards accept both)."""
    raw = str(identifier or "").strip()
    user = Users.get_or_none(Users.user_id == int(raw)) if raw.isdigit() else None
    if not user:
        user = Users.select().where(Users.username == raw).first() or \
            Users.select().where(fn.LOWER(Users.username) == raw.lower()).first()
    return int(user.user_id) if user else None
