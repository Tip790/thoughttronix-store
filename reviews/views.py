"""Review views — thin per the architecture convention.

Every endpoint is keyed by product pk and looks the product up across the
whole catalog, unavailable products included; an unknown pk is a 404.
The author's own review is always reached through ``request.user`` —
never fetched by id — so no customer can touch another's review.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from products.models import Product

from .forms import ReviewForm
from .models import Review

REVIEWS_PER_PAGE = 10
SLOT_TEMPLATE = "reviews/partials/_author_slot.html"


def slot_context(user, product, form=None):
    """The visitor's own slot in whichever state applies.

    Signed out → the sign-in link; has a review → their card; a buyer →
    the form (``form`` carries errors and typed values back); otherwise
    the only-buyers note.
    """
    if not user.is_authenticated:
        return {"slot": "sign_in"}
    own = Review.objects.filter(user=user, product=product).first()
    if own is not None:
        return {"slot": "card", "own_review": own}
    if Review.can_review(user, product):
        return {"slot": "form", "form": form or ReviewForm()}
    return {"slot": "note"}


class ReviewSectionView(TemplateView):
    """The whole reviews section — the single source for its content.

    The product detail page loads it once the page loads, so the product
    detail view itself never touches reviews. The visitor's own review
    lives in their slot, so it's left out of the list below.
    """

    template_name = "reviews/partials/_section.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        product = get_object_or_404(Product, pk=self.kwargs["pk"])
        reviews = product.reviews.select_related("user")
        others = reviews.exclude(user=user) if user.is_authenticated else reviews
        context.update(
            product=product,
            summary=reviews.summary(),
            reviews=others[:REVIEWS_PER_PAGE],
            **slot_context(user, product),
        )
        return context


class ReviewCreateView(LoginRequiredMixin, View):
    """Create the requesting user's review, then re-render their slot.

    A review that already exists (a double submit or a stale tab) is
    returned as-is and nothing is created; a non-buyer gets the note;
    invalid input comes back as the form with its errors. Every response
    carries the summary out of band.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = None
        reviewed = Review.objects.filter(user=request.user, product=product).exists()
        if not reviewed and Review.can_review(request.user, product):
            form = ReviewForm(request.POST)
            if form.is_valid():
                form.instance.user = request.user
                form.instance.product = product
                try:
                    with transaction.atomic():
                        form.save()
                except IntegrityError:
                    pass  # A concurrent submit won the race; show its card.
                form = None
        return render(
            request,
            SLOT_TEMPLATE,
            {
                "product": product,
                "summary": product.reviews.summary(),
                "oob_summary": True,
                **slot_context(request.user, product, form),
            },
        )
