from django.urls import path

from . import views

app_name = "wishlists"

urlpatterns = [
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path("wishlist/add/<int:pk>/", views.AddToWishlistView.as_view(), name="add"),
    path(
        "wishlist/remove/<int:pk>/",
        views.RemoveFromWishlistView.as_view(),
        name="remove",
    ),
]
