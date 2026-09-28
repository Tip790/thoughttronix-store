"""The checkout form — the codebase's showcase of declarative validation.

Every rule is visible at its field declaration, in the style of data
annotations: field types validate (``EmailField``), field arguments
validate (``required``, ``max_length``, ``ChoiceField``), and the
``validators=[...]`` list carries the rest. One exception, and only
one: ``clean_coupon_code``, because whether a code is redeemable depends
on the cart and today's date, which no field declaration can see. No
``clean()``.
"""

from django import forms
from django.core.validators import RegexValidator

from accounts.models import US_STATES, zip_validator
from coupons.models import Coupon, CouponError

from .models import Order
from .validators import validate_card_number, validate_expiry

cvv_validator = RegexValidator(r"^\d{3,4}$", "Enter the 3- or 4-digit CVV.")


class CheckoutForm(forms.Form):
    """One page, one POST: contact, shipping, billing, payment.

    Saved addresses only prefill the address fields (via HTMX and the
    view's initial data); the form always validates the typed values.
    """

    email = forms.EmailField(label="Email")

    shipping_name = forms.CharField(label="Full name", max_length=100)
    shipping_street = forms.CharField(label="Street address", max_length=200)
    shipping_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    shipping_city = forms.CharField(label="City", max_length=100)
    shipping_state = forms.ChoiceField(label="State", choices=US_STATES)
    shipping_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    billing_name = forms.CharField(label="Full name", max_length=100)
    billing_street = forms.CharField(label="Street address", max_length=200)
    billing_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    billing_city = forms.CharField(label="City", max_length=100)
    billing_state = forms.ChoiceField(label="State", choices=US_STATES)
    billing_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    card_number = forms.CharField(
        label="Card number", max_length=23, validators=[validate_card_number]
    )
    card_expiry = forms.CharField(
        label="Expiry (MM/YY)", max_length=5, validators=[validate_expiry]
    )
    card_cvv = forms.CharField(label="CVV", max_length=4, validators=[cvv_validator])

    coupon_code = forms.CharField(label="Coupon code", max_length=30, required=False)

    # Opt-in: after the order is placed, copy the section into the
    # customer's address book. Never read by ``place_order``.
    save_shipping_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )
    save_billing_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )

    def __init__(self, *args, cart=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The cart a coupon is checked against; the redeemed coupon lands
        # on ``self.coupon`` for the view's order summary.
        self.cart = cart
        self.coupon = None
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "checkbox checkbox-primary checkbox-sm"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"
        # Joined to its Apply button on the page.
        self.fields["coupon_code"].widget.attrs["class"] = "input join-item w-full"

    def clean_coupon_code(self):
        code = Coupon.normalize(self.cleaned_data["coupon_code"])
        if not code:
            return ""
        if self.cart is None:
            raise ValueError("CheckoutForm needs the cart to check a coupon code.")
        try:
            self.coupon = Coupon.objects.redeemable(
                code, user=self.cart.user, lines=list(self.cart.lines())
            )
        except CouponError as error:
            raise forms.ValidationError(str(error)) from None
        return code

    # Field groups for the template — the form owns its own structure.

    def address_fields(self, role):
        """One address section's fields; ``role`` is shipping or billing."""
        return [self[name] for name in self.fields if name.startswith(f"{role}_")]

    def shipping_fields(self):
        return self.address_fields("shipping")

    def billing_fields(self):
        return self.address_fields("billing")

    def card_fields(self):
        return [self[name] for name in self.fields if name.startswith("card_")]


class OrderStatusForm(forms.ModelForm):
    """The back-office status dropdown — any of the four states, anytime.

    Guarding the workflow (no un-cancelling, no re-shipping a delivered
    order) is deliberately left as a student exercise.
    """

    class Meta:
        model = Order
        fields = ["status"]
        widgets = {"status": forms.Select(attrs={"class": "select"})}
