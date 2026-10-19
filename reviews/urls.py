from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("reviews/<int:pk>/", views.ReviewSectionView.as_view(), name="section"),
    path("reviews/<int:pk>/create/", views.ReviewCreateView.as_view(), name="create"),
    path("reviews/<int:pk>/edit/", views.ReviewEditView.as_view(), name="edit"),
    path("reviews/<int:pk>/update/", views.ReviewUpdateView.as_view(), name="update"),
    path("reviews/<int:pk>/card/", views.ReviewCardView.as_view(), name="card"),
    path(
        "reviews/<int:pk>/delete/confirm/",
        views.ReviewDeleteConfirmView.as_view(),
        name="delete_confirm",
    ),
    path("reviews/<int:pk>/delete/", views.ReviewDeleteView.as_view(), name="delete"),
    path("reviews/<int:pk>/more/", views.ReviewMoreView.as_view(), name="more"),
]
