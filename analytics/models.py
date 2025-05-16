import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Count, Avg
from restaurants.models import Restaurant, Table
from menu.models import MenuItem, Category
from orders.models import Order, OrderItem


class DailySales(models.Model):
    """
    Модель для агрегации ежедневных продаж по ресторану.
    Данные заполняются автоматически через Celery-задачу или триггеры.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="daily_sales", verbose_name=_("Ресторан")
    )
    date = models.DateField(verbose_name=_("Дата"))
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("Всего заказов"))
    completed_orders = models.PositiveIntegerField(default=0, verbose_name=_("Выполненные заказы"))
    cancelled_orders = models.PositiveIntegerField(default=0, verbose_name=_("Отмененные заказы"))
    gross_sales = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Валовые продажи")
    )
    net_sales = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Чистые продажи")
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Сумма скидок")
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Сумма налогов")
    )
    average_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Средний чек")
    )
    peak_hour_orders = models.PositiveIntegerField(
        default=0, verbose_name=_("Пиковый час (заказы)")
    )
    peak_hour_sales = models.PositiveIntegerField(
        default=0, verbose_name=_("Пиковый час (продажи)")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Ежедневные продажи")
        verbose_name_plural = _("Ежедневные продажи")
        ordering = ["-date", "restaurant"]
        unique_together = ["restaurant", "date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["restaurant", "date"]),
        ]
        permissions = [
            ("view_sales_report", "Может просматривать отчет о продажах"),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.date.strftime('%d.%m.%Y')}: {self.net_sales}"

    @classmethod
    def generate_for_date(cls, date, restaurant=None):
        """
        Генерирует или обновляет запись DailySales для указанной даты и ресторана.
        Если ресторан не указан, обновляет данные для всех ресторанов.
        """
        # Начало и конец дня
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(date, timezone.datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(date, timezone.datetime.max.time())
        )

        restaurants = [restaurant] if restaurant else Restaurant.objects.all()

        for rest in restaurants:
            orders = Order.objects.filter(
                restaurant=rest, created_at__gte=start_datetime, created_at__lte=end_datetime
            )

            total_orders = orders.count()
            completed_orders = orders.filter(status=Order.OrderStatus.COMPLETED).count()
            cancelled_orders = orders.filter(status=Order.OrderStatus.CANCELLED).count()

            completed_orders_qs = orders.filter(status=Order.OrderStatus.COMPLETED)

            gross_sales = completed_orders_qs.aggregate(sum=Sum("subtotal"))["sum"] or Decimal(
                "0.00"
            )
            discount_amount = completed_orders_qs.aggregate(sum=Sum("discount_amount"))[
                "sum"
            ] or Decimal("0.00")
            tax_amount = completed_orders_qs.aggregate(sum=Sum("tax_amount"))["sum"] or Decimal(
                "0.00"
            )
            net_sales = completed_orders_qs.aggregate(sum=Sum("total_amount"))["sum"] or Decimal(
                "0.00"
            )

            average_order_value = Decimal("0.00")
            if completed_orders > 0:
                average_order_value = net_sales / Decimal(completed_orders)

            hourly_orders = {}
            hourly_sales = {}

            for order in completed_orders_qs:
                hour = order.created_at.hour
                hourly_orders[hour] = hourly_orders.get(hour, 0) + 1
                hourly_sales[hour] = hourly_sales.get(hour, Decimal("0.00")) + order.total_amount

            peak_hour_orders = (
                max(hourly_orders.items(), key=lambda x: x[1])[0] if hourly_orders else 0
            )
            peak_hour_sales = (
                max(hourly_sales.items(), key=lambda x: x[1])[0] if hourly_sales else 0
            )

            daily_sales, created = cls.objects.update_or_create(
                restaurant=rest,
                date=date,
                defaults={
                    "total_orders": total_orders,
                    "completed_orders": completed_orders,
                    "cancelled_orders": cancelled_orders,
                    "gross_sales": gross_sales,
                    "net_sales": net_sales,
                    "discount_amount": discount_amount,
                    "tax_amount": tax_amount,
                    "average_order_value": average_order_value,
                    "peak_hour_orders": peak_hour_orders,
                    "peak_hour_sales": peak_hour_sales,
                },
            )

            return daily_sales


class PopularItem(models.Model):
    """
    Модель для отслеживания популярности блюд.
    Обновляется регулярно, агрегируя статистику заказов.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="popular_items",
        verbose_name=_("Ресторан"),
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="popularity_stats",
        verbose_name=_("Позиция меню"),
    )
    date_period = models.CharField(
        max_length=7, verbose_name=_("Период (год-месяц)")  # YYYY-MM format
    )
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("Количество заказов"))
    total_quantity = models.PositiveIntegerField(
        default=0, verbose_name=_("Общее количество порций")
    )
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Общая выручка")
    )
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True, verbose_name=_("Средняя оценка")
    )
    last_ordered = models.DateTimeField(null=True, blank=True, verbose_name=_("Последний заказ"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Популярное блюдо")
        verbose_name_plural = _("Популярные блюда")
        ordering = ["-total_orders", "menu_item__name"]
        unique_together = ["restaurant", "menu_item", "date_period"]
        indexes = [
            models.Index(fields=["restaurant", "date_period"]),
            models.Index(fields=["menu_item", "date_period"]),
        ]
        permissions = [
            ("view_menu_analysis", "Может просматривать анализ меню"),
        ]

    def __str__(self):
        return f"{self.menu_item.name} - {self.date_period}: {self.total_orders} заказов"

    @classmethod
    def update_for_period(cls, year_month, restaurant=None):
        """
        Обновляет статистику популярности блюд за указанный месяц.
        Формат year_month: "YYYY-MM" (пример: "2023-05")
        """
        year, month = map(int, year_month.split("-"))

        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            end_date = timezone.datetime(year, month + 1, 1) - timezone.timedelta(days=1)

        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )

        restaurants = [restaurant] if restaurant else Restaurant.objects.all()

        for rest in restaurants:
            orders = Order.objects.filter(
                restaurant=rest,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime,
                status=Order.OrderStatus.COMPLETED,
            )

            order_items = OrderItem.objects.filter(order__in=orders).select_related("menu_item")

            item_stats = {}

            for item in order_items:
                menu_item_id = item.menu_item.id

                if menu_item_id not in item_stats:
                    item_stats[menu_item_id] = {
                        "menu_item": item.menu_item,
                        "orders": set(),
                        "total_quantity": 0,
                        "total_revenue": Decimal("0.00"),
                        "last_ordered": None,
                    }

                stats = item_stats[menu_item_id]
                stats["orders"].add(item.order_id)
                stats["total_quantity"] += item.quantity
                stats["total_revenue"] += item.get_total_price()

                if not stats["last_ordered"] or item.order.created_at > stats["last_ordered"]:
                    stats["last_ordered"] = item.order.created_at

            for menu_item_id, stats in item_stats.items():
                popular_item, created = cls.objects.update_or_create(
                    restaurant=rest,
                    menu_item=stats["menu_item"],
                    date_period=year_month,
                    defaults={
                        "total_orders": len(stats["orders"]),
                        "total_quantity": stats["total_quantity"],
                        "total_revenue": stats["total_revenue"],
                        "last_ordered": stats["last_ordered"],
                    },
                )


class StaffPerformance(models.Model):
    """
    Модель для отслеживания эффективности персонала.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="staff_performance",
        verbose_name=_("Ресторан"),
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="performance_records",
        verbose_name=_("Сотрудник"),
    )
    date_period = models.CharField(max_length=7, verbose_name=_("Период (год-месяц)"))
    # Для официантов
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("Всего заказов"))
    completed_orders = models.PositiveIntegerField(default=0, verbose_name=_("Выполненные заказы"))
    cancelled_orders = models.PositiveIntegerField(default=0, verbose_name=_("Отмененные заказы"))
    total_sales = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Общие продажи")
    )
    average_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Средний чек")
    )
    # Для поваров/барменов
    items_prepared = models.PositiveIntegerField(default=0, verbose_name=_("Приготовлено блюд"))
    average_preparation_time = models.PositiveIntegerField(
        default=0, verbose_name=_("Среднее время приготовления (мин)")
    )
    # Общие метрики
    hours_worked = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Отработанные часы")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Эффективность сотрудника")
        verbose_name_plural = _("Эффективность сотрудников")
        ordering = ["-date_period", "restaurant", "staff__last_name"]
        unique_together = ["restaurant", "staff", "date_period"]
        indexes = [
            models.Index(fields=["restaurant", "date_period"]),
            models.Index(fields=["staff", "date_period"]),
        ]
        permissions = [
            ("view_staff_performance", "Может просматривать эффективность персонала"),
        ]

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.date_period}"

    @property
    def sales_per_hour(self):
        """Рассчитывает продажи на час работы."""
        if self.hours_worked > 0:
            return self.total_sales / self.hours_worked
        return Decimal("0.00")


class TableOccupancy(models.Model):
    """
    Модель для отслеживания занятости столиков.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="table_occupancy",
        verbose_name=_("Ресторан"),
    )
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name="occupancy_records", verbose_name=_("Столик")
    )
    date = models.DateField(verbose_name=_("Дата"))
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("Всего заказов"))
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Общая выручка")
    )
    total_guests = models.PositiveIntegerField(default=0, verbose_name=_("Всего гостей"))
    usage_minutes = models.PositiveIntegerField(
        default=0, verbose_name=_("Время использования (мин)")
    )
    peak_usage_hour = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Пиковый час использования")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Занятость столика")
        verbose_name_plural = _("Занятость столиков")
        ordering = ["-date", "restaurant", "table__number"]
        unique_together = ["restaurant", "table", "date"]
        indexes = [
            models.Index(fields=["restaurant", "date"]),
            models.Index(fields=["table", "date"]),
        ]
        permissions = [
            ("view_table_occupancy", "Может просматривать занятость столиков"),
        ]

    def __str__(self):
        return f"Столик №{self.table.number} - {self.date.strftime('%d.%m.%Y')}"

    @property
    def occupancy_rate(self):
        """Рассчитывает процент времени, в течение которого столик был занят."""
        total_minutes = 24 * 60  # минут в дне
        return (self.usage_minutes / total_minutes) * 100 if self.usage_minutes else 0

    @property
    def revenue_per_hour(self):
        """Рассчитывает выручку на час использования столика."""
        hours_used = self.usage_minutes / 60
        return self.total_revenue / Decimal(hours_used) if hours_used > 0 else Decimal("0.00")


class NutritionalAnalytics(models.Model):
    """
    Модель для отслеживания пищевой ценности заказанных блюд.
    Эта модель поддерживает нашу "фишку" по КБЖУ и аллергенам.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="nutritional_analytics",
        verbose_name=_("Ресторан"),
    )
    date_period = models.CharField(max_length=7, verbose_name=_("Период (год-месяц)"))
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("Всего заказов"))
    avg_calories_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Среднее кол-во калорий на заказ"),
    )
    avg_protein_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Среднее кол-во белков на заказ"),
    )
    avg_fat_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Среднее кол-во жиров на заказ"),
    )
    avg_carbs_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Среднее кол-во углеводов на заказ"),
    )
    vegetarian_orders = models.PositiveIntegerField(
        default=0, verbose_name=_("Вегетарианские заказы")
    )
    vegan_orders = models.PositiveIntegerField(default=0, verbose_name=_("Веганские заказы"))
    gluten_free_orders = models.PositiveIntegerField(
        default=0, verbose_name=_("Безглютеновые заказы")
    )
    lactose_free_orders = models.PositiveIntegerField(
        default=0, verbose_name=_("Безлактозные заказы")
    )
    common_allergens = models.JSONField(
        default=dict,
        verbose_name=_("Распространенные аллергены"),
        help_text=_("JSON с данными о частоте аллергенов в заказах"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Анализ пищевой ценности")
        verbose_name_plural = _("Анализ пищевой ценности")
        ordering = ["-date_period", "restaurant"]
        unique_together = ["restaurant", "date_period"]
        indexes = [
            models.Index(fields=["restaurant", "date_period"]),
        ]
        permissions = [
            ("view_nutritional_analytics", "Может просматривать анализ пищевой ценности"),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.date_period}: Анализ пищевой ценности"

    @classmethod
    def generate_for_period(cls, year_month, restaurant=None):
        """
        Генерирует или обновляет запись NutritionalAnalytics для указанного месяца и ресторана.
        """
        year, month = map(int, year_month.split("-"))

        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            end_date = timezone.datetime(year, month + 1, 1) - timezone.timedelta(days=1)

        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )

        restaurants = [restaurant] if restaurant else Restaurant.objects.all()

        for rest in restaurants:
            orders = Order.objects.filter(
                restaurant=rest,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime,
                status=Order.OrderStatus.COMPLETED,
            )

            total_orders = orders.count()
            if total_orders == 0:
                continue

            total_calories = Decimal("0.00")
            total_protein = Decimal("0.00")
            total_fat = Decimal("0.00")
            total_carbs = Decimal("0.00")

            vegetarian_count = 0
            vegan_count = 0
            gluten_free_count = 0
            lactose_free_count = 0

            allergens_count = {}

            for order in orders:
                nutrition = order.get_order_nutrition()
                total_calories += nutrition.get("calories", Decimal("0.00"))
                total_protein += nutrition.get("protein", Decimal("0.00"))
                total_fat += nutrition.get("fat", Decimal("0.00"))
                total_carbs += nutrition.get("carbs", Decimal("0.00"))

                all_items_vegetarian = True
                all_items_vegan = True
                all_items_gluten_free = True
                all_items_lactose_free = True

                order_allergens = order.get_order_allergens()
                for allergen in order_allergens:
                    allergens_count[allergen.name] = allergens_count.get(allergen.name, 0) + 1

                for item in order.items.select_related("menu_item").all():
                    menu_item = item.menu_item

                    if not menu_item.is_vegetarian:
                        all_items_vegetarian = False
                    if not menu_item.is_vegan:
                        all_items_vegan = False
                    if not menu_item.is_gluten_free:
                        all_items_gluten_free = False
                    if not menu_item.is_lactose_free:
                        all_items_lactose_free = False

                if all_items_vegetarian:
                    vegetarian_count += 1
                if all_items_vegan:
                    vegan_count += 1
                if all_items_gluten_free:
                    gluten_free_count += 1
                if all_items_lactose_free:
                    lactose_free_count += 1

            avg_calories = total_calories / Decimal(total_orders)
            avg_protein = total_protein / Decimal(total_orders)
            avg_fat = total_fat / Decimal(total_orders)
            avg_carbs = total_carbs / Decimal(total_orders)

            sorted_allergens = dict(
                sorted(allergens_count.items(), key=lambda x: x[1], reverse=True)[:10]
            )

            nutritional_analytics, created = cls.objects.update_or_create(
                restaurant=rest,
                date_period=year_month,
                defaults={
                    "total_orders": total_orders,
                    "avg_calories_per_order": avg_calories,
                    "avg_protein_per_order": avg_protein,
                    "avg_fat_per_order": avg_fat,
                    "avg_carbs_per_order": avg_carbs,
                    "vegetarian_orders": vegetarian_count,
                    "vegan_orders": vegan_count,
                    "gluten_free_orders": gluten_free_count,
                    "lactose_free_orders": lactose_free_count,
                    "common_allergens": sorted_allergens,
                },
            )

            return nutritional_analytics


class CustomerSegment(models.Model):
    """
    Модель для сегментации клиентов на основе их предпочтений.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Название сегмента"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание"))
    dietary_preferences = models.JSONField(
        default=dict,
        verbose_name=_("Диетические предпочтения"),
        help_text=_("JSON с данными о диетических предпочтениях сегмента"),
    )
    avg_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Средний чек")
    )
    visit_frequency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Частота посещений (в месяц)"),
    )
    preferred_categories = models.ManyToManyField(
        Category,
        related_name="customer_segments",
        blank=True,
        verbose_name=_("Предпочитаемые категории"),
    )
    preferred_items = models.ManyToManyField(
        MenuItem,
        related_name="customer_segments",
        blank=True,
        verbose_name=_("Предпочитаемые блюда"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="customer_segments",
        null=True,
        blank=True,
        verbose_name=_("Ресторан"),
    )
    churn_risk = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_("Риск оттока"),
        help_text=_("Вероятность оттока клиентов этого сегмента (0-1)"),
    )
    loyalty_index = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        verbose_name=_("Индекс лояльности"),
        help_text=_("Оценка лояльности сегмента от 0 до 100"),
    )

    class Meta:
        verbose_name = _("Сегмент клиентов")
        verbose_name_plural = _("Сегменты клиентов")
        ordering = ["-loyalty_index", "name"]
        indexes = [
            models.Index(fields=["restaurant", "loyalty_index"]),
        ]
        permissions = [
            ("view_customer_segmentation", "Может просматривать сегментацию клиентов"),
        ]

    def __str__(self):
        if self.restaurant:
            return f"{self.name} ({self.restaurant.name})"
        return self.name

    def get_customer_count(self):
        """Возвращает количество клиентов в этом сегменте"""
        return self.customers.count()

    def get_total_revenue(self):
        """Подсчитывает общую выручку от клиентов этого сегмента"""
        return Order.objects.filter(
            customer__in=self.customers.all(), status=Order.OrderStatus.COMPLETED
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")


class CustomerInsight(models.Model):
    """
    Модель для хранения аналитических данных о конкретном клиенте.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_insight",
        verbose_name=_("Клиент"),
    )
    segment = models.ForeignKey(
        CustomerSegment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name=_("Сегмент"),
    )
    first_visit_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Дата первого визита")
    )
    last_visit_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Дата последнего визита")
    )
    total_visits = models.PositiveIntegerField(default=0, verbose_name=_("Всего визитов"))
    total_spend = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Всего потрачено")
    )
    avg_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name=_("Средний чек")
    )
    favorite_items = models.JSONField(
        default=list,
        verbose_name=_("Любимые блюда"),
        help_text=_("JSON-массив с ID и количеством заказов наиболее часто заказываемых блюд"),
    )
    dietary_preferences = models.JSONField(
        null=True, blank=True, verbose_name=_("Диетические предпочтения")
    )
    allergens = models.JSONField(null=True, blank=True, verbose_name=_("Аллергены"))
    feedback_rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True, verbose_name=_("Средняя оценка")
    )
    purchase_patterns = models.JSONField(
        default=dict,
        verbose_name=_("Шаблоны покупок"),
        help_text=_("JSON с данными о предпочтительных днях/часах посещения"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Аналитика по клиенту")
        verbose_name_plural = _("Аналитика по клиентам")
        ordering = ["-total_spend"]
        permissions = [
            ("view_analytics_dashboard", "Может просматривать аналитическую панель"),
        ]

    def __str__(self):
        return f"Аналитика клиента: {self.customer.get_full_name() or self.customer.username}"

    @property
    def lifetime_value(self):
        """Рассчитывает пожизненную ценность клиента (LTV)"""
        # Упрощенная формула: средний чек * частота посещений * ожидаемый срок лояльности
        if self.total_visits == 0:
            return Decimal("0.00")

        if self.first_visit_date and self.last_visit_date:
            days_active = (self.last_visit_date - self.first_visit_date).days
            if days_active <= 0:
                return self.total_spend

            visits_per_day = self.total_visits / days_active
            expected_loyalty_days = 365  # Предполагаем 1 год лояльности

            return self.avg_order_value * Decimal(visits_per_day * expected_loyalty_days)

        return self.total_spend
