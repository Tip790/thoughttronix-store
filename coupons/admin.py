from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "scope", "starts_on", "ends_on", "is_active")
    list_filter = ("is_active", "scope")
    search_fields = ("code",)
    filter_horizontal = ("products",)
