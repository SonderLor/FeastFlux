from django.urls import path
from . import views

urlpatterns = [
    path("public/<uuid:restaurant_id>/", views.public_menu, name="public_menu"),
    path("view/", views.menu_view, name="menu_view"),
    path("view/<uuid:restaurant_id>/", views.menu_view, name="menu_view_restaurant"),
    path("manage/", views.menu_management, name="menu_management"),
    path("manage/<uuid:restaurant_id>/", views.menu_management, name="menu_management_restaurant"),
    path("categories/create/", views.category_create, name="category_create"),
    path(
        "categories/create/<uuid:restaurant_id>/",
        views.category_create,
        name="category_create_restaurant",
    ),
    path("categories/<uuid:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<uuid:category_id>/delete/", views.category_delete, name="category_delete"),
    path(
        "categories/<uuid:category_id>/toggle/",
        views.toggle_category_status,
        name="toggle_category_status",
    ),
    path("items/create/", views.menu_item_create, name="menu_item_create"),
    path(
        "items/create/<uuid:restaurant_id>/",
        views.menu_item_create,
        name="menu_item_create_restaurant",
    ),
    path(
        "items/create/<uuid:restaurant_id>/<uuid:category_id>/",
        views.menu_item_create,
        name="menu_item_create_category",
    ),
    path("items/<uuid:item_id>/", views.menu_item_detail, name="menu_item_detail"),
    path("items/<uuid:item_id>/edit/", views.menu_item_edit, name="menu_item_edit"),
    path("items/<uuid:item_id>/delete/", views.menu_item_delete, name="menu_item_delete"),
    path(
        "items/<uuid:item_id>/toggle/",
        views.toggle_menu_item_status,
        name="toggle_menu_item_status",
    ),
    path("items/<uuid:item_id>/modal/", views.menu_item_modal, name="menu_item_modal"),
    path("items/<uuid:item_id>/info/", views.get_menu_item_info, name="get_menu_item_info"),
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path(
        "ingredients/<uuid:restaurant_id>/",
        views.ingredient_list,
        name="ingredient_list_restaurant",
    ),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path(
        "ingredients/create/<uuid:restaurant_id>/",
        views.ingredient_create,
        name="ingredient_create_restaurant",
    ),
    path("ingredients/<uuid:ingredient_id>/edit/", views.ingredient_edit, name="ingredient_edit"),
    path(
        "ingredients/<uuid:ingredient_id>/delete/",
        views.ingredient_delete,
        name="ingredient_delete",
    ),
    path("modifiers/", views.modifier_list, name="modifier_list"),
    path("modifiers/<uuid:restaurant_id>/", views.modifier_list, name="modifier_list_restaurant"),
    path("modifiers/create/", views.modifier_create, name="modifier_create"),
    path(
        "modifiers/create/<uuid:restaurant_id>/",
        views.modifier_create,
        name="modifier_create_restaurant",
    ),
    path("modifiers/<uuid:modifier_id>/edit/", views.modifier_edit, name="modifier_edit"),
    path("modifiers/<uuid:modifier_id>/delete/", views.modifier_delete, name="modifier_delete"),
]
