"""A small cache-based throttle for sign-in failures and account emails.

Each counter is a cache entry that starts at the first hit and expires a
fixed window later, so a blocked username, IP, or address is free again
once that window passes. Limits and windows are read from settings at
call time, so tests and deployments can tune them:

- ``SIGN_IN_THROTTLE_LIMIT`` failures per ``SIGN_IN_THROTTLE_WINDOW``
  seconds, counted per username and per IP address;
- ``EMAIL_THROTTLE_LIMIT`` emails per ``EMAIL_THROTTLE_WINDOW`` seconds,
  counted per address and per kind (reset links, confirmation links).

The default cache is per-process local memory: enough for one server,
and every counter resets when the server restarts.
"""

import hashlib

from django.conf import settings
from django.core.cache import cache


def _key(scope: str, identifier: str) -> str:
    # Hashed so any username or address makes a safe cache key.
    digest = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
    return f"accounts.throttle:{scope}:{digest}"


def _count(scope: str, identifier: str) -> int:
    return cache.get(_key(scope, identifier), 0)


def _hit(scope: str, identifier: str, window: int) -> int:
    """Count one more hit, starting the window on the first, and return
    the new count. ``incr`` keeps the entry's original expiry."""
    key = _key(scope, identifier)
    cache.add(key, 0, timeout=window)
    try:
        return cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, timeout=window)
        return 1


# --- Sign-in -----------------------------------------------------------------


def sign_in_blocked(username: str, ip: str | None) -> bool:
    """Whether sign-in is refused, for too many recent failures against
    ``username`` or from ``ip``."""
    limit = settings.SIGN_IN_THROTTLE_LIMIT
    return _count("sign-in-user", username) >= limit or (
        bool(ip) and _count("sign-in-ip", ip) >= limit
    )


def record_sign_in_failure(username: str, ip: str | None) -> None:
    """Count a failed sign-in against both ``username`` and ``ip``."""
    window = settings.SIGN_IN_THROTTLE_WINDOW
    _hit("sign-in-user", username, window)
    if ip:
        _hit("sign-in-ip", ip, window)


def clear_sign_in_failures(username: str) -> None:
    """Forget ``username``'s failures after it signs in. The IP counter
    stays, so one good account can't launder guesses at others."""
    cache.delete(_key("sign-in-user", username))


# --- Emails ------------------------------------------------------------------


def allow_email(kind: str, address: str) -> bool:
    """Count one ``kind`` email to ``address`` and say whether it may be
    sent — ``False`` once the address has had its share this window."""
    count = _hit(f"email-{kind}", address, settings.EMAIL_THROTTLE_WINDOW)
    return count <= settings.EMAIL_THROTTLE_LIMIT
