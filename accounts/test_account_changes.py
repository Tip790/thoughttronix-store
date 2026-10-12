"""Changing the password and the email from the Account page."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from .tokens import make_verification_token, user_for_verification_token

NEW_PASSWORD = "fresh-synapse-4242"


@pytest.fixture
def casey(customer):
    """A signed-up customer with a confirmed email."""
    customer.email = "casey@example.com"
    customer.email_verified = True
    customer.save()
    return customer


@pytest.fixture
def casey_client(client, casey):
    client.force_login(casey)
    return client


def change_password(client, old="customer123", new=NEW_PASSWORD):
    return client.post(
        reverse("accounts:password_change"),
        {"old_password": old, "new_password1": new, "new_password2": new},
        follow=True,
    )


def change_email(client, email, password="customer123"):
    return client.post(
        reverse("accounts:email_change"),
        {"email": email, "password": password},
        follow=True,
    )


def link_in(message):
    """The first link's path, pulled out of an email body."""
    return re.search(r"https?://[^/]+(/\S+)", message.body).group(1)


# --- The Account page links to both -----------------------------------------


def test_the_account_page_links_to_both_forms(casey_client):
    page = casey_client.get(reverse("accounts:account")).content.decode()

    assert reverse("accounts:password_change") in page
    assert reverse("accounts:email_change") in page


@pytest.mark.parametrize("name", ["password_change", "email_change"])
def test_both_forms_require_sign_in(client, db, name):
    response = client.get(reverse(f"accounts:{name}"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


# --- Password change ---------------------------------------------------------


def test_changing_the_password_sets_the_new_one(casey_client, casey):
    response = change_password(casey_client)

    assert response.redirect_chain[-1][0] == reverse("accounts:password_change_done")
    casey.refresh_from_db()
    assert casey.check_password(NEW_PASSWORD)


def test_changing_the_password_keeps_this_session_and_ends_the_others(casey):
    here, elsewhere = Client(), Client()
    here.force_login(casey)
    elsewhere.force_login(casey)

    change_password(here)

    account = reverse("accounts:account")
    assert here.get(account).status_code == 200
    assert elsewhere.get(account).url.startswith(reverse("accounts:login"))


def test_changing_the_password_sends_a_notice(casey_client, mailoutbox):
    change_password(casey_client)

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["casey@example.com"]
    assert "password was changed" in notice.subject
    assert reverse("accounts:password_reset") in notice.body


def test_a_wrong_current_password_changes_nothing(casey_client, casey, mailoutbox):
    response = change_password(casey_client, old="not-my-password")

    assert response.context["form"].errors["old_password"]
    casey.refresh_from_db()
    assert casey.check_password("customer123")
    assert mailoutbox == []


def test_the_new_password_must_pass_the_validators(casey_client, casey):
    response = change_password(casey_client, new="password")

    assert response.context["form"].errors["new_password2"]
    casey.refresh_from_db()
    assert casey.check_password("customer123")


# --- Email change ------------------------------------------------------------


def test_changing_the_email_stores_it_lowercase_and_unconfirmed(casey_client, casey):
    response = change_email(casey_client, "Casey.New@Example.com")

    assert response.redirect_chain[-1][0] == reverse("accounts:account")
    assert "Your email is now casey.new@example.com" in response.content.decode()
    casey.refresh_from_db()
    assert casey.email == "casey.new@example.com"
    assert not casey.email_verified


def test_changing_the_email_sends_a_link_to_the_new_and_a_notice_to_the_old(
    casey_client, mailoutbox
):
    change_email(casey_client, "casey.new@example.com")

    assert len(mailoutbox) == 2
    by_recipient = {message.to[0]: message for message in mailoutbox}
    assert set(by_recipient) == {"casey.new@example.com", "casey@example.com"}
    assert "/accounts/email/verify/" in by_recipient["casey.new@example.com"].body
    notice = by_recipient["casey@example.com"]
    assert "email" in notice.subject.lower()
    assert "casey.new@example.com" in notice.body
    assert "/accounts/email/verify/" not in notice.body


def test_the_link_sent_to_the_new_email_confirms_it(casey_client, casey, mailoutbox):
    change_email(casey_client, "casey.new@example.com")
    (link,) = [link_in(m) for m in mailoutbox if m.to == ["casey.new@example.com"]]

    casey_client.post(link)

    casey.refresh_from_db()
    assert casey.email_verified


def test_links_sent_to_the_old_email_stop_working(casey_client, casey):
    old_token = make_verification_token(casey)

    change_email(casey_client, "casey.new@example.com")

    assert user_for_verification_token(old_token) is None


def test_a_wrong_password_does_not_change_the_email(casey_client, casey, mailoutbox):
    response = change_email(casey_client, "casey.new@example.com", "wrong")

    assert response.context["form"].errors["password"]
    casey.refresh_from_db()
    assert casey.email == "casey@example.com"
    assert casey.email_verified
    assert mailoutbox == []


@pytest.mark.parametrize("taken", ["other@example.com", "Other@EXAMPLE.com"])
def test_an_email_used_by_another_account_is_refused(
    casey_client, casey, other_customer, mailoutbox, taken
):
    other_customer.email = "other@example.com"
    other_customer.save()

    response = change_email(casey_client, taken)

    assert "already in use" in response.context["form"].errors["email"][0]
    casey.refresh_from_db()
    assert casey.email == "casey@example.com"
    assert mailoutbox == []


def test_the_current_email_is_refused_as_a_new_one(casey_client, casey):
    response = change_email(casey_client, "CASEY@example.com")

    assert response.context["form"].errors["email"]
    casey.refresh_from_db()
    assert casey.email_verified


def test_an_invalid_email_is_refused(casey_client, casey):
    response = change_email(casey_client, "not-an-email")

    assert response.context["form"].errors["email"]


def test_adding_a_first_email_sends_only_the_link(client, customer, mailoutbox):
    """Accounts from before sign-up required an email have no old address
    to notify."""
    client.force_login(customer)

    change_email(client, "casey@example.com")

    assert [m.to for m in mailoutbox] == [["casey@example.com"]]


# --- Staff -------------------------------------------------------------------


def test_staff_can_change_their_password(client, staff_user):
    client.force_login(staff_user)

    response = change_password(client, old="employee123")

    assert response.redirect_chain[-1][0] == reverse("accounts:password_change_done")
    staff_user.refresh_from_db()
    assert staff_user.check_password(NEW_PASSWORD)


def test_staff_can_change_their_email(client, staff_user):
    client.force_login(staff_user)

    change_email(client, "employee@example.com", password="employee123")

    staff_user.refresh_from_db()
    assert staff_user.email == "employee@example.com"
    assert not staff_user.email_verified
