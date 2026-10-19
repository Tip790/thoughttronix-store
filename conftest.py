"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from accounts.models import Address
from coupons.models import Coupon
from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Category, Product, Tag


def order_for(user, product, status=Order.Status.PLACED):
    """A one-line order of ``product`` for ``user`` — enough to make a buyer."""
    order = Order.objects.create(
        user=user,
        status=status,
        total=product.price,
        email=f"{user.username}@example.com",
        shipping_name=user.username,
        shipping_street="12 Cortex Lane",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name=user.username,
        billing_street="12 Cortex Lane",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    return order


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploaded files go to a per-test temp dir, never the real ``media/``."""
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture(autouse=True)
def clear_cache():
    """Every test starts with an empty cache, so throttle counters never
    leak from one test into the next."""
    cache.clear()


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
def buyer(product):
    """A customer with a non-cancelled (PLACED) order for ``product``."""
    user = get_user_model().objects.create_user(
        username="buyer", password="buyer123", first_name="Mira", last_name="Kovacs"
    )
    order_for(user, product)
    return user


@pytest.fixture
def other_buyer(product):
    """A second buyer of ``product``, for privacy tests."""
    user = get_user_model().objects.create_user(username="otherbuyer", password="x")
    order_for(user, product)
    return user


@pytest.fixture
def cancelled_buyer(product):
    """A customer whose only order for ``product`` was cancelled."""
    user = get_user_model().objects.create_user(username="cancelled", password="x")
    order_for(user, product, status=Order.Status.CANCELLED)
    return user


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
