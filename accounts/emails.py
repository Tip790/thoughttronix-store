"""The account emails: plain text, rendered from ``templates/accounts/email/``.

Each email is a pair of templates, ``<name>_subject.txt`` and
``<name>.txt``. Links are built from the request, so they point at
whichever host the customer is using.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from .tokens import make_verification_token


def send_account_email(name, to, context):
    """Render the ``name`` template pair with ``context`` and send it to ``to``.

    Users made before sign-up required an email may have none; there's
    nobody to tell, so nothing is sent.
    """
    if not to:
        return
    subject = render_to_string(f"accounts/email/{name}_subject.txt", context)
    body = render_to_string(f"accounts/email/{name}.txt", context)
    # A subject must be one line; templates end with a newline.
    send_mail(" ".join(subject.split()), body, None, [to])


def send_verification_email(request, user):
    """Send ``user`` a link that confirms their current email address."""
    path = reverse("accounts:verify_email", args=[make_verification_token(user)])
    send_account_email(
        "verify_email",
        user.email,
        {"user": user, "verify_url": request.build_absolute_uri(path)},
    )


def send_password_changed_email(request, user):
    """Tell ``user`` their password just changed, with a way back in if
    it wasn't them."""
    path = reverse("accounts:password_reset")
    send_account_email(
        "password_changed",
        user.email,
        {"user": user, "reset_url": request.build_absolute_uri(path)},
    )


def send_email_changed_email(user, old_email):
    """Tell ``old_email`` that ``user``'s email moved away from it, so the
    real owner hears about a hijack at the address they still read.

    There's no reset link here: reset links now go to the new address,
    so one would only help whoever made the change.
    """
    send_account_email(
        "email_changed", old_email, {"user": user, "old_email": old_email}
    )
