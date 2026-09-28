from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AddressForm, SignInForm, SignupForm
from .models import Address


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- The address book --------------------------------------------------------


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    success_url = reverse_lazy("accounts:address_list")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(OwnAddressesMixin, ListView):
    template_name = "accounts/address_list.html"
    context_object_name = "addresses"


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
