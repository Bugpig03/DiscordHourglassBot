"""Votes for Hourglass on top.gg: received by webhook in real time, and caught up from the top.gg API every hour.

Table topgg_votes (web side only), one row per vote: the voter's Discord ID, when they voted, when they can vote
again (12 h later) and the weight (2 on weekends; the Supporter badge counts votes, not weight). A vote sent twice
(webhook retry, then the hourly catch-up) is stored once: the key is (user_id, created_at to the second).

Environment:
  - TOPGG_WEBHOOK_SECRET: signing secret of the top.gg webhook (whs_..., v1), or the Authorization value of a
    legacy (v0) webhook. The endpoint refuses everything while it is not set.
  - TOPGG_TOKEN: API token of the project (Integrations & API), to fetch the vote history; optional.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import Blueprint, current_app, jsonify, request
from peewee import DatabaseError

from app.cache import cache
from app.database import create_tables, db

log = logging.getLogger(__name__)

BOT_ID = "1210665993328926750"
VOTE_URL = f"https://top.gg/bot/{BOT_ID}/vote"
API_BASE = "https://top.gg/api/v1"
SYNC_SECONDS = 3600
SYNC_LOCK_ID = 727302
SIGNATURE_MAX_AGE = 600  # seconds: an older signed request is a replay
# A member's votes are kept this long per Gunicorn worker. Short on purpose: the webhook reaches one worker only,
# the 3 others would show the old count until it runs out (a vote seemed to come and go between refreshes).
# The query reads the primary key (user_id first), so it stays cheap without a longer cache.
CACHE_SECONDS = 5

TABLE = ("CREATE TABLE IF NOT EXISTS topgg_votes (user_id BIGINT NOT NULL, created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, "
         "expires_at TIMESTAMP WITHOUT TIME ZONE, weight SMALLINT NOT NULL DEFAULT 1, source VARCHAR(8) NOT NULL, "
         "PRIMARY KEY (user_id, created_at))")
INDEXES = ["CREATE INDEX IF NOT EXISTS topgg_votes_created ON topgg_votes (created_at)"]
INSERT = ("INSERT INTO topgg_votes (user_id, created_at, expires_at, weight, source) VALUES (%s, %s, %s, %s, %s) "
          "ON CONFLICT (user_id, created_at) DO NOTHING")

webhooks_bp = Blueprint("webhooks", __name__)
_enabled = True
_thread_started = False


def ensure_table() -> None:
    global _enabled
    # Retried: the 4 workers start together and race on CREATE TABLE IF NOT EXISTS for a new table
    error = create_tables([TABLE, *INDEXES])
    if error is not None:
        _enabled = False
        log.warning("top.gg votes disabled (table unavailable, run the web migrations): %s", error)


def _parse_time(value) -> datetime | None:
    """ISO 8601 from top.gg (with 7 decimals and an offset) -> naive UTC, to the second."""
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    if "." in text:  # Python wants at most 6 decimals
        head, rest = text.split(".", 1)
        digits = "".join(ch for ch in rest if ch.isdigit())
        text = head + "." + digits[:6] + rest[len(digits):]
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def record_vote(user_id, created_at: datetime, expires_at: datetime | None, weight: int, source: str) -> bool:
    """Store one vote (ignored if already known). True when the database accepted it."""
    if not _enabled or not str(user_id).isdigit() or not created_at:
        return False
    try:
        with db.connection_context():
            db.execute_sql(INSERT, (int(user_id), created_at, expires_at, max(1, int(weight or 1)), source))
        cache.delete(("topgg_votes", int(user_id)))
        return True
    except (DatabaseError, ValueError) as e:
        log.warning("Could not store a top.gg vote: %s", e)
        return False


def user_votes(user_id) -> dict:
    """{"total": votes, "last": datetime, "active": voted less than 12 h ago, "next": when they can vote again}."""
    empty = {"total": 0, "last": None, "active": False, "next": None}
    if not _enabled or not str(user_id).isdigit():
        return empty

    def load():
        try:
            row = db.execute_sql("SELECT COUNT(*), MAX(created_at), MAX(expires_at) FROM topgg_votes WHERE user_id = %s",
                                 (int(user_id),)).fetchone()
        except DatabaseError:
            db.rollback()
            return empty
        total, last, expires = row
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires = expires or (last + timedelta(hours=12) if last else None)
        return {"total": int(total or 0), "last": last, "active": bool(expires and expires > now), "next": expires}

    return cache.get_or_set(("topgg_votes", int(user_id)), CACHE_SECONDS, load)


def vote_totals() -> dict:
    """{user_id: votes since the start}, every member at once (search, disambiguation, server members)."""
    if not _enabled:
        return {}

    def load():
        try:
            rows = db.execute_sql("SELECT user_id, COUNT(*) FROM topgg_votes GROUP BY user_id").fetchall()
        except DatabaseError:
            db.rollback()
            return {}
        return {int(uid): int(n) for uid, n in rows}

    return cache.get_or_set(("topgg_votes", "totals"), CACHE_SECONDS, load)


def vote_counts(start: datetime | None, prev_start: datetime | None, prev_end: datetime) -> dict:
    """{user_id: (votes since start, votes between prev_start and prev_end)} for the members page (sort by votes).
    A start of None counts every vote."""
    if not _enabled:
        return {}
    oldest = datetime(1970, 1, 1)
    try:
        rows = db.execute_sql(
            "SELECT user_id, COUNT(*) FILTER (WHERE created_at >= %s), "
            "COUNT(*) FILTER (WHERE created_at >= %s AND created_at < %s) FROM topgg_votes GROUP BY user_id",
            (start or oldest, prev_start or oldest, prev_end)).fetchall()
    except DatabaseError:
        db.rollback()
        return {}
    return {int(uid): (int(cur), int(prev)) for uid, cur, prev in rows}


# ------------------------------------------------------------------------------
# Webhook
# ------------------------------------------------------------------------------

def _signature_ok(secret: str, raw: bytes) -> bool:
    """v1: x-topgg-signature "t=<unix>,v1=<hex HMAC-SHA256 of '<t>.<raw body>'>"; v0: Authorization == secret."""
    header = request.headers.get("x-topgg-signature", "")
    if header:
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        stamp, given = parts.get("t", ""), parts.get("v1", "")
        if not stamp.isdigit() or not given or abs(time.time() - int(stamp)) > SIGNATURE_MAX_AGE:
            return False
        expected = hmac.new(secret.encode(), f"{stamp}.".encode() + raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, given)
    auth = request.headers.get("Authorization", "")
    return bool(auth) and hmac.compare_digest(auth.encode(), secret.encode())


@webhooks_bp.route("/webhooks/topgg", methods=["POST"])
def topgg_webhook():
    """Vote notifications from top.gg (v1 vote.create / webhook.test, or legacy v0 upvote / test)."""
    from app.security_log import record as security_event
    secret = (current_app.config.get("TOPGG_WEBHOOK_SECRET") or os.environ.get("TOPGG_WEBHOOK_SECRET", "")).strip()
    raw = request.get_data(cache=False)
    if not secret or not _signature_ok(secret, raw):
        security_event("webhook_fail", "top.gg : signature absente ou fausse" if secret else "top.gg : TOPGG_WEBHOOK_SECRET non défini")
        return jsonify({"error": "unauthorized"}), 401
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return jsonify({"error": "bad json"}), 400

    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    kind = payload.get("type")
    if kind == "vote.create":
        data = payload.get("data") or {}
        user = (data.get("user") or {}).get("platform_id")
        created = _parse_time(data.get("created_at")) or now
        record_vote(user, created, _parse_time(data.get("expires_at")), data.get("weight") or 1, "webhook")
    elif kind == "upvote":  # legacy v0
        record_vote(payload.get("user"), now, now + timedelta(hours=12), 2 if payload.get("isWeekend") else 1, "webhook")
    elif kind in ("webhook.test", "test"):
        log.info("top.gg test webhook received")
    return "", 204


# ------------------------------------------------------------------------------
# Hourly catch-up from the API (and the vote history on first run)
# ------------------------------------------------------------------------------

def sync_history(force: bool = False) -> int:
    """Fetch the votes since the last sync (one year back on the first run). Returns how many were new."""
    token = os.environ.get("TOPGG_TOKEN", "").strip()
    if not _enabled or not token:
        return 0
    added = 0
    with db.connection_context():
        with db.atomic():
            if not db.execute_sql("SELECT pg_try_advisory_xact_lock(%s)", (SYNC_LOCK_ID,)).fetchone()[0]:
                return 0
            row = db.execute_sql("SELECT value FROM web_settings WHERE key = 'topgg_votes_synced_at'").fetchone() \
                if db.execute_sql("SELECT to_regclass('web_settings')").fetchone()[0] else None
            last = _parse_time(row[0]) if row else None
            now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
            if last and not force and now - last < timedelta(seconds=SYNC_SECONDS - 300):
                return 0
            start = (last - timedelta(days=1)) if last else now - timedelta(days=364)
            auth = token if token.lower().startswith("bearer ") else f"Bearer {token}"
            params = {"startDate": start.isoformat() + "Z"}
            for _ in range(200):  # pages of votes, oldest first
                resp = requests.get(f"{API_BASE}/projects/@me/votes", params=params, headers={"Authorization": auth}, timeout=15)
                if resp.status_code != 200:
                    log.warning("top.gg votes sync: HTTP %s %s", resp.status_code, resp.text[:200])
                    return added
                body = resp.json()
                votes = body.get("data") or []
                if not votes:
                    break
                cursor = db.cursor()
                for v in votes:
                    created = _parse_time(v.get("created_at"))
                    if str(v.get("platform_id", "")).isdigit() and created:
                        cursor.execute(INSERT, (int(v["platform_id"]), created, _parse_time(v.get("expires_at")),
                                                max(1, int(v.get("weight") or 1)), "api"))
                        added += cursor.rowcount or 0
                if not body.get("cursor"):
                    break
                params = {"cursor": body["cursor"]}
            db.execute_sql("CREATE TABLE IF NOT EXISTS web_settings (key VARCHAR(64) PRIMARY KEY, value TEXT NOT NULL)")
            db.execute_sql("INSERT INTO web_settings (key, value) VALUES ('topgg_votes_synced_at', %s) "
                           "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (now.isoformat(),))
    if added:
        log.info("top.gg votes sync: %d new vote(s)", added)
    return added


def init_topgg_votes(app) -> None:
    global _thread_started
    ensure_table()
    app.register_blueprint(webhooks_bp)
    if not _enabled or _thread_started or app.config.get("TESTING"):
        return
    _thread_started = True

    def loop():
        time.sleep(60)
        while True:
            try:
                sync_history()
            except Exception as e:  # never break the worker for the votes
                log.warning("top.gg votes sync failed: %s", e)
            time.sleep(SYNC_SECONDS)

    threading.Thread(target=loop, name="topgg-votes", daemon=True).start()
