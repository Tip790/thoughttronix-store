"""Coupon rules: normalizing, rounding, validation, the live window,
every redemption message, and usage counting."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.formats import date_format

from orders.models import CartItem, Order

from .models import CANCELLED, Coupon, CouponError, percent_of

pytestmark = pytest.mark.django_db


def days(n):
    return timezone.localdate() + timedelta(days=n)


def use(coupon, user, *, status=Order.Status.PLACED, discount="10.00"):
    """A bare order that used ``coupon`` — enough for usage counting."""
    return Order.objects.create(
        user=user,
        status=status,
        total=Decimal("90.00"),
        discount_amount=Decimal(discount),
        coupon=coupon,
        coupon_code=coupon.code,
        coupon_percent_off=coupon.percent_off,
    )


def redeem(code, cart):
    return Coupon.objects.redeemable(code, user=cart.user, lines=list(cart.lines()))


# --- The model ---------------------------------------------------------------


def test_codes_are_saved_trimmed_and_upper_cased():
    coupon = Coupon.objects.create(
        code="  fall26 ", percent_off=10, starts_on=days(0), ends_on=days(1)
    )

    assert coupon.code == "FALL26"


def test_codes_are_unique():
    Coupon.objects.create(
        code="FALL26", percent_off=10, starts_on=days(0), ends_on=days(1)
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Coupon.objects.create(
            code="fall26", percent_off=5, starts_on=days(0), ends_on=days(1)
        )


@pytest.mark.parametrize(
    ("amount", "percent", "expected"),
    [
        ("33.33", 15, "5.00"),  # 4.9995 rounds up
        ("0.05", 50, "0.03"),  # half a cent rounds up, not to even
        ("699.98", 10, "70.00"),
        ("99.99", 50, "50.00"),
        ("12.00", 100, "12.00"),
    ],
)
def test_percent_of_rounds_half_up_to_the_cent(amount, percent, expected):
    assert percent_of(Decimal(amount), percent) == Decimal(expected)


def test_a_promotion_cannot_end_before_it_starts():
    coupon = Coupon(
        code="BACKWARDS", percent_off=10, starts_on=days(5), ends_on=days(1)
    )

    with pytest.raises(ValidationError) as error:
        coupon.full_clean()

    assert "ends_on" in error.value.message_dict


def test_the_database_also_refuses_backwards_dates():
    with pytest.raises(IntegrityError), transaction.atomic():
        Coupon.objects.create(
            code="BACKWARDS", percent_off=10, starts_on=days(5), ends_on=days(1)
        )


def test_whole_order_coupons_are_capped():
    coupon = Coupon(code="TOOMUCH", percent_off=51, starts_on=days(0), ends_on=days(1))

    with pytest.raises(ValidationError) as error:
        coupon.full_clean()

    assert error.value.message_dict["percent_off"] == [
        "Whole-order coupons can take at most 50% off."
    ]


def test_product_coupons_may_give_it_away():
    coupon = Coupon(
        code="FREEBIE",
        percent_off=100,
        scope=Coupon.Scope.PRODUCTS,
        starts_on=days(0),
        ends_on=days(1),
    )

    coupon.full_clean()  # no error


def test_the_cancelled_constant_matches_the_order_status():
    """coupons never imports orders — this pins the spelled-out status."""
    assert CANCELLED == Order.Status.CANCELLED


@pytest.mark.parametrize(
    ("starts", "ends", "active", "status"),
    [
        (-1, 1, True, "Live"),
        (1, 5, True, "Scheduled"),
        (-5, -1, True, "Expired"),
        (-1, 1, False, "Retired"),
    ],
)
def test_status(starts, ends, active, status):
    coupon = Coupon(
        code="X",
        percent_off=10,
        starts_on=days(starts),
        ends_on=days(ends),
        is_active=active,
    )

    assert coupon.status == status


def test_live_includes_both_boundary_days_and_nothing_else():
    first_day = Coupon.objects.create(
        code="FIRST", percent_off=5, starts_on=days(0), ends_on=days(3)
    )
    last_day = Coupon.objects.create(
        code="LAST", percent_off=5, starts_on=days(-3), ends_on=days(0)
    )
    Coupon.objects.create(
        code="SOON", percent_off=5, starts_on=days(1), ends_on=days(3)
    )
    Coupon.objects.create(
        code="GONE", percent_off=5, starts_on=days(-3), ends_on=days(-1)
    )
    Coupon.objects.create(
        code="OFF", percent_off=5, starts_on=days(-3), ends_on=days(3), is_active=False
    )

    assert set(Coupon.objects.live()) == {first_day, last_day}


# --- Discount math -----------------------------------------------------------


def test_an_order_coupon_rounds_once_on_the_subtotal(order_coupon, product):
    lines = [(product, Decimal("0.05")), (product, Decimal("0.05"))]

    line_discounts, total = order_coupon.discounts(lines)

    # 10% of 0.10 = 0.01; per-line rounding would have given 0.02.
    assert total == Decimal("0.01")
    assert line_discounts == [Decimal("0.00"), Decimal("0.00")]


def test_a_product_coupon_discounts_matching_lines_only(
    product_coupon, product, unavailable_product
):
    lines = [(product, Decimal("699.98")), (unavailable_product, Decimal("139.00"))]

    line_discounts, total = product_coupon.discounts(lines)

    assert line_discounts == [Decimal("349.99"), Decimal("0.00")]
    assert total == Decimal("349.99")


# --- Redemption: every message -----------------------------------------------


def test_a_good_code_is_redeemable_in_any_case(cart, cart_item, order_coupon):
    assert redeem(" thoughts10", cart) == order_coupon


def test_an_unknown_code(cart, cart_item):
    with pytest.raises(CouponError, match="^NOPE isn't a valid code.$"):
        redeem("nope", cart)


def test_a_code_that_hasnt_started_reads_as_unknown(cart, cart_item, order_coupon):
    order_coupon.starts_on, order_coupon.ends_on = days(3), days(10)
    order_coupon.save()

    with pytest.raises(CouponError, match="^THOUGHTS10 isn't a valid code.$"):
        redeem("THOUGHTS10", cart)


def test_an_expired_code_says_when(cart, cart_item, order_coupon):
    order_coupon.starts_on, order_coupon.ends_on = days(-10), days(-1)
    order_coupon.save()

    ended = date_format(days(-1), "F j, Y")
    with pytest.raises(CouponError) as error:
        redeem("THOUGHTS10", cart)

    assert str(error.value) == f"THOUGHTS10 expired on {ended}."


def test_a_code_works_through_its_last_day(cart, cart_item, order_coupon):
    order_coupon.ends_on = days(0)
    order_coupon.save()

    assert redeem("THOUGHTS10", cart) == order_coupon


def test_a_retired_code(cart, cart_item, order_coupon):
    order_coupon.is_active = False
    order_coupon.save()

    with pytest.raises(CouponError, match="^THOUGHTS10 is no longer available.$"):
        redeem("THOUGHTS10", cart)


def test_once_per_customer(cart, cart_item, order_coupon):
    use(order_coupon, cart.user)

    with pytest.raises(CouponError, match="^You've already used THOUGHTS10.$"):
        redeem("THOUGHTS10", cart)


def test_a_cancelled_order_gives_the_use_back(cart, cart_item, order_coupon):
    use(order_coupon, cart.user, status=Order.Status.CANCELLED)

    assert redeem("THOUGHTS10", cart) == order_coupon


def test_another_customers_use_doesnt_count(
    cart, cart_item, order_coupon, other_customer
):
    use(order_coupon, other_customer)

    assert redeem("THOUGHTS10", cart) == order_coupon


def test_a_product_code_needs_its_product_in_the_cart(
    cart, product_coupon, unavailable_product
):
    CartItem.objects.create(cart=cart, product=unavailable_product)

    with pytest.raises(CouponError) as error:
        redeem("SERAPHINE50", cart)

    assert str(error.value) == (
        "SERAPHINE50 applies only to Seraphine Home Hub. "
        "Add it to your cart to use this code."
    )


def test_a_product_code_with_its_product_in_the_cart(cart, cart_item, product_coupon):
    assert redeem("SERAPHINE50", cart) == product_coupon


# --- Usage -------------------------------------------------------------------


def test_with_usage_leaves_out_cancelled_orders(order_coupon, customer, other_customer):
    use(order_coupon, customer, discount="10.00")
    use(order_coupon, other_customer, discount="5.50")
    use(order_coupon, other_customer, status=Order.Status.CANCELLED, discount="99.00")

    coupon = Coupon.objects.with_usage().get()

    assert coupon.uses == 2
    assert coupon.discount_given == Decimal("15.50")
    assert coupon.order_count == 3


def test_an_unused_coupon_shows_zero_usage(order_coupon):
    coupon = Coupon.objects.with_usage().get()

    assert coupon.uses == 0
    assert coupon.discount_given == Decimal("0.00")


def test_any_order_counts_as_used_even_cancelled(order_coupon, customer):
    assert not order_coupon.is_used

    use(order_coupon, customer, status=Order.Status.CANCELLED)

    assert order_coupon.is_used
