from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import KitchenQueue, KitchenOrder, KitchenOrderItem, CookingStation, KitchenEvent


class KitchenQueueForm(forms.ModelForm):
    """Форма для создания и редактирования очереди кухни."""

    class Meta:
        model = KitchenQueue
        fields = ["name", "status", "order", "is_default", "description", "responsible_roles"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "responsible_roles": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class KitchenOrderForm(forms.ModelForm):
    """Форма для обновления заказа на кухне."""

    class Meta:
        model = KitchenOrder
        fields = ["status", "priority", "assigned_to", "notes", "estimated_completion_time"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estimated_completion_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }


class KitchenOrderItemForm(forms.ModelForm):
    """Форма для обновления позиции заказа на кухне."""

    class Meta:
        model = KitchenOrderItem
        fields = [
            "status",
            "assigned_to",
            "cooking_station",
            "preparation_notes",
            "estimated_cooking_time",
            "sequence_number",
        ]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "cooking_station": forms.TextInput(attrs={"class": "form-control"}),
            "preparation_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estimated_cooking_time": forms.NumberInput(attrs={"class": "form-control"}),
            "sequence_number": forms.NumberInput(attrs={"class": "form-control"}),
        }


class CookingStationForm(forms.ModelForm):
    """Форма для создания и редактирования кухонной станции."""

    class Meta:
        model = CookingStation
        fields = [
            "name",
            "description",
            "is_active",
            "queue",
            "responsible_roles",
            "average_prep_time",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "queue": forms.Select(attrs={"class": "form-select"}),
            "responsible_roles": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "average_prep_time": forms.NumberInput(attrs={"class": "form-control"}),
        }


class KitchenEventFilterForm(forms.Form):
    """Форма для фильтрации событий на кухне."""

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label=_("Дата начала"),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label=_("Дата окончания"),
    )
    event_type = forms.ChoiceField(
        required=False,
        choices=[("", "Все типы")] + list(KitchenEvent.EventType.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Тип события"),
    )
    order_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label=_("Номер заказа"),
    )
    user = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label=_("Пользователь"),
    )


class UpdateKitchenOrderStatusForm(forms.Form):
    """Форма для быстрого обновления статуса заказа на кухне."""

    status = forms.ChoiceField(
        choices=KitchenOrder.KitchenOrderStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Статус"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        label=_("Примечание"),
    )


class UpdateKitchenItemStatusForm(forms.Form):
    """Форма для быстрого обновления статуса позиции заказа на кухне."""

    status = forms.ChoiceField(
        choices=KitchenOrderItem.KitchenItemStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Статус"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        label=_("Примечание"),
    )


class AssignOrderForm(forms.Form):
    """Форма для назначения сотрудника на заказ."""

    assigned_to = forms.ModelChoiceField(
        queryset=None, widget=forms.Select(attrs={"class": "form-select"}), label=_("Назначить")
    )

    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop("restaurant", None)
        super().__init__(*args, **kwargs)

        from django.contrib.auth import get_user_model

        User = get_user_model()

        if restaurant:
            self.fields["assigned_to"].queryset = (
                User.objects.filter(Q(restaurant=restaurant) | Q(managed_restaurants=restaurant))
                .filter(role__in=["CHEF", "BARTENDER", "COOK"])
                .distinct()
            )
        else:
            self.fields["assigned_to"].queryset = User.objects.none()
