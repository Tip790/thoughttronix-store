from django.db import models, transaction
from django.templatetags.static import static
from django.urls import reverse

# Categories with a dedicated placeholder illustration; anything else
# falls back to default.svg. Products without an uploaded image show
# their category's placeholder, a static file.
PLACEHOLDER_CATEGORIES = {
    "home-assistants",
    "neural-implants",
    "neural-wearables",
    "accessories",
    "defense",
    "legacy-products",
}


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})

    @property
    def placeholder_image(self):
        """Static path of the placeholder image shown for this category's products."""
        if self.slug in PLACEHOLDER_CATEGORIES:
            return f"images/placeholders/{self.slug}.svg"
        return "images/placeholders/default.svg"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def search(self, text):
        """Simple icontains search over name and description."""
        return self.filter(
            models.Q(name__icontains=text) | models.Q(description__icontains=text)
        )


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    # Always a normalized WebP (products/images.py); blank means "use the
    # category placeholder".
    image = models.ImageField(upload_to="products/", blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Save, then delete the replaced or removed image file once committed."""
        old_name = ""
        if not self._state.adding:
            old_name = (
                Product.objects.filter(pk=self.pk)
                .values_list("image", flat=True)
                .first()
                or ""
            )
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self._delete_image_file_on_commit(old_name)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    def delete(self, *args, **kwargs):
        """Delete the product, then its image file once committed."""
        name = self.image.name
        result = super().delete(*args, **kwargs)
        if name:
            self._delete_image_file_on_commit(name)
        return result

    @property
    def image_url(self):
        """URL of the product's picture: its own image, else the category placeholder."""
        if self.image:
            return self.image.url
        return static(self.category.placeholder_image)

    def _delete_image_file_on_commit(self, name):
        # Only after the commit: a rolled-back save must not lose the
        # file the database still points at.
        storage = self.image.storage
        transaction.on_commit(lambda: storage.delete(name))
