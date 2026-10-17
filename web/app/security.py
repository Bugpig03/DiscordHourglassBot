"""HTTP security layer: Content-Security-Policy with per-request nonces, security headers,
CSRF tokens for state-changing forms and a lightweight per-IP rate limiter."""

import hmac
import ipaddress
import logging
import os
import secrets
import threading
import time
from collections import deque

from flask import g, jsonify, request, session

log = logging.getLogger(__name__)

# Origins the pages legitimately load from (Chart.js and its date adapter, Discord avatars/icons)
SCRIPT_CDN = "https://cdn.jsdelivr.net"
IMAGE_HOSTS = "https://cdn.discordapp.com https://media.discordapp.net"

# Requests per minute and per client IP. Counters live in each Gunicorn worker: with 4 workers the
# effective ceiling is up to 4x higher, which is fine for abuse protection (not exact quotas).
RATE_LIMITS = [
    ("/api/card/", 30),
    ("/api/search", 90),
    ("/api/", 120),
    ("/auth/", 30),
    ("/server/", 120),
    ("/me/", 60),  # includes /server/<id>/members ("Voir plus" and live member search)
]
RATE_WINDOW_SECONDS = 60


def csp_nonce() -> str:
    """Nonce allowing this response's own inline <script> blocks."""
    if not hasattr(g, "csp_nonce"):
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def csrf_token() -> str:
    """Per-session token embedded in POST forms (logout)."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def valid_csrf(submitted: str | None) -> bool:
    expected = session.get("csrf_token")
    return bool(expected and submitted and hmac.compare_digest(expected, submitted))


def build_csp() -> str:
    directives = [
        "default-src 'self'",
        f"script-src 'self' 'nonce-{csp_nonce()}' {SCRIPT_CDN}",
        # Templates still use inline style attributes; scripts are what CSP needs to lock down
        "style-src 'self' 'unsafe-inline'",
        f"img-src 'self' data: {IMAGE_HOSTS}",
        "connect-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    if request.is_secure:
        directives.append("upgrade-insecure-requests")
    return "; ".join(directives)


class RateLimiter:
    """Sliding-window counter per (client IP, rule) kept in memory, thread-safe."""

    def __init__(self):
        self._hits: dict[tuple[str, str], deque] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()
        self._warned_no_client_ip = False

    def client_ip(self) -> str | None:
        """Visitor IP as seen by the reverse proxy; None when it cannot be told apart from the proxy."""
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            return real_ip
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            # The proxy appends the address it received the request from: the right-most entry
            return forwarded.split(",")[-1].strip()
        remote = request.remote_addr or ""
        try:
            if ipaddress.ip_address(remote).is_private and not ipaddress.ip_address(remote).is_loopback:
                # Behind a proxy that forwards no client IP: every visitor would share one bucket
                if not self._warned_no_client_ip:
                    log.warning("Rate limiting disabled: proxy sends neither X-Real-IP nor X-Forwarded-For")
                    self._warned_no_client_ip = True
                return None
        except ValueError:
            pass
        return remote or None

    def check(self) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds) for the current request."""
        rule = next(((prefix, limit) for prefix, limit in RATE_LIMITS if request.path.startswith(prefix)), None)
        if rule is None:
            return True, 0
        ip = self.client_ip()
        if ip is None:
            return True, 0

        now = time.monotonic()
        key = (ip, rule[0])
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > RATE_WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= rule[1]:
                return False, max(1, int(RATE_WINDOW_SECONDS - (now - hits[0])) + 1)
            hits.append(now)
            if now - self._last_sweep > RATE_WINDOW_SECONDS:
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > RATE_WINDOW_SECONDS]:
                    del self._hits[k]
                self._last_sweep = now
        return True, 0


def init_security(app) -> None:
    limiter = RateLimiter()
    report_only = os.environ.get("CSP_REPORT_ONLY", "false").lower() in ("1", "true", "yes")

    @app.before_request
    def _rate_limit():
        allowed, retry_after = limiter.check()
        if allowed:
            return None
        message = "Trop de requêtes, réessayez dans quelques secondes." if request.cookies.get("lang", "fr") == "fr" \
            else "Too many requests, please retry in a few seconds."
        response = jsonify({"error": "rate_limited", "message": message}) if request.path.startswith("/api/") \
            else app.response_class(message, mimetype="text/plain")
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        if response.mimetype == "text/html":
            response.headers.setdefault("X-Frame-Options", "DENY")
            header = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
            response.headers[header] = build_csp()
        return response

    @app.context_processor
    def _security_context():
        return {"csp_nonce": csp_nonce, "csrf_token": csrf_token}
