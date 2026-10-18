"""Wishlist views — thin per the architecture convention.

Add and Remove are two endpoints, not a toggle, so a double-click or a
stale tab always does what the button's label said. Both act on the
requesting user's own wishlist — never one fetched by id — and look the
product up across the whole catalog, unavailable products included.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from products.models import Product

from .models import Wishlist, WishlistItem


class WishlistView(LoginRequiredMixin, TemplateView):
    """The signed-in user's own wishlist page — no user or wishlist id in the URL."""

    template_name = "wishlists/wishlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = WishlistItem.objects.filter(
            wishlist__user=self.request.user
        ).select_related("product")
        return context


class WishlistActionView(LoginRequiredMixin, View):
    """Base for HTMX wishlist mutations: act, then re-render the button.

    The button reads its state from the ``wishlists`` context processor,
    which runs at render time — after the action — so it shows the new state.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        wishlist = Wishlist.for_user(request.user)
        self.act(wishlist, product)
        return self.respond(wishlist, product)

    def act(self, wishlist, product):
        raise NotImplementedError

    def respond(self, wishlist, product):
        return render(
            self.request,
            "wishlists/partials/_wishlist_button.html",
            {"product": product},
        )


class AddToWishlistView(WishlistActionView):
    def act(self, wishlist, product):
        wishlist.add(product)


class RemoveFromWishlistView(WishlistActionView):
    """Remove; from the wishlist page (``from=wishlist``) re-render its rows."""

    def act(self, wishlist, product):
        wishlist.remove(product)

    def respond(self, wishlist, product):
        if self.request.POST.get("from") != "wishlist":
            return super().respond(wishlist, product)
        return render(
            self.request,
            "wishlists/partials/_wishlist_contents.html",
            {"items": wishlist.items.select_related("product")},
        )
