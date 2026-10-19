from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("reviews/<int:pk>/", views.ReviewSectionView.as_view(), name="section"),
]
