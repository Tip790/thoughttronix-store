"""Product images: upload validation, normalization, display, and file cleanup."""

import os
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import transaction
from django.urls import reverse
from PIL import Image

from .forms import ProductForm
from .images import normalize_image
from .management.commands.seed import SEED_IMAGES
from .models import Product

pytestmark = pytest.mark.django_db


def picture_bytes(size=(600, 500), fmt="PNG", **save_kwargs):
    """A noisy picture (so it doesn't compress to nothing) encoded as ``fmt``."""
    picture = Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
    buffer = BytesIO()
    picture.save(buffer, fmt, **save_kwargs)
    return buffer.getvalue()


def upload(content=None, name="photo.png"):
    return SimpleUploadedFile(name, picture_bytes() if content is None else content)


def form_data(product, **overrides):
    data = {
        "name": product.name,
        "slug": product.slug,
        "price": str(product.price),
        "category": str(product.category.pk),
        "is_available": "on",
    }
    data.update(overrides)
    return data


def image_errors(product, file):
    form = ProductForm(form_data(product), {"image": file}, instance=product)
    assert not form.is_valid()
    return form.errors["image"]


def give_image(product, name="old.webp"):
    product.image = ContentFile(picture_bytes(fmt="WEBP"), name=name)
    product.save()
    return product.image.name


# --- Validation: one test per rule -----------------------------------------


def test_rejects_a_file_that_isnt_a_picture(product):
    errors = image_errors(product, upload(b"not a picture at all", name="photo.jpg"))

    assert errors == [
        "This file isn't a picture we can use. Please upload a JPEG, PNG, or WebP "
        "image."
    ]


def test_rejects_a_real_picture_in_another_format(product):
    errors = image_errors(product, upload(picture_bytes(fmt="GIF"), name="a.gif"))

    assert errors == [
        "We can't use GIF images. Please save it as a JPEG or PNG and try again."
    ]


def test_names_heic_even_though_pillow_cant_open_it(product):
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64

    errors = image_errors(product, upload(heic, name="IMG_0042.HEIC"))

    assert errors == [
        "We can't use HEIC images. Please save it as a JPEG or PNG and try again."
    ]


def test_rejects_files_over_10_mb(product):
    too_big = b"\x00" * int(14.2 * 1024 * 1024)

    errors = image_errors(product, upload(too_big))

    assert errors == [
        "This image is 14.2 MB, which is over our 10 MB limit. Please use a "
        "smaller file."
    ]


def test_rejects_pictures_under_400_pixels_on_a_side(product):
    errors = image_errors(product, upload(picture_bytes(size=(250, 180))))

    assert errors == [
        "This image is only 250 × 180 pixels, so it would look blurry on the "
        "product page. Please use one at least 400 pixels on each side."
    ]


DAMAGED = (
    "This image appears to be damaged or incomplete. Please try exporting it again."
)


def test_rejects_a_truncated_picture(product):
    whole = picture_bytes()

    errors = image_errors(product, upload(whole[: len(whole) // 2]))

    assert errors == [DAMAGED]


@pytest.mark.parametrize("limit", [500 * 400, 600 * 500 // 2 - 1])
def test_rejects_decompression_bombs(product, monkeypatch, limit):
    # The upload is 600 × 500. Past the limit Pillow warns; past twice
    # the limit it raises. Both reject.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", limit)

    assert image_errors(product, upload()) == [DAMAGED]


# --- Normalization -----------------------------------------------------------


def test_normalize_shrinks_to_webp_and_strips_metadata():
    exif = Image.Exif()
    exif[0x010F] = "SpyCam Inc."  # Make
    exif[0x8825] = {2: (35.0, 11.0, 0.0)}  # GPS IFD: latitude
    source = BytesIO(picture_bytes(size=(2400, 1600), fmt="JPEG", exif=exif))
    assert Image.open(source).getexif()  # the fixture really carries EXIF

    result = normalize_image(source, "upload.jpeg")

    assert result.name == "upload.webp"
    with Image.open(result) as picture:
        assert picture.format == "WEBP"
        assert picture.size == (1200, 800)
        assert not picture.getexif()
        assert "exif" not in picture.info and "xmp" not in picture.info


def test_normalize_never_upscales():
    result = normalize_image(BytesIO(picture_bytes(size=(500, 450))), "small.png")

    with Image.open(result) as picture:
        assert picture.size == (500, 450)


# --- Display -----------------------------------------------------------------


def test_product_without_image_uses_category_placeholder(client, product):
    assert product.image_url == "/static/images/placeholders/home-assistants.svg"
    assert product.image_url in client.get(product.get_absolute_url()).content.decode()


def test_product_with_image_uses_it(client, product):
    give_image(product)

    assert product.image_url.startswith("/media/products/")
    for url in (reverse("products:catalog"), product.get_absolute_url()):
        assert product.image_url in client.get(url).content.decode()


# --- Back-office uploads -----------------------------------------------------


def test_staff_upload_is_stored_as_normalized_webp(client, staff_user, product):
    client.force_login(staff_user)

    client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        form_data(product, image=upload(picture_bytes(size=(1600, 2000)))),
    )

    product.refresh_from_db()
    assert product.image.name.endswith(".webp")
    with product.image.open() as stored, Image.open(stored) as picture:
        assert picture.size == (960, 1200)


def test_failed_form_asks_to_reselect_the_file(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        form_data(product, name="", image=upload()),
    )

    assert "Please choose the file again" in response.content.decode()
    product.refresh_from_db()
    assert not product.image


# --- File cleanup ------------------------------------------------------------


def test_replacing_an_image_deletes_the_old_file(
    client, staff_user, product, django_capture_on_commit_callbacks
):
    old = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            form_data(product, image=upload()),
        )

    product.refresh_from_db()
    assert product.image.name != old
    assert default_storage.exists(product.image.name)
    assert not default_storage.exists(old)


def test_removing_an_image_reverts_to_placeholder_and_deletes_the_file(
    client, staff_user, product, django_capture_on_commit_callbacks
):
    old = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            form_data(product, remove_image="on"),
        )

    product.refresh_from_db()
    assert not product.image
    assert not default_storage.exists(old)


def test_saving_without_a_new_file_keeps_the_image(
    client, staff_user, product, django_capture_on_commit_callbacks
):
    old = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            form_data(product, tagline="Still listening."),
        )

    product.refresh_from_db()
    assert product.image.name == old
    assert default_storage.exists(old)


def test_deleting_a_product_deletes_its_image(
    client, staff_user, product, django_capture_on_commit_callbacks
):
    old = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_delete", kwargs={"pk": product.pk})
        )

    assert not Product.objects.exists()
    assert not default_storage.exists(old)


def test_rolled_back_save_keeps_the_old_file(
    product, django_capture_on_commit_callbacks
):
    old = give_image(product)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError), transaction.atomic():
            product.image = ContentFile(picture_bytes(fmt="WEBP"), name="new.webp")
            product.save()
            raise RuntimeError("the rest of the request failed")

    assert callbacks == []
    assert default_storage.exists(old)


# --- Seed --------------------------------------------------------------------


def test_seed_attaches_exactly_the_mapped_images():
    call_command("seed")

    with_images = Product.objects.exclude(image="")
    assert sorted(with_images.values_list("slug", flat=True)) == sorted(SEED_IMAGES)
    assert Product.objects.filter(image="").count() == 22
    for product in with_images:
        assert product.image.name.endswith(".webp")
        assert default_storage.exists(product.image.name)


def test_reseeding_leaves_no_orphaned_files():
    call_command("seed")
    call_command("seed")

    _, files = default_storage.listdir("products")
    assert len(files) == len(SEED_IMAGES)
