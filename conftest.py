"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Address
from coupons.models import Coupon
from orders.models import Cart, CartItem
from products.models import Category, Product, Tag


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploaded files go to a per-test temp dir, never the real ``media/``."""
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture
def customer(db):
    return get_user_model().objects.create_user(
        username="customer", password="customer123"
    )


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="employee",
        password="employee123",
        is_staff=True,
        job_title="Junior Thought Curator",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Home Assistants", slug="home-assistants")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Seraphine Home Hub",
        slug="seraphine-home-hub",
        tagline="She's always listening. In a good way.",
        description="The flagship Seraphine hub with a seven-microphone array.",
        price=Decimal("349.99"),
        category=category,
    )


@pytest.fixture
def unavailable_product(category):
    return Product.objects.create(
        name="EchoPatch",
        slug="echopatch",
        tagline="Never miss a word. Anyone's.",
        price=Decimal("139.00"),
        is_available=False,
        category=category,
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="bestseller", slug="bestseller")


@pytest.fixture
def cart(customer):
    return Cart.for_user(customer)


@pytest.fixture
def cart_item(cart, product):
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def order_coupon(db):
    """A live whole-order coupon: 10% off, running a week either side of today."""
    today = timezone.localdate()
    return Coupon.objects.create(
        code="THOUGHTS10",
        percent_off=10,
        starts_on=today - timedelta(days=7),
        ends_on=today + timedelta(days=7),
    )


@pytest.fixture
def product_coupon(product):
    """A live product coupon: 50% off the Seraphine Home Hub."""
    today = timezone.localdate()
    coupon = Coupon.objects.create(
        code="SERAPHINE50",
        percent_off=50,
        scope=Coupon.Scope.PRODUCTS,
        starts_on=today - timedelta(days=7),
        ends_on=today + timedelta(days=7),
    )
    coupon.products.add(product)
    return coupon


@pytest.fixture
def address(customer):
    """A saved address matching the checkout tests' shipping section."""
    return Address.objects.create(
        user=customer,
        label="Home",
        name="Casey Monroe",
        street="12 Cortex Lane",
        line2="Unit 7",
        city="Canyon",
        state="TX",
        zip="79015",
    )
