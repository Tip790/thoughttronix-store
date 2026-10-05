"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. Widgets get their DaisyUI classes
in one shared ``__init__`` loop, as on ``CheckoutForm``.
"""

import math
from decimal import Decimal

from django import forms
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

from . import images
from .models import Category, Product, Tag


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "select h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    # A plain FileField, not forms.ImageField: clean_image does its own
    # decoding so every rejection gets a plain-language reason.
    image = forms.FileField(
        label="Product image",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        help_text="A JPEG, PNG, or WebP, at least 400 pixels on each side and "
        "no larger than 10 MB.",
    )
    remove_image = forms.BooleanField(
        label="Remove image and use the category placeholder",
        required=False,
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "price",
            "category",
            "tags",
            "image",
            "is_available",
            "is_featured",
        ]

    def clean_image(self):
        """Reject unusable uploads with a plain-language reason; normalize the rest."""
        upload = self.cleaned_data.get("image")
        if not isinstance(upload, UploadedFile):
            return upload  # no new file: keep the current image (or none)

        if upload.size > images.MAX_UPLOAD_BYTES:
            megabytes = math.ceil(upload.size / (1024 * 1024) * 10) / 10
            raise forms.ValidationError(
                f"This image is {megabytes:.1f} MB, which is over our 10 MB "
                "limit. Please use a smaller file.",
                code="too_large",
            )

        upload.seek(0)
        try:
            with images.strict_decoding(), Image.open(upload) as picture:
                if picture.format not in images.ACCEPTED_FORMATS:
                    raise self._unsupported(picture.format)
                width, height = picture.size
                if min(width, height) < images.MIN_SIDE:
                    raise forms.ValidationError(
                        f"This image is only {width} × {height} pixels, so it "
                        "would look blurry on the product page. Please use one "
                        f"at least {images.MIN_SIDE} pixels on each side.",
                        code="too_small",
                    )
                picture.load()  # decode every pixel: catches truncated files
        except UnidentifiedImageError:
            format_name = images.sniff_format(upload)
            if format_name:
                raise self._unsupported(format_name) from None
            raise forms.ValidationError(
                "This file isn't a picture we can use. Please upload a JPEG, "
                "PNG, or WebP image.",
                code="not_an_image",
            ) from None
        except (
            OSError,
            SyntaxError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise forms.ValidationError(
                "This image appears to be damaged or incomplete. Please try "
                "exporting it again.",
                code="damaged",
            ) from None

        return images.normalize_image(upload, upload.name)

    @staticmethod
    def _unsupported(format_name):
        return forms.ValidationError(
            f"We can't use {format_name} images. Please save it as a JPEG or "
            "PNG and try again.",
            code="unsupported_format",
        )

    def clean(self):
        cleaned_data = super().clean()
        # A new upload wins over the remove toggle.
        if cleaned_data.get("remove_image") and not self.files.get("image"):
            cleaned_data["image"] = False  # the model field stores "" for False
        return cleaned_data

    @property
    def stored_image(self):
        """The image already saved for this product, whatever was just submitted.

        ``instance.image`` can't serve: validation has already copied an
        unsaved upload (or the removal) onto the instance.
        """
        return self.initial.get("image")

    @property
    def upload_dropped(self):
        """True when a usable file was chosen but the form failed elsewhere.

        Browsers don't refill file inputs, so the employee must pick the
        file again; the template says so.
        """
        return (
            bool(self.files.get("image"))
            and bool(self.errors)
            and "image" not in self.errors
        )


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
