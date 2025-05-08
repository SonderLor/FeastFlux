from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField, Sum
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction

from .models import KitchenQueue, KitchenOrder, KitchenOrderItem, CookingStation, KitchenEvent
from .forms import (
    CookingStationForm,
    KitchenEventFilterForm,
    UpdateKitchenOrderStatusForm,
    UpdateKitchenItemStatusForm,
    AssignOrderForm,
)
from restaurants.models import Restaurant


@login_required
@permission_required("kitchen.view_kitchen_dashboard", raise_exception=True)
def kitchen_dashboard(request):
    """Основная панель кухни."""
    if request.user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.is_manager():
        restaurants = request.user.managed_restaurants.filter(is_active=True)
    else:
        if request.user.restaurant:
            restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("kitchen_dashboard")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {"restaurants": restaurants, "action": "kitchen"}
            return render(request, "kitchen/select_restaurant.html", context)

    queues = KitchenQueue.objects.filter(restaurant=restaurant)

    queue_stats = []
    for queue in queues:
        active_orders = KitchenOrder.objects.filter(
            queue=queue,
            status__in=[
                KitchenOrder.KitchenOrderStatus.NEW,
                KitchenOrder.KitchenOrderStatus.IN_PROGRESS,
            ],
        )

        new_orders = active_orders.filter(status=KitchenOrder.KitchenOrderStatus.NEW).count()
        in_progress_orders = active_orders.filter(
            status=KitchenOrder.KitchenOrderStatus.IN_PROGRESS
        ).count()
        delayed_orders = active_orders.filter(
            status=KitchenOrder.KitchenOrderStatus.DELAYED
        ).count()

        avg_time = queue.average_processing_time()

        queue_stats.append(
            {
                "queue": queue,
                "active_orders": active_orders.count(),
                "new_orders": new_orders,
                "in_progress_orders": in_progress_orders,
                "delayed_orders": delayed_orders,
                "avg_time": avg_time,
            }
        )

    delayed_orders = KitchenOrder.objects.filter(
        Q(queue__restaurant=restaurant),
        Q(status=KitchenOrder.KitchenOrderStatus.DELAYED)
        | Q(
            Q(status=KitchenOrder.KitchenOrderStatus.IN_PROGRESS)
            & Q(estimated_completion_time__isnull=False)
            & Q(estimated_completion_time__lt=timezone.now())
        ),
    ).order_by("created_at")[:5]

    total_orders_today = KitchenOrder.objects.filter(
        queue__restaurant=restaurant, created_at__date=timezone.now().date()
    ).count()

    completed_orders_today = KitchenOrder.objects.filter(
        queue__restaurant=restaurant,
        status=KitchenOrder.KitchenOrderStatus.COMPLETED,
        completed_at__date=timezone.now().date(),
    ).count()

    avg_prep_time_today = (
        KitchenOrder.objects.filter(
            queue__restaurant=restaurant,
            status=KitchenOrder.KitchenOrderStatus.COMPLETED,
            completed_at__date=timezone.now().date(),
            started_at__isnull=False,
        )
        .annotate(
            prep_time=ExpressionWrapper(
                F("completed_at") - F("started_at"), output_field=DurationField()
            )
        )
        .aggregate(avg_time=Avg("prep_time"))["avg_time"]
    )

    if avg_prep_time_today:
        avg_prep_minutes = avg_prep_time_today.total_seconds() / 60
    else:
        avg_prep_minutes = 0

    context = {
        "restaurant": restaurant,
        "queues": queues,
        "queue_stats": queue_stats,
        "delayed_orders": delayed_orders,
        "total_orders_today": total_orders_today,
        "completed_orders_today": completed_orders_today,
        "avg_prep_minutes": round(avg_prep_minutes),
    }

    return render(request, "kitchen/dashboard.html", context)


@login_required
@permission_required("kitchen.view_kitchen_queue", raise_exception=True)
def kitchen_queue(request, id):
    """Детальный вид очереди кухни."""
    queue = get_object_or_404(KitchenQueue, id=id)
    restaurant = queue.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этой очереди."))
            return redirect("kitchen_dashboard")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этой очереди."))
        return redirect("kitchen_dashboard")

    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")

    orders = KitchenOrder.objects.filter(queue=queue)

    if status_filter:
        orders = orders.filter(status=status_filter)

    if priority_filter:
        orders = orders.filter(priority=priority_filter)

    new_orders = orders.filter(status=KitchenOrder.KitchenOrderStatus.NEW).order_by(
        "-priority", "created_at"
    )
    in_progress_orders = orders.filter(status=KitchenOrder.KitchenOrderStatus.IN_PROGRESS).order_by(
        "-priority", "started_at"
    )
    completed_orders = orders.filter(status=KitchenOrder.KitchenOrderStatus.COMPLETED).order_by(
        "-completed_at"
    )[:10]
    delayed_orders = orders.filter(status=KitchenOrder.KitchenOrderStatus.DELAYED).order_by(
        "-priority", "created_at"
    )

    new_count = new_orders.count()
    in_progress_count = in_progress_orders.count()
    completed_count = completed_orders.count()
    delayed_count = delayed_orders.count()

    from django.contrib.auth import get_user_model

    User = get_user_model()

    kitchen_staff = (
        User.objects.filter(Q(restaurant=restaurant) | Q(managed_restaurants=restaurant))
        .filter(role__in=["CHEF", "BARTENDER", "COOK"])
        .distinct()
    )

    assign_form = AssignOrderForm(restaurant=restaurant)

    context = {
        "queue": queue,
        "restaurant": restaurant,
        "new_orders": new_orders,
        "in_progress_orders": in_progress_orders,
        "completed_orders": completed_orders,
        "delayed_orders": delayed_orders,
        "new_count": new_count,
        "in_progress_count": in_progress_count,
        "completed_count": completed_count,
        "delayed_count": delayed_count,
        "kitchen_staff": kitchen_staff,
        "assign_form": assign_form,
        "status_filter": status_filter,
        "priority_filter": priority_filter,
        "status_choices": KitchenOrder.KitchenOrderStatus.choices,
        "priority_choices": KitchenOrder.KitchenOrderPriority.choices,
    }

    return render(request, "kitchen/queue.html", context)


@login_required
@permission_required("kitchen.view_kitchen_order", raise_exception=True)
def kitchen_order_details(request, id):
    """Детальная информация о заказе на кухне."""
    kitchen_order = get_object_or_404(KitchenOrder, id=id)
    restaurant = kitchen_order.queue.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("kitchen_dashboard")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("kitchen_dashboard")

    kitchen_items = KitchenOrderItem.objects.filter(kitchen_order=kitchen_order).order_by(
        "sequence_number"
    )

    events = KitchenEvent.objects.filter(kitchen_order=kitchen_order).order_by("-created_at")[:10]

    order_status_form = UpdateKitchenOrderStatusForm(initial={"status": kitchen_order.status})

    order_allergens = (
        kitchen_order.order.get_order_allergens()
        if hasattr(kitchen_order.order, "get_order_allergens")
        else []
    )

    nutrition_preferences = (
        kitchen_order.order.nutritional_preferences
        if kitchen_order.order.nutritional_preferences
        else {}
    )

    context = {
        "kitchen_order": kitchen_order,
        "order": kitchen_order.order,
        "kitchen_items": kitchen_items,
        "events": events,
        "order_status_form": order_status_form,
        "order_allergens": order_allergens,
        "nutrition_preferences": nutrition_preferences,
        "restaurant": restaurant,
    }

    return render(request, "kitchen/order_details.html", context)


@login_required
@permission_required("kitchen.view_kitchen_order", raise_exception=True)
@transaction.atomic
def update_kitchen_order_status(request, id):
    """Обновление статуса заказа на кухне."""
    kitchen_order = get_object_or_404(KitchenOrder, id=id)
    restaurant = kitchen_order.queue.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("kitchen_dashboard")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("kitchen_dashboard")

    if request.method == "POST":
        form = UpdateKitchenOrderStatusForm(request.POST)
        if form.is_valid():
            old_status = kitchen_order.status
            new_status = form.cleaned_data["status"]
            notes = form.cleaned_data.get("notes", "")

            kitchen_order.status = new_status

            if (
                new_status == KitchenOrder.KitchenOrderStatus.IN_PROGRESS
                and not kitchen_order.started_at
            ):
                kitchen_order.started_at = timezone.now()

            if (
                new_status == KitchenOrder.KitchenOrderStatus.COMPLETED
                and not kitchen_order.completed_at
            ):
                kitchen_order.completed_at = timezone.now()

            if notes:
                kitchen_order.notes = notes

            kitchen_order.save()

            if new_status == KitchenOrder.KitchenOrderStatus.IN_PROGRESS:
                KitchenOrderItem.objects.filter(
                    kitchen_order=kitchen_order, status=KitchenOrderItem.KitchenItemStatus.PENDING
                ).update(
                    status=KitchenOrderItem.KitchenItemStatus.PREPARING, started_at=timezone.now()
                )

            elif new_status == KitchenOrder.KitchenOrderStatus.COMPLETED:
                KitchenOrderItem.objects.filter(
                    kitchen_order=kitchen_order,
                    status__in=[
                        KitchenOrderItem.KitchenItemStatus.PENDING,
                        KitchenOrderItem.KitchenItemStatus.PREPARING,
                    ],
                ).update(
                    status=KitchenOrderItem.KitchenItemStatus.READY, completed_at=timezone.now()
                )

            elif new_status == KitchenOrder.KitchenOrderStatus.CANCELLED:
                KitchenOrderItem.objects.filter(
                    kitchen_order=kitchen_order,
                    status__in=[
                        KitchenOrderItem.KitchenItemStatus.PENDING,
                        KitchenOrderItem.KitchenItemStatus.PREPARING,
                    ],
                ).update(status=KitchenOrderItem.KitchenItemStatus.CANCELLED)

            KitchenEvent.objects.create(
                restaurant=restaurant,
                kitchen_order=kitchen_order,
                event_type=KitchenEvent.EventType.ORDER_STATUS_CHANGED,
                description=f"Статус заказа изменен с '{old_status}' на '{new_status}'",
                created_by=request.user,
                ip_address=request.META.get("REMOTE_ADDR", None),
                user_agent=request.META.get("HTTP_USER_AGENT", None),
            )

            messages.success(request, _("Статус заказа успешно обновлен."))

            referer = request.META.get("HTTP_REFERER")
            if "queue" in referer:
                return redirect("kitchen_queue", id=kitchen_order.queue.id)
            else:
                return redirect("kitchen_order_details", id=kitchen_order.id)

    messages.error(request, _("Ошибка при обновлении статуса заказа."))
    return redirect("kitchen_order_details", id=kitchen_order.id)


@login_required
@permission_required("kitchen.view_kitchen_order", raise_exception=True)
@transaction.atomic
def update_kitchen_item_status(request, id):
    """Обновление статуса позиции заказа на кухне."""
    kitchen_item = get_object_or_404(KitchenOrderItem, id=id)
    kitchen_order = kitchen_item.kitchen_order
    restaurant = kitchen_order.queue.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этой позиции."))
            return redirect("kitchen_dashboard")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этой позиции."))
        return redirect("kitchen_dashboard")

    if request.method == "POST":
        form = UpdateKitchenItemStatusForm(request.POST)
        if form.is_valid():
            old_status = kitchen_item.status
            new_status = form.cleaned_data["status"]
            notes = form.cleaned_data.get("notes", "")

            kitchen_item.status = new_status

            if (
                new_status == KitchenOrderItem.KitchenItemStatus.PREPARING
                and not kitchen_item.started_at
            ):
                kitchen_item.started_at = timezone.now()

                if kitchen_order.status == KitchenOrder.KitchenOrderStatus.NEW:
                    kitchen_order.status = KitchenOrder.KitchenOrderStatus.IN_PROGRESS
                    kitchen_order.started_at = timezone.now()
                    kitchen_order.save()

            if (
                new_status == KitchenOrderItem.KitchenItemStatus.READY
                and not kitchen_item.completed_at
            ):
                kitchen_item.completed_at = timezone.now()

            if notes:
                kitchen_item.preparation_notes = notes

            kitchen_item.save()

            if new_status == KitchenOrderItem.KitchenItemStatus.READY:
                all_items_ready = (
                    not KitchenOrderItem.objects.filter(kitchen_order=kitchen_order)
                    .exclude(
                        status__in=[
                            KitchenOrderItem.KitchenItemStatus.READY,
                            KitchenOrderItem.KitchenItemStatus.SERVED,
                            KitchenOrderItem.KitchenItemStatus.CANCELLED,
                        ]
                    )
                    .exists()
                )

                if (
                    all_items_ready
                    and kitchen_order.status != KitchenOrder.KitchenOrderStatus.COMPLETED
                ):
                    kitchen_order.status = KitchenOrder.KitchenOrderStatus.COMPLETED
                    kitchen_order.completed_at = timezone.now()
                    kitchen_order.save()

            KitchenEvent.objects.create(
                restaurant=restaurant,
                kitchen_order=kitchen_order,
                kitchen_item=kitchen_item,
                event_type=KitchenEvent.EventType.ITEM_STATUS_CHANGED,
                description=f"Статус позиции '{kitchen_item.order_item.menu_item.name}' изменен с '{old_status}' на '{new_status}'",
                created_by=request.user,
                ip_address=request.META.get("REMOTE_ADDR", None),
                user_agent=request.META.get("HTTP_USER_AGENT", None),
            )

            messages.success(request, _("Статус позиции успешно обновлен."))

            kitchen_order.refresh_from_db()

            referer = request.META.get("HTTP_REFERER")
            if "queue" in referer:
                return redirect("kitchen_queue", id=kitchen_order.queue.id)
            else:
                return redirect("kitchen_order_details", id=kitchen_order.id)

    messages.error(request, _("Ошибка при обновлении статуса позиции."))
    return redirect("kitchen_order_details", id=kitchen_order.id)


@login_required
@permission_required("kitchen.view_kitchen_order", raise_exception=True)
@transaction.atomic
def assign_kitchen_order(request, id):
    """Назначение сотрудника для заказа на кухне."""
    kitchen_order = get_object_or_404(KitchenOrder, id=id)
    restaurant = kitchen_order.queue.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этому заказу."))
            return redirect("kitchen_dashboard")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этому заказу."))
        return redirect("kitchen_dashboard")

    if request.method == "POST":
        form = AssignOrderForm(request.POST, restaurant=restaurant)
        if form.is_valid():
            assigned_to = form.cleaned_data["assigned_to"]

            previous_assignee = kitchen_order.assigned_to
            kitchen_order.assigned_to = assigned_to
            kitchen_order.save()

            KitchenEvent.objects.create(
                restaurant=restaurant,
                kitchen_order=kitchen_order,
                event_type=KitchenEvent.EventType.STAFF_ASSIGNED,
                description=f"Заказ назначен на {assigned_to.get_full_name() or assigned_to.username}"
                + (
                    f" (предыдущий назначенный: {previous_assignee.get_full_name() or previous_assignee.username})"
                    if previous_assignee
                    else ""
                ),
                created_by=request.user,
                ip_address=request.META.get("REMOTE_ADDR", None),
                user_agent=request.META.get("HTTP_USER_AGENT", None),
            )

            messages.success(request, _("Заказ успешно назначен."))

            referer = request.META.get("HTTP_REFERER")
            if "queue" in referer:
                return redirect("kitchen_queue", id=kitchen_order.queue.id)
            else:
                return redirect("kitchen_order_details", id=kitchen_order.id)

    messages.error(request, _("Ошибка при назначении сотрудника на заказ."))
    return redirect("kitchen_order_details", id=kitchen_order.id)


@login_required
@permission_required("kitchen.manage_cooking_stations", raise_exception=True)
def cooking_stations(request):
    """Управление кухонными станциями."""
    if request.user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.is_manager():
        restaurants = request.user.managed_restaurants.filter(is_active=True)
    else:
        if request.user.restaurant:
            restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("cooking_stations")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {"restaurants": restaurants, "action": "cooking_stations"}
            return render(request, "kitchen/select_restaurant.html", context)

    stations = CookingStation.objects.filter(restaurant=restaurant)

    is_active_filter = request.GET.get("is_active")
    queue_filter = request.GET.get("queue")
    search = request.GET.get("search", "")

    if is_active_filter == "true":
        stations = stations.filter(is_active=True)
    elif is_active_filter == "false":
        stations = stations.filter(is_active=False)

    if queue_filter:
        stations = stations.filter(queue_id=queue_filter)

    if search:
        stations = stations.filter(Q(name__icontains=search) | Q(description__icontains=search))

    queues = KitchenQueue.objects.filter(restaurant=restaurant)

    for station in stations:
        station.current_workload = station.get_current_workload()

    context = {
        "restaurant": restaurant,
        "stations": stations,
        "queues": queues,
        "is_active_filter": is_active_filter,
        "queue_filter": queue_filter,
        "search": search,
    }

    return render(request, "kitchen/cooking_stations.html", context)


@login_required
@permission_required("kitchen.manage_cooking_stations", raise_exception=True)
def cooking_station_create(request):
    """Создание новой кухонной станции."""
    if request.user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.is_manager():
        restaurants = request.user.managed_restaurants.filter(is_active=True)
    else:
        if request.user.restaurant:
            restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("cooking_stations")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {"restaurants": restaurants, "action": "create_cooking_station"}
            return render(request, "kitchen/select_restaurant.html", context)

    queues = KitchenQueue.objects.filter(restaurant=restaurant)

    if request.method == "POST":
        form = CookingStationForm(request.POST)
        if form.is_valid():
            station = form.save(commit=False)
            station.restaurant = restaurant
            station.save()

            messages.success(request, _("Кухонная станция успешно создана."))
            return redirect("cooking_stations")
        else:
            messages.error(request, _("Пожалуйста, исправьте ошибки в форме."))
    else:
        form = CookingStationForm()

    form.fields["queue"].queryset = queues

    context = {"form": form, "restaurant": restaurant, "queues": queues, "is_create": True}

    return render(request, "kitchen/cooking_station_form.html", context)


@login_required
@permission_required("kitchen.manage_cooking_stations", raise_exception=True)
def cooking_station_edit(request, id):
    """Редактирование кухонной станции."""
    station = get_object_or_404(CookingStation, id=id)
    restaurant = station.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этой кухонной станции."))
            return redirect("cooking_stations")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этой кухонной станции."))
        return redirect("cooking_stations")

    queues = KitchenQueue.objects.filter(restaurant=restaurant)

    if request.method == "POST":
        form = CookingStationForm(request.POST, instance=station)
        if form.is_valid():
            form.save()
            messages.success(request, _("Кухонная станция успешно обновлена."))
            return redirect("cooking_stations")
        else:
            messages.error(request, _("Пожалуйста, исправьте ошибки в форме."))
    else:
        form = CookingStationForm(instance=station)

    form.fields["queue"].queryset = queues

    context = {
        "form": form,
        "station": station,
        "restaurant": restaurant,
        "queues": queues,
        "is_create": False,
    }

    return render(request, "kitchen/cooking_station_form.html", context)


@login_required
@permission_required("kitchen.manage_cooking_stations", raise_exception=True)
def cooking_station_toggle(request, id):
    """Включение/выключение кухонной станции."""
    station = get_object_or_404(CookingStation, id=id)
    restaurant = station.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этой кухонной станции."))
            return redirect("cooking_stations")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этой кухонной станции."))
        return redirect("cooking_stations")

    station.is_active = not station.is_active
    station.save()

    status_text = _("активирована") if station.is_active else _("деактивирована")
    messages.success(request, _(f'Кухонная станция "{station.name}" успешно {status_text}.'))

    return redirect("cooking_stations")


@login_required
@permission_required("kitchen.manage_cooking_stations", raise_exception=True)
def cooking_station_delete(request, id):
    """Удаление кухонной станции."""
    station = get_object_or_404(CookingStation, id=id)
    restaurant = station.restaurant

    if not request.user.is_admin() and not request.user.is_manager():
        if request.user.restaurant and request.user.restaurant != restaurant:
            messages.error(request, _("У вас нет доступа к этой кухонной станции."))
            return redirect("cooking_stations")
    elif (
        request.user.is_manager()
        and not request.user.managed_restaurants.filter(id=restaurant.id).exists()
    ):
        messages.error(request, _("У вас нет доступа к этой кухонной станции."))
        return redirect("cooking_stations")

    active_items = KitchenOrderItem.objects.filter(
        cooking_station=station.name,
        status__in=[
            KitchenOrderItem.KitchenItemStatus.PENDING,
            KitchenOrderItem.KitchenItemStatus.PREPARING,
        ],
    ).exists()

    if active_items:
        messages.error(
            request,
            _(
                "Невозможно удалить кухонную станцию, так как есть активные позиции, связанные с ней."
            ),
        )
        return redirect("cooking_stations")

    if request.method == "POST":
        station_name = station.name
        station.delete()

        messages.success(request, _(f'Кухонная станция "{station_name}" успешно удалена.'))
        return redirect("cooking_stations")

    context = {"station": station, "restaurant": restaurant}

    return render(request, "kitchen/cooking_station_delete.html", context)


@login_required
@permission_required("kitchen.view_kitchen_log", raise_exception=True)
def kitchen_log(request):
    """Журнал событий кухни."""
    if request.user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.is_manager():
        restaurants = request.user.managed_restaurants.filter(is_active=True)
    else:
        if request.user.restaurant:
            restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("kitchen_log")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            context = {"restaurants": restaurants, "action": "kitchen_log"}
            return render(request, "kitchen/select_restaurant.html", context)

    filter_form = KitchenEventFilterForm(request.GET)

    events = KitchenEvent.objects.filter(restaurant=restaurant)

    if filter_form.is_valid():
        start_date = filter_form.cleaned_data.get("start_date")
        end_date = filter_form.cleaned_data.get("end_date")
        event_type = filter_form.cleaned_data.get("event_type")
        order_number = filter_form.cleaned_data.get("order_number")
        user = filter_form.cleaned_data.get("user")

        if start_date:
            events = events.filter(created_at__date__gte=start_date)

        if end_date:
            events = events.filter(created_at__date__lte=end_date)

        if event_type:
            events = events.filter(event_type=event_type)

        if order_number:
            events = events.filter(kitchen_order__order__order_number__icontains=order_number)

        if user:
            events = events.filter(
                Q(created_by__username__icontains=user)
                | Q(created_by__first_name__icontains=user)
                | Q(created_by__last_name__icontains=user)
            )

    event_stats = events.values("event_type").annotate(count=Count("id")).order_by("-count")

    paginator = Paginator(events.order_by("-created_at"), 20)
    page = request.GET.get("page")

    try:
        events_page = paginator.page(page)
    except PageNotAnInteger:
        events_page = paginator.page(1)
    except EmptyPage:
        events_page = paginator.page(paginator.num_pages)

    context = {
        "events": events_page,
        "restaurant": restaurant,
        "filter_form": filter_form,
        "event_stats": event_stats,
        "event_type_choices": KitchenEvent.EventType.choices,
    }

    return render(request, "kitchen/kitchen_log.html", context)


@login_required
@permission_required("kitchen.view_kitchen_log", raise_exception=True)
def export_kitchen_log(request):
    """Экспорт журнала событий кухни."""
    if request.user.is_admin():
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.is_manager():
        restaurants = request.user.managed_restaurants.filter(is_active=True)
    else:
        if request.user.restaurant:
            restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
        else:
            messages.error(request, _("Вы не привязаны ни к одному ресторану."))
            return redirect("home")

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        if restaurant not in restaurants:
            messages.error(request, _("У вас нет доступа к этому ресторану."))
            return redirect("kitchen_log")
    else:
        if restaurants.count() == 1:
            restaurant = restaurants.first()
        else:
            messages.error(request, _("Необходимо выбрать ресторан."))
            return redirect("kitchen_log")

    filter_form = KitchenEventFilterForm(request.GET)

    events = KitchenEvent.objects.filter(restaurant=restaurant)

    if filter_form.is_valid():
        start_date = filter_form.cleaned_data.get("start_date")
        end_date = filter_form.cleaned_data.get("end_date")
        event_type = filter_form.cleaned_data.get("event_type")
        order_number = filter_form.cleaned_data.get("order_number")
        user = filter_form.cleaned_data.get("user")

        if start_date:
            events = events.filter(created_at__date__gte=start_date)

        if end_date:
            events = events.filter(created_at__date__lte=end_date)

        if event_type:
            events = events.filter(event_type=event_type)

        if order_number:
            events = events.filter(kitchen_order__order__order_number__icontains=order_number)

        if user:
            events = events.filter(
                Q(created_by__username__icontains=user)
                | Q(created_by__first_name__icontains=user)
                | Q(created_by__last_name__icontains=user)
            )

    events = events.order_by("-created_at")

    export_format = request.GET.get("format", "csv")

    if export_format == "csv":
        import csv

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="kitchen_log_{restaurant.name}_{timezone.now().strftime("%Y%m%d%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Тип события",
                "Описание",
                "Заказ",
                "Позиция",
                "Создан",
                "Пользователь",
                "IP-адрес",
            ]
        )

        for event in events:
            writer.writerow(
                [
                    event.id,
                    event.get_event_type_display(),
                    event.description,
                    event.kitchen_order.order.order_number if event.kitchen_order else "",
                    event.kitchen_item.order_item.menu_item.name if event.kitchen_item else "",
                    event.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                    event.created_by.get_full_name() if event.created_by else "",
                    event.ip_address or "",
                ]
            )

        return response

    elif export_format == "excel":
        import xlwt

        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Kitchen Log")

        header_style = xlwt.easyxf(
            "font: bold on; align: wrap on, vert centre, horiz center; pattern: pattern solid, fore_colour gray25"
        )
        date_style = xlwt.easyxf(num_format_str="DD.MM.YYYY HH:MM:SS")

        columns = [
            "ID",
            "Тип события",
            "Описание",
            "Заказ",
            "Позиция",
            "Создан",
            "Пользователь",
            "IP-адрес",
        ]
        for col_num, column_title in enumerate(columns):
            worksheet.write(0, col_num, column_title, header_style)

        for row_num, event in enumerate(events, 1):
            worksheet.write(row_num, 0, str(event.id))
            worksheet.write(row_num, 1, event.get_event_type_display())
            worksheet.write(row_num, 2, event.description)
            worksheet.write(
                row_num, 3, event.kitchen_order.order.order_number if event.kitchen_order else ""
            )
            worksheet.write(
                row_num,
                4,
                event.kitchen_item.order_item.menu_item.name if event.kitchen_item else "",
            )
            worksheet.write(row_num, 5, event.created_at, date_style)
            worksheet.write(
                row_num, 6, event.created_by.get_full_name() if event.created_by else ""
            )
            worksheet.write(row_num, 7, event.ip_address or "")

        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = (
            f'attachment; filename="kitchen_log_{restaurant.name}_{timezone.now().strftime("%Y%m%d%H%M%S")}.xls"'
        )
        workbook.save(response)

        return response

    elif export_format == "pdf":
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]

        title = Paragraph(f"Журнал событий кухни - {restaurant.name}", title_style)
        elements.append(title)
        elements.append(
            Paragraph(
                f"Отчет сформирован: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}",
                styles["Normal"],
            )
        )
        elements.append(Paragraph(" ", styles["Normal"]))  # Пустая строка

        data = [["ID", "Тип события", "Описание", "Заказ", "Создан", "Пользователь"]]

        for event in events[:1000]:
            data.append(
                [
                    str(event.id),
                    event.get_event_type_display(),
                    event.description,
                    event.kitchen_order.order.order_number if event.kitchen_order else "",
                    event.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                    event.created_by.get_full_name() if event.created_by else "",
                ]
            )

        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )

        elements.append(table)

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="kitchen_log_{restaurant.name}_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf"'
        )
        response.write(pdf)

        return response

    messages.error(request, _("Неизвестный формат экспорта."))
    return redirect("kitchen_log")
