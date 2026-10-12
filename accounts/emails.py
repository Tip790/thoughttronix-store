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
    """Render the ``name`` template pair with ``context`` and send it to ``to``."""
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
