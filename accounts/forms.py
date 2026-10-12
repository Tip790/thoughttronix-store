from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from . import throttle
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
    """The stock authentication form, dressed in DaisyUI, plus "Remember
    me" and a throttle on wrong passwords.

    Too many recent failures for the username, or from the visitor's IP,
    refuse sign-in before the password is even checked — so the right
    password doesn't get through either until the window passes.
    """

    remember_me = forms.BooleanField(label="Remember me", required=False)

    error_messages = {
        **AuthenticationForm.error_messages,
        "throttled": "Too many sign-in attempts — try again later.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password"):
            self.fields[name].widget.attrs["class"] = "input w-full"
        self.fields["remember_me"].widget.attrs["class"] = "checkbox"

    def clean(self):
        username = self.cleaned_data.get("username")
        if username is None or not self.cleaned_data.get("password"):
            return super().clean()
        # REMOTE_ADDR is the direct peer; behind a proxy every visitor
        # would share the proxy's IP.
        ip = self.request.META.get("REMOTE_ADDR") if self.request else None
        if throttle.sign_in_blocked(username, ip):
            raise forms.ValidationError(
                self.error_messages["throttled"], code="throttled"
            )
        try:
            cleaned_data = super().clean()
        except forms.ValidationError as error:
            if error.code == "invalid_login":
                throttle.record_sign_in_failure(username, ip)
            raise
        throttle.clear_sign_in_failures(username)
        return cleaned_data


class PasswordResetRequestForm(PasswordResetForm):
    """The stock "email me a reset link" form, dressed in DaisyUI.

    Django's form already keeps quiet about unknown emails, matches
    emails ignoring case, and only mails active accounts with a usable
    password — verified or not. On top of that, each address gets only a
    few links an hour; past that, nothing is sent, but the page looks
    just the same.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = "input w-full"

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        if throttle.allow_email("reset", to_email):
            super().send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                to_email,
                html_email_template_name=html_email_template_name,
            )


class NewPasswordForm(SetPasswordForm):
    """The stock "choose a new password" form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ChangePasswordForm(PasswordChangeForm):
    """The stock "current password, then a new one twice" form, dressed
    in DaisyUI. The new password runs through the usual validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ChangeEmailForm(forms.Form):
    """A new email, confirmed with the current password.

    The password check means someone who borrowed a signed-in session
    can't redirect the account's recovery email to themselves. Like
    sign-up, a new email must not belong to another account in any
    capitalization.
    """

    email = forms.EmailField(label="New email")
    password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if email == self.user.email:
            raise forms.ValidationError("That's already the email on your account.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("That email is already in use.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Your current password was entered incorrectly. Please try again."
            )
        return password


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
