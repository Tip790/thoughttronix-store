from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone

from products.models import Product


class ReviewQuerySet(models.QuerySet):
    def summary(self):
        """The average rating and review count, in one query.

        With no reviews the average is ``None`` and the count ``0``.
        """
        return self.aggregate(average=Avg("rating"), count=Count("pk"))


class Review(models.Model):
    """A customer's star rating and comment on a product — one per pair.

    ``created_at`` is a default, not auto-now-add, so the seed can backdate
    reviews. ``save`` keeps ``updated_at`` equal to ``created_at`` on the
    first save and stamps it on every later one, so any gap marks an edit.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(editable=False)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_user_product_review"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.rating}★ {self.product.name} by {self.user.username}"

    def save(self, *args, **kwargs):
        self.updated_at = self.created_at if self._state.adding else timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_edited(self):
        """Saved again after posting — the first save leaves the stamps equal."""
        return self.updated_at > self.created_at

    @property
    def display_name(self):
        """The reviewer as first name and last initial, e.g. "Mira K.".

        A first name alone stands alone; no first name falls back to the
        username, so a full name or login never shows.
        """
        first = self.user.first_name.strip()
        last = self.user.last_name.strip()
        if not first:
            return self.user.username
        return f"{first} {last[0]}." if last else first
