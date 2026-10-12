from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Address, User


class AddressInline(admin.StackedInline):
    """A customer's address book, shown on their user page."""

    model = Address
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title", "email_verified")}),
    )
    list_display = ("username", "email", "email_verified", "job_title", "is_staff")
    inlines = [AddressInline]
