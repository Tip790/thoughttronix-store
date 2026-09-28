"""Saved addresses at checkout: prefill, the HTMX picker, and saving."""

from http import HTTPStatus

from django.urls import reverse

from accounts.models import Address

from .models import Order
from .test_checkout_form import VALID_DATA


def fields_url(role):
    return reverse("orders:checkout_address_fields", kwargs={"role": role})


# --- Prefill -----------------------------------------------------------------


def test_checkout_prefills_each_section_from_its_default(
    client, customer, cart_item, address
):
    work = Address.objects.create(
        user=customer,
        label="Work",
        name="Casey Monroe",
        street="1 Cognition Plaza",
        city="Amarillo",
        state="TX",
        zip="79101",
    )
    address.make_default("shipping")
    work.make_default("billing")
    client.force_login(customer)

    form = client.get(reverse("orders:checkout")).context["form"]

    assert form["shipping_street"].value() == "12 Cortex Lane"
    assert form["billing_street"].value() == "1 Cognition Plaza"


def test_checkout_without_defaults_starts_blank(client, customer, cart_item, address):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.context["form"]["shipping_street"].value() is None
    assert "Use a saved address" in response.content.decode()  # but can pick one


def test_checkout_without_saved_addresses_hides_the_picker(client, customer, cart_item):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert "Use a saved address" not in page
    assert reverse("accounts:address_list") in page  # "Manage saved addresses"


# --- The HTMX picker ---------------------------------------------------------


def test_picking_a_saved_address_fills_the_section(client, address):
    client.force_login(address.user)

    response = client.get(fields_url("billing"), {"billing_saved_address": address.pk})

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page  # a partial, never base.html
    assert 'name="billing_street"' in page
    assert 'value="12 Cortex Lane"' in page
    assert 'name="shipping_street"' not in page


def test_picking_new_address_clears_the_section(client, address):
    client.force_login(address.user)

    response = client.get(fields_url("shipping"), {"shipping_saved_address": ""})

    page = response.content.decode()
    assert 'name="shipping_street"' in page
    assert "12 Cortex Lane" not in page


def test_the_picker_404s_on_anothers_address(client, other_customer, address):
    client.force_login(other_customer)

    response = client.get(
        fields_url("shipping"), {"shipping_saved_address": address.pk}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_picker_404s_on_bad_input(client, address):
    client.force_login(address.user)

    assert client.get(fields_url("gift")).status_code == HTTPStatus.NOT_FOUND
    assert (
        client.get(
            fields_url("shipping"), {"shipping_saved_address": "abc"}
        ).status_code
        == HTTPStatus.NOT_FOUND
    )


def test_the_picker_requires_login(client, db):
    response = client.get(fields_url("shipping"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Saving at checkout ------------------------------------------------------


def test_checked_boxes_save_addresses_after_the_order(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "save_shipping_address": "on", "save_billing_address": "on"},
    )

    assert Order.objects.exists()
    assert Address.objects.filter(user=customer).count() == 2
    shipping = Address.objects.default_for(customer, "shipping")
    billing = Address.objects.default_for(customer, "billing")
    assert shipping.line2 == "Unit 7"
    assert billing.zip == "79015-1234"


def test_unchecked_boxes_save_nothing(client, customer, cart_item):
    client.force_login(customer)

    client.post(reverse("orders:checkout"), VALID_DATA)

    assert Order.objects.exists()
    assert not Address.objects.exists()


def test_an_invalid_checkout_saves_no_address(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"),
        {
            **VALID_DATA,
            "card_number": "4242 4242 4242 4241",
            "save_shipping_address": "on",
        },
    )

    assert not Order.objects.exists()
    assert not Address.objects.exists()


def test_an_invalid_checkout_keeps_the_picked_address_selected(
    client, customer, cart_item, address
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "card_cvv": "", "shipping_saved_address": str(address.pk)},
    )

    assert response.context["selected_address"]["shipping"] == str(address.pk)
    assert f'<option value="{address.pk}" selected>' in response.content.decode()


def test_the_order_keeps_its_copy_when_the_address_changes(client, customer, cart_item):
    client.force_login(customer)
    client.post(
        reverse("orders:checkout"), {**VALID_DATA, "save_shipping_address": "on"}
    )

    Address.objects.update(street="999 Elsewhere Road")

    assert Order.objects.get().shipping_street == "12 Cortex Lane"
