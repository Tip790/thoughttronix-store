"""Signed, time-limited email verification links.

A token carries the user's pk and the email it was sent to, signed with
``SECRET_KEY``. It lives as long as a password reset link
(``PASSWORD_RESET_TIMEOUT``, 3 days) and only verifies while the account's
email is still the one it was sent for — change the email and every
older link goes stale.
"""

from django.conf import settings
from django.core import signing

from .models import User

SALT = "accounts.email-verification"


def make_verification_token(user: User) -> str:
    """A token that verifies ``user``'s current email."""
    return signing.dumps({"user": user.pk, "email": user.email}, salt=SALT)


def user_for_verification_token(token: str) -> User | None:
    """The user ``token`` verifies, or ``None`` if it is expired,
    tampered with, or was sent to an email the account no longer has."""
    try:
        data = signing.loads(token, salt=SALT, max_age=settings.PASSWORD_RESET_TIMEOUT)
    except signing.BadSignature:  # SignatureExpired is a BadSignature too
        return None
    return (
        User.objects.filter(pk=data["user"], email=data["email"])
        .exclude(email="")
        .first()
    )
