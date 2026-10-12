from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Address, User


class SignupForm(UserCreationForm):
    """Username, email, and password with confirmation.

    The email is required — it's how a customer recovers their account —
    and must not belong to another account in any capitalization. The
    database constraint is only a backstop; this form gives the friendly
    error. The widgets carry DaisyUI classes because plain Django forms
    own their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "That email is already in use. Sign in instead, or reset "
                "your password if you've forgotten it."
            )
        return email


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class AddressForm(forms.ModelForm):
    """Add or edit a saved address; the model carries every rule.

    Defaults aren't fields here — they change through their own
    "make default" buttons, so a save can never break the one-default rule.
    """

    class Meta:
        model = Address
        fields = ["label", *Address.FIELDS]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"
