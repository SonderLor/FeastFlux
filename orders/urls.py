from django.urls import path
from . import views

urlpatterns = [
    path('customer/create/', views.customer_order_create, name='customer_order_create'),
    path('customer/menu-selection/', views.customer_menu_selection, name='customer_menu_selection'),
    path('customer/add-to-cart/', views.customer_add_to_cart, name='customer_add_to_cart'),
    path('customer/cart/', views.customer_cart, name='customer_cart'),
    path('customer/cart/update/<uuid:item_id>/', views.customer_update_cart_item, name='customer_update_cart_item'),
    path('customer/cart/remove/<uuid:item_id>/', views.customer_remove_cart_item, name='customer_remove_cart_item'),
    path('customer/checkout/', views.customer_checkout, name='customer_checkout'),
    path('customer/<uuid:id>/status/', views.customer_order_status, name='customer_order_status'),
    path('customer/history/', views.customer_orders_history, name='customer_orders_history'),
    path('active/', views.active_orders, name='active_orders'),
    path('create/', views.create_order, name='create_order'),
    path('create/table/<uuid:table_id>/', views.create_order, name='create_order_table'),
    path('<uuid:id>/', views.order_details, name='order_details'),
    path('<uuid:id>/edit/', views.edit_order, name='edit_order'),
    path('<uuid:id>/edit/update-item/<uuid:item_id>/', views.update_order_item, name='update_order_item'),
    path('<uuid:id>/edit/remove-item/<uuid:item_id>/', views.remove_order_item, name='remove_order_item'),
    path('<uuid:id>/update-status/', views.update_order_status, name='update_order_status'),
    path('<uuid:id>/payment/', views.order_payment, name='order_payment'),
    path('history/', views.order_history, name='order_history'),
    path('discounts/', views.discount_list, name='discount_list'),
    path('discounts/create/', views.discount_create, name='discount_create'),
    path('discounts/<uuid:id>/edit/', views.discount_edit, name='discount_edit'),
    path('discounts/<uuid:id>/toggle-status/', views.discount_toggle_status, name='discount_toggle_status'),
    path('discounts/<uuid:id>/delete/', views.discount_delete, name='discount_delete'),
]
