from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .emails import (
    send_email_changed_email,
    send_password_changed_email,
    send_verification_email,
)
from .forms import (
    AddressForm,
    ChangeEmailForm,
    ChangePasswordForm,
    NewPasswordForm,
    PasswordResetRequestForm,
    SignInForm,
    SignupForm,
)
from .models import Address
from .tokens import user_for_verification_token


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account and sign the new customer straight in.

    They land on the catalog, ready to shop, without retyping the
    password they just chose. A link to confirm their email is on its
    way, but confirming never stands between them and checkout. Nobody
    ticked "Remember me", so the session ends when the browser closes.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("products:catalog")
    success_message = (
        "Welcome to ThoughtTronix — your account is ready. We sent a link "
        "to %(email)s to confirm your email address."
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        self.request.session.set_expiry(0)
        send_verification_email(self.request, self.object)
        return response


class SignInView(LoginView):
    """Sign in by username. Without "Remember me" the session ends when
    the browser closes; with it, it lasts the standard two weeks."""

    template_name = "accounts/login.html"
    authentication_form = SignInForm

    def form_valid(self, form):
        response = super().form_valid(form)
        # 0 = until the browser closes; None = SESSION_COOKIE_AGE.
        self.request.session.set_expiry(None if form.cleaned_data["remember_me"] else 0)
        return response


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- The Account page and email confirmation ---------------------------------


class AccountView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/account.html"


class ResendVerificationView(LoginRequiredMixin, View):
    """POST-only: email the signed-in user a fresh confirmation link."""

    def post(self, request):
        user = request.user
        if user.email_verified:
            messages.info(request, "Your email is already confirmed.")
        elif not user.email:
            messages.error(request, "There's no email on your account to confirm.")
        elif send_verification_email(request, user):
            messages.success(
                request, f"We sent a new confirmation link to {user.email}."
            )
        else:
            messages.warning(
                request,
                "We've sent several confirmation links recently. Check your "
                "inbox and spam folder, or try again in an hour.",
            )
        return redirect("accounts:account")


class VerifyEmailView(TemplateView):
    """The target of the emailed link; works signed in or not.

    GET only shows the page, and its button POSTs the confirmation, so a
    mail scanner that pre-fetches links can't confirm on the customer's
    behalf — every state change here is a POST.
    """

    template_name = "accounts/verify_email.html"

    def dispatch(self, request, *args, token, **kwargs):
        self.verified_user = user_for_verification_token(token)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(verified_user=self.verified_user, **kwargs)

    def post(self, request):
        if self.verified_user is None:
            return self.get(request)
        self.verified_user.email_verified = True
        self.verified_user.save(update_fields=["email_verified"])
        messages.success(request, f"Thanks — {self.verified_user.email} is confirmed.")
        if request.user == self.verified_user:
            return redirect("accounts:account")
        return redirect("products:catalog")


# --- Forgotten passwords -----------------------------------------------------


class PasswordResetRequestView(auth_views.PasswordResetView):
    """Ask for a reset link by email.

    Known or unknown, every email lands on the same "check your inbox"
    page, so the form can't be used to learn who shops here.
    """

    form_class = PasswordResetRequestForm
    template_name = "accounts/password_reset_form.html"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    email_template_name = "accounts/email/password_reset.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """The target of the emailed link: choose a new password.

    The link works once — the new password retires its token — and
    proves the customer reads this inbox, so it confirms the email too.
    There's no auto-login: they sign in with the new password, which
    shows it works.
    """

    form_class = NewPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        send_password_changed_email(self.request, user)
        messages.success(
            self.request, "Your password has been reset. Sign in with your new one."
        )
        return response


# --- Changing the password and the email ------------------------------------


class PasswordChangeView(auth_views.PasswordChangeView):
    """Swap the current password for a new one.

    Django re-stamps this session with the new password's hash, so this
    device stays signed in while every other session signed in as the
    user is signed out.
    """

    form_class = ChangePasswordForm
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_changed_email(self.request, form.user)
        return response


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class EmailChangeView(LoginRequiredMixin, FormView):
    """Move the account to a new email, confirmed with the password.

    The new address starts unconfirmed and gets a fresh link; the old one
    is told about the change, in case it wasn't the owner who made it.
    """

    form_class = ChangeEmailForm
    template_name = "accounts/email_change_form.html"
    success_url = reverse_lazy("accounts:account")

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        user = self.request.user
        old_email = user.email
        user.change_email(form.cleaned_data["email"])
        sent = send_verification_email(self.request, user)
        send_email_changed_email(user, old_email)
        if sent:
            follow_up = "We sent a link there to confirm it."
        else:
            follow_up = "You can ask for a confirmation link from this page later."
        messages.success(self.request, f"Your email is now {user.email}. {follow_up}")
        return super().form_valid(form)


# --- The address book --------------------------------------------------------


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    success_url = reverse_lazy("accounts:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(OwnAddressesMixin, ListView):
    template_name = "accounts/address_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return super().get_queryset().order_by("label")


class AddressCreateView(OwnAddressesMixin, SuccessMessageMixin, CreateView):
    """Add an address; a customer's first address becomes both defaults."""

    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address saved."

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        self.object.fill_empty_defaults(*Address.ROLES)
        return response


class AddressUpdateView(OwnAddressesMixin, SuccessMessageMixin, UpdateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address saved."


class AddressDeleteView(OwnAddressesMixin, SuccessMessageMixin, DeleteView):
    """Delete an address. A deleted default leaves no default behind —
    the store never guesses which address should take its place."""

    template_name = "accounts/address_confirm_delete.html"
    context_object_name = "address"
    success_message = "Address deleted."


class MakeDefaultAddressView(LoginRequiredMixin, View):
    """POST-only: make one of the customer's addresses a default."""

    def post(self, request, pk, role):
        if role not in Address.ROLES:
            raise Http404
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.make_default(role)
        messages.success(request, f"{address} is now your default {role} address.")
        return redirect("accounts:address_list")
