"""Back-office review moderation: access control, the list, edit, delete."""

import re
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from products.models import Product

from .models import Review

pytestmark = pytest.mark.django_db


def review(user, product, rating=4, comment="Does exactly what it says.", **kwargs):
    return Review.objects.create(
        user=user, product=product, rating=rating, comment=comment, **kwargs
    )


@pytest.fixture
def second_product(category):
    return Product.objects.create(
        name="Lumen Desk Lamp",
        slug="lumen-desk-lamp",
        tagline="It sees what you read.",
        price=Decimal("89.00"),
        category=category,
    )


@pytest.fixture
def target(customer, product):
    return review(customer, product, rating=2, comment="Original words here.")


def manage_urls(review):
    return [
        reverse("reviews:manage_reviews"),
        reverse("reviews:manage_review_update", kwargs={"pk": review.pk}),
        reverse("reviews:manage_review_delete", kwargs={"pk": review.pk}),
    ]


VALID_EDIT = {"rating": "5", "comment": "Changed by someone else."}


# --- Access control ----------------------------------------------------------


def test_anonymous_users_are_sent_to_login_and_nothing_changes(client, target):
    for url in manage_urls(target):
        for response in (client.get(url), client.post(url, VALID_EDIT)):
            assert response.status_code == HTTPStatus.FOUND, url
            assert reverse("accounts:login") in response.url

    target.refresh_from_db()
    assert (target.rating, target.comment) == (2, "Original words here.")


def test_customers_get_403_and_nothing_changes(client, other_customer, target):
    client.force_login(other_customer)

    for url in manage_urls(target):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url
        assert client.post(url, VALID_EDIT).status_code == HTTPStatus.FORBIDDEN, url

    target.refresh_from_db()
    assert (target.rating, target.comment) == (2, "Original words here.")


def test_even_the_author_gets_403(client, customer, target):
    client.force_login(customer)

    for url in manage_urls(target):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url


def test_staff_get_200(client, staff_user, target):
    client.force_login(staff_user)

    for url in manage_urls(target):
        response = client.get(url)

        assert response.status_code == HTTPStatus.OK, url
        assert "{#" not in response.content.decode(), url


def test_unknown_review_pk_is_404(client, staff_user):
    client.force_login(staff_user)

    for name in ("reviews:manage_review_update", "reviews:manage_review_delete"):
        url = reverse(name, kwargs={"pk": 999})
        assert client.get(url).status_code == HTTPStatus.NOT_FOUND, name
        assert client.post(url).status_code == HTTPStatus.NOT_FOUND, name


def test_the_back_office_has_a_reviews_tab(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("products:manage_products"))

    assert reverse("reviews:manage_reviews") in response.content.decode()


# --- The list ----------------------------------------------------------------


def test_list_is_newest_first_and_filters_by_product_and_rating(
    client, staff_user, customer, other_customer, product, second_product
):
    now = timezone.now()
    old_hub = review(customer, product, rating=5, created_at=now - timedelta(days=2))
    new_hub = review(other_customer, product, rating=2, created_at=now)
    lamp = review(
        customer, second_product, rating=5, created_at=now - timedelta(days=1)
    )
    client.force_login(staff_user)
    url = reverse("reviews:manage_reviews")

    def listed(**params):
        return list(client.get(url, params).context["reviews"])

    assert listed() == [new_hub, lamp, old_hub]
    assert listed(product=product.pk) == [new_hub, old_hub]
    assert listed(rating=5) == [lamp, old_hub]
    assert listed(product=product.pk, rating=5) == [old_hub]


def test_list_shows_product_reviewer_rating_and_excerpt(
    client, staff_user, buyer, product
):
    review(buyer, product, rating=3, comment="A" * 200)
    client.force_login(staff_user)

    html = client.get(reverse("reviews:manage_reviews")).content.decode()

    assert product.name in html
    assert "Mira K." in html
    assert "3★" in html
    assert "A" * 79 + "…" in html
    assert "A" * 200 not in html


def test_list_paginates_at_twenty(client, staff_user, product):
    users = get_user_model().objects
    for n in range(21):
        review(users.create_user(username=f"reviewer{n}"), product)
    client.force_login(staff_user)
    url = reverse("reviews:manage_reviews")

    assert len(client.get(url).context["reviews"]) == 20
    assert len(client.get(url, {"page": 2}).context["reviews"]) == 1


def test_list_ignores_junk_filters(client, staff_user, target):
    client.force_login(staff_user)

    response = client.get(
        reverse("reviews:manage_reviews"), {"product": "abc", "rating": "9"}
    )

    assert list(response.context["reviews"]) == [target]


def test_empty_list_and_empty_filter_get_designed_states(client, staff_user, product):
    client.force_login(staff_user)
    url = reverse("reviews:manage_reviews")

    assert "No reviews yet" in client.get(url).content.decode()
    filtered = client.get(url, {"rating": "1"}).content.decode()
    assert "No reviews match those filters" in filtered


# --- Edit --------------------------------------------------------------------


def test_staff_edit_changes_only_rating_and_comment(
    client, staff_user, customer, other_customer, product, second_product
):
    target = review(customer, product, rating=1, comment="Original words here.")
    client.force_login(staff_user)
    url = reverse("reviews:manage_review_update", kwargs={"pk": target.pk})

    invalid = client.post(url, {"rating": "9", "comment": "  short  "})

    assert invalid.status_code == HTTPStatus.OK
    assert set(invalid.context["form"].errors) == {"rating", "comment"}
    assert "short" in invalid.content.decode()
    target.refresh_from_db()
    assert (target.rating, target.comment) == (1, "Original words here.")

    valid = client.post(
        url,
        {
            "rating": "3",
            "comment": "  Redacted by the moderation team.  ",
            "user": str(other_customer.pk),
            "product": str(second_product.pk),
        },
    )

    assert valid.status_code == HTTPStatus.FOUND
    target.refresh_from_db()
    assert (target.rating, target.comment) == (3, "Redacted by the moderation team.")
    assert (target.user, target.product) == (customer, product)


def test_edit_form_is_prefilled(client, staff_user, target):
    client.force_login(staff_user)

    response = client.get(
        reverse("reviews:manage_review_update", kwargs={"pk": target.pk})
    )

    form = response.context["form"]
    assert form["rating"].value() == 2
    assert form["comment"].value() == "Original words here."
    assert re.search(r'value="2"[^>]*checked', response.content.decode())


def test_a_staff_edit_shows_the_edited_marker_on_the_product_page(
    client, staff_user, target, product
):
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:manage_review_update", kwargs={"pk": target.pk}),
        VALID_EDIT,
        follow=True,
    )

    assert "saved." in response.content.decode()
    target.refresh_from_db()
    assert target.is_edited
    section = client.get(reverse("reviews:section", kwargs={"pk": product.pk}))
    assert "· edited" in section.content.decode()


# --- Delete ------------------------------------------------------------------


def test_delete_confirms_first_then_removes_the_review(client, staff_user, target):
    client.force_login(staff_user)
    url = reverse("reviews:manage_review_delete", kwargs={"pk": target.pk})

    confirm = client.get(url).content.decode()

    assert "Delete this review?" in confirm
    assert "btn-error" in confirm
    assert Review.objects.filter(pk=target.pk).exists()

    response = client.post(url, follow=True)

    assert not Review.objects.filter(pk=target.pk).exists()
    assert "deleted." in response.content.decode()
