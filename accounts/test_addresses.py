"""Address model behavior: display, defaults, and the checkout save."""

import pytest
from django.db import IntegrityError

from orders.test_checkout_form import VALID_DATA

from .models import Address


def test_str_leads_with_the_label(address):
    assert str(address) == "Home — 12 Cortex Lane, Unit 7, Canyon, TX 79015"


def test_str_falls_back_to_the_name_without_a_label(address):
    address.label = ""
    address.line2 = ""

    assert str(address) == "Casey Monroe — 12 Cortex Lane, Canyon, TX 79015"


# --- Defaults ----------------------------------------------------------------


def second_address(user):
    return Address.objects.create(
        user=user,
        label="Work",
        name="Casey Monroe",
        street="1 Cognition Plaza",
        city="Amarillo",
        state="TX",
        zip="79101",
    )


def test_make_default_moves_the_flag(customer, address):
    work = second_address(customer)
    address.make_default("shipping")

    work.make_default("shipping")

    address.refresh_from_db()
    assert not address.is_default_shipping
    assert work.is_default_shipping
    assert Address.objects.default_for(customer, "shipping") == work


def test_shipping_and_billing_defaults_are_independent(customer, address):
    work = second_address(customer)

    address.make_default("shipping")
    work.make_default("billing")

    assert Address.objects.default_for(customer, "shipping") == address
    assert Address.objects.default_for(customer, "billing") == work


def test_the_database_refuses_a_second_default(customer, address):
    address.make_default("billing")

    with pytest.raises(IntegrityError):
        Address.objects.create(
            user=customer,
            name="Casey Monroe",
            street="1 Cognition Plaza",
            city="Amarillo",
            state="TX",
            zip="79101",
            is_default_billing=True,
        )


def test_each_customer_has_their_own_defaults(customer, other_customer, address):
    address.make_default("shipping")
    theirs = second_address(other_customer)

    theirs.make_default("shipping")

    address.refresh_from_db()
    assert address.is_default_shipping


def test_an_unknown_role_is_rejected(address):
    with pytest.raises(ValueError):
        address.make_default("gift")


def test_deleting_a_default_leaves_no_default(customer, address):
    work = second_address(customer)
    address.make_default("shipping")

    address.delete()

    work.refresh_from_db()
    assert not work.is_default_shipping
    assert Address.objects.default_for(customer, "shipping") is None


def test_fill_empty_defaults_never_displaces_a_default(customer, address):
    address.make_default("shipping")
    work = second_address(customer)

    work.fill_empty_defaults("shipping", "billing")

    assert Address.objects.default_for(customer, "shipping") == address
    assert Address.objects.default_for(customer, "billing") == work


# --- Saving from checkout ----------------------------------------------------


def test_save_from_checkout_copies_the_section(customer):
    address = Address.objects.save_from_checkout(customer, VALID_DATA, role="billing")

    assert address.user == customer
    assert address.label == ""
    assert address.street == "12 Cortex Lane"
    assert address.line2 == ""
    assert address.zip == "79015-1234"


def test_save_from_checkout_skips_an_exact_duplicate(customer, address):
    saved = Address.objects.save_from_checkout(customer, VALID_DATA, role="shipping")

    assert saved == address
    assert Address.objects.count() == 1


def test_a_near_duplicate_is_a_new_address(customer, address):
    data = {**VALID_DATA, "shipping_street": "12 cortex lane"}

    Address.objects.save_from_checkout(customer, data, role="shipping")

    assert Address.objects.count() == 2


def test_duplicates_are_checked_per_customer(other_customer, address):
    Address.objects.save_from_checkout(other_customer, VALID_DATA, role="shipping")

    assert Address.objects.filter(user=other_customer).count() == 1


def test_same_address_in_both_sections_is_saved_once(customer):
    data = {
        **VALID_DATA,
        **{f"billing_{f}": VALID_DATA[f"shipping_{f}"] for f in Address.FIELDS},
    }

    Address.objects.save_from_checkout(customer, data, role="shipping")
    Address.objects.save_from_checkout(customer, data, role="billing")

    address = Address.objects.get()
    assert address.is_default_shipping
    assert address.is_default_billing


def test_a_checkout_save_fills_only_its_own_empty_default(customer):
    Address.objects.save_from_checkout(customer, VALID_DATA, role="shipping")

    assert Address.objects.default_for(customer, "shipping") is not None
    assert Address.objects.default_for(customer, "billing") is None


def test_a_checkout_save_never_displaces_a_default(customer, address):
    address.make_default("billing")

    new = Address.objects.save_from_checkout(customer, VALID_DATA, role="billing")

    assert new != address
    assert Address.objects.default_for(customer, "billing") == address
