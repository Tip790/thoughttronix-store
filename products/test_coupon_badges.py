"""Promo badges: live product coupons advertised on the catalog and detail pages."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Product

pytestmark = pytest.mark.django_db


def test_catalog_card_shows_a_live_product_coupon(client, product_coupon):
    page = client.get(reverse("products:catalog")).content.decode()

    assert "50% off · SERAPHINE50" in page


def test_detail_page_shows_the_code_and_last_day(client, product, product_coupon):
    page = client.get(product.get_absolute_url()).content.decode()

    assert "SERAPHINE50" in page
    assert f"through {product_coupon.ends_on:%B} {product_coupon.ends_on.day}" in page


@pytest.mark.parametrize(
    "change",
    [
        {"is_active": False},  # retired
        {"starts_on_offset": 3},  # not started — stays secret
        {"ends_on_offset": -1},  # expired
    ],
)
def test_only_live_coupons_are_advertised(client, product, product_coupon, change):
    today = timezone.localdate()
    if "is_active" in change:
        product_coupon.is_active = False
    if "starts_on_offset" in change:
        product_coupon.starts_on = today + timedelta(days=3)
        product_coupon.ends_on = today + timedelta(days=10)
    if "ends_on_offset" in change:
        product_coupon.starts_on = today - timedelta(days=10)
        product_coupon.ends_on = today - timedelta(days=1)
    product_coupon.save()

    for url in (reverse("products:catalog"), product.get_absolute_url()):
        assert "SERAPHINE50" not in client.get(url).content.decode(), url


def test_whole_order_coupons_get_no_product_badge(client, product, order_coupon):
    assert "THOUGHTS10" not in client.get(reverse("products:catalog")).content.decode()


def test_badges_cost_no_query_per_card(client, category, product_coupon):
    """The live-coupon prefetch keeps the catalog's query count flat."""

    def catalog_queries():
        with CaptureQueriesContext(connection) as queries:
            client.get(reverse("products:catalog"))
        return len(queries)

    few = catalog_queries()
    for n in range(5):
        product = Product.objects.create(
            name=f"Hush {n}", slug=f"hush-{n}", price=Decimal("9.00"), category=category
        )
        product_coupon.products.add(product)

    assert catalog_queries() == few
