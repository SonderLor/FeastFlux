from django.urls import path
from . import views

app_name = "kitchen"

urlpatterns = [
    path("dashboard/", views.kitchen_dashboard, name="kitchen_dashboard"),
    path("queue/<uuid:id>/", views.kitchen_queue, name="kitchen_queue"),
    path("order/<uuid:id>/", views.kitchen_order_details, name="kitchen_order_details"),
    path(
        "order/<uuid:id>/update-status/",
        views.update_kitchen_order_status,
        name="update_kitchen_order_status",
    ),
    path(
        "item/<uuid:id>/update-status/",
        views.update_kitchen_item_status,
        name="update_kitchen_item_status",
    ),
    path("order/<uuid:id>/assign/", views.assign_kitchen_order, name="assign_kitchen_order"),
    path("stations/", views.cooking_stations, name="cooking_stations"),
    path("stations/create/", views.cooking_station_create, name="cooking_station_create"),
    path("stations/<uuid:id>/edit/", views.cooking_station_edit, name="cooking_station_edit"),
    path("stations/<uuid:id>/toggle/", views.cooking_station_toggle, name="cooking_station_toggle"),
    path("stations/<uuid:id>/delete/", views.cooking_station_delete, name="cooking_station_delete"),
    path("log/", views.kitchen_log, name="kitchen_log"),
    path("log/export/", views.export_kitchen_log, name="export_kitchen_log"),
]
