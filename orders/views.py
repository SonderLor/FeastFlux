from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model

from decimal import Decimal

from restaurants.models import Restaurant, Table
from menu.models import MenuItem, Modifier
from .models import Order, OrderItem, OrderItemModifier, Payment, Discount
from .forms import OrderTypeForm, DiscountForm, PaymentForm, CheckoutForm, DiscountAdminForm

User = get_user_model()


@login_required
@permission_required("orders.add_customer_order", raise_exception=True)
def customer_order_create(request):
    """Создание заказа клиентом."""
    if request.method == "POST":
        form = OrderTypeForm(request.POST, user=request.user)
        if form.is_valid():
            order = Order.objects.create(
                restaurant=form.cleaned_data["restaurant"],
                table=form.cleaned_data.get("table"),
                order_type=form.cleaned_data["order_type"],
                status=Order.OrderStatus.DRAFT,
                customer=request.user,
                customer_name=request.user.get_full_name() or request.user.username,
                customer_phone=(
                    request.user.profile.phone_number if hasattr(request.user, "profile") else None
                ),
                delivery_address=form.cleaned_data.get("delivery_address"),
            )

            request.session["current_order_id"] = str(order.id)

            return redirect("customer_menu_selection")
    else:
        current_order_id = request.session.get("current_order_id")
        if current_order_id:
            try:
                current_order = Order.objects.get(
                    id=current_order_id, status=Order.OrderStatus.DRAFT
                )
                return redirect("customer_cart")
            except Order.DoesNotExist:
                request.session.pop("current_order_id", None)

        form = OrderTypeForm(user=request.user)

    restaurants = Restaurant.objects.filter(is_active=True)

    context = {
        "form": form,
        "restaurants": restaurants,
    }

    return render(request, "orders/customer_order_create.html", context)


@login_required
@permission_required("orders.add_customer_order", raise_exception=True)
def customer_menu_selection(request):
    """Выбор блюд для заказа клиентом."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        messages.error(request, _("Заказ не найден. Пожалуйста, начните заново."))
        return redirect("customer_order_create")

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
    except Order.DoesNotExist:
        messages.error(request, _("Заказ не найден. Пожалуйста, начните заново."))
        request.session.pop("current_order_id", None)
        return redirect("customer_order_create")

    categories = order.restaurant.menu_categories.filter(
        parent__isnull=True, is_active=True
    ).prefetch_related("subcategories")

    menu_structure = []
    for category in categories:
        category_data = {
            "category": category,
            "subcategories": [],
            "items": MenuItem.objects.filter(
                category=category, is_active=True, status="AVAILABLE"
            ).order_by("order_in_category"),
        }

        for subcategory in category.subcategories.filter(is_active=True):
            subcategory_data = {
                "category": subcategory,
                "items": MenuItem.objects.filter(
                    category=subcategory, is_active=True, status="AVAILABLE"
                ).order_by("order_in_category"),
            }
            category_data["subcategories"].append(subcategory_data)

        menu_structure.append(category_data)

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    order.calculate_totals()

    context = {
        "order": order,
        "menu_structure": menu_structure,
        "order_items": order_items,
    }

    return render(request, "orders/customer_menu_selection.html", context)


@login_required
@permission_required("orders.add_customer_order", raise_exception=True)
@require_POST
def customer_add_to_cart(request):
    """AJAX-метод для добавления блюда в корзину."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        return JsonResponse({"success": False, "error": "Order not found"}, status=400)

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"}, status=400)

    menu_item_id = request.POST.get("menu_item_id")
    quantity = int(request.POST.get("quantity", 1))
    notes = request.POST.get("notes", "")

    try:
        menu_item = MenuItem.objects.get(id=menu_item_id, is_active=True, status="AVAILABLE")
    except MenuItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Menu item not found"}, status=400)

    order_item = OrderItem.objects.create(
        order=order, menu_item=menu_item, quantity=quantity, unit_price=menu_item.price, notes=notes
    )

    for key, value in request.POST.items():
        if key.startswith("modifier_") and value == "on":
            modifier_id = key.split("_")[1]
            try:
                modifier = Modifier.objects.get(id=modifier_id, is_active=True)
                quantity_key = f"modifier_{modifier_id}_quantity"
                modifier_quantity = int(request.POST.get(quantity_key, 1))

                OrderItemModifier.objects.create(
                    order_item=order_item, modifier=modifier, quantity=modifier_quantity
                )
            except (Modifier.DoesNotExist, ValueError):
                pass

    order.calculate_totals()

    cart_count = OrderItem.objects.filter(order=order).count()

    return JsonResponse(
        {"success": True, "cart_count": cart_count, "cart_total": float(order.total_amount)}
    )


@login_required
@permission_required("orders.view_own_cart", raise_exception=True)
def customer_cart(request):
    """Просмотр корзины клиентом."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        messages.error(request, _("Корзина пуста. Пожалуйста, начните заказ."))
        return redirect("customer_order_create")

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
    except Order.DoesNotExist:
        messages.error(request, _("Заказ не найден. Пожалуйста, начните заново."))
        request.session.pop("current_order_id", None)
        return redirect("customer_order_create")

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    if not order_items.exists():
        messages.warning(request, _("Ваша корзина пуста. Пожалуйста, добавьте блюда в заказ."))
        return redirect("customer_menu_selection")

    discount_form = DiscountForm()
    discount_error = None

    if request.method == "POST" and "apply_discount" in request.POST:
        discount_form = DiscountForm(request.POST)
        if discount_form.is_valid():
            discount_code = discount_form.cleaned_data["discount_code"]
            try:
                discount = Discount.objects.get(code__iexact=discount_code, is_active=True)

                if discount.is_valid():
                    if order.subtotal >= discount.min_order_value:
                        order.discount = discount
                        order.save()
                        order.calculate_totals()
                        messages.success(request, _("Промокод успешно применен!"))
                    else:
                        discount_error = _(
                            f"Минимальная сумма заказа для этого промокода: {discount.min_order_value} ₽"
                        )
                else:
                    discount_error = _("Промокод недействителен или срок его действия истек")
            except Discount.DoesNotExist:
                discount_error = _("Промокод не найден")

    if discount_error:
        messages.error(request, discount_error)

    order_nutrition = order.get_order_nutrition()
    order_allergens = order.get_order_allergens()

    context = {
        "order": order,
        "order_items": order_items,
        "discount_form": discount_form,
        "order_nutrition": order_nutrition,
        "order_allergens": order_allergens,
    }

    return render(request, "orders/customer_cart.html", context)


@login_required
@permission_required("orders.view_own_cart", raise_exception=True)
@require_POST
def customer_update_cart_item(request, item_id):
    """AJAX-метод для обновления количества позиции в корзине."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        return JsonResponse({"success": False, "error": "Order not found"}, status=400)

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
        order_item = OrderItem.objects.get(id=item_id, order=order)
    except (Order.DoesNotExist, OrderItem.DoesNotExist):
        return JsonResponse({"success": False, "error": "Item not found"}, status=400)

    quantity = int(request.POST.get("quantity", 1))

    if quantity <= 0:
        order_item.delete()
    else:
        order_item.quantity = quantity
        order_item.save()

    order.calculate_totals()

    cart_count = OrderItem.objects.filter(order=order).count()

    return JsonResponse(
        {
            "success": True,
            "item_total": float(order_item.get_total_price()) if quantity > 0 else 0,
            "cart_total": float(order.total_amount),
            "subtotal": float(order.subtotal),
            "discount_amount": float(order.discount_amount),
            "tax_amount": float(order.tax_amount),
            "cart_count": cart_count,
        }
    )


@login_required
@permission_required("orders.view_own_cart", raise_exception=True)
def customer_remove_cart_item(request, item_id):
    """Удаление позиции из корзины."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        messages.error(request, _("Корзина не найдена."))
        return redirect("customer_order_create")

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
        order_item = OrderItem.objects.get(id=item_id, order=order)
    except (Order.DoesNotExist, OrderItem.DoesNotExist):
        messages.error(request, _("Позиция не найдена."))
        return redirect("customer_cart")

    order_item.delete()

    order.calculate_totals()

    messages.success(request, _("Позиция успешно удалена из заказа."))

    if not OrderItem.objects.filter(order=order).exists():
        return redirect("customer_menu_selection")

    return redirect("customer_cart")


@login_required
@permission_required("orders.checkout_order", raise_exception=True)
def customer_checkout(request):
    """Оформление заказа клиентом."""
    current_order_id = request.session.get("current_order_id")

    if not current_order_id:
        messages.error(request, _("Заказ не найден. Пожалуйста, начните заново."))
        return redirect("customer_order_create")

    try:
        order = Order.objects.get(
            id=current_order_id, status=Order.OrderStatus.DRAFT, customer=request.user
        )
    except Order.DoesNotExist:
        messages.error(request, _("Заказ не найден. Пожалуйста, начните заново."))
        request.session.pop("current_order_id", None)
        return redirect("customer_order_create")

    if not OrderItem.objects.filter(order=order).exists():
        messages.warning(request, _("Ваша корзина пуста. Пожалуйста, добавьте блюда в заказ."))
        return redirect("customer_menu_selection")

    if request.method == "POST":
        form = CheckoutForm(
            request.POST, instance=order, user=request.user, order_type=order.order_type
        )
        if form.is_valid():
            order.customer_name = form.cleaned_data["customer_name"]
            order.customer_phone = form.cleaned_data["customer_phone"]

            if order.order_type == Order.OrderType.DELIVERY:
                order.delivery_address = form.cleaned_data["delivery_address"]

            order.special_requests = form.cleaned_data.get("special_requests", "")
            order.status = Order.OrderStatus.PLACED
            order.placed_at = timezone.now()
            order.save()

            OrderItem.objects.filter(order=order).update(status=Order.OrderStatus.PLACED)

            payment_method = form.cleaned_data["payment_method"]
            Payment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=order.total_amount,
                status=Payment.PaymentStatus.PENDING,
            )

            request.session.pop("current_order_id", None)

            # TODO Реализовать отдельно отправку уведомлений
            # send_order_confirmation_email(order)

            messages.success(
                request,
                _("Ваш заказ успешно оформлен! Номер заказа: {}.").format(order.order_number),
            )
            return redirect("customer_order_status", id=order.id)
    else:
        initial_data = {}
        if hasattr(request.user, "profile"):
            initial_data = {
                "customer_name": request.user.get_full_name() or request.user.username,
                "customer_phone": request.user.profile.phone_number or "",
            }
        form = CheckoutForm(
            instance=order, user=request.user, order_type=order.order_type, initial=initial_data
        )

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    order_nutrition = order.get_order_nutrition()
    order_allergens = order.get_order_allergens()

    context = {
        "order": order,
        "form": form,
        "order_items": order_items,
        "order_nutrition": order_nutrition,
        "order_allergens": order_allergens,
    }

    return render(request, "orders/customer_checkout.html", context)


@login_required
@permission_required("orders.view_own_order", raise_exception=True)
def customer_order_status(request, id):
    """Просмотр статуса заказа клиентом."""
    order = get_object_or_404(Order, id=id)

    if order.customer != request.user:
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("customer_orders_history")

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    payments = Payment.objects.filter(order=order).order_by("-payment_date")

    context = {
        "order": order,
        "order_items": order_items,
        "payments": payments,
    }

    return render(request, "orders/customer_order_status.html", context)


@login_required
@permission_required("orders.view_own_order", raise_exception=True)
def customer_orders_history(request):
    """История заказов клиента."""
    orders = (
        Order.objects.filter(customer=request.user)
        .exclude(status=Order.OrderStatus.DRAFT)
        .order_by("-placed_at")
    )

    paginator = Paginator(orders, 10)
    page = request.GET.get("page")

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    context = {
        "orders": orders_page,
    }

    return render(request, "orders/customer_orders_history.html", context)


@login_required
@permission_required("orders.view_order", raise_exception=True)
def active_orders(request):
    """Список активных заказов для персонала."""
    user = request.user

    if user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif user.is_manager():
        restaurants = user.managed_restaurants.filter(is_active=True)
    else:
        if user.restaurant:
            restaurants = Restaurant.objects.filter(id=user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("active_orders")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
            }
            return render(request, "orders/select_restaurant.html", context)

    status_filter = request.GET.get("status", "")
    waiter_filter = request.GET.get("waiter", "")

    orders = (
        Order.objects.filter(restaurant=restaurant)
        .exclude(
            status__in=[
                Order.OrderStatus.DRAFT,
                Order.OrderStatus.COMPLETED,
                Order.OrderStatus.CANCELLED,
            ]
        )
        .order_by("-placed_at")
    )

    if status_filter:
        orders = orders.filter(status=status_filter)

    if waiter_filter:
        orders = orders.filter(waiter_id=waiter_filter)

    waiters = User.objects.filter(
        Q(role="WAITER") & (Q(restaurant=restaurant) | Q(managed_restaurants=restaurant))
    ).distinct()

    paginator = Paginator(orders, 20)
    page = request.GET.get("page")

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    order_stats = {
        "total": orders.count(),
        "preparing": orders.filter(status=Order.OrderStatus.PREPARING).count(),
        "ready": orders.filter(status=Order.OrderStatus.READY).count(),
        "served": orders.filter(status=Order.OrderStatus.SERVED).count(),
        "placed": orders.filter(status=Order.OrderStatus.PLACED).count(),
    }

    context = {
        "orders": orders_page,
        "restaurant": restaurant,
        "waiters": waiters,
        "status_choices": Order.OrderStatus.choices,
        "selected_status": status_filter,
        "selected_waiter": waiter_filter,
        "order_stats": order_stats,
    }

    return render(request, "orders/active_orders.html", context)


@login_required
@permission_required("orders.add_order", raise_exception=True)
def create_order(request, table_id=None):
    """Создание заказа персоналом."""
    user = request.user

    if user.restaurant:
        restaurant = user.restaurant
    elif user.is_admin() or user.is_manager():
        if "restaurant_id" in request.GET:
            restaurant = get_object_or_404(
                Restaurant, id=request.GET["restaurant_id"], is_active=True
            )
            if user.is_manager() and not user.managed_restaurants.filter(id=restaurant.id).exists():
                messages.error(request, _("У вас нет доступа к этому ресторану."))
                return redirect("home")
        else:
            if user.is_admin():
                restaurants = Restaurant.objects.filter(is_active=True)
            else:
                restaurants = user.managed_restaurants.filter(is_active=True)

            if restaurants.count() == 1:
                restaurant = restaurants.first()
            else:
                context = {
                    "restaurants": restaurants,
                }
                return render(request, "orders/select_restaurant.html", context)
    else:
        messages.error(request, _("Вы не привязаны ни к одному ресторану."))
        return redirect("home")

    table = None
    if table_id:
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    elif "table_id" in request.GET:
        table = get_object_or_404(Table, id=request.GET["table_id"], restaurant=restaurant)

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "")
        customer_phone = request.POST.get("customer_phone", "")
        special_requests = request.POST.get("special_requests", "")

        order = Order.objects.create(
            restaurant=restaurant,
            table=table,
            waiter=user,
            status=Order.OrderStatus.PLACED,
            order_type=Order.OrderType.DINE_IN if table else Order.OrderType.TAKEAWAY,
            customer_name=customer_name,
            customer_phone=customer_phone,
            special_requests=special_requests,
            placed_at=timezone.now(),
        )

        messages.success(request, _("Заказ успешно создан! Добавьте позиции в заказ."))
        return redirect("edit_order", id=order.id)

    if table:
        tables = [table]
    else:
        tables = Table.objects.filter(
            restaurant=restaurant,
            is_active=True,
            status__in=[Table.TableStatus.FREE, Table.TableStatus.RESERVED],
        ).order_by("number")

    context = {
        "restaurant": restaurant,
        "tables": tables,
        "selected_table": table,
    }

    return render(request, "orders/create_order.html", context)


@login_required
@permission_required("orders.view_order", raise_exception=True)
def order_details(request, id):
    """Просмотр деталей заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("active_orders")
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("active_orders")

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    payments = Payment.objects.filter(order=order).order_by("-payment_date")

    total_paid = payments.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(Sum("amount"))[
        "amount__sum"
    ] or Decimal("0.00")
    payment_status = {
        "paid": total_paid,
        "remaining": order.total_amount - total_paid,
        "is_fully_paid": total_paid >= order.total_amount,
    }

    order_nutrition = order.get_order_nutrition()
    order_allergens = order.get_order_allergens()

    context = {
        "order": order,
        "order_items": order_items,
        "payments": payments,
        "payment_status": payment_status,
        "order_nutrition": order_nutrition,
        "order_allergens": order_allergens,
    }

    return render(request, "orders/order_details.html", context)


@login_required
@permission_required("orders.change_order", raise_exception=True)
def edit_order(request, id):
    """Редактирование заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("active_orders")
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("active_orders")

    if order.status in [Order.OrderStatus.COMPLETED, Order.OrderStatus.CANCELLED]:
        messages.error(request, _("Невозможно редактировать завершенный или отмененный заказ."))
        return redirect("order_details", id=order.id)

    if request.method == "POST" and "add_item" in request.POST:
        menu_item_id = request.POST.get("menu_item_id")
        quantity = int(request.POST.get("quantity", 1))
        notes = request.POST.get("notes", "")

        try:
            menu_item = MenuItem.objects.get(
                id=menu_item_id, restaurant=order.restaurant, is_active=True
            )

            order_item = OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                unit_price=menu_item.price,
                notes=notes,
                status=order.status,
            )

            for key, value in request.POST.items():
                if key.startswith("modifier_") and value == "on":
                    modifier_id = key.split("_")[1]
                    try:
                        modifier = Modifier.objects.get(id=modifier_id, is_active=True)
                        quantity_key = f"modifier_{modifier_id}_quantity"
                        modifier_quantity = int(request.POST.get(quantity_key, 1))

                        OrderItemModifier.objects.create(
                            order_item=order_item, modifier=modifier, quantity=modifier_quantity
                        )
                    except (Modifier.DoesNotExist, ValueError):
                        pass

            order.calculate_totals()

            messages.success(request, _("Позиция успешно добавлена в заказ."))
            return redirect("edit_order", id=order.id)

        except MenuItem.DoesNotExist:
            messages.error(request, _("Выбранное блюдо не найдено."))

    elif request.method == "POST" and "update_order" in request.POST:
        customer_name = request.POST.get("customer_name", "")
        customer_phone = request.POST.get("customer_phone", "")
        special_requests = request.POST.get("special_requests", "")

        order.customer_name = customer_name
        order.customer_phone = customer_phone
        order.special_requests = special_requests
        order.save()

        messages.success(request, _("Информация о заказе обновлена."))
        return redirect("edit_order", id=order.id)

    order_items = OrderItem.objects.filter(order=order).select_related("menu_item")

    categories = order.restaurant.menu_categories.filter(
        parent__isnull=True, is_active=True
    ).prefetch_related("subcategories")

    menu_structure = []
    for category in categories:
        category_data = {
            "category": category,
            "subcategories": [],
            "items": MenuItem.objects.filter(
                category=category, is_active=True, status="AVAILABLE"
            ).order_by("order_in_category"),
        }

        for subcategory in category.subcategories.filter(is_active=True):
            subcategory_data = {
                "category": subcategory,
                "items": MenuItem.objects.filter(
                    category=subcategory, is_active=True, status="AVAILABLE"
                ).order_by("order_in_category"),
            }
            category_data["subcategories"].append(subcategory_data)

        menu_structure.append(category_data)

    order_nutrition = order.get_order_nutrition()
    order_allergens = order.get_order_allergens()

    context = {
        "order": order,
        "order_items": order_items,
        "menu_structure": menu_structure,
        "order_nutrition": order_nutrition,
        "order_allergens": order_allergens,
    }

    return render(request, "orders/edit_order.html", context)


@login_required
@permission_required("orders.change_order", raise_exception=True)
@require_POST
def update_order_item(request, id, item_id):
    """AJAX-метод для обновления позиции заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            return JsonResponse({"success": False, "error": "Access denied"}, status=403)
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        return JsonResponse({"success": False, "error": "Access denied"}, status=403)

    try:
        order_item = OrderItem.objects.get(id=item_id, order=order)
    except OrderItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found"}, status=404)

    if order.status in [Order.OrderStatus.COMPLETED, Order.OrderStatus.CANCELLED]:
        return JsonResponse({"success": False, "error": "Order cannot be modified"}, status=400)

    quantity = int(request.POST.get("quantity", 1))

    if quantity <= 0:
        order_item.delete()
    else:
        order_item.quantity = quantity
        order_item.save()

    order.calculate_totals()

    return JsonResponse(
        {
            "success": True,
            "item_total": float(order_item.get_total_price()) if quantity > 0 else 0,
            "order_total": float(order.total_amount),
            "subtotal": float(order.subtotal),
            "discount_amount": float(order.discount_amount),
            "tax_amount": float(order.tax_amount),
        }
    )


@login_required
@permission_required("orders.change_order", raise_exception=True)
def remove_order_item(request, id, item_id):
    """Удаление позиции из заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("active_orders")
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("active_orders")

    if order.status in [Order.OrderStatus.COMPLETED, Order.OrderStatus.CANCELLED]:
        messages.error(request, _("Невозможно редактировать завершенный или отмененный заказ."))
        return redirect("order_details", id=order.id)

    try:
        order_item = OrderItem.objects.get(id=item_id, order=order)
    except OrderItem.DoesNotExist:
        messages.error(request, _("Позиция не найдена."))
        return redirect("edit_order", id=order.id)

    order_item.delete()

    order.calculate_totals()

    messages.success(request, _("Позиция успешно удалена из заказа."))
    return redirect("edit_order", id=order.id)


@login_required
@permission_required("orders.change_order", raise_exception=True)
@require_POST
def update_order_status(request, id):
    """Обновление статуса заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("active_orders")
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("active_orders")

    new_status = request.POST.get("status")

    valid_statuses = [status[0] for status in Order.OrderStatus.choices]
    if new_status not in valid_statuses:
        messages.error(request, _("Указан неверный статус."))
        return redirect("order_details", id=order.id)

    if order.status == Order.OrderStatus.COMPLETED and new_status != Order.OrderStatus.CANCELLED:
        messages.error(request, _("Невозможно изменить статус завершенного заказа."))
        return redirect("order_details", id=order.id)

    if order.status == Order.OrderStatus.CANCELLED and new_status != Order.OrderStatus.PLACED:
        messages.error(request, _("Невозможно изменить статус отмененного заказа."))
        return redirect("order_details", id=order.id)

    order.status = new_status

    if new_status == Order.OrderStatus.COMPLETED:
        order.completed_at = timezone.now()

    order.save()

    OrderItem.objects.filter(order=order).update(status=new_status)

    messages.success(request, _("Статус заказа успешно обновлен."))
    return redirect("order_details", id=order.id)


@login_required
@permission_required("orders.process_payment", raise_exception=True)
def order_payment(request, id):
    """Оплата заказа."""
    order = get_object_or_404(Order, id=id)
    user = request.user

    if not user.is_admin() and not user.is_manager():
        if user.restaurant and user.restaurant != order.restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("active_orders")
    elif user.is_manager() and not user.managed_restaurants.filter(id=order.restaurant.id).exists():
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("active_orders")

    if order.status in [Order.OrderStatus.DRAFT, Order.OrderStatus.CANCELLED]:
        messages.error(request, _("Невозможно оплатить черновик или отмененный заказ."))
        return redirect("order_details", id=order.id)

    payments = Payment.objects.filter(order=order)
    total_paid = payments.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(Sum("amount"))[
        "amount__sum"
    ] or Decimal("0.00")
    remaining = order.total_amount - total_paid

    if remaining <= 0:
        messages.info(request, _("Заказ уже полностью оплачен."))
        return redirect("order_details", id=order.id)

    if request.method == "POST":
        form = PaymentForm(request.POST, order=order)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.processed_by = user

            if payment.amount > remaining:
                form.add_error("amount", _("Сумма платежа превышает остаток к оплате."))
            else:
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.save()

                new_total_paid = total_paid + payment.amount
                if new_total_paid >= order.total_amount and order.status in [
                    Order.OrderStatus.SERVED,
                    Order.OrderStatus.READY,
                ]:
                    order.status = Order.OrderStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save()

                    OrderItem.objects.filter(order=order).update(status=Order.OrderStatus.COMPLETED)

                messages.success(request, _("Платеж успешно обработан."))
                return redirect("order_details", id=order.id)
    else:
        form = PaymentForm(order=order, initial={"amount": remaining})

    context = {
        "order": order,
        "form": form,
        "payments": payments,
        "total_paid": total_paid,
        "remaining": remaining,
    }

    return render(request, "orders/order_payment.html", context)


@login_required
@permission_required("orders.view_order_history", raise_exception=True)
def order_history(request):
    """История заказов."""
    user = request.user

    if user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif user.is_manager():
        restaurants = user.managed_restaurants.filter(is_active=True)
    else:
        if user.restaurant:
            restaurants = Restaurant.objects.filter(id=user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("order_history")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {
                "restaurants": restaurants,
                "action": "history",
            }
            return render(request, "orders/select_restaurant.html", context)

    status_filter = request.GET.get("status", "")
    waiter_filter = request.GET.get("waiter", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

    orders = Order.objects.filter(
        restaurant=restaurant, status__in=[Order.OrderStatus.COMPLETED, Order.OrderStatus.CANCELLED]
    ).order_by("-completed_at", "-placed_at")

    if status_filter:
        orders = orders.filter(status=status_filter)

    if waiter_filter:
        orders = orders.filter(waiter_id=waiter_filter)

    if from_date:
        try:
            from_date_obj = timezone.datetime.strptime(from_date, "%Y-%m-%d").date()
            orders = orders.filter(placed_at__date__gte=from_date_obj)
        except ValueError:
            pass

    if to_date:
        try:
            to_date_obj = timezone.datetime.strptime(to_date, "%Y-%m-%d").date()
            orders = orders.filter(placed_at__date__lte=to_date_obj)
        except ValueError:
            pass

    waiters = User.objects.filter(
        Q(role="WAITER") & (Q(restaurant=restaurant) | Q(managed_restaurants=restaurant))
    ).distinct()

    paginator = Paginator(orders, 20)
    page = request.GET.get("page")

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    if from_date or to_date or status_filter or waiter_filter:
        filtered_orders = orders
    else:
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        filtered_orders = orders.filter(placed_at__gte=thirty_days_ago)

    completed_orders = filtered_orders.filter(status=Order.OrderStatus.COMPLETED)

    order_stats = {
        "total_count": filtered_orders.count(),
        "completed_count": completed_orders.count(),
        "cancelled_count": filtered_orders.filter(status=Order.OrderStatus.CANCELLED).count(),
        "total_revenue": completed_orders.aggregate(Sum("total_amount"))["total_amount__sum"] or 0,
        "avg_order_value": completed_orders.aggregate(Avg("total_amount"))["total_amount__avg"]
        or 0,
    }

    context = {
        "orders": orders_page,
        "restaurant": restaurant,
        "waiters": waiters,
        "status_choices": [
            (Order.OrderStatus.COMPLETED, _("Выполнен")),
            (Order.OrderStatus.CANCELLED, _("Отменен")),
        ],
        "selected_status": status_filter,
        "selected_waiter": waiter_filter,
        "from_date": from_date,
        "to_date": to_date,
        "order_stats": order_stats,
    }

    return render(request, "orders/order_history.html", context)


@login_required
@permission_required("orders.manage_discounts", raise_exception=True)
def discount_list(request):
    """Список скидок и промокодов."""
    user = request.user

    if user.is_admin():
        discounts = Discount.objects.all()
        restaurants = Restaurant.objects.filter(is_active=True)
    elif user.is_manager():
        restaurants = user.managed_restaurants.filter(is_active=True)
        discounts = Discount.objects.filter(
            Q(restaurant__in=restaurants) | Q(restaurant__isnull=True)
        )
    else:
        if user.restaurant:
            restaurants = Restaurant.objects.filter(id=user.restaurant.id)
            discounts = Discount.objects.filter(
                Q(restaurant=user.restaurant) | Q(restaurant__isnull=True)
            )
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_filter = request.GET.get("restaurant", "")
    is_active_filter = request.GET.get("is_active", "")
    discount_type_filter = request.GET.get("discount_type", "")
    search = request.GET.get("search", "")

    if restaurant_filter:
        discounts = discounts.filter(restaurant_id=restaurant_filter)

    if is_active_filter:
        is_active = is_active_filter == "true"
        discounts = discounts.filter(is_active=is_active)

    if discount_type_filter:
        discounts = discounts.filter(discount_type=discount_type_filter)

    if search:
        discounts = discounts.filter(
            Q(code__icontains=search) | Q(name__icontains=search) | Q(description__icontains=search)
        )

    discounts = discounts.order_by("-created_at")

    paginator = Paginator(discounts, 20)
    page = request.GET.get("page")

    try:
        discounts_page = paginator.page(page)
    except PageNotAnInteger:
        discounts_page = paginator.page(1)
    except EmptyPage:
        discounts_page = paginator.page(paginator.num_pages)

    context = {
        "discounts": discounts_page,
        "restaurants": restaurants,
        "selected_restaurant": restaurant_filter,
        "selected_is_active": is_active_filter,
        "selected_discount_type": discount_type_filter,
        "search": search,
        "discount_types": Discount.DiscountType.choices,
    }

    return render(request, "orders/discount_list.html", context)


@login_required
@permission_required("orders.manage_discounts", raise_exception=True)
def discount_create(request):
    """Создание новой скидки/промокода."""
    user = request.user

    if request.method == "POST":
        form = DiscountAdminForm(request.POST, user=user)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.created_by = user
            discount.save()
            form.save_m2m()

            messages.success(request, _("Скидка/промокод успешно создана!"))
            return redirect("discount_list")
    else:
        form = DiscountAdminForm(user=user)

    context = {
        "form": form,
        "is_create": True,
    }

    return render(request, "orders/discount_form.html", context)


@login_required
@permission_required("orders.manage_discounts", raise_exception=True)
def discount_edit(request, id):
    """Редактирование скидки/промокода."""
    discount = get_object_or_404(Discount, id=id)
    user = request.user

    if not user.is_admin():
        if discount.restaurant and user.is_manager():
            if not user.managed_restaurants.filter(id=discount.restaurant.id).exists():
                messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
                return redirect("discount_list")
        elif user.restaurant and user.restaurant != discount.restaurant:
            messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
            return redirect("discount_list")

    if request.method == "POST":
        form = DiscountAdminForm(request.POST, instance=discount, user=user)
        if form.is_valid():
            form.save()

            messages.success(request, _("Скидка/промокод успешно обновлена!"))
            return redirect("discount_list")
    else:
        form = DiscountAdminForm(instance=discount, user=user)

    usage_stats = {
        "total_used": discount.times_used,
        "orders_count": discount.orders.count(),
        "total_discount_amount": discount.orders.aggregate(Sum("discount_amount"))[
            "discount_amount__sum"
        ]
        or 0,
    }

    context = {
        "form": form,
        "discount": discount,
        "is_create": False,
        "usage_stats": usage_stats,
    }

    return render(request, "orders/discount_form.html", context)


@login_required
@permission_required("orders.manage_discounts", raise_exception=True)
def discount_toggle_status(request, id):
    """Изменение статуса скидки/промокода (активна/неактивна)."""
    discount = get_object_or_404(Discount, id=id)
    user = request.user

    if not user.is_admin():
        if discount.restaurant and user.is_manager():
            if not user.managed_restaurants.filter(id=discount.restaurant.id).exists():
                messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
                return redirect("discount_list")
        elif user.restaurant and user.restaurant != discount.restaurant:
            messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
            return redirect("discount_list")

    discount.is_active = not discount.is_active
    discount.save()

    messages.success(
        request,
        _("Статус скидки/промокода изменен на: {}").format(
            _("Активна") if discount.is_active else _("Неактивна")
        ),
    )

    return redirect("discount_list")


@login_required
@permission_required("orders.manage_discounts", raise_exception=True)
def discount_delete(request, id):
    """Удаление скидки/промокода."""
    discount = get_object_or_404(Discount, id=id)
    user = request.use

    if not user.is_admin():
        if discount.restaurant and user.is_manager():
            if not user.managed_restaurants.filter(id=discount.restaurant.id).exists():
                messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
                return redirect("discount_list")
        elif user.restaurant and user.restaurant != discount.restaurant:
            messages.error(request, _("У вас нет доступа к этой скидке/промокоду."))
            return redirect("discount_list")

    active_orders_with_discount = Order.objects.filter(
        discount=discount,
        status__in=[
            Order.OrderStatus.DRAFT,
            Order.OrderStatus.PLACED,
            Order.OrderStatus.PREPARING,
            Order.OrderStatus.READY,
            Order.OrderStatus.SERVED,
        ],
    )

    if active_orders_with_discount.exists():
        messages.error(
            request,
            _("Невозможно удалить скидку/промокод, так как она используется в активных заказах."),
        )
        return redirect("discount_edit", id=discount.id)

    if request.method == "POST":
        discount.delete()

        messages.success(request, _("Скидка/промокод успешно удалена."))
        return redirect("discount_list")

    usage_stats = {
        "total_used": discount.times_used,
        "orders_count": discount.orders.count(),
        "total_discount_amount": discount.orders.aggregate(Sum("discount_amount"))[
            "discount_amount__sum"
        ]
        or 0,
    }

    context = {
        "discount": discount,
        "usage_stats": usage_stats,
    }

    return render(request, "orders/discount_delete.html", context)
