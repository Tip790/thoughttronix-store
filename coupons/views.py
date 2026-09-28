"""Back-office coupon management — marketing is staff.

Every view gates on ``StaffRequiredMixin``; URLs use pks. Retiring is a
flag flip, never a delete: only coupons no order has used can be deleted.
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import CouponForm
from .models import Coupon

STATUS_FILTERS = {"active": Q(is_active=True), "retired": Q(is_active=False)}


class ManageCouponListView(StaffRequiredMixin, ListView):
    """Every coupon with its usage, filterable via ``?status=active|retired``."""

    template_name = "coupons/manage_coupons.html"
    context_object_name = "coupons"
    extra_context = {"section": "coupons"}

    def get_queryset(self):
        coupons = Coupon.objects.with_usage().prefetch_related("products")
        status = self.request.GET.get("status", "")
        if status in STATUS_FILTERS:
            coupons = coupons.filter(STATUS_FILTERS[status])
        return coupons

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_status"] = self.request.GET.get("status", "")
        return context


class CouponFormViewMixin(StaffRequiredMixin, SuccessMessageMixin):
    """Shared create/edit wiring, plus the non-blocking deep-discount warning."""

    model = Coupon
    form_class = CouponForm
    template_name = "coupons/manage_coupon_form.html"
    success_url = reverse_lazy("coupons:manage_coupons")
    extra_context = {
        "section": "coupons",
        "max_order_percent": Coupon.MAX_ORDER_PERCENT,
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.needs_double_check:
            messages.warning(
                self.request,
                f"{self.object.code} takes {self.object.percent_off}% off. "
                "Double-check the products and dates before it goes live.",
            )
        return response


class ManageCouponCreateView(CouponFormViewMixin, CreateView):
    success_message = "%(code)s created."


class ManageCouponUpdateView(CouponFormViewMixin, UpdateView):
    success_message = "%(code)s saved."


class ManageCouponDeleteView(StaffRequiredMixin, DeleteView):
    """Delete an unused coupon; a used one is refused — retire it instead."""

    model = Coupon
    context_object_name = "coupon"
    template_name = "coupons/manage_coupon_confirm_delete.html"
    success_url = reverse_lazy("coupons:manage_coupons")
    extra_context = {"section": "coupons"}

    def form_valid(self, form):
        if self.object.is_used:
            messages.error(
                self.request,
                f"{self.object.code} has been used by orders, so it can't be "
                "deleted. Retire it instead.",
            )
            return redirect(self.success_url)
        messages.success(self.request, f"{self.object.code} deleted.")
        return super().form_valid(form)


class ToggleCouponView(StaffRequiredMixin, View):
    """POST-only: retire an active coupon, or bring a retired one back."""

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=["is_active"])
        if coupon.is_active:
            messages.success(request, f"{coupon.code} is active again.")
        else:
            messages.success(request, f"{coupon.code} retired.")
        return redirect("coupons:manage_coupons")
