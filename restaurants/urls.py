from django.urls import path
from . import views

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
]
