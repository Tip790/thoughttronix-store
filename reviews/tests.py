import ast
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateNotUsed, assertTemplateUsed

from products.models import Product

from .admin import ReviewAdmin
from .models import Review


def review(user, product, rating=4, comment="Does exactly what it says.", **kwargs):
    return Review.objects.create(
        user=user, product=product, rating=rating, comment=comment, **kwargs
    )


def section_url(product):
    return reverse("reviews:section", kwargs={"pk": product.pk})


# --- Model behavior ---------------------------------------------------------


def test_display_name_is_first_name_and_last_initial(customer, other_customer):
    named = customer
    named.first_name, named.last_name = "Mira", "Kovacs"
    first_name_only = get_user_model()(username="ada", first_name="Ada")
    unnamed = other_customer

    assert Review(user=named).display_name == "Mira K."
    assert Review(user=first_name_only).display_name == "Ada"
    assert Review(user=unnamed).display_name == "other"


def test_summary_is_average_and_count_in_one_query(
    django_assert_num_queries,
    customer,
    other_customer,
    staff_user,
    product,
    unavailable_product,
):
    review(customer, product, rating=5)
    review(other_customer, product, rating=4)
    review(staff_user, product, rating=4)
    review(customer, unavailable_product, rating=1)

    with django_assert_num_queries(1):
        summary = product.reviews.summary()

    assert summary["average"] == pytest.approx(13 / 3)
    assert summary["count"] == 3
    assert Review.objects.none().summary() == {"average": None, "count": 0}


def test_user_product_pair_is_unique(customer, product):
    review(customer, product)

    with pytest.raises(IntegrityError):
        review(customer, product, rating=2)


@pytest.mark.parametrize("rating", [0, 6])
def test_database_rejects_rating_outside_one_to_five(customer, product, rating):
    with pytest.raises(IntegrityError):
        review(customer, product, rating=rating)


def test_rating_validators_reject_outside_one_to_five(customer, product):
    with pytest.raises(ValidationError) as error:
        Review(user=customer, product=product, rating=6, comment="x").full_clean()

    assert "rating" in error.value.message_dict


def test_deleting_a_product_deletes_its_reviews(customer, product):
    review(customer, product)

    product.delete()

    assert not Review.objects.exists()


def test_reviews_are_newest_first(customer, other_customer, product):
    older = review(customer, product, created_at=timezone.now() - timedelta(days=1))
    newer = review(other_customer, product)

    assert list(product.reviews.all()) == [newer, older]


def test_a_review_saved_once_is_not_edited(customer, product):
    saved = review(customer, product, created_at=timezone.now() - timedelta(days=30))

    saved.refresh_from_db()

    assert saved.updated_at == saved.created_at
    assert not saved.is_edited


def test_saving_again_marks_the_review_edited(customer, product):
    saved = review(customer, product, created_at=timezone.now() - timedelta(days=30))

    saved.rating = 2
    saved.save()
    saved.refresh_from_db()

    assert saved.is_edited


def test_str(customer, product):
    assert str(review(customer, product, rating=5)) == (
        "5★ Seraphine Home Hub by customer"
    )


# --- The reviews section ----------------------------------------------------


def test_section_shows_summary_and_ten_newest_reviews(client, product, category):
    now = timezone.now()
    for i in range(11):
        reviewer = get_user_model().objects.create_user(username=f"reviewer{i}")
        review(
            reviewer,
            product,
            rating=1 + i % 5,
            comment=f"Comment #{i:02d}, newest first.",
            created_at=now - timedelta(days=i),
        )
    quiet = Product.objects.create(
        name="Quiet Thing", slug="quiet-thing", price=1, category=category
    )

    content = client.get(section_url(product)).content.decode()

    assert "★ 2.8 · 11 reviews" in content
    positions = [content.index(f"Comment #{i:02d}") for i in range(10)]
    assert positions == sorted(positions)
    assert "Comment #10" not in content
    assert "No reviews yet" in client.get(section_url(quiet)).content.decode()


def test_section_card_shows_reviewer_badge_date_and_edited_marker(
    client, customer, other_customer, product
):
    customer.first_name, customer.last_name = "Mira", "Kovacs"
    customer.save()
    edited = review(customer, product, created_at=timezone.now() - timedelta(days=3))
    edited.save()
    review(other_customer, product)

    response = client.get(section_url(product))
    content = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assert "Mira K." in content
    assert "Kovacs" not in content
    assert content.count("Verified purchase") == 2
    assert content.count("edited") == 1
    assert "★ 4.0 · 2 reviews" in content
    assert 'id="review-author-slot"' in content


def test_section_singular_summary(client, customer, product):
    review(customer, product, rating=5)

    assert "★ 5.0 · 1 review\n" in client.get(section_url(product)).content.decode()


def test_section_works_for_unavailable_products(client, customer, unavailable_product):
    review(customer, unavailable_product)

    response = client.get(section_url(unavailable_product))

    assert response.status_code == HTTPStatus.OK
    assert "1 review" in response.content.decode()


def test_section_is_a_partial(client, product):
    response = client.get(section_url(product))

    assertTemplateUsed(response, "reviews/partials/_section.html")
    assertTemplateNotUsed(response, "base.html")


def test_unknown_product_pk_is_404(client, db):
    response = client.get(reverse("reviews:section", kwargs={"pk": 99999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


# --- The product detail page ------------------------------------------------


@pytest.mark.parametrize("signed_in", [False, True])
def test_detail_page_loads_the_section(client, customer, product, signed_in):
    if signed_in:
        client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert f'hx-get="{section_url(product)}"' in content
    assert 'hx-trigger="load"' in content


def test_detail_view_does_not_load_reviews(client, customer, product):
    review(customer, product)

    response = client.get(product.get_absolute_url())

    assert "reviews" not in response.context
    assert "summary" not in response.context


# --- Admin ------------------------------------------------------------------


def test_admin_lists_filters_and_searches_reviews(admin_client, customer, product):
    review(customer, product, comment="Listens a little too well.")
    changelist = reverse("admin:reviews_review_changelist")

    listing = admin_client.get(changelist)
    filtered = admin_client.get(changelist, {"rating__exact": 4})
    searched = admin_client.get(changelist, {"q": "too well"})
    missed = admin_client.get(changelist, {"q": "nothing like it"})

    assert listing.status_code == HTTPStatus.OK
    assert listing.context["cl"].list_display[1:] == [
        "product",
        "user",
        "rating",
        "created_at",
        "updated_at",
    ]
    assert filtered.context["cl"].result_count == 1
    assert searched.context["cl"].result_count == 1
    assert missed.context["cl"].result_count == 0
    assert ReviewAdmin.list_filter == ("product", "rating")


# --- Boundaries -------------------------------------------------------------


@pytest.mark.parametrize(
    "app", ["products", "orders", "coupons", "wishlists", "accounts"]
)
def test_other_apps_do_not_import_reviews(app):
    """Only ``seed`` (Phase 5) may import ``reviews``; templates include it."""
    for path in (settings.BASE_DIR / app).rglob("*.py"):
        if path.name == "seed.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                name == "reviews" or name.startswith("reviews.") for name in names
            ), f"{path} imports reviews"
