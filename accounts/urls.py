from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("", views.AccountView.as_view(), name="account"),
    path(
        "email/resend/",
        views.ResendVerificationView.as_view(),
        name="resend_verification",
    ),
    path(
        "email/verify/<str:token>/",
        views.VerifyEmailView.as_view(),
        name="verify_email",
    ),
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/sent/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("addresses/", views.AddressListView.as_view(), name="address_list"),
    path("addresses/new/", views.AddressCreateView.as_view(), name="address_create"),
    path(
        "addresses/<int:pk>/edit/",
        views.AddressUpdateView.as_view(),
        name="address_update",
    ),
    path(
        "addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),
    path(
        "addresses/<int:pk>/default/<str:role>/",
        views.MakeDefaultAddressView.as_view(),
        name="address_make_default",
    ),
]
