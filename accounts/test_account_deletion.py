"""Deleting an account: anonymizing the person, keeping the business record."""

from decimal import Decimal
from http import HTTPStatus
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.urls import reverse

from dashboard import queries
from orders.models import Cart, Order
from orders.services import place_order
from orders.test_checkout_form import VALID_DATA
from wishlists.models import Wishlist, WishlistItem

from .models import Address

PERSONAL_ORDER_FIELDS = ["email"] + [
    f"{role}_{field}" for role in Address.ROLES for field in Address.FIELDS
]


@pytest.fixture
def casey(customer):
    customer.email = "casey@example.com"
    customer.email_verified = True
    customer.first_name = "Casey"
    customer.last_name = "Monroe"
    customer.job_title = "Daydreamer"
    customer.save()
    return customer


@pytest.fixture
def order(casey, cart, cart_item, order_coupon):
    return place_order(cart, casey, dict(VALID_DATA), coupon_code="THOUGHTS10")


@pytest.fixture
def casey_client(client, casey):
    client.force_login(casey)
    return client


def delete_account(client, password="customer123"):
    return client.post(
        reverse("accounts:account_delete"), {"password": password}, follow=True
    )


# --- Orders protect their customer ------------------------------------------


def test_a_user_with_orders_cannot_be_deleted(order, casey):
    with pytest.raises(ProtectedError):
        casey.delete()


def test_a_user_without_orders_can_still_be_deleted(casey, address):
    casey.delete()

    assert not get_user_model().objects.filter(pk=casey.pk).exists()


def test_the_admin_refuses_to_delete_a_user_with_orders(client, order, casey):
    admin = get_user_model().objects.create_superuser(username="root", password="x")
    client.force_login(admin)

    client.post(reverse("admin:accounts_user_delete", args=[casey.pk]), {"post": "yes"})

    assert get_user_model().objects.filter(pk=casey.pk).exists()


# --- anonymize() -------------------------------------------------------------


def test_anonymize_scrubs_the_user(casey):
    casey.anonymize()
    casey.refresh_from_db()

    assert casey.username == f"deleted-user-{casey.pk}"
    assert casey.email == ""
    assert casey.first_name == ""
    assert casey.last_name == ""
    assert casey.job_title is None
    assert casey.email_verified is False
    assert casey.is_active is False
    assert not casey.has_usable_password()
    assert casey.is_anonymized


def test_anonymize_deletes_addresses_and_cart(casey, address, cart_item):
    casey.anonymize()

    assert not Address.objects.filter(user=casey).exists()
    assert not Cart.objects.filter(user=casey).exists()


def test_anonymize_deletes_the_wishlist_and_its_items(
    casey, product, unavailable_product
):
    wishlist = Wishlist.for_user(casey)
    wishlist.add(product)
    wishlist.add(unavailable_product)
    item_pks = list(wishlist.items.values_list("pk", flat=True))

    casey.anonymize()

    assert not Wishlist.objects.filter(user=casey).exists()
    assert not WishlistItem.objects.filter(pk__in=item_pks).exists()


def test_anonymize_succeeds_without_a_wishlist(casey):
    casey.anonymize()

    assert casey.is_anonymized
    assert not Wishlist.objects.filter(user=casey).exists()


def test_accounts_does_not_import_wishlists():
    accounts_dir = Path(__file__).resolve().parent
    sources = [
        path for path in accounts_dir.rglob("*.py") if not path.name.startswith("test")
    ]

    assert sources
    for path in sources:
        assert "wishlists" not in path.read_text(encoding="utf-8"), path


def test_anonymize_blanks_personal_details_on_orders(order, casey):
    casey.anonymize()
    order.refresh_from_db()

    for field in PERSONAL_ORDER_FIELDS:
        assert getattr(order, field) == "", field


def test_anonymize_keeps_the_business_record(order, casey):
    before = Order.objects.get(pk=order.pk)
    revenue = queries.total_revenue()
    count = queries.order_count()

    casey.anonymize()
    after = Order.objects.get(pk=order.pk)

    assert after.user_id == casey.pk
    assert after.total == before.total
    assert after.discount_amount == before.discount_amount > Decimal("0")
    assert after.coupon_code == "THOUGHTS10"
    assert after.status == before.status
    assert after.created_at == before.created_at
    assert after.card_last4 == "4242"
    assert list(after.items.values_list("product_name", "quantity")) == list(
        before.items.values_list("product_name", "quantity")
    )
    assert queries.total_revenue() == revenue
    assert queries.order_count() == count


def test_anonymize_leaves_other_customers_alone(order, casey, other_customer):
    Address.objects.create(
        user=other_customer,
        name="Other Person",
        street="1 Elsewhere",
        city="Amarillo",
        state="TX",
        zip="79101",
    )

    casey.anonymize()

    assert Address.objects.filter(user=other_customer).exists()
    other_customer.refresh_from_db()
    assert other_customer.username == "other"


def test_a_live_user_is_not_anonymized(casey):
    assert not casey.is_anonymized


def test_signup_refuses_the_deleted_user_prefix(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "Deleted-User-7",
            "email": "sneaky@example.com",
            "password1": "fresh-synapse-4242",
            "password2": "fresh-synapse-4242",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "That username is reserved" in response.content.decode()
    assert not get_user_model().objects.filter(email="sneaky@example.com").exists()


# --- The delete view ---------------------------------------------------------


def test_the_account_page_offers_customers_a_delete_link(casey_client):
    page = casey_client.get(reverse("accounts:account")).content.decode()

    assert reverse("accounts:account_delete") in page


def test_deletion_requires_sign_in(client, db):
    response = client.get(reverse("accounts:account_delete"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_a_wrong_password_does_not_delete_the_account(casey_client, casey):
    response = delete_account(casey_client, password="not-it")

    assert "entered incorrectly" in response.content.decode()
    casey.refresh_from_db()
    assert casey.is_active
    assert casey.username == "customer"


def test_deleting_signs_out_and_confirms(casey_client, casey, order):
    response = delete_account(casey_client)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert not response.wsgi_request.user.is_authenticated
    assert "Your account has been deleted" in response.content.decode()
    casey.refresh_from_db()
    assert casey.is_anonymized


def test_the_old_credentials_no_longer_sign_in(casey_client, client):
    delete_account(casey_client)

    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
    )

    assert response.status_code == HTTPStatus.OK
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.parametrize("role", ["is_staff", "is_superuser"])
def test_staff_get_no_delete_button_and_are_refused(client, db, role):
    user = get_user_model().objects.create_user(
        username="worker", password="worker123", **{role: True}
    )
    client.force_login(user)

    page = client.get(reverse("accounts:account")).content.decode()
    assert reverse("accounts:account_delete") not in page
    assert "administrator" in page

    response = client.post(
        reverse("accounts:account_delete"), {"password": "worker123"}
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    user.refresh_from_db()
    assert user.is_active
    assert user.username == "worker"


# --- Staff order screens -----------------------------------------------------


def test_staff_see_anonymized_orders_as_a_deleted_customer(
    client, staff_user, order, casey
):
    casey.anonymize()
    client.force_login(staff_user)

    listing = client.get(reverse("orders:manage_orders")).content.decode()
    detail = client.get(
        reverse("orders:manage_order_detail", kwargs={"pk": order.pk})
    ).content.decode()

    assert order.number in listing
    assert "Deleted customer" in listing
    assert f"deleted-user-{casey.pk}" not in listing
    assert "deleted customer" in detail
    assert "Casey Monroe" not in detail
    assert "12 Cortex Lane" not in detail
