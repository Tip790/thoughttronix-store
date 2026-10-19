from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """The superuser's moderation tool — the only one; there's no back-office tab."""

    list_display = ("product", "user", "rating", "created_at", "updated_at")
    list_filter = ("product", "rating")
    search_fields = ("comment",)
    list_select_related = ("product", "user")
