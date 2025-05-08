from django import forms
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from restaurants.models import Restaurant
from menu.models import Category, MenuItem

User = get_user_model()


class DateRangeForm(forms.Form):
    """Базовая форма с выбором диапазона дат"""

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Начальная дата",
        required=False,
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Конечная дата",
        required=False,
    )
    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.all(),
        label="Ресторан",
        required=False,
        empty_label="Все рестораны",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if hasattr(user, "restaurant_manager"):
                self.fields["restaurant"].queryset = Restaurant.objects.filter(managers=user)
                self.fields["restaurant"].initial = user.restaurant_manager.first()
                self.fields["restaurant"].widget.attrs["disabled"] = True

        today = timezone.now().date()
        self.fields["end_date"].initial = today
        self.fields["start_date"].initial = today - timedelta(days=30)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Начальная дата не может быть позже конечной даты")

        return cleaned_data


class SalesReportForm(DateRangeForm):
    """Форма для отчета по продажам с расширенными фильтрами"""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="Категория",
        required=False,
        empty_label="Все категории",
    )
    payment_method = forms.ChoiceField(
        choices=[
            ("", "Все способы оплаты"),
            ("cash", "Наличные"),
            ("card", "Карта"),
            ("online", "Онлайн"),
        ],
        label="Способ оплаты",
        required=False,
    )
    order_type = forms.ChoiceField(
        choices=[
            ("", "Все типы заказов"),
            ("dine_in", "В ресторане"),
            ("takeaway", "Навынос"),
            ("delivery", "Доставка"),
        ],
        label="Тип заказа",
        required=False,
    )
    group_by = forms.ChoiceField(
        choices=[
            ("day", "По дням"),
            ("week", "По неделям"),
            ("month", "По месяцам"),
            ("category", "По категориям"),
            ("item", "По блюдам"),
        ],
        label="Группировка",
        required=False,
        initial="day",
    )
    export_format = forms.ChoiceField(
        choices=[("", "Не экспортировать"), ("csv", "CSV"), ("excel", "Excel"), ("pdf", "PDF")],
        label="Экспорт",
        required=False,
    )


class MenuAnalysisForm(DateRangeForm):
    """Форма для анализа меню"""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="Категория",
        required=False,
        empty_label="Все категории",
    )
    analysis_type = forms.ChoiceField(
        choices=[
            ("popularity", "Популярность"),
            ("revenue", "Выручка"),
            ("profitability", "Прибыльность"),
            ("abc", "ABC-анализ"),
        ],
        label="Тип анализа",
        initial="popularity",
    )


class StaffPerformanceForm(DateRangeForm):
    """Форма для анализа эффективности персонала"""

    staff_member = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        label="Сотрудник",
        required=False,
        empty_label="Все сотрудники",
    )
    staff_role = forms.ChoiceField(
        choices=[
            ("", "Все роли"),
            ("waiter", "Официанты"),
            ("chef", "Повара"),
            ("bartender", "Бармены"),
            ("manager", "Менеджеры"),
        ],
        label="Должность",
        required=False,
    )
    metrics = forms.MultipleChoiceField(
        choices=[
            ("orders", "Количество заказов"),
            ("sales", "Объем продаж"),
            ("avg_time", "Среднее время обслуживания"),
            ("avg_check", "Средний чек"),
        ],
        label="Показатели",
        widget=forms.CheckboxSelectMultiple,
        initial=["orders", "sales"],
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)

        if user and not user.is_superuser and hasattr(user, "restaurant_manager"):
            restaurants = user.restaurant_manager.all()
            self.fields["staff_member"].queryset = User.objects.filter(
                Q(waiter_profile__restaurant__in=restaurants)
                | Q(chef_profile__restaurant__in=restaurants)
                | Q(bartender_profile__restaurant__in=restaurants)
                | Q(restaurant_manager__in=restaurants)
            ).distinct()


class TableOccupancyForm(DateRangeForm):
    """Форма для анализа загруженности столиков"""

    view_mode = forms.ChoiceField(
        choices=[
            ("heatmap", "Тепловая карта"),
            ("chart", "График загруженности"),
            ("table", "Таблица с данными"),
        ],
        label="Вид отображения",
        initial="heatmap",
    )
    display_by = forms.ChoiceField(
        choices=[
            ("day", "По дням"),
            ("week", "По дням недели"),
            ("hour", "По часам"),
        ],
        label="Группировка",
        initial="hour",
    )


class NutritionalAnalyticsForm(DateRangeForm):
    """Форма для анализа пищевой ценности"""

    chart_type = forms.ChoiceField(
        choices=[
            ("nutrients", "Распределение КБЖУ"),
            ("dietary", "Диетические предпочтения"),
            ("allergens", "Распространенность аллергенов"),
        ],
        label="Тип анализа",
        initial="nutrients",
    )
    dietary_focus = forms.MultipleChoiceField(
        choices=[
            ("vegetarian", "Вегетарианские блюда"),
            ("vegan", "Веганские блюда"),
            ("gluten_free", "Безглютеновые блюда"),
            ("lactose_free", "Безлактозные блюда"),
        ],
        label="Диетические категории",
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )


class CustomerSegmentationForm(forms.Form):
    """Форма для анализа клиентских сегментов"""

    restaurant = forms.ModelChoiceField(
        queryset=Restaurant.objects.all(),
        label="Ресторан",
        required=False,
        empty_label="Все рестораны",
    )
    segment = forms.ChoiceField(
        label="Сегмент клиентов",
        required=False,
    )
    period = forms.ChoiceField(
        choices=[
            ("30", "Последние 30 дней"),
            ("90", "Последние 90 дней"),
            ("180", "Последние 180 дней"),
            ("365", "Последний год"),
            ("all", "Все время"),
        ],
        label="Период",
        initial="90",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        from analytics.models import CustomerSegment

        segments = CustomerSegment.objects.all()

        if user and not user.is_superuser and hasattr(user, "restaurant_manager"):
            restaurants = user.restaurant_manager.all()
            segments = segments.filter(restaurant__in=restaurants)
            self.fields["restaurant"].queryset = restaurants
            self.fields["restaurant"].initial = restaurants.first()

        self.fields["segment"].choices = [("", "Все сегменты")] + [(s.id, s.name) for s in segments]
