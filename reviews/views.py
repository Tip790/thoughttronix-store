"""Review views — thin per the architecture convention.

Every endpoint is keyed by product pk and looks the product up across the
whole catalog, unavailable products included; an unknown pk is a 404.
"""

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from products.models import Product

REVIEWS_PER_PAGE = 10


class ReviewSectionView(TemplateView):
    """The whole reviews section — the single source for its content.

    The product detail page loads it once the page loads, so the product
    detail view itself never touches reviews.
    """

    template_name = "reviews/partials/_section.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, pk=self.kwargs["pk"])
        reviews = product.reviews.select_related("user")
        context.update(
            product=product,
            summary=reviews.summary(),
            reviews=reviews[:REVIEWS_PER_PAGE],
        )
        return context
