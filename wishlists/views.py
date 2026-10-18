"""Wishlist views — thin per the architecture convention.

Add and Remove are two endpoints, not a toggle, so a double-click or a
stale tab always does what the button's label said. Both act on the
requesting user's own wishlist — never one fetched by id — and look the
product up across the whole catalog, unavailable products included.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .models import Wishlist


class WishlistActionView(LoginRequiredMixin, View):
    """Base for HTMX wishlist mutations: act, then re-render the button.

    The button reads its state from the ``wishlists`` context processor,
    which runs at render time — after the action — so it shows the new state.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        self.act(Wishlist.for_user(request.user), product)
        return render(
            request, "wishlists/partials/_wishlist_button.html", {"product": product}
        )

    def act(self, wishlist, product):
        raise NotImplementedError


class AddToWishlistView(WishlistActionView):
    def act(self, wishlist, product):
        wishlist.add(product)


class RemoveFromWishlistView(WishlistActionView):
    def act(self, wishlist, product):
        wishlist.remove(product)
