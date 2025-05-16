from django.urls import path
from . import views

app_name = "restaurants"

# TODO Сделать пользователю историю бронирований
urlpatterns = [
    path("public/", views.public_restaurant_list, name="public_restaurants"),
    path("public/<uuid:id>/", views.public_restaurant_detail, name="public_restaurant_detail"),
    path("public/<uuid:id>/tables/", views.public_table_view, name="public_table_view"),
    path("public/<uuid:id>/reserve/", views.customer_reservation, name="customer_reservation"),
    path(
        "reservation/<uuid:id>/confirmation/",
        views.reservation_confirmation,
        name="reservation_confirmation",
    ),
    path("", views.restaurant_list, name="restaurant_list"),
    path("<uuid:id>/", views.restaurant_detail, name="restaurant_detail"),
    path("manage/", views.restaurant_manage, name="restaurant_manage"),
    path("create/", views.restaurant_create, name="restaurant_create"),
    path("<uuid:id>/edit/", views.restaurant_edit, name="restaurant_edit"),
    path("<uuid:id>/tables/", views.table_layout, name="table_layout"),
    path("<uuid:restaurant_id>/tables/create/", views.table_create, name="table_create"),
    path("tables/<uuid:id>/edit/", views.table_edit, name="table_edit"),
    path("tables/<uuid:id>/delete/", views.table_delete, name="table_delete"),
    path("<uuid:id>/reservations/", views.reservation_list, name="reservation_list"),
    path("<uuid:id>/reservations/create/", views.reservation_create, name="reservation_create"),
    path("reservations/<uuid:id>/edit/", views.reservation_edit, name="reservation_edit"),
    path("reservations/<uuid:id>/cancel/", views.reservation_cancel, name="reservation_cancel"),
]
