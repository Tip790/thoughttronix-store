"""Forgot password: the request page, the emailed link, and what a
completed reset does."""

import re
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

NEW_PASSWORD = "fresh-synapse-4242"


@pytest.fixture
def casey(customer):
    """An unconfirmed customer with an email on file."""
    customer.email = "casey@example.com"
    customer.save()
    return customer


def request_reset(client, email):
    return client.post(
        reverse("accounts:password_reset"), {"email": email}, follow=True
    )


def link_in(message):
    """The reset link's path, pulled out of an email body."""
    return re.search(r"https?://[^/]+(/\S+)", message.body).group(1)


def reset_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("accounts:password_reset_confirm", args=[uid, token])


def set_new_password(client, link):
    """Open ``link`` and submit a new password, as the customer would."""
    form_page = client.get(link, follow=True)
    set_password_url = form_page.redirect_chain[-1][0]
    return client.post(
        set_password_url,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        follow=True,
    )


# --- The request page --------------------------------------------------------


def test_the_sign_in_page_links_to_password_reset(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert reverse("accounts:password_reset") in page


def without_csrf(response):
    """The page with its CSRF token blanked; Django masks the token
    differently on every response, even for the same visitor."""
    return response.content.decode().replace(str(response.context["csrf_token"]), "")


def test_known_and_unknown_emails_get_identical_responses(client, casey, mailoutbox):
    known = request_reset(client, "casey@example.com")
    unknown = request_reset(client, "nobody@example.com")

    assert known.redirect_chain == unknown.redirect_chain
    assert known.redirect_chain[-1][0] == reverse("accounts:password_reset_done")
    assert without_csrf(known) == without_csrf(unknown)
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["casey@example.com"]


def test_the_confirmation_suggests_checking_spam_and_the_email_used(client, db):
    page = request_reset(client, "nobody@example.com").content.decode()

    assert "If an account uses that email" in page
    assert "spam folder" in page
    assert "email on your account" in page


def test_the_email_matches_ignoring_capitalization(client, casey, mailoutbox):
    request_reset(client, "Casey@Example.COM")

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["casey@example.com"]


def test_an_unconfirmed_email_still_gets_a_reset_link(client, casey, mailoutbox):
    assert not casey.email_verified

    request_reset(client, "casey@example.com")

    assert len(mailoutbox) == 1
    assert "/accounts/password/reset/" in mailoutbox[0].body
    assert "\n" not in mailoutbox[0].subject
    assert mailoutbox[0].from_email == settings.DEFAULT_FROM_EMAIL


def test_accounts_without_a_usable_password_get_no_link(client, casey, mailoutbox):
    casey.set_unusable_password()
    casey.save()

    request_reset(client, "casey@example.com")

    assert mailoutbox == []


def test_inactive_accounts_get_no_link(client, casey, mailoutbox):
    casey.is_active = False
    casey.save()

    request_reset(client, "casey@example.com")

    assert mailoutbox == []


# --- The link ----------------------------------------------------------------


def test_the_emailed_link_resets_the_password(client, casey, mailoutbox):
    request_reset(client, "casey@example.com")

    set_new_password(client, link_in(mailoutbox[0]))

    casey.refresh_from_db()
    assert casey.check_password(NEW_PASSWORD)


def test_a_used_link_is_refused(client, casey):
    link = reset_link(casey)
    set_new_password(client, link)

    page = client.get(link, follow=True)

    assert not page.context["validlink"]
    assert "can't be used" in page.content.decode()


def issued_at(moment):
    """Make tokens as though it were ``moment``."""
    return mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=moment)


def test_an_expired_link_is_refused(client, casey):
    timeout = timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
    with issued_at(datetime.now() - timeout - timedelta(minutes=1)):
        link = reset_link(casey)

    page = client.get(link, follow=True)

    assert not page.context["validlink"]


def test_a_link_inside_its_lifetime_still_works(client, casey):
    timeout = timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
    with issued_at(datetime.now() - timeout + timedelta(minutes=1)):
        link = reset_link(casey)

    page = client.get(link, follow=True)

    assert page.context["validlink"]


def test_a_tampered_link_is_refused(client, casey):
    page = client.get(reset_link(casey)[:-3] + "xx/", follow=True)

    assert not page.context["validlink"]


# --- A completed reset -------------------------------------------------------


def test_a_reset_confirms_an_unconfirmed_email(client, casey):
    set_new_password(client, reset_link(casey))

    casey.refresh_from_db()
    assert casey.email_verified


def test_a_reset_sends_a_password_changed_notice(client, casey, mailoutbox):
    set_new_password(client, reset_link(casey))

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["casey@example.com"]
    assert "password was changed" in notice.subject
    assert reverse("accounts:password_reset") in notice.body


def test_a_reset_sends_you_to_sign_in_without_signing_you_in(client, casey):
    response = set_new_password(client, reset_link(casey))

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert not response.context["user"].is_authenticated
    assert "Sign in with your new one" in response.content.decode()


def test_the_new_password_signs_in_and_the_old_one_does_not(client, casey):
    set_new_password(client, reset_link(casey))

    assert not client.login(username="customer", password="customer123")
    assert client.login(username="customer", password=NEW_PASSWORD)


def test_a_seeded_style_customer_can_reset_straight_away(client, casey, mailoutbox):
    """Seeded users have a confirmed email and a real password."""
    casey.email_verified = True
    casey.save()

    request_reset(client, "casey@example.com")
    response = set_new_password(client, link_in(mailoutbox[0]))

    assert response.status_code == HTTPStatus.OK
    assert client.login(username="customer", password=NEW_PASSWORD)
