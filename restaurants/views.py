from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Restaurant, Table, Reservation
from .forms import ReservationForm, TableFilterForm, RestaurantFilterForm


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

            return redirect("reservation_confirmation", id=reservation.id)
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
        return redirect("home")

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
