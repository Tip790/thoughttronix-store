"""Discount coupons — marketing's seasonal promotion codes.

A coupon takes a percentage off either the whole order or specific
products, for a run of calendar days in the store's time zone. Retiring
a coupon flips ``is_active``; used coupons are never deleted
(``Order.coupon`` is ``PROTECT``), and orders keep their own copy of
the discount they received.

Dependencies run one way: ``orders → coupons → products``. Nothing here
imports from ``orders`` — the redemption rule takes cart lines as an
argument and counts past uses through the ``orders`` reverse relation.
"""

from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.formats import date_format

CENT = Decimal("0.01")

ZERO = Decimal("0.00")

# ``Order.Status.CANCELLED``, spelled out so this app never imports
# ``orders`` — a test pins the two together.
CANCELLED = "CANCELLED"


class CouponError(ValueError):
    """A code that can't be redeemed; the message is customer-facing."""


def percent_of(amount: Decimal, percent: int) -> Decimal:
    """``percent``% of ``amount``, rounded half-up to the cent."""
    return (amount * Decimal(percent) / Decimal(100)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


class CouponQuerySet(models.QuerySet):
    def live(self):
        """Coupons a customer could redeem today: active and in their run."""
        today = timezone.localdate()
        return self.filter(is_active=True, starts_on__lte=today, ends_on__gte=today)

    def with_usage(self):
        """Annotate ``uses`` and ``discount_given`` (cancelled orders excluded)
        and ``order_count`` (every order, cancelled included — any order
        locks a coupon's terms and blocks its deletion)."""
        sold = ~Q(orders__status=CANCELLED)
        return self.annotate(
            uses=Count("orders", filter=sold),
            discount_given=Sum("orders__discount_amount", filter=sold, default=ZERO),
            order_count=Count("orders"),
        )

    def redeemable(self, code: str, *, user, lines: Sequence) -> "Coupon":
        """The coupon for ``code`` if ``user`` can use it on ``lines``.

        ``lines`` are cart lines (anything with a ``product``). Raises
        ``CouponError`` with the message to show the customer.
        """
        code = Coupon.normalize(code)
        try:
            coupon = self.get(code=code)
        except Coupon.DoesNotExist:
            raise CouponError(f"{code} isn't a valid code.") from None
        coupon.check_redeemable(user=user, lines=lines)
        return coupon


class Coupon(models.Model):
    class Scope(models.TextChoices):
        ORDER = "ORDER", "Whole order"
        PRODUCTS = "PRODUCTS", "Specific products"

    # A leaked whole-order code can cost at most half of one order per
    # customer. Product coupons may go to 100% (giveaways).
    MAX_ORDER_PERCENT = 50
    # Product coupons at or above this get a double-check warning on save.
    WARN_PERCENT = 50
    # The deal itself; frozen once any order has used the coupon.
    TERMS = ("code", "percent_off", "scope", "products")

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="What customers type. Stored in capitals; matched without regard to case.",
    )
    percent_off = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    scope = models.CharField(max_length=8, choices=Scope.choices, default=Scope.ORDER)
    products = models.ManyToManyField(
        "products.Product",
        blank=True,
        related_name="coupons",
        help_text="Only for product coupons — the products the discount applies to.",
    )
    starts_on = models.DateField(help_text="First day the code works.")
    ends_on = models.DateField(help_text="Last day the code works (inclusive).")
    is_active = models.BooleanField(
        default=True, help_text="Off means retired — the code stops working."
    )

    objects = CouponQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_on", "code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")),
                name="coupon_ends_after_it_starts",
            ),
            models.CheckConstraint(
                condition=Q(percent_off__gte=1, percent_off__lte=100),
                name="coupon_percent_between_1_and_100",
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.normalize(self.code)
        super().save(*args, **kwargs)

    @staticmethod
    def normalize(code: str) -> str:
        """Codes are compared trimmed and upper-cased: ``fall26 `` is ``FALL26``."""
        return code.strip().upper()

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError(
                {"ends_on": "A promotion can't end before it starts."}
            )
        if (
            self.scope == self.Scope.ORDER
            and self.percent_off
            and self.percent_off > self.MAX_ORDER_PERCENT
        ):
            raise ValidationError(
                {
                    "percent_off": "Whole-order coupons can take at most "
                    f"{self.MAX_ORDER_PERCENT}% off."
                }
            )

    # --- State ---------------------------------------------------------------

    @property
    def status(self) -> str:
        """Retired, Scheduled, Expired, or Live — for the back office."""
        today = timezone.localdate()
        if not self.is_active:
            return "Retired"
        if today < self.starts_on:
            return "Scheduled"
        if today > self.ends_on:
            return "Expired"
        return "Live"

    @property
    def is_used(self) -> bool:
        """Any order, cancelled included, has used it — its terms are frozen."""
        return self.orders.exists()

    @property
    def needs_double_check(self) -> bool:
        return (
            self.scope == self.Scope.PRODUCTS and self.percent_off >= self.WARN_PERCENT
        )

    # --- Redemption ----------------------------------------------------------

    def check_redeemable(self, *, user, lines: Sequence) -> None:
        """Raise ``CouponError`` if ``user`` can't use this coupon on ``lines``.

        A coupon that hasn't started reads as unknown, so an unannounced
        promotion can't be confirmed early. Cancelled orders give the
        customer their one use back.
        """
        today = timezone.localdate()
        if today < self.starts_on:
            raise CouponError(f"{self.code} isn't a valid code.")
        if today > self.ends_on:
            ended = date_format(self.ends_on, "F j, Y")
            raise CouponError(f"{self.code} expired on {ended}.")
        if not self.is_active:
            raise CouponError(f"{self.code} is no longer available.")
        if self.orders.filter(user=user).exclude(status=CANCELLED).exists():
            raise CouponError(f"You've already used {self.code}.")
        if self.scope == self.Scope.PRODUCTS:
            eligible = self._product_ids()
            if not any(line.product.pk in eligible for line in lines):
                names = ", ".join(product.name for product in self.products.all())
                raise CouponError(
                    f"{self.code} applies only to {names}. "
                    "Add it to your cart to use this code."
                )

    def discounts(
        self, lines: Iterable[tuple[object, Decimal]]
    ) -> tuple[list[Decimal], Decimal]:
        """Price the discount for ``(product, line_total)`` pairs.

        Returns ``(line_discounts, total_discount)``. Product coupons
        discount each matching line, rounded once per line; whole-order
        coupons round once on the subtotal and leave every line at zero.
        Shared by ``place_order`` and the seed, so the math has one home.
        """
        lines = list(lines)
        if self.scope == self.Scope.ORDER:
            subtotal = sum((line_total for _, line_total in lines), ZERO)
            return [ZERO] * len(lines), percent_of(subtotal, self.percent_off)
        eligible = self._product_ids()
        line_discounts = [
            percent_of(line_total, self.percent_off) if product.pk in eligible else ZERO
            for product, line_total in lines
        ]
        return line_discounts, sum(line_discounts, ZERO)

    def _product_ids(self) -> set[int]:
        return {product.pk for product in self.products.all()}
