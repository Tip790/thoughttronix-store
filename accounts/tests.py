from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


SIGNUP = {
    "username": "fresh-thinker",
    "email": "fresh@example.com",
    "password1": "neural-implant-9000",
    "password2": "neural-implant-9000",
}


def test_signup_creates_customer_and_signs_them_in(client, db):
    response = client.post(reverse("accounts:signup"), SIGNUP, follow=True)

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"
    assert not user.is_staff
    assert not user.is_superuser

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "your account is ready" in response.content.decode()
    assert response.context["user"] == user


def test_signup_password_mismatch_shows_field_error(client, db):
    response = client.post(
        reverse("accounts:signup"), {**SIGNUP, "password2": "neural-implant-9001"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_runs_password_validators(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {**SIGNUP, "password1": "12345678", "password2": "12345678"},
    )

    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_requires_email(client, db):
    response = client.post(reverse("accounts:signup"), {**SIGNUP, "email": ""})

    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_rejects_email_taken_in_any_case(client, customer):
    customer.email = "casey@example.com"
    customer.save()

    response = client.post(
        reverse("accounts:signup"), {**SIGNUP, "email": "Casey@Example.COM"}
    )

    assert "already in use" in response.context["form"].errors["email"][0]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_stores_email_lowercase(client, db):
    client.post(reverse("accounts:signup"), {**SIGNUP, "email": "Fresh@Example.com"})

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"


# --- Email on the user model ---------------------------------------------------


def test_saving_user_lowercases_email(customer):
    customer.email = "Casey@Example.com"
    customer.save()

    customer.refresh_from_db()
    assert customer.email == "casey@example.com"


def test_duplicate_email_outside_the_form_fails_at_the_database(customer):
    customer.email = "casey@example.com"
    customer.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.create_user(
            username="impostor", email="CASEY@example.com", password="x"
        )


def test_bulk_update_cannot_bypass_email_constraint(customer, other_customer):
    customer.email = "casey@example.com"
    customer.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.filter(pk=other_customer.pk).update(
            email="CASEY@EXAMPLE.COM"
        )


def test_many_users_may_have_a_blank_email(customer, other_customer):
    assert customer.email == other_customer.email == ""


# --- Login and logout --------------------------------------------------------


def test_login_page_returns_200(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == HTTPStatus.OK


def test_login_round_trip(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert response.context["user"] == customer


def test_login_bad_credentials_stays_put(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()


def test_logout_signs_out_with_message(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:logout"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "You have signed out." in response.content.decode()
    assert not response.context["user"].is_authenticated


# --- Auth-aware navbar --------------------------------------------------------


def test_navbar_offers_login_and_signup_to_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:login") in page
    assert reverse("accounts:signup") in page
    assert "Sign out" not in page


def test_navbar_greets_signed_in_customer(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert "Hi, customer" in page
    assert "Sign out" in page
    assert reverse("accounts:signup") not in page
