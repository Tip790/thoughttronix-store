"""Sign-in hardening: "Remember me", the sign-in throttle, and the cap on
reset and confirmation emails."""

import time
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse

from .tests import SIGNUP

THROTTLED = "Too many sign-in attempts — try again later."


@pytest.fixture
def casey(customer):
    """An unconfirmed customer with an email on file."""
    customer.email = "casey@example.com"
    customer.save()
    return customer


def sign_in(
    client, username="customer", password="customer123", ip="10.0.0.1", **extra
):
    return client.post(
        reverse("accounts:login"),
        {"username": username, "password": password, **extra},
        REMOTE_ADDR=ip,
    )


def is_signed_in(client):
    return "_auth_user_id" in client.session


def session_cookie(client):
    return client.cookies[settings.SESSION_COOKIE_NAME]


# --- Remember me -------------------------------------------------------------


def test_the_sign_in_form_offers_remember_me_unchecked(client, db):
    form = client.get(reverse("accounts:login")).context["form"]

    assert "remember_me" in form.fields
    assert 'name="remember_me"' in str(form["remember_me"])
    assert "checked" not in str(form["remember_me"])


def test_without_remember_me_the_session_ends_with_the_browser(client, customer):
    sign_in(client)

    assert client.session.get_expire_at_browser_close()
    assert session_cookie(client)["max-age"] == ""


def test_with_remember_me_the_session_lasts_two_weeks(client, customer):
    sign_in(client, remember_me="on")

    assert not client.session.get_expire_at_browser_close()
    assert client.session.get_expiry_age() == settings.SESSION_COOKIE_AGE
    assert session_cookie(client)["max-age"] == settings.SESSION_COOKIE_AGE


def test_signing_up_gives_a_browser_session(client, db):
    client.post(reverse("accounts:signup"), SIGNUP)

    assert is_signed_in(client)
    assert client.session.get_expire_at_browser_close()
    assert session_cookie(client)["max-age"] == ""


# --- The sign-in throttle ----------------------------------------------------


def test_five_failures_for_one_username_lock_it_out(client, customer):
    for n in range(5):
        sign_in(client, password="wrong", ip=f"10.0.0.{n}")

    response = sign_in(client, ip="10.0.0.99")

    assert THROTTLED in response.content.decode()
    assert not is_signed_in(client)


def test_four_failures_still_let_the_right_password_in(client, customer):
    for n in range(4):
        sign_in(client, password="wrong", ip=f"10.0.0.{n}")

    sign_in(client, ip="10.0.0.99")

    assert is_signed_in(client)


def test_five_failures_from_one_ip_lock_out_every_username(client, customer):
    for n in range(5):
        sign_in(client, username=f"guess-{n}", password="wrong", ip="10.0.0.7")

    response = sign_in(client, ip="10.0.0.7")

    assert THROTTLED in response.content.decode()
    assert not is_signed_in(client)
    # The username itself isn't locked: from elsewhere it still signs in.
    sign_in(client, ip="10.0.0.8")
    assert is_signed_in(client)


def test_a_successful_sign_in_does_not_clear_the_ip_counter(client, customer):
    for n in range(4):
        sign_in(client, username=f"guess-{n}", password="wrong", ip="10.0.0.7")
    sign_in(client, ip="10.0.0.7")
    assert is_signed_in(client)
    client.post(reverse("accounts:logout"))

    sign_in(client, username="guess-4", password="wrong", ip="10.0.0.7")
    response = sign_in(client, ip="10.0.0.7")

    assert THROTTLED in response.content.decode()


def test_a_successful_sign_in_clears_the_username_counter(client, customer):
    for n in range(4):
        sign_in(client, password="wrong", ip=f"10.0.0.{n}")
    sign_in(client, ip="10.0.1.0")
    client.post(reverse("accounts:logout"))

    for n in range(4):
        sign_in(client, password="wrong", ip=f"10.0.2.{n}")
    sign_in(client, ip="10.0.3.0")

    assert is_signed_in(client)


def test_the_lockout_lifts_once_the_window_passes(client, customer):
    for n in range(5):
        sign_in(client, password="wrong", ip=f"10.0.0.{n}")
    later = time.time() + settings.SIGN_IN_THROTTLE_WINDOW + 1

    with mock.patch("django.core.cache.backends.locmem.time.time", return_value=later):
        sign_in(client, ip="10.0.0.99")
        assert is_signed_in(client)


def test_the_sign_in_limit_comes_from_settings(client, customer, settings):
    settings.SIGN_IN_THROTTLE_LIMIT = 2
    for n in range(2):
        sign_in(client, password="wrong", ip=f"10.0.0.{n}")

    response = sign_in(client, ip="10.0.0.99")

    assert THROTTLED in response.content.decode()


# --- The email cap -----------------------------------------------------------


def request_reset(client, email="casey@example.com"):
    return client.post(
        reverse("accounts:password_reset"), {"email": email}, follow=True
    )


def without_csrf(response):
    return response.content.decode().replace(str(response.context["csrf_token"]), "")


def test_a_fourth_reset_request_in_the_hour_sends_nothing(client, casey, mailoutbox):
    responses = [request_reset(client) for _ in range(4)]

    assert len(mailoutbox) == 3
    assert responses[3].redirect_chain == responses[2].redirect_chain
    assert without_csrf(responses[3]) == without_csrf(responses[2])


def test_the_reset_cap_matches_emails_ignoring_case(client, casey, mailoutbox):
    for email in ["casey@example.com", "CASEY@example.com", "Casey@Example.com"]:
        request_reset(client, email)

    request_reset(client, "casey@EXAMPLE.com")

    assert len(mailoutbox) == 3


def test_a_fourth_confirmation_link_in_the_hour_sends_nothing(
    client, casey, mailoutbox
):
    client.force_login(casey)
    for _ in range(3):
        client.post(reverse("accounts:resend_verification"), follow=True)

    response = client.post(reverse("accounts:resend_verification"), follow=True)

    assert len(mailoutbox) == 3
    [message] = response.context["messages"]
    assert message.level_tag == "warning"
    assert "try again in an hour" in message.message


def test_used_up_confirmation_links_do_not_block_a_reset(client, casey, mailoutbox):
    client.force_login(casey)
    for _ in range(4):
        client.post(reverse("accounts:resend_verification"))
    client.post(reverse("accounts:logout"))

    request_reset(client)

    assert len(mailoutbox) == 4
    assert "reset" in mailoutbox[-1].subject.lower()


def test_the_email_limit_comes_from_settings(client, casey, mailoutbox, settings):
    settings.EMAIL_THROTTLE_LIMIT = 1

    request_reset(client)
    request_reset(client)

    assert len(mailoutbox) == 1
