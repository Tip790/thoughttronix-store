import ast
import re
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

from conftest import order_for
from orders.models import Order
from products.models import Product

from .admin import ReviewAdmin
from .forms import ReviewForm
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


# --- Eligibility ------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "eligible"),
    [
        (Order.Status.PLACED, True),
        (Order.Status.SHIPPED, True),
        (Order.Status.DELIVERED, True),
        (Order.Status.CANCELLED, False),
    ],
)
def test_only_a_non_cancelled_order_makes_a_buyer(
    customer, product, unavailable_product, status, eligible
):
    order_for(customer, product, status=status)
    order_for(customer, unavailable_product, status=status)

    assert Review.can_review(customer, product) is eligible
    assert Review.can_review(customer, unavailable_product) is eligible


def test_no_order_means_no_review(customer, buyer, product):
    assert not Review.can_review(customer, product)


# --- The form ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("comment", "message"),
    [
        ("", "Write a comment to go with your rating."),
        ("   \n\t ", "Write a comment to go with your rating."),
        ("Too short", "at least 10 characters"),
        ("x" * 2001, "at most 2,000 characters"),
    ],
    ids=["blank", "whitespace", "short", "long"],
)
def test_form_rejects_blank_short_and_long_comments(db, comment, message):
    form = ReviewForm(data={"rating": 4, "comment": comment})

    assert not form.is_valid()
    assert message in " ".join(form.errors["comment"])


def test_form_trims_the_comment_before_checking_its_length(db):
    padded = ReviewForm(data={"rating": 4, "comment": "  Ten chars.  \n"})
    longest = ReviewForm(data={"rating": 4, "comment": f" {'x' * 2000} "})
    short_once_trimmed = ReviewForm(data={"rating": 4, "comment": "  Nine ch  "})

    assert padded.is_valid()
    assert padded.cleaned_data["comment"] == "Ten chars."
    assert longest.is_valid()
    assert not short_once_trimmed.is_valid()


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


# --- Create -----------------------------------------------------------------


def create_url(product):
    return reverse("reviews:create", kwargs={"pk": product.pk})


def test_second_create_returns_the_existing_card_and_creates_nothing(
    client, buyer, product
):
    """A double submit or a stale tab never errors and never doubles up."""
    client.raise_request_exception = False  # See what the browser would see.
    client.force_login(buyer)
    client.post(create_url(product), {"rating": 5, "comment": "First and only."})

    response = client.post(
        create_url(product), {"rating": 1, "comment": "Second go from a stale tab."}
    )

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "First and only." in content
    assert "Second go from a stale tab." not in content
    assert 'id="review-author-slot"' in content
    assert Review.objects.get().rating == 5


def test_create_returns_the_card_and_the_summary_out_of_band(
    client, buyer, other_customer, product
):
    review(other_customer, product, rating=2)
    client.force_login(buyer)

    response = client.post(
        create_url(product), {"rating": "5", "comment": "  Worth every penny.  "}
    )
    content = response.content.decode()

    created = Review.objects.get(user=buyer)
    assert (created.rating, created.comment) == (5, "Worth every penny.")
    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assertTemplateNotUsed(response, "base.html")
    assert "Your review" in content
    assert "Mira K." in content
    assert 'id="review-summary" hx-swap-oob="true"' in content
    assert "★ 3.5 · 2 reviews" in content
    assert "<form" not in content


def test_invalid_create_returns_the_form_with_errors_and_what_was_typed(
    client, buyer, product
):
    client.force_login(buyer)

    response = client.post(create_url(product), {"rating": "3", "comment": "Meh."})
    content = response.content.decode()

    assert not Review.objects.exists()
    assert "at least 10 characters" in content
    assert re.search(r">\s*Meh\.</textarea>", content)
    assert re.search(r'value="3"[^>]*checked', content)
    assert len(re.findall(r'type="radio"[^>]*checked', content)) == 1
    assert "No reviews yet" in content


def test_create_without_a_rating_keeps_the_comment(client, buyer, product):
    client.force_login(buyer)

    response = client.post(create_url(product), {"comment": "Rating forgotten."})
    content = response.content.decode()

    assert not Review.objects.exists()
    assert "Pick a rating from 1 to 5 stars." in content
    assert re.search(r">\s*Rating forgotten\.</textarea>", content)


def test_out_of_range_rating_is_rejected(client, buyer, product):
    client.force_login(buyer)

    response = client.post(
        create_url(product), {"rating": "6", "comment": "Off the charts!"}
    )

    assert not Review.objects.exists()
    assert "Pick a rating from 1 to 5 stars." in response.content.decode()


@pytest.mark.parametrize("who", ["customer", "cancelled_buyer"])
def test_non_buyer_create_creates_nothing_and_returns_the_note(
    request, client, product, who
):
    client.force_login(request.getfixturevalue(who))

    response = client.post(
        create_url(product), {"rating": 5, "comment": "Never bought it, love it."}
    )

    assert not Review.objects.exists()
    assert "Only customers who've bought this product" in response.content.decode()


def test_anonymous_create_redirects_to_login_and_creates_nothing(client, product):
    response = client.post(
        create_url(product), {"rating": 5, "comment": "Drive-by opinion."}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))
    assert not Review.objects.exists()


def test_create_for_an_unknown_product_is_404(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": 99999}),
        {"rating": 5, "comment": "Nothing to review."},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_buyer_can_review_an_unavailable_product(client, buyer, unavailable_product):
    order_for(buyer, unavailable_product)
    client.force_login(buyer)

    client.post(
        create_url(unavailable_product), {"rating": 4, "comment": "Glad I got one."}
    )

    assert Review.objects.filter(user=buyer, product=unavailable_product).exists()


def test_staff_buyer_can_review(client, staff_user, product):
    order_for(staff_user, product, status=Order.Status.DELIVERED)
    client.force_login(staff_user)

    client.post(create_url(product), {"rating": 3, "comment": "Fine for the office."})

    assert Review.objects.filter(user=staff_user).exists()


# --- Edit and delete your own review ----------------------------------------


def own_url(name, product):
    return reverse(f"reviews:{name}", kwargs={"pk": product.pk})


def test_update_saves_and_returns_the_edited_card_and_the_summary_out_of_band(
    client, buyer, other_buyer, product
):
    mine = review(
        buyer, product, rating=2, created_at=timezone.now() - timedelta(days=3)
    )
    review(other_buyer, product, rating=4)
    client.force_login(buyer)

    response = client.post(
        own_url("update", product), {"rating": "5", "comment": "  Grew on me a lot.  "}
    )
    content = response.content.decode()

    mine.refresh_from_db()
    assert (mine.rating, mine.comment) == (5, "Grew on me a lot.")
    assert mine.is_edited
    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assertTemplateNotUsed(response, "base.html")
    assert "Your review" in content
    assert "Grew on me a lot." in content
    assert "· edited" in content
    assert 'id="review-summary" hx-swap-oob="true"' in content
    assert "★ 4.5 · 2 reviews" in content
    assert "<form" not in content


def test_delete_removes_only_your_review_and_returns_the_empty_form(
    client, buyer, other_buyer, product
):
    review(buyer, product, rating=1, comment="Changed my mind about this.")
    theirs = review(other_buyer, product, rating=5)
    client.force_login(buyer)

    response = client.post(own_url("delete", product))
    content = response.content.decode()

    assert list(Review.objects.all()) == [theirs]
    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assert f'hx-post="{create_url(product)}"' in content
    assert "Write a review" in content
    assert "checked" not in content
    assert "Changed my mind about this." not in content
    assert 'id="review-summary" hx-swap-oob="true"' in content
    assert "★ 5.0 · 1 review" in content


STALE_REQUESTS = [
    ("get", "edit"),
    ("post", "update"),
    ("get", "card"),
    ("get", "delete_confirm"),
    ("post", "delete"),
]


@pytest.mark.parametrize(("method", "name"), STALE_REQUESTS)
@pytest.mark.parametrize(
    ("who", "slot_text"),
    [
        ("buyer", "Write a review"),
        ("customer", "Only customers who've bought this product can review it."),
    ],
)
def test_a_review_that_no_longer_exists_returns_the_current_slot(
    request, client, other_buyer, product, method, name, who, slot_text
):
    """A stale tab — or someone else's review — is never an error."""
    theirs = review(other_buyer, product, comment="Not yours to touch.")
    client.raise_request_exception = False  # See what the browser would see.
    client.force_login(request.getfixturevalue(who))

    response = getattr(client, method)(
        own_url(name, product), {"rating": 1, "comment": "Overwrite attempt."}
    )
    content = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assert slot_text in content
    assert "Not yours to touch." not in content
    assert list(Review.objects.all()) == [theirs]
    theirs.refresh_from_db()
    assert (theirs.rating, theirs.comment) == (4, "Not yours to touch.")


def test_your_card_carries_edit_and_delete_controls(client, buyer, product):
    review(buyer, product)
    client.force_login(buyer)

    content = client.get(section_url(product)).content.decode()

    assert f'hx-get="{own_url("edit", product)}"' in content
    assert f'hx-get="{own_url("delete_confirm", product)}"' in content


def test_other_reviews_carry_no_controls(client, buyer, other_buyer, product):
    review(other_buyer, product)
    client.force_login(buyer)

    content = client.get(section_url(product)).content.decode()

    assert own_url("edit", product) not in content
    assert own_url("delete_confirm", product) not in content


def test_edit_form_is_prefilled_with_your_review(client, buyer, product):
    review(buyer, product, rating=2, comment="Bit of a letdown.")
    client.force_login(buyer)

    response = client.get(own_url("edit", product))
    content = response.content.decode()

    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assert 'id="review-author-slot"' in content
    assert f'hx-post="{own_url("update", product)}"' in content
    assert "Edit your review" in content
    assert re.search(r">\s*Bit of a letdown\.</textarea>", content)
    assert re.search(r'value="2"[^>]*checked', content)
    assert len(re.findall(r'type="radio"[^>]*checked', content)) == 1
    assert f'hx-get="{own_url("card", product)}"' in content
    assert "hx-swap-oob" not in content


def test_invalid_update_returns_the_form_with_errors_and_what_was_typed(
    client, buyer, product
):
    mine = review(buyer, product, rating=2, comment="Bit of a letdown.")
    client.force_login(buyer)

    response = client.post(
        own_url("update", product), {"rating": "3", "comment": "Meh."}
    )
    content = response.content.decode()

    mine.refresh_from_db()
    assert (mine.rating, mine.comment, mine.is_edited) == (
        2,
        "Bit of a letdown.",
        False,
    )
    assert "at least 10 characters" in content
    assert f'hx-post="{own_url("update", product)}"' in content
    assert re.search(r">\s*Meh\.</textarea>", content)
    assert re.search(r'value="3"[^>]*checked', content)


def test_card_endpoint_returns_your_card_unchanged(client, buyer, product):
    review(buyer, product, comment="Exactly as I left it.")
    client.force_login(buyer)

    response = client.get(own_url("card", product))
    content = response.content.decode()

    assertTemplateUsed(response, "reviews/partials/_author_slot.html")
    assert "Your review" in content
    assert "Exactly as I left it." in content
    assert "edited" not in content
    assert "<form" not in content
    assert "hx-swap-oob" not in content


def test_delete_confirmation_asks_inside_the_card(client, buyer, product):
    review(buyer, product, comment="Still here until I say so.")
    client.force_login(buyer)

    content = client.get(own_url("delete_confirm", product)).content.decode()

    assert Review.objects.exists()
    assert "Still here until I say so." in content
    assert "Delete this review?" in content
    assert re.search(
        rf'class="btn btn-error[^"]*"\s+hx-post="{own_url("delete", product)}"', content
    )
    assert "Yes, delete" in content
    assert "Keep it" in content
    assert f'hx-get="{own_url("card", product)}"' in content
    assert own_url("edit", product) not in content
    assert "btn-primary" not in content


def test_author_whose_order_was_cancelled_can_still_edit_and_delete(
    client, buyer, product
):
    review(buyer, product, rating=5)
    Order.objects.filter(user=buyer).update(status=Order.Status.CANCELLED)
    client.force_login(buyer)

    edit = client.get(own_url("edit", product)).content.decode()
    client.post(own_url("update", product), {"rating": 2, "comment": "Sent it back."})
    updated = Review.objects.get()
    deleted = client.post(own_url("delete", product)).content.decode()

    assert "Edit your review" in edit
    assert (updated.rating, updated.comment) == (2, "Sent it back.")
    assert not Review.objects.exists()
    assert "Only customers who've bought this product can review it." in deleted


@pytest.mark.parametrize(("method", "name"), STALE_REQUESTS)
def test_anonymous_requests_redirect_to_login_and_change_nothing(
    client, buyer, product, method, name
):
    mine = review(buyer, product, rating=5, comment="Leave this alone.")

    response = getattr(client, method)(
        own_url(name, product), {"rating": 1, "comment": "Anonymous rewrite."}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))
    mine.refresh_from_db()
    assert (mine.rating, mine.comment, mine.is_edited) == (
        5,
        "Leave this alone.",
        False,
    )


@pytest.mark.parametrize(("method", "name"), STALE_REQUESTS)
def test_unknown_product_pk_is_404_for_your_review(client, buyer, method, name):
    client.force_login(buyer)

    response = getattr(client, method)(reverse(f"reviews:{name}", kwargs={"pk": 99999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_editing_a_review_keeps_its_place_in_the_list(
    client, buyer, other_buyer, customer, product
):
    now = timezone.now()
    review(customer, product, comment="Newest of the three.", created_at=now)
    review(
        buyer,
        product,
        comment="Middle, about to be edited.",
        created_at=now - timedelta(days=1),
    )
    review(
        other_buyer,
        product,
        comment="Oldest of the three.",
        created_at=now - timedelta(days=2),
    )
    client.force_login(buyer)
    client.post(
        own_url("update", product), {"rating": 1, "comment": "Middle, now edited."}
    )
    client.logout()

    content = client.get(section_url(product)).content.decode()

    positions = [
        content.index(text)
        for text in [
            "Newest of the three.",
            "Middle, now edited.",
            "Oldest of the three.",
        ]
    ]
    assert positions == sorted(positions)


# --- The author's slot ------------------------------------------------------


def test_signed_out_visitors_get_a_plain_sign_in_link(client, product):
    content = client.get(section_url(product)).content.decode()

    login = reverse("accounts:login")
    assert f'href="{login}?next=/products/seraphine-home-hub/"' in content
    assert "Sign in to review" in content
    assert "hx-post" not in content
    assert "hx-get" not in content
    assert "<form" not in content


@pytest.mark.parametrize("who", ["customer", "cancelled_buyer"])
def test_signed_in_non_buyers_get_the_only_buyers_note(request, client, product, who):
    client.force_login(request.getfixturevalue(who))

    content = client.get(section_url(product)).content.decode()

    assert "Only customers who've bought this product can review it." in content
    assert "<form" not in content
    assert "Sign in to review" not in content


def test_buyers_who_have_not_reviewed_get_the_form(client, buyer, product):
    client.force_login(buyer)

    content = client.get(section_url(product)).content.decode()

    assert f'hx-post="{create_url(product)}"' in content
    assert 'hx-target="#review-author-slot"' in content
    assert 'maxlength="2000"' in content
    assert content.count('type="radio"') == 5
    for n, label in enumerate(["1 star", "2 stars", "3 stars", "4 stars"], 1):
        assert f'value="{n}"' in content
        assert f'aria-label="{label}"' in content
    assert 'aria-label="5 stars"' in content
    assert "<legend" in content


def test_authors_see_their_own_card_in_the_slot_not_the_list(
    client, buyer, other_buyer, product
):
    review(buyer, product, comment="Mine, pinned to the top.")
    review(other_buyer, product, comment="Someone else's take.")
    client.force_login(buyer)

    content = client.get(section_url(product)).content.decode()

    list_start = content.index("<ul")
    assert content.count("Mine, pinned to the top.") == 1
    assert content.index("Your review") < content.index("Mine, pinned") < list_start
    assert content.index("Someone else&#x27;s take.") > list_start
    assert "<form" not in content
    assert "★ 4.0 · 2 reviews" in content


def test_the_review_section_has_no_primary_button(
    client, buyer, other_buyer, customer, product
):
    review(other_buyer, product)
    pages = []
    for user in [None, customer, buyer, other_buyer]:
        client.logout()
        if user:
            client.force_login(user)
        pages.append(client.get(section_url(product)).content.decode())

    detail = client.get(product.get_absolute_url()).content.decode()

    assert all("btn-primary" not in page for page in pages)
    assert detail.count("btn-primary") == 1


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
