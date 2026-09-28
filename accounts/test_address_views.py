"""The address book pages: login, owner-only access, and the CRUD flows."""

from http import HTTPStatus

import pytest
from django.urls import reverse

from .models import Address

NEW_ADDRESS = {
    "label": "Work",
    "name": "Casey Monroe",
    "street": "1 Cognition Plaza",
    "line2": "Suite 400",
    "city": "Amarillo",
    "state": "TX",
    "zip": "79101",
}


@pytest.mark.parametrize(
    "url",
    [
        reverse("accounts:address_list"),
        reverse("accounts:address_create"),
        reverse("accounts:address_update", kwargs={"pk": 1}),
        reverse("accounts:address_delete", kwargs={"pk": 1}),
    ],
)
def test_the_address_book_requires_login(client, db, url):
    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_navbar_links_to_the_address_book(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:address_list") in page


def test_list_has_a_designed_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:address_list"))

    assert "No saved addresses yet" in response.content.decode()


def test_list_shows_only_the_customers_addresses(client, other_customer, address):
    Address.objects.create(user=other_customer, **{**NEW_ADDRESS, "label": "Theirs"})
    client.force_login(address.user)
    address.make_default("shipping")

    page = client.get(reverse("accounts:address_list")).content.decode()

    assert "Home" in page
    assert "Default shipping" in page
    assert "Theirs" not in page


def test_creating_the_first_address_makes_it_both_defaults(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:address_create"), NEW_ADDRESS)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:address_list")
    address = Address.objects.get()
    assert address.user == customer
    assert address.is_default_shipping
    assert address.is_default_billing


def test_creating_another_address_leaves_the_defaults_alone(client, address):
    address.make_default("shipping")
    address.make_default("billing")
    client.force_login(address.user)

    client.post(reverse("accounts:address_create"), NEW_ADDRESS)

    work = Address.objects.get(label="Work")
    assert not work.is_default_shipping
    assert not work.is_default_billing


def test_the_account_page_does_not_check_for_duplicates(client, address):
    client.force_login(address.user)
    data = {f: getattr(address, f) for f in ["label", *Address.FIELDS]}

    client.post(reverse("accounts:address_create"), data)

    assert Address.objects.count() == 2


def test_an_invalid_address_shows_field_errors(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_create"), {**NEW_ADDRESS, "zip": "790"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["zip"]
    assert not Address.objects.exists()


def test_editing_an_address(client, address):
    client.force_login(address.user)

    response = client.post(
        reverse("accounts:address_update", kwargs={"pk": address.pk}),
        {**NEW_ADDRESS, "label": "Old place"},
    )

    assert response.status_code == HTTPStatus.FOUND
    address.refresh_from_db()
    assert address.label == "Old place"
    assert address.street == "1 Cognition Plaza"


def test_deleting_a_default_warns_then_leaves_a_gap(client, address):
    address.make_default("shipping")
    client.force_login(address.user)
    url = reverse("accounts:address_delete", kwargs={"pk": address.pk})

    confirm = client.get(url).content.decode()
    response = client.post(url)

    assert "have no default until you choose another" in confirm
    assert response.status_code == HTTPStatus.FOUND
    assert not Address.objects.exists()


def test_make_default_is_post_only_and_switches_the_default(client, address):
    work = Address.objects.create(user=address.user, **NEW_ADDRESS)
    address.make_default("billing")
    client.force_login(address.user)
    url = reverse(
        "accounts:address_make_default", kwargs={"pk": work.pk, "role": "billing"}
    )

    assert client.get(url).status_code == HTTPStatus.METHOD_NOT_ALLOWED
    response = client.post(url)

    assert response.status_code == HTTPStatus.FOUND
    assert Address.objects.default_for(address.user, "billing") == work


def test_make_default_rejects_an_unknown_role(client, address):
    client.force_login(address.user)

    response = client.post(
        reverse(
            "accounts:address_make_default", kwargs={"pk": address.pk, "role": "gift"}
        )
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_customers_cannot_touch_anothers_address(client, other_customer, address):
    client.force_login(other_customer)
    pk = {"pk": address.pk}

    assert (
        client.get(reverse("accounts:address_update", kwargs=pk)).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert (
        client.post(reverse("accounts:address_update", kwargs=pk), NEW_ADDRESS)
    ).status_code == HTTPStatus.NOT_FOUND
    assert (
        client.post(reverse("accounts:address_delete", kwargs=pk)).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert (
        client.post(
            reverse("accounts:address_make_default", kwargs={**pk, "role": "shipping"})
        ).status_code
        == HTTPStatus.NOT_FOUND
    )
    address.refresh_from_db()
    assert address.label == "Home"
    assert not address.is_default_shipping
