from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.test import RequestFactory
from django.urls import reverse

from .context_processors import wishlists
from .models import Wishlist, WishlistItem


def add_url(product):
    return reverse("wishlists:add", kwargs={"pk": product.pk})


def remove_url(product):
    return reverse("wishlists:remove", kwargs={"pk": product.pk})


# --- Model behavior ---------------------------------------------------------


def test_for_user_creates_the_wishlist_once(customer):
    first = Wishlist.for_user(customer)
    second = Wishlist.for_user(customer)

    assert first == second
    assert Wishlist.objects.count() == 1
    assert customer.wishlist == first


def test_wishlist_str(customer):
    assert str(Wishlist.for_user(customer)) == "Wishlist for customer"


def test_add_twice_leaves_one_row(customer, product):
    wishlist = Wishlist.for_user(customer)

    wishlist.add(product)
    wishlist.add(product)

    assert wishlist.items.count() == 1


def test_remove_deletes_the_row(customer, product):
    wishlist = Wishlist.for_user(customer)
    wishlist.add(product)

    wishlist.remove(product)

    assert not wishlist.items.exists()


def test_remove_unsaved_product_is_a_no_op(customer, product):
    Wishlist.for_user(customer).remove(product)

    assert not WishlistItem.objects.exists()


def test_wishlist_product_pair_is_unique(customer, product):
    wishlist = Wishlist.for_user(customer)
    wishlist.add(product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(wishlist=wishlist, product=product)


def test_items_are_newest_first(customer, product, unavailable_product):
    wishlist = Wishlist.for_user(customer)
    wishlist.add(product)
    wishlist.add(unavailable_product)

    assert [item.product for item in wishlist.items.all()] == [
        unavailable_product,
        product,
    ]


def test_deleting_a_product_removes_it_from_every_wishlist(
    customer, other_customer, product
):
    Wishlist.for_user(customer).add(product)
    Wishlist.for_user(other_customer).add(product)

    product.delete()

    assert not WishlistItem.objects.exists()
    assert Wishlist.objects.count() == 2


# --- Add and Remove (HTMX) ---------------------------------------------------


def test_add_returns_the_saved_button(client, customer, product):
    client.force_login(customer)

    response = client.post(add_url(product))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "Saved" in page
    assert 'aria-pressed="true"' in page
    assert remove_url(product) in page
    assert "btn-primary" not in page
    assert customer.wishlist.items.filter(product=product).exists()


def test_remove_returns_the_save_button(client, customer, product):
    Wishlist.for_user(customer).add(product)
    client.force_login(customer)

    response = client.post(remove_url(product))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "Saved" not in page
    assert 'aria-pressed="false"' in page
    assert add_url(product) in page
    assert not customer.wishlist.items.exists()


def test_repeated_add_never_flips_to_removed(client, customer, product):
    """A double-click or stale tab on "Save" keeps the product saved."""
    client.force_login(customer)
    client.post(add_url(product))

    response = client.post(add_url(product))

    assert 'aria-pressed="true"' in response.content.decode()
    assert customer.wishlist.items.count() == 1


def test_repeated_remove_never_flips_to_saved(client, customer, product):
    client.force_login(customer)

    response = client.post(remove_url(product))

    assert 'aria-pressed="false"' in response.content.decode()
    assert not WishlistItem.objects.exists()


def test_unavailable_product_can_be_saved(client, customer, unavailable_product):
    client.force_login(customer)

    response = client.post(add_url(unavailable_product))

    assert response.status_code == HTTPStatus.OK
    assert customer.wishlist.items.filter(product=unavailable_product).exists()


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_unknown_product_404s(client, customer, name):
    client.force_login(customer)

    response = client.post(reverse(name, kwargs={"pk": 999999}))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert not Wishlist.objects.exists()


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_anonymous_requests_redirect_and_create_nothing(client, product, name):
    response = client.post(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert not Wishlist.objects.exists()
    assert not WishlistItem.objects.exists()


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_get_is_not_allowed(client, customer, product, name):
    client.force_login(customer)

    response = client.get(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


# --- Privacy -----------------------------------------------------------------


def test_add_never_touches_another_customers_wishlist(
    client, customer, other_customer, product
):
    client.force_login(customer)

    client.post(add_url(product))

    assert not Wishlist.objects.filter(user=other_customer).exists()


def test_remove_never_touches_another_customers_wishlist(
    client, customer, other_customer, product
):
    Wishlist.for_user(other_customer).add(product)
    client.force_login(customer)

    client.post(remove_url(product))

    assert other_customer.wishlist.items.filter(product=product).exists()


def test_staff_can_save_a_product(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(add_url(product))

    assert response.status_code == HTTPStatus.OK
    assert staff_user.wishlist.items.filter(product=product).exists()


# --- The detail page -----------------------------------------------------------


def test_detail_page_shows_save_for_an_unsaved_product(client, customer, product):
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert add_url(product) in page
    assert 'aria-pressed="false"' in page


def test_detail_page_shows_saved_state_on_load(client, customer, product):
    Wishlist.for_user(customer).add(product)
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert remove_url(product) in page
    assert 'aria-pressed="true"' in page


def test_detail_page_prompts_anonymous_visitors_to_sign_in(client, product):
    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert f"{reverse('accounts:login')}?next={product.get_absolute_url()}" in page
    assert add_url(product) not in page
    assert "aria-pressed" not in page


def test_detail_page_of_an_unavailable_product_offers_save(
    client, customer, unavailable_product
):
    client.force_login(customer)

    response = client.get(unavailable_product.get_absolute_url())

    assert add_url(unavailable_product) in response.content.decode()


# --- Context processor -------------------------------------------------------


def test_context_processor_is_empty_for_anonymous_visitors(db):
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    assert wishlists(request) == {"wishlist_product_ids": set()}


def test_context_processor_returns_the_users_saved_ids(
    customer, other_customer, product, unavailable_product
):
    Wishlist.for_user(customer).add(product)
    Wishlist.for_user(other_customer).add(unavailable_product)
    request = RequestFactory().get("/")
    request.user = customer

    assert wishlists(request) == {"wishlist_product_ids": {product.pk}}


def test_context_processor_uses_one_query(customer, product, django_assert_num_queries):
    Wishlist.for_user(customer).add(product)
    request = RequestFactory().get("/")
    request.user = customer

    with django_assert_num_queries(1):
        wishlists(request)


# --- Admin -------------------------------------------------------------------


def test_admin_shows_wishlist_with_items_inline(admin_client, customer, product):
    wishlist = Wishlist.for_user(customer)
    wishlist.add(product)

    response = admin_client.get(
        reverse("admin:wishlists_wishlist_change", args=[wishlist.pk])
    )

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "items-TOTAL_FORMS" in page
    assert product.name in page
