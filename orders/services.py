"""Order placement — one of the codebase's two deliberate deep modules.

The interface is the product: one function that turns a cart and a
validated checkout into an order, all-or-nothing. Callers never touch
``Order`` construction directly.
"""

from collections.abc import Mapping
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from coupons.models import Coupon

from .models import Cart, Order, OrderItem, Quote

ADDRESS_FIELDS = [
    "email",
    "shipping_name",
    "shipping_street",
    "shipping_line2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "billing_name",
    "billing_street",
    "billing_line2",
    "billing_city",
    "billing_state",
    "billing_zip",
]


@transaction.atomic
def place_order(
    cart: Cart,
    user: AbstractBaseUser,
    checkout_data: Mapping[str, Any],
    *,
    coupon_code: str | None = None,
) -> Order:
    """Create an order from the cart's contents, then empty the cart.

    ``checkout_data`` is the ``cleaned_data`` of a valid ``CheckoutForm``.
    Addresses and line prices are denormalized onto the order — an order
    is a snapshot, immune to later catalog or address edits. Of the card,
    only the last four digits are stored; the full number and CVV never
    touch the database.

    ``coupon_code`` (optional; blank means none) is re-checked here with
    the same rule the checkout form used — the backstop for a code that
    expired or was retired between Apply and Place order. The discount
    is copied onto the order and its lines, so later edits to the coupon
    change nothing.

    All-or-nothing: runs in a transaction, so a failure partway through
    leaves no partial order and the cart intact.

    Raises ``ValueError`` if the cart is empty or holds a product that is
    no longer available, and ``CouponError`` (a ``ValueError``) if the
    coupon can't be redeemed; its message is customer-facing.
    """
    lines = list(cart.lines())
    if not lines:
        raise ValueError("Cannot place an order from an empty cart.")
    unavailable = [line.product.name for line in lines if not line.product.is_available]
    if unavailable:
        raise ValueError(
            f"No longer available: {', '.join(unavailable)}. "
            "Remove them from the cart to check out."
        )
    coupon = None
    if coupon_code and coupon_code.strip():
        coupon = Coupon.objects.redeemable(coupon_code, user=user, lines=lines)
    quote = Quote.for_lines(lines, coupon)

    card_digits = checkout_data["card_number"].replace(" ", "").replace("-", "")
    order = Order.objects.create(
        user=user,
        total=quote.total,
        discount_amount=quote.discount,
        coupon=coupon,
        coupon_code=coupon.code if coupon else "",
        coupon_percent_off=coupon.percent_off if coupon else None,
        card_last4=card_digits[-4:],
        **{name: checkout_data[name] for name in ADDRESS_FIELDS},
    )
    for line in quote.lines:
        OrderItem.objects.create(
            order=order,
            product=line.item.product,
            product_name=line.item.product.name,
            unit_price=line.item.product.price,
            quantity=line.item.quantity,
            discount=line.discount,
        )
    cart.items.all().delete()
    return order
