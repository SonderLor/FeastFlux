from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Restaurant, Table, Reservation
from .forms import (
    ReservationForm,
    TableFilterForm,
    RestaurantFilterForm,
    RestaurantForm,
    TableForm,
    StaffReservationForm,
)


@login_required
@permission_required("restaurants.view_restaurant", raise_exception=True)
def restaurant_list(request):
    """Список всех ресторанов для администраторов и менеджеров."""
    user = request.user

    if user.is_manager() and not user.is_admin():
        restaurants = user.managed_restaurants.all()
    else:
        restaurants = Restaurant.objects.all()

    form = RestaurantFilterForm(request.GET)
    if form.is_valid():
        city = form.cleaned_data.get("city")
        search = form.cleaned_data.get("search")

        if city:
            restaurants = restaurants.filter(city__icontains=city)

        if search:
            restaurants = restaurants.filter(
                Q(name__icontains=search)
                | Q(address__icontains=search)
                | Q(description__icontains=search)
            )

    paginator = Paginator(restaurants, 10)
    page = request.GET.get("page")

    try:
        restaurants_page = paginator.page(page)
    except PageNotAnInteger:
        restaurants_page = paginator.page(1)
    except EmptyPage:
        restaurants_page = paginator.page(paginator.num_pages)

    context = {
        "restaurants": restaurants_page,
        "form": form,
    }

    return render(request, "restaurants/restaurant_list.html", context)


@login_required
@permission_required("restaurants.view_restaurant", raise_exception=True)
def restaurant_detail(request, id):
    """Детальная информация о ресторане для персонала."""
    restaurant = get_object_or_404(Restaurant, id=id)
    user = request.user

    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет доступа к этому ресторану."))
        return redirect("restaurants:restaurant_list")

    today = timezone.now().date()
    reservations_today = Reservation.objects.filter(
        restaurant=restaurant, reservation_date=today
    ).order_by("reservation_time")

    tables = Table.objects.filter(restaurant=restaurant)
    tables_free = tables.filter(status=Table.TableStatus.FREE).count()
    tables_occupied = tables.filter(status=Table.TableStatus.OCCUPIED).count()
    tables_reserved = tables.filter(status=Table.TableStatus.RESERVED).count()

    context = {
        "restaurant": restaurant,
        "reservations_today": reservations_today,
        "tables_count": tables.count(),
        "tables_free": tables_free,
        "tables_occupied": tables_occupied,
        "tables_reserved": tables_reserved,
        "is_open": is_restaurant_open(restaurant),
    }

    return render(request, "restaurants/restaurant_detail.html", context)


@login_required
@permission_required("restaurants.manage_restaurant", raise_exception=True)
def restaurant_manage(request):
    """Управление ресторанами (список для создания/редактирования)."""
    restaurants = Restaurant.objects.all().order_by("name")

    context = {
        "restaurants": restaurants,
    }

    return render(request, "restaurants/restaurant_manage.html", context)


@login_required
@permission_required("restaurants.manage_restaurant", raise_exception=True)
def restaurant_create(request):
    """Создание нового ресторана."""
    if request.method == "POST":
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save()
            messages.success(request, _("Ресторан успешно создан!"))
            return redirect("restaurants:restaurant_detail", id=restaurant.id)
    else:
        form = RestaurantForm()

    context = {
        "form": form,
        "is_create": True,
    }

    return render(request, "restaurants/restaurant_form.html", context)


@login_required
@permission_required("restaurants.manage_restaurant", raise_exception=True)
def restaurant_edit(request, id):
    """Редактирование ресторана."""
    restaurant = get_object_or_404(Restaurant, id=id)

    if request.method == "POST":
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            restaurant = form.save()
            messages.success(request, _("Ресторан успешно обновлен!"))
            return redirect("restaurants:restaurant_detail", id=restaurant.id)
    else:
        form = RestaurantForm(instance=restaurant)

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": False,
    }

    return render(request, "restaurants/restaurant_form.html", context)


@login_required
@permission_required("restaurants.view_table", raise_exception=True)
def table_layout(request, id):
    """Интерактивный план расположения столиков."""
    restaurant = get_object_or_404(Restaurant, id=id)
    user = request.user

    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет доступа к этому ресторану."))
        return redirect("restaurants:restaurant_list")

    tables = Table.objects.filter(restaurant=restaurant)

    form = TableFilterForm(request.GET)
    if form.is_valid():
        status = request.GET.get("status")
        min_capacity = form.cleaned_data.get("min_capacity")
        max_capacity = form.cleaned_data.get("max_capacity")

        if status:
            tables = tables.filter(status=status)

        if min_capacity:
            tables = tables.filter(capacity__gte=min_capacity)

        if max_capacity:
            tables = tables.filter(capacity__lte=max_capacity)

    edit_mode = request.GET.get("edit_mode") == "1" and (user.is_admin() or user.is_manager())

    context = {
        "restaurant": restaurant,
        "tables": tables,
        "form": form,
        "edit_mode": edit_mode,
        "table_statuses": Table.TableStatus.choices,
    }

    return render(request, "restaurants/table_layout.html", context)


@login_required
@permission_required("restaurants.add_table", raise_exception=True)
def table_create(request, restaurant_id):
    """Создание нового столика."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    if request.method == "POST":
        form = TableForm(request.POST, user=request.user)
        if form.is_valid():
            table = form.save(commit=False)
            table.restaurant = restaurant
            table.save()
            messages.success(request, _("Столик успешно создан!"))
            return redirect("restaurants:table_layout", id=restaurant.id)
    else:
        form = TableForm(user=request.user, initial={"restaurant": restaurant})

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "restaurants/table_form.html", context)


@login_required
@permission_required("restaurants.change_table", raise_exception=True)
def table_edit(request, id):
    """Редактирование столика."""
    table = get_object_or_404(Table, id=id)
    restaurant = table.restaurant

    if request.method == "POST":
        form = TableForm(request.POST, instance=table, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Столик успешно обновлен!"))
            return redirect("restaurants:table_layout", id=restaurant.id)
    else:
        form = TableForm(instance=table, user=request.user)

    context = {
        "form": form,
        "table": table,
        "restaurant": restaurant,
        "is_create": False,
    }

    return render(request, "restaurants/table_form.html", context)


@login_required
@permission_required("restaurants.delete_table", raise_exception=True)
def table_delete(request, id):
    """Удаление столика."""
    table = get_object_or_404(Table, id=id)
    restaurant = table.restaurant

    if request.method == "POST":
        table.delete()
        messages.success(request, _("Столик успешно удален!"))
        return redirect("restaurants:table_layout", id=restaurant.id)

    context = {
        "table": table,
        "restaurant": restaurant,
    }

    return render(request, "restaurants/table_confirm_delete.html", context)


@login_required
@permission_required("restaurants.view_reservation", raise_exception=True)
def reservation_list(request, id):
    """Список бронирований ресторана."""
    restaurant = get_object_or_404(Restaurant, id=id)
    user = request.user

    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет доступа к этому ресторану."))
        return redirect("restaurants:restaurant_list")

    date = request.GET.get("date")
    status = request.GET.get("status")
    table_id = request.GET.get("table")

    reservations = Reservation.objects.filter(restaurant=restaurant)

    if date:
        try:
            filter_date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
            reservations = reservations.filter(reservation_date=filter_date)
        except ValueError:
            reservations = reservations.filter(reservation_date=timezone.now().date())
    else:
        reservations = reservations.filter(reservation_date=timezone.now().date())

    if status:
        reservations = reservations.filter(status=status)

    if table_id:
        reservations = reservations.filter(table_id=table_id)

    reservations = reservations.order_by("reservation_date", "reservation_time")

    tables = Table.objects.filter(restaurant=restaurant).order_by("number")

    context = {
        "restaurant": restaurant,
        "reservations": reservations,
        "tables": tables,
        "statuses": Reservation.ReservationStatus.choices,
        "filter_date": date or timezone.now().date().strftime("%Y-%m-%d"),
        "filter_status": status,
        "filter_table": table_id,
    }

    return render(request, "restaurants/reservation_list.html", context)


@login_required
@permission_required("restaurants.add_reservation", raise_exception=True)
def reservation_create(request, id):
    """Создание нового бронирования персоналом."""
    restaurant = get_object_or_404(Restaurant, id=id)
    user = request.user

    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет доступа к этому ресторану."))
        return redirect("restaurants:restaurant_list")

    if request.method == "POST":
        form = StaffReservationForm(request.POST, restaurant=restaurant, user=user)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.restaurant = restaurant
            reservation.created_by = user
            reservation.save()
            messages.success(request, _("Бронирование успешно создано!"))
            return redirect("restaurants:reservation_list", id=restaurant.id)
    else:
        form = StaffReservationForm(restaurant=restaurant, user=user)

    context = {
        "form": form,
        "restaurant": restaurant,
        "is_create": True,
    }

    return render(request, "restaurants/reservation_form.html", context)


@login_required
@permission_required("restaurants.change_reservation", raise_exception=True)
def reservation_edit(request, id):
    """Редактирование бронирования."""
    reservation = get_object_or_404(Reservation, id=id)
    restaurant = reservation.restaurant
    user = request.user

    if user.is_waiter() and (not user.restaurant or user.restaurant.id != restaurant.id):
        messages.error(request, _("У вас нет доступа к этому ресторану."))
        return redirect("restaurants:restaurant_list")

    if request.method == "POST":
        form = StaffReservationForm(
            request.POST, instance=reservation, restaurant=restaurant, user=user
        )
        if form.is_valid():
            form.save()
            messages.success(request, _("Бронирование успешно обновлено!"))
            return redirect("restaurants:reservation_list", id=restaurant.id)
    else:
        form = StaffReservationForm(instance=reservation, restaurant=restaurant, user=user)

    context = {
        "form": form,
        "reservation": reservation,
        "restaurant": restaurant,
        "is_create": False,
    }

    return render(request, "restaurants/reservation_form.html", context)


@login_required
@permission_required("restaurants.delete_reservation", raise_exception=True)
def reservation_cancel(request, id):
    """Отмена бронирования."""
    reservation = get_object_or_404(Reservation, id=id)
    restaurant = reservation.restaurant

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        reservation.status = Reservation.ReservationStatus.CANCELLED
        reservation.special_requests = f"{reservation.special_requests or ''}\n\nОтменено: {reason}"
        reservation.save()
        messages.success(request, _("Бронирование успешно отменено!"))
        return redirect("restaurants:reservation_list", id=restaurant.id)

    context = {
        "reservation": reservation,
        "restaurant": restaurant,
    }

    return render(request, "restaurants/reservation_cancel.html", context)


@login_required
def customer_reservation_history(request):
    """Представление для отображения истории бронирований клиента."""
    user = request.user

    reservations = Reservation.objects.filter(user=user).order_by(
        "-reservation_date", "-reservation_time"
    )

    status = request.GET.get("status")
    if status:
        reservations = reservations.filter(status=status)

    date_from = request.GET.get("date_from")
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            reservations = reservations.filter(reservation_date__gte=date_from)
        except ValueError:
            pass

    date_to = request.GET.get("date_to")
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            reservations = reservations.filter(reservation_date__lte=date_to)
        except ValueError:
            pass

    restaurant_id = request.GET.get("restaurant")
    if restaurant_id:
        reservations = reservations.filter(restaurant_id=restaurant_id)

    paginator = Paginator(reservations, 10)
    page = request.GET.get("page")

    try:
        reservations_page = paginator.page(page)
    except PageNotAnInteger:
        reservations_page = paginator.page(1)
    except EmptyPage:
        reservations_page = paginator.page(paginator.num_pages)

    user_restaurants = Restaurant.objects.filter(
        id__in=Reservation.objects.filter(user=user).values_list("restaurant", flat=True).distinct()
    )

    current_date = timezone.now().date()
    current_time = timezone.now().time()

    context = {
        "reservations": reservations_page,
        "statuses": Reservation.ReservationStatus.choices,
        "selected_status": status,
        "selected_date_from": date_from.strftime("%Y-%m-%d") if date_from else "",
        "selected_date_to": date_to.strftime("%Y-%m-%d") if date_to else "",
        "selected_restaurant": restaurant_id,
        "user_restaurants": user_restaurants,
        "current_date": current_date,
        "current_time": current_time,
    }

    return render(request, "restaurants/customer_reservation_history.html", context)


def public_restaurant_list(request):
    """Представление для публичного списка всех ресторанов."""
    form = RestaurantFilterForm(request.GET)
    restaurants = Restaurant.objects.filter(is_active=True)

    if form.is_valid():
        city = form.cleaned_data.get("city")
        search = form.cleaned_data.get("search")

        if city:
            restaurants = restaurants.filter(city__icontains=city)

        if search:
            restaurants = restaurants.filter(
                Q(name__icontains=search)
                | Q(address__icontains=search)
                | Q(description__icontains=search)
            )

    paginator = Paginator(restaurants, 12)
    page = request.GET.get("page")

    try:
        restaurants_page = paginator.page(page)
    except PageNotAnInteger:
        restaurants_page = paginator.page(1)
    except EmptyPage:
        restaurants_page = paginator.page(paginator.num_pages)

    all_cities = Restaurant.objects.filter(is_active=True).values_list("city", flat=True).distinct()

    context = {
        "restaurants": restaurants_page,
        "form": form,
        "all_cities": all_cities,
    }

    return render(request, "restaurants/public_restaurant_list.html", context)


def public_restaurant_detail(request, id):
    """Представление для публичной страницы конкретного ресторана."""
    restaurant = get_object_or_404(Restaurant, id=id, is_active=True)

    is_open = is_restaurant_open(restaurant)

    featured_tables = Table.objects.filter(restaurant=restaurant, is_active=True).order_by("?")[:3]

    context = {
        "restaurant": restaurant,
        "is_open": is_open,
        "featured_tables": featured_tables,
    }

    return render(request, "restaurants/public_restaurant_detail.html", context)


@login_required
@permission_required("restaurants.view_public_tables", raise_exception=True)
def public_table_view(request, id):
    """Представление для просмотра столиков в ресторане клиентами."""
    restaurant = get_object_or_404(Restaurant, id=id, is_active=True)

    form = TableFilterForm(request.GET)
    tables = Table.objects.filter(restaurant=restaurant, is_active=True)

    if form.is_valid():
        min_capacity = form.cleaned_data.get("min_capacity")
        max_capacity = form.cleaned_data.get("max_capacity")
        date = form.cleaned_data.get("date")
        time = form.cleaned_data.get("time")
        shape = form.cleaned_data.get("shape")

        if min_capacity:
            tables = tables.filter(capacity__gte=min_capacity)

        if max_capacity:
            tables = tables.filter(capacity__lte=max_capacity)

        if shape:
            tables = tables.filter(shape=shape)

        if date and time:
            available_tables = []
            for table in tables:
                if table.is_available(date, time):
                    available_tables.append(table.id)

            tables = tables.filter(id__in=available_tables)

    context = {
        "restaurant": restaurant,
        "tables": tables,
        "form": form,
    }

    return render(request, "restaurants/public_table_view.html", context)


@login_required
@permission_required("restaurants.add_reservation", raise_exception=True)
def customer_reservation(request, id):
    """Представление для бронирования столика клиентом."""
    restaurant = get_object_or_404(Restaurant, id=id, is_active=True)

    if request.method == "POST":
        form = ReservationForm(request.POST, restaurant=restaurant, user=request.user)

        if form.is_valid():
            reservation = form.save(commit=False)

            table_id = request.POST.get("table_id")

            if table_id:
                table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
                reservation.table = table
            else:
                reservation.table = form.available_tables[0]

            reservation.status = Reservation.ReservationStatus.PENDING
            reservation.save()

            messages.success(
                request, _("Бронирование успешно создано! Мы свяжемся с вами для подтверждения.")
            )

            return redirect("restaurants:reservation_confirmation", id=reservation.id)
    else:
        form = ReservationForm(restaurant=restaurant, user=request.user)

    context = {
        "restaurant": restaurant,
        "form": form,
    }

    return render(request, "restaurants/customer_reservation.html", context)


@login_required
def reservation_confirmation(request, id):
    """Страница подтверждения бронирования."""
    reservation = get_object_or_404(Reservation, id=id)

    if reservation.user != request.user and not request.user.is_staff:
        messages.error(request, _("У вас нет прав для просмотра этого бронирования."))
        return redirect("core:home")

    context = {
        "reservation": reservation,
    }

    return render(request, "restaurants/reservation_confirmation.html", context)


def is_restaurant_open(restaurant):
    """Проверяет, открыт ли ресторан в текущее время."""
    now = timezone.now()
    today = now.strftime("%A").lower()

    hours = restaurant.opening_hours.get(today)

    if not hours:
        return False

    open_time_str = hours.get("open")
    close_time_str = hours.get("close")

    if not open_time_str or not close_time_str:
        return False

    from datetime import datetime

    open_time = datetime.strptime(open_time_str, "%H:%M").time()
    close_time = datetime.strptime(close_time_str, "%H:%M").time()

    current_time = now.time()

    if close_time < open_time:
        return current_time >= open_time or current_time <= close_time
    else:
        return open_time <= current_time <= close_time
