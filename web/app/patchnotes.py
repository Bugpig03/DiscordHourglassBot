"""Patch notes on the official Discord server (admin page > Patch notes).

Each new version of the website and of the bot is posted by the bot in the channel chosen on the admin page,
with its CHANGELOG entry. How it works:
  - at startup, the website writes the entries of its own CHANGELOG.md in `patchnotes` (the bot does the same with
    its own, built into it); an entry already there is never added twice;
  - the bot posts, within a minute, every entry not posted yet that arrived after the patch notes were turned on
    (nothing old is posted when they are turned on), oldest first, one message per version;
  - "Post the latest version now" asks the bot to post (again) the latest entry of the website or of the bot.
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone

from app.database import create_tables, db

log = logging.getLogger(__name__)

COMPONENTS = ("web", "bot")
SCOPES = ("both", "web", "bot")
REGISTERED_ENTRIES = 40      # newest CHANGELOG entries written at startup (a version skipped by a fast deploy is caught)
TEST_COOLDOWN_SECONDS = 60

TABLES = [
    # Also created by the bot (same definitions)
    """CREATE TABLE IF NOT EXISTS patchnote_settings (
        id SMALLINT PRIMARY KEY DEFAULT 1,
        enabled BOOLEAN NOT NULL DEFAULT FALSE,
        server_id BIGINT,
        channel_id BIGINT,
        scope VARCHAR(8) NOT NULL DEFAULT 'both',
        mention_role_id BIGINT,
        since TIMESTAMP WITHOUT TIME ZONE,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by BIGINT
    )""",
    """CREATE TABLE IF NOT EXISTS patchnotes (
        id BIGSERIAL PRIMARY KEY,
        component VARCHAR(8) NOT NULL,
        version VARCHAR(32) NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        released VARCHAR(10),
        body TEXT NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        requested_at TIMESTAMP WITHOUT TIME ZONE,
        posted_at TIMESTAMP WITHOUT TIME ZONE,
        ok BOOLEAN,
        detail TEXT,
        baseline BOOLEAN NOT NULL DEFAULT FALSE,
        title_en TEXT NOT NULL DEFAULT '',
        body_en TEXT NOT NULL DEFAULT '',
        UNIQUE (component, version)
    )""",
]

HEADER = re.compile(r"^##\s+Version\s+([0-9][0-9A-Za-z.\-]*)\s+-\s+(.*?)\s+-\s+(\d{2}/\d{2}/\d{4})\s*$")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_changelog(text: str) -> list[dict]:
    """Entries of a CHANGELOG ("## Version X - Title - dd/mm/yyyy" then the text), newest first."""
    entries, current = [], None
    for line in text.splitlines():
        match = HEADER.match(line.strip())
        if match:
            if current:
                entries.append(current)
            current = {"version": match.group(1), "title": match.group(2).strip(), "released": match.group(3), "lines": []}
        elif line.startswith("## ") or line.startswith("# "):
            if current:
                entries.append(current)
            current = None
        elif current is not None:
            current["lines"].append(line.rstrip())
    if current:
        entries.append(current)
    return [{"version": e["version"], "title": e["title"], "released": e["released"], "body": "\n".join(e["lines"]).strip()}
            for e in entries if "\n".join(e["lines"]).strip()]


def _changelog_path(name: str = "CHANGELOG.md") -> str | None:
    base = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(base, "..", name), os.path.join(base, name)):
        if os.path.isfile(path):
            return path
    return None


def merge_english(entries: list[dict], english: list[dict]) -> list[dict]:
    """Adds title_en / body_en to the French entries, from the English CHANGELOG (same versions; empty when the
    version has no English entry: the bot then posts the French text only)."""
    by_version = {e["version"]: e for e in english}
    return [dict(e, title_en=by_version.get(e["version"], {}).get("title", ""), body_en=by_version.get(e["version"], {}).get("body", ""))
            for e in entries]


def register(component: str, entries: list[dict]) -> None:
    """Writes the entries (oldest first, so the ids follow the versions). An entry not posted yet takes the latest
    text of its CHANGELOG; a posted one is never touched.

    The very first time (no entry of this component yet), every entry is a "baseline": already known, never posted,
    so turning the patch notes on never floods the channel with the whole history. Locked per component, so the
    workers starting together (and the bot) never see a half-written first batch."""
    with db.atomic():
        db.execute_sql("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"patchnotes:{component}",))
        first = not db.execute_sql("SELECT EXISTS (SELECT 1 FROM patchnotes WHERE component = %s)", (component,)).fetchone()[0]
        for e in reversed(entries[:REGISTERED_ENTRIES]):
            db.execute_sql(
                "INSERT INTO patchnotes (component, version, title, released, body, title_en, body_en, baseline) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (component, version) DO UPDATE SET title = EXCLUDED.title, released = EXCLUDED.released, "
                "body = EXCLUDED.body, title_en = EXCLUDED.title_en, body_en = EXCLUDED.body_en WHERE patchnotes.posted_at IS NULL",
                (component, e["version"][:32], e["title"], e["released"], e["body"], e.get("title_en", ""), e.get("body_en", ""), first))


def init_patchnotes() -> None:
    """At startup: tables, then this website's CHANGELOG entries (never blocks startup)."""
    error = create_tables(TABLES)
    if error is not None:
        log.warning("Patch notes disabled (tables unavailable): %s", error)
        return
    path = _changelog_path()
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as f:
            entries = parse_changelog(f.read())
        english_path = _changelog_path("CHANGELOG.en.md")
        if english_path:
            with open(english_path, encoding="utf-8") as f:
                entries = merge_english(entries, parse_changelog(f.read()))
        with db.connection_context():
            register("web", entries)  # one transaction: rolled back by itself on error
    except Exception:
        log.exception("Patch notes: CHANGELOG entries not written")


def _rows(sql: str, params=()) -> list[tuple]:
    try:
        return db.execute_sql(sql, params).fetchall()
    except Exception:
        db.rollback()
        return []


def get_settings() -> dict:
    rows = _rows("SELECT enabled, server_id, channel_id, scope, mention_role_id, since, updated_at FROM patchnote_settings WHERE id = 1")
    if not rows:
        return {"enabled": False, "server_id": None, "channel_id": None, "scope": "both", "mention_role_id": None,
                "since": None, "updated_at": None}
    enabled, server, channel, scope, role, since, at = rows[0]
    return {"enabled": bool(enabled), "server_id": str(server) if server else None, "channel_id": str(channel) if channel else None,
            "scope": scope if scope in SCOPES else "both", "mention_role_id": str(role) if role else None,
            "since": since, "updated_at": at}


def save_settings(form: dict, by: int) -> str | None:
    """None when saved, else "server", "channel" or "error". Turning them on starts from now: nothing old is posted."""
    from app import server_admin as sa

    enabled = form.get("enabled") == "1"
    server = form.get("server_id") or ""
    channel = form.get("channel_id") or ""
    role = form.get("mention_role_id") or ""
    scope = form.get("scope") if form.get("scope") in SCOPES else "both"
    present = {s["server_id"] for s in servers()}
    if server and server not in present:
        return "server"
    known_channels = {c["id"] for c in sa.channels(int(server))} if server else set()
    if channel and channel not in known_channels:
        return "channel"
    if enabled and not (server and channel):
        return "channel"
    known_roles = {r["id"] for r in sa.roles(int(server)) if not r["managed"]} if server else set()
    role = role if role in known_roles else ""
    before = get_settings()
    since = before["since"] if before["enabled"] and enabled and before["since"] else (_now() if enabled else None)
    try:
        db.execute_sql(
            "INSERT INTO patchnote_settings (id, enabled, server_id, channel_id, scope, mention_role_id, since, updated_at, updated_by) "
            "VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET enabled = EXCLUDED.enabled, "
            "server_id = EXCLUDED.server_id, channel_id = EXCLUDED.channel_id, scope = EXCLUDED.scope, "
            "mention_role_id = EXCLUDED.mention_role_id, since = EXCLUDED.since, updated_at = EXCLUDED.updated_at, "
            "updated_by = EXCLUDED.updated_by",
            (enabled, int(server) if server else None, int(channel) if channel else None, scope, int(role) if role else None,
             since, _now(), int(by)))
    except Exception:
        db.rollback()
        return "error"
    return None


def request_post(component: str) -> str | None:
    """Asks the bot to post (again) the latest version of the website or of the bot. None when asked, else
    "component", "settings", "none" or "wait"."""
    if component not in COMPONENTS:
        return "component"
    settings = get_settings()
    if not (settings["server_id"] and settings["channel_id"]):
        return "settings"
    if _rows("SELECT 1 FROM patchnotes WHERE requested_at > %s", (_now() - timedelta(seconds=TEST_COOLDOWN_SECONDS),)):
        return "wait"
    latest = _rows("SELECT id FROM patchnotes WHERE component = %s ORDER BY id DESC LIMIT 1", (component,))
    # a test of a baseline entry is a deliberate post: it stops being baseline
    if not latest:
        return "none"
    try:
        db.execute_sql("UPDATE patchnotes SET requested_at = %s, posted_at = NULL, ok = NULL, detail = NULL, baseline = FALSE WHERE id = %s",
                       (_now(), latest[0][0]))
    except Exception:
        db.rollback()
        return "none"
    return None


def servers() -> list[dict]:
    """Servers the bot is on (the official one is among them)."""
    return [{"server_id": str(sid), "name": name or f"#{sid}"} for sid, name in _rows(
        "SELECT m.server_id, s.servername FROM guild_meta m LEFT JOIN servers s ON s.server_id = m.server_id "
        "WHERE m.bot_present ORDER BY LOWER(COALESCE(s.servername, ''))")]


def latest_versions() -> dict:
    """{component: latest version known} (what "Post the latest version now" would post)."""
    out = {}
    for component, version, title in _rows(
            "SELECT DISTINCT ON (component) component, version, title FROM patchnotes ORDER BY component, id DESC"):
        out[component] = {"version": version, "title": title}
    return out


def history(limit: int = 15) -> list[dict]:
    """Versions posted, waiting or failed, newest first."""
    settings = get_settings()
    rows = _rows(
        "SELECT component, version, title, created_at, requested_at, posted_at, ok, detail FROM patchnotes "
        "WHERE NOT baseline AND (posted_at IS NOT NULL OR requested_at IS NOT NULL OR (%s AND created_at >= %s)) "
        "ORDER BY COALESCE(posted_at, requested_at, created_at) DESC LIMIT %s",
        (bool(settings["enabled"] and settings["since"]), settings["since"] or _now(), limit))
    return [{"component": c, "version": v, "title": t, "created_at": ca.isoformat(timespec="seconds") if ca else None,
             "posted_at": pa.isoformat(timespec="seconds") if pa else None, "requested": bool(ra),
             "requested_at": ra.isoformat(timespec="seconds") if ra else None, "ok": ok, "detail": detail or ""}
            for c, v, t, ca, ra, pa, ok, detail in rows]
