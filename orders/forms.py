from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Order, OrderItem, OrderItemModifier, Payment, Discount
from restaurants.models import Restaurant, Table
from menu.models import Modifier


class OrderTypeForm(forms.Form):
    """Форма для выбора типа заказа."""

    order_type = forms.ChoiceField(
        choices=Order.OrderType.choices,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label=_("Тип заказа"),
    )

    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.filter(is_active=True),
        empty_label=_("Выберите ресторан"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Ресторан"),
        required=False,
    )

    table = forms.ModelChoiceField(
        queryset=Table.objects.none(),
        empty_label=_("Выберите столик"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Столик"),
        required=False,
    )

    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label=_("Адрес доставки"),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, "profile") and user.profile.saved_delivery_addresses:
            saved_addresses = user.profile.saved_delivery_addresses
            self.fields["saved_address"] = forms.ChoiceField(
                choices=[("", _("Выберите сохраненный адрес"))]
                + [(addr, addr) for addr in saved_addresses],
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
                label=_("Сохраненные адреса"),
            )

    def clean(self):
        cleaned_data = super().clean()
        order_type = cleaned_data.get("order_type")
        restaurant = cleaned_data.get("restaurant")
        table = cleaned_data.get("table")
        delivery_address = cleaned_data.get("delivery_address")
        saved_address = cleaned_data.get("saved_address", "")

        if order_type == Order.OrderType.DINE_IN:
            if not restaurant:
                self.add_error(
                    "restaurant", _("Для заказа в ресторане необходимо выбрать ресторан")
                )
            if not table:
                self.add_error("table", _("Для заказа в ресторане необходимо выбрать столик"))

        elif order_type == Order.OrderType.DELIVERY:
            if not restaurant:
                self.add_error("restaurant", _("Для доставки необходимо выбрать ресторан"))

            if not delivery_address and not saved_address:
                self.add_error("delivery_address", _("Для доставки необходимо указать адрес"))
            elif saved_address and not delivery_address:
                cleaned_data["delivery_address"] = saved_address

        elif order_type == Order.OrderType.TAKEAWAY:
            if not restaurant:
                self.add_error("restaurant", _("Для самовывоза необходимо выбрать ресторан"))

        return cleaned_data


class OrderItemForm(forms.ModelForm):
    """Форма для создания позиции в заказе."""

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label=_("Количество"),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "2"}),
        label=_("Особые пожелания"),
    )

    class Meta:
        model = OrderItem
        fields = ["quantity", "notes"]

    def __init__(self, *args, **kwargs):
        self.menu_item = kwargs.pop("menu_item", None)
        self.order = kwargs.pop("order", None)
        super().__init__(*args, **kwargs)

        if self.menu_item:
            modifiers = (
                Modifier.objects.filter(restaurant=self.menu_item.restaurant, is_active=True)
                .filter(Q(applicable_items=self.menu_item) | Q(applicable_items__isnull=True))
                .distinct()
            )

            for modifier in modifiers:
                field_name = f"modifier_{modifier.id}"
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=f"{modifier.name} ({'+' if modifier.price_change >= 0 else ''}{modifier.price_change} ₽)",
                )

                if modifier.modifier_type in ["ADDITION", "REMOVAL"]:
                    quantity_field = f"modifier_{modifier.id}_quantity"
                    self.fields[quantity_field] = forms.IntegerField(
                        min_value=1,
                        initial=1,
                        required=False,
                        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
                        label=_("Количество"),
                    )

    def save(self, commit=True):
        order_item = super().save(commit=False)

        if self.menu_item:
            order_item.menu_item = self.menu_item
            order_item.unit_price = self.menu_item.price

        if self.order:
            order_item.order = self.order

        if commit:
            order_item.save()

            for field_name, value in self.cleaned_data.items():
                if (
                    field_name.startswith("modifier_")
                    and not field_name.endswith("_quantity")
                    and value
                ):
                    modifier_id = field_name.split("_")[1]
                    try:
                        modifier = Modifier.objects.get(id=modifier_id)
                        quantity = self.cleaned_data.get(f"modifier_{modifier_id}_quantity", 1)

                        OrderItemModifier.objects.create(
                            order_item=order_item, modifier=modifier, quantity=quantity
                        )
                    except Modifier.DoesNotExist:
                        pass

        return order_item


class CustomerOrderForm(forms.ModelForm):
    """Форма для создания заказа клиентом."""

    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
        label=_("Особые пожелания к заказу"),
    )

    save_delivery_address = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Сохранить этот адрес доставки"),
    )

    class Meta:
        model = Order
        fields = ["special_requests"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)


class DiscountForm(forms.Form):
    """Форма для применения промокода/скидки."""

    discount_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Введите промокод")}
        ),
        label=_("Промокод"),
    )


class PaymentForm(forms.ModelForm):
    """Форма для создания платежа."""

    class Meta:
        model = Payment
        fields = ["payment_method", "amount", "notes"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": "2"}),
        }

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order", None)
        super().__init__(*args, **kwargs)

        if self.order:
            remaining = self.order.total_amount - sum(
                p.amount for p in self.order.payments.filter(status=Payment.PaymentStatus.COMPLETED)
            )
            self.fields["amount"].initial = remaining


class CheckoutForm(forms.ModelForm):
    """Форма для оформления заказа."""

    customer_name = forms.CharField(
        max_length=100, widget=forms.TextInput(attrs={"class": "form-control"}), label=_("Ваше имя")
    )

    customer_phone = forms.CharField(
        max_length=20, widget=forms.TextInput(attrs={"class": "form-control"}), label=_("Телефон")
    )

    delivery_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
        label=_("Адрес доставки"),
    )

    payment_method = forms.ChoiceField(
        choices=Payment.PaymentMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Способ оплаты"),
    )

    terms_accepted = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label=_("Я согласен с условиями обслуживания и доставки"),
        required=True,
    )

    class Meta:
        model = Order
        fields = ["customer_name", "customer_phone", "delivery_address", "special_requests"]
        widgets = {
            "special_requests": forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.order_type = kwargs.pop("order_type", None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_authenticated:
            self.fields["customer_name"].initial = self.user.get_full_name() or self.user.username

            if hasattr(self.user, "profile"):
                self.fields["customer_phone"].initial = self.user.profile.phone_number

        if self.order_type != Order.OrderType.DELIVERY:
            self.fields["delivery_address"].widget = forms.HiddenInput()
            self.fields["delivery_address"].required = False

    def clean(self):
        cleaned_data = super().clean()

        if self.order_type == Order.OrderType.DELIVERY and not cleaned_data.get("delivery_address"):
            self.add_error("delivery_address", _("Для доставки необходимо указать адрес"))

        return cleaned_data


class DiscountAdminForm(forms.ModelForm):
    """Форма для создания/редактирования скидки администратором."""

    class Meta:
        model = Discount
        fields = [
            "code",
            "name",
            "description",
            "discount_type",
            "value",
            "min_order_value",
            "max_discount_amount",
            "valid_from",
            "valid_to",
            "usage_limit",
            "restaurant",
            "applicable_categories",
            "applicable_items",
            "free_item",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
            "discount_type": forms.Select(attrs={"class": "form-select"}),
            "value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "min_order_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "max_discount_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "valid_from": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "valid_to": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "usage_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "restaurant": forms.Select(attrs={"class": "form-select"}),
            "applicable_categories": forms.SelectMultiple(
                attrs={"class": "form-select", "size": "5"}
            ),
            "applicable_items": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "free_item": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and not user.is_admin():
            if user.is_manager():
                self.fields["restaurant"].queryset = user.managed_restaurants.filter(is_active=True)
            elif user.restaurant:
                self.fields["restaurant"].queryset = Restaurant.objects.filter(
                    id=user.restaurant.id
                )
                self.fields["restaurant"].initial = user.restaurant
                self.fields["restaurant"].widget.attrs["disabled"] = "disabled"

        if self.instance and self.instance.pk and self.instance.restaurant:
            self.fields["applicable_categories"].queryset = (
                self.instance.restaurant.menu_categories.filter(is_active=True)
            )
            self.fields["applicable_items"].queryset = self.instance.restaurant.menu_items.filter(
                is_active=True
            )
            self.fields["free_item"].queryset = self.instance.restaurant.menu_items.filter(
                is_active=True
            )
