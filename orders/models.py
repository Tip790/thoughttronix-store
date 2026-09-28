from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from coupons.models import Coupon
from products.models import Product

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class QuoteLine:
    item: "CartItem"
    discount: Decimal

    @property
    def net_total(self):
        return self.item.line_total - self.discount


@dataclass(frozen=True)
class Quote:
    """What the cart costs, with or without a coupon — the checkout summary.

    Priced by ``Coupon.discounts``, the same math ``place_order`` stores,
    so the total a customer sees is the total they pay.
    """

    lines: list[QuoteLine]
    subtotal: Decimal
    discount: Decimal
    coupon: Coupon | None = None

    @property
    def total(self):
        return self.subtotal - self.discount

    @classmethod
    def for_lines(cls, items, coupon=None):
        items = list(items)
        subtotal = sum((item.line_total for item in items), ZERO)
        if coupon is None:
            line_discounts, discount = [ZERO] * len(items), ZERO
        else:
            line_discounts, discount = coupon.discounts(
                (item.product, item.line_total) for item in items
            )
        return cls(
            lines=[
                QuoteLine(item, d)
                for item, d in zip(items, line_discounts, strict=True)
            ],
            subtotal=subtotal,
            discount=discount,
            coupon=coupon,
        )


class Cart(models.Model):
    """A customer's cart — one per user, created lazily on first touch."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    def __str__(self):
        return f"Cart for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's cart, creating it on first touch."""
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def add(self, product):
        """Add a product to the cart; a duplicate add increments its line."""
        item, created = self.items.get_or_create(product=product)
        if not created:
            item.quantity += 1
            item.save()
        return item

    def lines(self):
        """Line items with their products loaded, ready for display."""
        return self.items.select_related("product")

    def total(self):
        return sum((item.line_total for item in self.lines()), ZERO)

    def quote(self, coupon=None):
        """Price the cart, optionally with an already-validated coupon."""
        return Quote.for_lines(self.lines(), coupon)

    def item_count(self):
        """Total units across all lines — the navbar badge number."""
        return self.items.aggregate(count=models.Sum("quantity"))["count"] or 0


class CartItem(models.Model):
    """One product line in a cart; the cart–product pair is unique."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_cart_product"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def increment(self):
        self.quantity += 1
        self.save()

    def decrement(self):
        """Step the quantity down, stopping at one — removal is explicit."""
        if self.quantity > 1:
            self.quantity -= 1
            self.save()


class Order(models.Model):
    """A placed order — a snapshot, never a live view of the catalog.

    Addresses are flat denormalized fields: the order must not change if
    the customer later edits anything. Of the card, only the last four
    digits survive checkout. A coupon's effect is copied too — code,
    percent, and amount — so retiring or editing the coupon changes
    nothing here; the ``coupon`` FK is ``PROTECT`` so it can't vanish.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLACED
    )
    # What was charged, after any discount. ``subtotal`` is derived.
    total = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_percent_off = models.PositiveSmallIntegerField(null=True, blank=True)
    email = models.EmailField()

    shipping_name = models.CharField(max_length=100)
    shipping_street = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=2)
    shipping_zip = models.CharField(max_length=10)

    billing_name = models.CharField(max_length=100)
    billing_street = models.CharField(max_length=200)
    billing_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=2)
    billing_zip = models.CharField(max_length=10)

    card_last4 = models.CharField(max_length=4)

    # default (not auto_now_add) so the seed can backdate orders.
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def number(self):
        """The customer-facing order number, e.g. ``TT-2026-00042``."""
        return f"TT-{self.created_at.year}-{self.pk:05d}"

    @property
    def subtotal(self):
        """The price before the coupon: what was charged plus what was taken off."""
        return self.total + self.discount_amount


class OrderItem(models.Model):
    """One line of an order, priced as of purchase time.

    Name and unit price are denormalized: order history must not change
    when the catalog does. The product FK survives for linking while the
    product exists. ``discount`` is this line's share of a product
    coupon; whole-order coupons leave it at zero.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def net_total(self):
        return self.line_total - self.discount
