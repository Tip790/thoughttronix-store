"""Email confirmation: the sign-up email, the link, the Account page, and
the email settings."""

import importlib.util
import io
import re
import time
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse

from orders.models import Order
from orders.test_checkout_form import VALID_DATA

from .mail import ConsoleEmailBackend
from .tests import SIGNUP
from .tokens import make_verification_token, user_for_verification_token


@pytest.fixture
def unverified(customer):
    customer.email = "casey@example.com"
    customer.save()
    return customer


def link_in(message):
    """The confirmation link's path, pulled out of an email body."""
    return re.search(r"https?://[^/]+(/\S+)", message.body).group(1)


# --- Sign-up sends the link ----------------------------------------------------


def test_signup_sends_one_confirmation_email(client, db, mailoutbox):
    response = client.post(reverse("accounts:signup"), SIGNUP, follow=True)

    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == ["fresh@example.com"]
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert "\n" not in message.subject
    assert "/accounts/email/verify/" in message.body
    assert "sent a link to fresh@example.com" in response.content.decode()


def test_new_customers_start_unconfirmed(client, db):
    client.post(reverse("accounts:signup"), SIGNUP)

    user = client.get(reverse("accounts:account")).context["user"]
    assert user.is_authenticated
    assert not user.email_verified


def test_the_emailed_link_confirms_the_email(client, db, mailoutbox):
    client.post(reverse("accounts:signup"), SIGNUP)
    path = link_in(mailoutbox[0])

    page = client.get(path)
    assert page.status_code == HTTPStatus.OK
    assert "fresh@example.com" in page.content.decode()

    response = client.post(path, follow=True)

    user = response.context["user"]
    user.refresh_from_db()
    assert user.email_verified
    assert response.redirect_chain[-1][0] == reverse("accounts:account")
    assert "fresh@example.com is confirmed" in response.content.decode()


# --- The link ----------------------------------------------------------------


def verify(client, token):
    return client.post(reverse("accounts:verify_email", args=[token]))


def test_opening_the_link_does_not_confirm_by_itself(client, unverified):
    client.get(
        reverse("accounts:verify_email", args=[make_verification_token(unverified)])
    )

    unverified.refresh_from_db()
    assert not unverified.email_verified


def test_the_link_works_signed_out(client, unverified):
    response = verify(client, make_verification_token(unverified))

    unverified.refresh_from_db()
    assert unverified.email_verified
    assert response.url == reverse("products:catalog")


def test_an_expired_link_does_not_confirm(client, unverified):
    issued = time.time() - settings.PASSWORD_RESET_TIMEOUT - 60
    with mock.patch("django.core.signing.time.time", return_value=issued):
        token = make_verification_token(unverified)

    response = verify(client, token)

    unverified.refresh_from_db()
    assert not unverified.email_verified
    assert "can't be used" in response.content.decode()


def test_a_link_inside_its_lifetime_still_works(unverified):
    issued = time.time() - settings.PASSWORD_RESET_TIMEOUT + 60
    with mock.patch("django.core.signing.time.time", return_value=issued):
        token = make_verification_token(unverified)

    assert user_for_verification_token(token) == unverified


def test_a_tampered_link_does_not_confirm(client, unverified, other_customer):
    token = make_verification_token(unverified)
    forged = token.replace(str(unverified.pk), str(other_customer.pk), 1)

    verify(client, forged)
    verify(client, token[:-2])

    unverified.refresh_from_db()
    assert not unverified.email_verified
    assert user_for_verification_token(forged) is None


def test_a_link_for_an_old_email_does_not_confirm(client, unverified):
    token = make_verification_token(unverified)
    unverified.email = "casey@new.example.com"
    unverified.save()

    verify(client, token)

    unverified.refresh_from_db()
    assert not unverified.email_verified


def test_a_link_for_a_blank_email_never_confirms(customer):
    assert customer.email == ""

    assert user_for_verification_token(make_verification_token(customer)) is None


# --- Confirmation never blocks shopping ---------------------------------------


def test_an_unconfirmed_customer_can_add_to_cart_and_check_out(
    client, unverified, product
):
    assert not unverified.email_verified
    client.force_login(unverified)

    client.post(reverse("orders:add", kwargs={"pk": product.pk}))
    response = client.post(reverse("orders:checkout"), VALID_DATA)

    order = Order.objects.get()
    assert order.user == unverified
    assert response.url == reverse("orders:confirmation", kwargs={"pk": order.pk})


# --- The Account page ---------------------------------------------------------


def test_account_page_requires_sign_in(client, db):
    response = client.get(reverse("accounts:account"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_account_page_shows_an_unconfirmed_email_with_resend(client, unverified):
    client.force_login(unverified)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "casey@example.com" in page
    assert "Not confirmed" in page
    assert reverse("accounts:resend_verification") in page


def test_account_page_shows_a_confirmed_email_without_resend(client, unverified):
    unverified.email_verified = True
    unverified.save()
    client.force_login(unverified)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "Confirmed" in page
    assert "Not confirmed" not in page
    assert reverse("accounts:resend_verification") not in page


def test_resend_sends_a_fresh_working_link(client, unverified, mailoutbox):
    client.force_login(unverified)

    response = client.post(reverse("accounts:resend_verification"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:account")
    assert "sent a new confirmation link" in response.content.decode()
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["casey@example.com"]

    client.post(link_in(mailoutbox[0]))
    unverified.refresh_from_db()
    assert unverified.email_verified


def test_resend_is_post_only(client, unverified, mailoutbox):
    client.force_login(unverified)

    response = client.get(reverse("accounts:resend_verification"))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert mailoutbox == []


def test_resend_sends_nothing_once_confirmed(client, unverified, mailoutbox):
    unverified.email_verified = True
    unverified.save()
    client.force_login(unverified)

    client.post(reverse("accounts:resend_verification"))

    assert mailoutbox == []


def test_resend_sends_nothing_without_an_email(client, customer, mailoutbox):
    client.force_login(customer)

    client.post(reverse("accounts:resend_verification"))

    assert mailoutbox == []


def test_navbar_links_signed_in_users_to_their_account(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:account") in page


def test_navbar_has_no_account_link_for_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert f'href="{reverse("accounts:account")}"' not in page


# --- Email settings -----------------------------------------------------------


def load_settings(monkeypatch, **environ):
    """A fresh copy of ``config/settings.py`` read under ``environ``."""
    for name in ("EMAIL_BACKEND", "EMAIL_HOST", "EMAIL_PORT", "DEFAULT_FROM_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    path = Path(settings.BASE_DIR) / "config" / "settings.py"
    spec = importlib.util.spec_from_file_location("settings_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_email_prints_to_the_console_by_default(monkeypatch):
    loaded = load_settings(monkeypatch)

    assert loaded.EMAIL_BACKEND == "accounts.mail.ConsoleEmailBackend"
    assert loaded.DEFAULT_FROM_EMAIL


def test_smtp_and_the_from_address_come_from_the_environment(monkeypatch):
    loaded = load_settings(
        monkeypatch,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_PORT="587",
        DEFAULT_FROM_EMAIL="Store <store@example.com>",
    )

    assert loaded.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
    assert loaded.EMAIL_HOST == "smtp.example.com"
    assert loaded.EMAIL_PORT == 587
    assert loaded.DEFAULT_FROM_EMAIL == "Store <store@example.com>"


def test_the_console_prints_long_links_unbroken():
    link = "http://127.0.0.1:8000/accounts/email/verify/" + "x" * 120 + "/"
    stream = io.StringIO()

    message = EmailMessage(
        "Confirm", f"Open this link:\n\n{link}\n\n— Us", to=["a@b.c"]
    )

    ConsoleEmailBackend(stream=stream).send_messages([message])

    printed = stream.getvalue()
    assert link in printed
    assert "— Us" in printed
