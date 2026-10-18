"""Wishlist context for every page render.

Each Save button needs to know on page load whether its product is already
saved — one small query per authenticated request supplies the whole set.
"""

from .models import WishlistItem


def wishlists(request):
    if not request.user.is_authenticated:
        return {"wishlist_product_ids": set()}
    return {
        "wishlist_product_ids": set(
            WishlistItem.objects.filter(wishlist__user=request.user).values_list(
                "product_id", flat=True
            )
        )
    }
