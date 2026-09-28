"""Back-office coupon management: access control, CRUD, locking, retiring."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from orders.models import Order

from .models import Coupon

pytestmark = pytest.mark.django_db


def manage_urls(coupon):
    return [
        reverse("coupons:manage_coupons"),
        reverse("coupons:manage_coupon_create"),
        reverse("coupons:manage_coupon_update", kwargs={"pk": coupon.pk}),
        reverse("coupons:manage_coupon_delete", kwargs={"pk": coupon.pk}),
    ]


def coupon_data(**overrides):
    today = timezone.localdate()
    data = {
        "code": "fall26",
        "percent_off": "20",
        "scope": Coupon.Scope.ORDER,
        "starts_on": today.isoformat(),
        "ends_on": (today + timedelta(days=30)).isoformat(),
        "is_active": "on",
    }
    data.update(overrides)
    return data


def use(coupon, user, *, status=Order.Status.PLACED):
    return Order.objects.create(
        user=user,
        status=status,
        total=Decimal("90.00"),
        discount_amount=Decimal("10.00"),
        coupon=coupon,
        coupon_code=coupon.code,
        coupon_percent_off=coupon.percent_off,
    )


# --- Access control ----------------------------------------------------------


def test_anonymous_users_are_sent_to_login(client, order_coupon):
    for url in manage_urls(order_coupon):
        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer, order_coupon):
    client.force_login(customer)

    for url in manage_urls(order_coupon):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url
    toggle = reverse("coupons:manage_coupon_toggle", kwargs={"pk": order_coupon.pk})
    assert client.post(toggle).status_code == HTTPStatus.FORBIDDEN


def test_staff_get_200(client, staff_user, order_coupon):
    client.force_login(staff_user)

    for url in manage_urls(order_coupon):
        response = client.get(url)

        assert response.status_code == HTTPStatus.OK, url
        assert "{#" not in response.content.decode(), url


def test_the_back_office_has_a_coupons_tab(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("products:manage_products"))

    assert reverse("coupons:manage_coupons") in response.content.decode()


# --- The list ----------------------------------------------------------------


def test_list_shows_usage(client, staff_user, order_coupon, customer):
    use(order_coupon, customer)
    client.force_login(staff_user)

    response = client.get(reverse("coupons:manage_coupons"))

    coupon = response.context["coupons"].get()
    assert coupon.uses == 1
    assert coupon.discount_given == Decimal("10.00")
    assert "THOUGHTS10" in response.content.decode()


def test_list_filters_by_active_or_retired(
    client, staff_user, order_coupon, product_coupon
):
    product_coupon.is_active = False
    product_coupon.save()
    client.force_login(staff_user)

    active = client.get(reverse("coupons:manage_coupons"), {"status": "active"})
    retired = client.get(reverse("coupons:manage_coupons"), {"status": "retired"})

    assert list(active.context["coupons"]) == [order_coupon]
    assert list(retired.context["coupons"]) == [product_coupon]


def test_an_empty_list_gets_a_designed_empty_state(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("coupons:manage_coupons"))

    assert "No coupons yet" in response.content.decode()


# --- Create and edit ---------------------------------------------------------


def test_create_normalizes_the_code(client, staff_user):
    client.force_login(staff_user)

    response = client.post(reverse("coupons:manage_coupon_create"), coupon_data())

    assert response.status_code == HTTPStatus.FOUND
    assert Coupon.objects.get().code == "FALL26"


def test_a_code_differing_only_in_case_is_a_duplicate(client, staff_user, order_coupon):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"), coupon_data(code="Thoughts10")
    )

    assert response.status_code == HTTPStatus.OK
    assert "code" in response.context["form"].errors


def test_whole_order_cap_is_enforced(client, staff_user):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"), coupon_data(percent_off="60")
    )

    assert response.context["form"].errors["percent_off"] == [
        "Whole-order coupons can take at most 50% off."
    ]
    assert not Coupon.objects.exists()


def test_a_product_coupon_needs_products(client, staff_user):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"),
        coupon_data(scope=Coupon.Scope.PRODUCTS),
    )

    assert "products" in response.context["form"].errors
    assert not Coupon.objects.exists()


def test_a_whole_order_coupon_refuses_products(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"),
        coupon_data(products=[str(product.pk)]),
    )

    assert "products" in response.context["form"].errors


def test_a_deep_product_discount_saves_with_a_warning(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"),
        coupon_data(
            code="freebie",
            percent_off="100",
            scope=Coupon.Scope.PRODUCTS,
            products=[str(product.pk)],
        ),
        follow=True,
    )

    assert Coupon.objects.get().percent_off == 100
    assert "Double-check" in response.content.decode()


def test_an_unused_coupons_terms_can_be_edited(client, staff_user, order_coupon):
    client.force_login(staff_user)

    client.post(
        reverse("coupons:manage_coupon_update", kwargs={"pk": order_coupon.pk}),
        coupon_data(code="THOUGHTS10", percent_off="15"),
    )

    order_coupon.refresh_from_db()
    assert order_coupon.percent_off == 15


def test_a_used_coupons_terms_are_locked_but_its_dates_are_not(
    client, staff_user, order_coupon, customer
):
    use(order_coupon, customer, status=Order.Status.CANCELLED)  # any order locks
    later = timezone.localdate() + timedelta(days=60)
    client.force_login(staff_user)

    client.post(
        reverse("coupons:manage_coupon_update", kwargs={"pk": order_coupon.pk}),
        coupon_data(code="HACKED", percent_off="45", ends_on=later.isoformat()),
    )

    order_coupon.refresh_from_db()
    assert order_coupon.code == "THOUGHTS10"
    assert order_coupon.percent_off == 10
    assert order_coupon.ends_on == later


# --- Retire and delete -------------------------------------------------------


def test_retire_and_reactivate(client, staff_user, order_coupon):
    client.force_login(staff_user)
    url = reverse("coupons:manage_coupon_toggle", kwargs={"pk": order_coupon.pk})

    client.post(url)
    order_coupon.refresh_from_db()
    assert not order_coupon.is_active

    client.post(url)
    order_coupon.refresh_from_db()
    assert order_coupon.is_active


def test_toggle_is_post_only(client, staff_user, order_coupon):
    client.force_login(staff_user)

    response = client.get(
        reverse("coupons:manage_coupon_toggle", kwargs={"pk": order_coupon.pk})
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_an_unused_coupon_can_be_deleted(client, staff_user, order_coupon):
    client.force_login(staff_user)

    client.post(reverse("coupons:manage_coupon_delete", kwargs={"pk": order_coupon.pk}))

    assert not Coupon.objects.exists()


def test_a_used_coupon_cannot_be_deleted(client, staff_user, order_coupon, customer):
    use(order_coupon, customer, status=Order.Status.CANCELLED)
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_delete", kwargs={"pk": order_coupon.pk}),
        follow=True,
    )

    assert Coupon.objects.filter(pk=order_coupon.pk).exists()
    assert "Retire it instead" in response.content.decode()
