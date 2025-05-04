from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Reservation, Table
from menu.models import Allergen


class ReservationForm(forms.ModelForm):
    """Форма для бронирования столика клиентом."""

    allergens = forms.ModelMultipleChoiceField(
        queryset=Allergen.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Аллергены"),
        help_text=_("Выберите аллергены, которые есть у вас или ваших гостей"),
    )

    is_vegetarian = forms.BooleanField(required=False, label=_("Вегетарианская диета"))
    is_vegan = forms.BooleanField(required=False, label=_("Веганская диета"))
    is_gluten_free = forms.BooleanField(required=False, label=_("Безглютеновая диета"))
    is_lactose_free = forms.BooleanField(required=False, label=_("Безлактозная диета"))

    reservation_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        initial=timezone.now().date(),
        label=_("Дата бронирования"),
    )

    reservation_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        label=_("Время бронирования"),
    )

    duration = forms.IntegerField(
        initial=2,
        min_value=1,
        max_value=5,
        label=_("Продолжительность (часы)"),
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Reservation
        fields = [
            "customer_name",
            "customer_email",
            "customer_phone",
            "number_of_guests",
            "special_requests",
        ]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_email": forms.EmailInput(attrs={"class": "form-control"}),
            "customer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "number_of_guests": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "special_requests": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.restaurant = kwargs.pop("restaurant", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_authenticated:
            self.fields["customer_name"].initial = self.user.get_full_name() or self.user.username
            self.fields["customer_email"].initial = self.user.email
            if hasattr(self.user, "profile"):
                self.fields["customer_phone"].initial = self.user.profile.phone_number

    def clean(self):
        cleaned_data = super().clean()
        reservation_date = cleaned_data.get("reservation_date")
        reservation_time = cleaned_data.get("reservation_time")
        number_of_guests = cleaned_data.get("number_of_guests")
        duration = cleaned_data.get("duration", 2)

        if reservation_date and reservation_date < timezone.now().date():
            self.add_error("reservation_date", _("Нельзя бронировать на прошедшую дату"))

        if (
            reservation_date
            and reservation_time
            and reservation_date == timezone.now().date()
            and reservation_time < timezone.now().time()
        ):
            self.add_error("reservation_time", _("Нельзя бронировать на прошедшее время"))

        if self.restaurant and reservation_date and reservation_time and number_of_guests:
            available_tables = []

            suitable_tables = Table.objects.filter(
                restaurant=self.restaurant, is_active=True, capacity__gte=number_of_guests
            ).order_by("capacity")

            for table in suitable_tables:
                if table.is_available(reservation_date, reservation_time, duration):
                    available_tables.append(table)

            if not available_tables:
                self.add_error(
                    None,
                    _(
                        "К сожалению, нет доступных столиков на выбранное время и дату. Пожалуйста, выберите другое время или дату."
                    ),
                )
            else:
                self.available_tables = available_tables

        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        dietary_preferences = {}
        if self.cleaned_data.get("is_vegetarian"):
            dietary_preferences["vegetarian"] = True
        if self.cleaned_data.get("is_vegan"):
            dietary_preferences["vegan"] = True
        if self.cleaned_data.get("is_gluten_free"):
            dietary_preferences["gluten_free"] = True
        if self.cleaned_data.get("is_lactose_free"):
            dietary_preferences["lactose_free"] = True

        reservation.dietary_preferences = dietary_preferences

        allergens = self.cleaned_data.get("allergens", [])
        if allergens:
            allergy_information = {
                "ids": [str(a.id) for a in allergens],
                "names": [a.name for a in allergens],
            }
            reservation.allergy_information = allergy_information

        if self.restaurant:
            reservation.restaurant = self.restaurant

        if self.user and self.user.is_authenticated:
            reservation.user = self.user
            reservation.created_by = self.user

        if self.cleaned_data.get("reservation_time") and self.cleaned_data.get("duration"):
            reservation_datetime = timezone.datetime.combine(
                timezone.datetime.today(), self.cleaned_data["reservation_time"]
            )
            end_datetime = reservation_datetime + timezone.timedelta(
                hours=self.cleaned_data["duration"]
            )
            reservation.end_time = end_datetime.time()

        if commit:
            reservation.save()

        return reservation


class TableFilterForm(forms.Form):
    """Форма для фильтрации столиков."""

    min_capacity = forms.IntegerField(
        required=False,
        min_value=1,
        label=_("Минимальная вместимость"),
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": _("Минимум гостей")}
        ),
    )
    max_capacity = forms.IntegerField(
        required=False,
        min_value=1,
        label=_("Максимальная вместимость"),
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": _("Максимум гостей")}
        ),
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        initial=timezone.now().date(),
        label=_("Дата"),
    )
    time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        label=_("Время"),
    )
    shape = forms.ChoiceField(
        required=False,
        choices=[("", _("Все формы"))] + list(Table.TableShape.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Форма столика"),
    )


class RestaurantFilterForm(forms.Form):
    """Форма для фильтрации ресторанов."""

    city = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Город")}),
        label=_("Город"),
    )
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Поиск по названию или адресу")}
        ),
        label=_("Поиск"),
    )
