from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("verify-email/<str:token>/", views.verify_email_view, name="verify_email"),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path(
        "password-reset/confirm/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("profile/customer/", views.customer_profile_view, name="customer_profile"),
    path("profile/staff/", views.staff_profile_view, name="staff_profile"),
    path("staff/", views.staff_list_view, name="staff_list"),
    path("staff/create/", views.staff_create_view, name="staff_create"),
    path("staff/edit/<int:user_id>/", views.staff_edit_view, name="staff_edit"),
    path("staff/deactivate/<int:user_id>/", views.staff_deactivate_view, name="staff_deactivate"),
]
