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


MODAL_TITLE = "We had other thoughts about that code"


def test_a_failed_apply_opens_the_pop_up_and_marks_the_field(
    client, customer, cart_item
):
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": "nope"})

    page = response.content.decode()
    assert '<div id="coupon-modal" hx-swap-oob="true">' in page
    assert "<dialog" in page and MODAL_TITLE in page
    assert "Continue without a coupon" in page
    # The field swaps too: the reminder beside it, the code kept to fix.
    assert '<div id="coupon-field" hx-swap-oob="true">' in page
    assert (
        '<p class="mt-1 text-sm text-error">NOPE isn&#x27;t a valid code.</p>' in page
    )
    assert 'value="NOPE"' in page
    # The old yellow alert in the summary is gone.
    assert "alert-warning" not in page


def test_a_good_apply_clears_any_open_pop_up(client, customer, cart_item, order_coupon):
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": "THOUGHTS10"})

    page = response.content.decode()
    assert '<div id="coupon-modal" hx-swap-oob="true">' in page  # swapped in, empty
    assert "<dialog" not in page
    assert "text-error" not in page


def test_continue_without_a_coupon_empties_the_field_at_full_price(
    client, customer, cart_item
):
    """The pop-up's button posts a blank code to Apply."""
    client.force_login(customer)

    response = client.post(APPLY_URL, {"coupon_code": ""})

    page = response.content.decode()
    assert "<dialog" not in page
    assert 'name="coupon_code"' in page
    assert 'name="coupon_code" value=' not in page  # the input is empty
    assert "Place order" not in page  # the order isn't placed for them
    assert "$699.98" in page


def test_the_pop_up_continue_button_posts_a_blank_code(client, customer, cart_item):
    client.force_login(customer)

    page = client.post(APPLY_URL, {"coupon_code": "nope"}).content.decode()

    assert f'hx-post="{APPLY_URL}"' in page
    assert """hx-vals='{"coupon_code": ""}'""" in page


def test_apply_requires_login(client, db):
    response = client.post(APPLY_URL, {"coupon_code": "THOUGHTS10"})

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_checkout_page_has_the_apply_button(client, customer, cart_item):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert f'hx-post="{APPLY_URL}"' in page
    assert 'id="order-summary"' in page
    assert '<div id="coupon-modal">' in page  # the empty container, ready to swap
    assert "<dialog" not in page


def test_a_failed_submit_renders_the_pop_up_open_outside_the_form(
    client, customer, cart_item
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "nope"}
    )

    page = response.content.decode()
    assert "<dialog" in page and MODAL_TITLE in page
    assert "NOPE isn&#x27;t a valid code." in page
    # Forms can't nest: the pop-up's method="dialog" forms follow the checkout form.
    # (The checkout form closes before the summary's </aside>.)
    assert page.index('<div id="coupon-modal">') > page.index("</aside>")


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
