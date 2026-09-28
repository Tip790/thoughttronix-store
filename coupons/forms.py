"""The back-office coupon form.

The model carries the scalar rules (date order, the whole-order cap);
the form adds the two that need the many-to-many — scope and products
must agree — and freezes a used coupon's terms by disabling them.
"""

from django import forms

from products.forms import StyledModelForm

from .models import Coupon

LOCKED_HELP = (
    "Locked — orders have used this coupon. "
    "Retire it and create a new code to change the deal."
)


class CouponForm(StyledModelForm):
    class Meta:
        model = Coupon
        fields = [
            "code",
            "percent_off",
            "scope",
            "products",
            "starts_on",
            "ends_on",
            "is_active",
        ]
        labels = {"percent_off": "Percent off", "is_active": "Active"}
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "ends_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disabled fields ignore whatever is posted and keep their
        # initial values — the terms of a used coupon cannot change.
        if self.instance.pk and self.instance.is_used:
            for name in Coupon.TERMS:
                self.fields[name].disabled = True
                self.fields[name].help_text = LOCKED_HELP

    def clean_code(self):
        # Normalize before the unique check, so "fall26" collides with FALL26.
        return Coupon.normalize(self.cleaned_data["code"])

    def clean(self):
        cleaned = super().clean()
        scope = cleaned.get("scope")
        products = cleaned.get("products")
        if scope == Coupon.Scope.PRODUCTS and not products:
            self.add_error(
                "products", "Pick at least one product for a product coupon."
            )
        if scope == Coupon.Scope.ORDER and products:
            self.add_error(
                "products",
                "Whole-order coupons don't take products — clear them or "
                "switch to specific products.",
            )
        return cleaned
