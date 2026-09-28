"""Coupons at checkout: the HTMX Apply preview, and the blocking re-check on submit."""

from decimal import Decimal
from http import HTTPStatus

from django.urls import reverse

from coupons.models import CouponError

from .models import Order
from .test_checkout_form import VALID_DATA

APPLY_URL = reverse("orders:checkout_coupon")


# --- Apply (HTMX) ------------------------------------------------------------


def test_apply_returns_the_summary_partial_with_the_discount(
    client, customer, cart_item, order_coupon
):
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": "thoughts10"})

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert 'id="order-summary"' in page
    assert "−$70.00" in page
    assert "$629.98" in page
    # The Place-order button's total updates out of band.
    assert 'id="place-order-total" hx-swap-oob="true"' in page


def test_apply_shows_why_a_code_fails(client, customer, cart_item, order_coupon):
    order_coupon.is_active = False
    order_coupon.save()
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": "THOUGHTS10"})

    page = response.content.decode()
    assert "THOUGHTS10 is no longer available." in page
    assert "$699.98" in page  # full price, no discount


def test_apply_with_a_blank_code_clears_the_discount(client, customer, cart_item):
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": ""})

    page = response.content.decode()
    assert "$699.98" in page
    assert "alert" not in page


def test_apply_requires_login(client, db):
    response = client.post(APPLY_URL, {"coupon_code": "THOUGHTS10"})

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_checkout_page_has_the_apply_button(client, customer, cart_item):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert f'hx-post="{APPLY_URL}"' in page
    assert 'id="order-summary"' in page


# --- Submit ------------------------------------------------------------------


def test_checkout_with_a_coupon_places_a_discounted_order(
    client, customer, cart_item, product_coupon
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "seraphine50"}
    )

    order = Order.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert order.total == Decimal("349.99")
    assert order.coupon_code == "SERAPHINE50"


def test_an_invalid_code_blocks_the_order_and_keeps_the_form(
    client, customer, cart_item
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "nope"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["coupon_code"] == [
        "NOPE isn't a valid code."
    ]
    assert response.context["form"]["shipping_street"].value() == "12 Cortex Lane"
    assert not Order.objects.exists()
    assert customer.cart.items.exists()


def test_a_code_that_fails_at_the_last_moment_blocks_the_order(
    client, customer, cart_item, order_coupon, monkeypatch
):
    """The form passed it, then place_order's re-check refused it."""

    def refuse(*args, **kwargs):
        raise CouponError("THOUGHTS10 expired on September 30, 2026.")

    monkeypatch.setattr("orders.views.place_order", refuse)
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "THOUGHTS10"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["coupon_code"] == [
        "THOUGHTS10 expired on September 30, 2026."
    ]
    assert response.context["quote"].discount == Decimal("0.00")


def test_a_rerendered_form_keeps_a_good_coupon_in_the_summary(
    client, customer, cart_item, order_coupon
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "coupon_code": "THOUGHTS10", "card_cvv": "1"},
    )

    assert response.context["quote"].total == Decimal("629.98")


def test_the_order_pages_show_the_snapshot_discount(
    client, customer, staff_user, cart_item, order_coupon
):
    client.force_login(customer)
    client.post(reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "THOUGHTS10"})
    order = Order.objects.get()
    order_coupon.is_active = False
    order_coupon.save()

    detail = client.get(
        reverse("orders:detail", kwargs={"pk": order.pk})
    ).content.decode()
    confirmation = client.get(
        reverse("orders:confirmation", kwargs={"pk": order.pk})
    ).content.decode()
    client.force_login(staff_user)
    manage = client.get(
        reverse("orders:manage_order_detail", kwargs={"pk": order.pk})
    ).content.decode()

    for page in (detail, manage):
        assert "THOUGHTS10 (10% off) −$70.00" in page
        assert "Subtotal $699.98" in page
    assert "You saved $70.00 with THOUGHTS10." in confirmation
