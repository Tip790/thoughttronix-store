"""Review views — thin per the architecture convention.

Every endpoint is keyed by product pk and looks the product up across the
whole catalog, unavailable products included; an unknown pk is a 404.
The author's own review is always reached through ``request.user`` —
never fetched by id — so no customer can touch another's review.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView, TemplateView

from products.models import Product

from .forms import ReviewForm
from .models import Review

REVIEWS_PER_PAGE = 10
SLOT_TEMPLATE = "reviews/partials/_author_slot.html"


def other_reviews(user, product):
    """Everyone's reviews of ``product`` but the visitor's own, newest first.

    The section's list and every Show more batch page through this same
    queryset; the visitor's own review lives in their slot instead.
    """
    reviews = product.reviews.select_related("user")
    return reviews.exclude(user=user) if user.is_authenticated else reviews


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


def render_slot(request, product, oob_summary=False, **state):
    """Render the author's slot, in ``state`` or else its current state.

    Writes pass ``oob_summary`` so the summary line refreshes with them.
    """
    context = {"product": product, **(state or slot_context(request.user, product))}
    if oob_summary:
        context.update(summary=product.reviews.summary(), oob_summary=True)
    return render(request, SLOT_TEMPLATE, context)


class OwnReviewView(LoginRequiredMixin, View):
    """Base for the endpoints that act on the requesting user's own review.

    The review is found only through ``request.user``, so another
    customer's review is never in reach. When there is none — a stale tab
    after a delete, or a review that was never written — the slot comes
    back in its current state (the form or the note), never an error.
    Authorship is the only gate: eligibility is checked on create alone,
    so a later cancellation never locks an author out.
    """

    def own_review(self, pk):
        product = get_object_or_404(Product, pk=pk)
        review = Review.objects.filter(user=self.request.user, product=product)
        return product, review.first()


class ReviewEditView(OwnReviewView):
    """The author's review as a pre-filled form, in the same slot."""

    def get(self, request, pk):
        product, review = self.own_review(pk)
        if review is None:
            return render_slot(request, product)
        return render_slot(
            request,
            product,
            slot="edit",
            own_review=review,
            form=ReviewForm(instance=review),
        )


class ReviewUpdateView(OwnReviewView):
    """Save the author's edit and return the updated card, or the form with
    its errors. A save refreshes the summary out of band."""

    def post(self, request, pk):
        product, review = self.own_review(pk)
        if review is None:
            return render_slot(request, product, oob_summary=True)
        form = ReviewForm(request.POST, instance=review)
        if not form.is_valid():
            return render_slot(
                request, product, slot="edit", own_review=review, form=form
            )
        form.save()
        return render_slot(request, product, oob_summary=True)


class ReviewCardView(OwnReviewView):
    """The author's own card, unchanged — Cancel and Keep it fetch this."""

    def get(self, request, pk):
        product, _ = self.own_review(pk)
        return render_slot(request, product)


class ReviewDeleteConfirmView(OwnReviewView):
    """The author's card in its "Delete this review?" state."""

    def get(self, request, pk):
        product, review = self.own_review(pk)
        if review is None:
            return render_slot(request, product)
        return render_slot(request, product, slot="confirm_delete", own_review=review)


class ReviewDeleteView(OwnReviewView):
    """Delete the author's review and return their slot's new state — the
    empty form for a buyer — with the summary out of band."""

    def post(self, request, pk):
        product, review = self.own_review(pk)
        if review is not None:
            review.delete()
        return render_slot(request, product, oob_summary=True)


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
        page = Paginator(other_reviews(user, product), REVIEWS_PER_PAGE).page(1)
        context.update(
            product=product,
            summary=product.reviews.summary(),
            reviews=page.object_list,
            page_obj=page,
            **slot_context(user, product),
        )
        return context


class ReviewMoreView(ListView):
    """The next batch of other customers' reviews, behind Show more.

    Public, like the section. ``?page=N`` continues the section's list,
    and the batch carries a fresh button only while more remain.
    """

    template_name = "reviews/partials/_more_reviews.html"
    context_object_name = "reviews"
    paginate_by = REVIEWS_PER_PAGE

    def get_queryset(self):
        self.product = get_object_or_404(Product, pk=self.kwargs["pk"])
        return other_reviews(self.request.user, self.product)

    def get_context_data(self, **kwargs):
        return super().get_context_data(product=self.product, **kwargs)


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
