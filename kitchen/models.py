import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from restaurants.models import Restaurant
from orders.models import Order, OrderItem


class KitchenQueue(models.Model):
    """
    Модель для управления очередью заказов на кухне.
    """

    class QueueStatus(models.TextChoices):
        OPEN = "OPEN", _("Открыта")
        CLOSED = "CLOSED", _("Закрыта")
        PAUSED = "PAUSED", _("Приостановлена")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="kitchen_queues",
        verbose_name=_("Ресторан"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Название очереди"))
    status = models.CharField(
        max_length=10,
        choices=QueueStatus.choices,
        default=QueueStatus.OPEN,
        verbose_name=_("Статус"),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок отображения"))
    is_default = models.BooleanField(default=False, verbose_name=_("Очередь по умолчанию"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание"))
    responsible_roles = models.JSONField(
        default=list,
        verbose_name=_("Ответственные роли"),
        help_text=_("JSON-массив с ролями сотрудников, ответственных за эту очередь"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Очередь кухни")
        verbose_name_plural = _("Очереди кухни")
        ordering = ["restaurant", "order", "name"]
        unique_together = [["restaurant", "name"]]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def active_orders_count(self):
        """Возвращает количество активных заказов в очереди."""
        return self.kitchen_orders.filter(
            status__in=[
                KitchenOrder.KitchenOrderStatus.NEW,
                KitchenOrder.KitchenOrderStatus.IN_PROGRESS,
            ]
        ).count()

    def average_processing_time(self):
        """Возвращает среднее время обработки заказов в этой очереди (в минутах)."""
        completed_orders = self.kitchen_orders.filter(
            status=KitchenOrder.KitchenOrderStatus.COMPLETED, completed_at__isnull=False
        )

        if not completed_orders.exists():
            return 0

        total_minutes = 0
        count = 0

        for kitchen_order in completed_orders:
            if kitchen_order.started_at:
                processing_time = (
                    kitchen_order.completed_at - kitchen_order.started_at
                ).total_seconds() / 60
                total_minutes += processing_time
                count += 1

        return round(total_minutes / count) if count > 0 else 0


class KitchenOrder(models.Model):
    """
    Модель для отслеживания статуса заказа на кухне.
    """

    class KitchenOrderStatus(models.TextChoices):
        NEW = "NEW", _("Новый")
        IN_PROGRESS = "IN_PROGRESS", _("Готовится")
        COMPLETED = "COMPLETED", _("Готов")
        DELAYED = "DELAYED", _("Задержан")
        CANCELLED = "CANCELLED", _("Отменен")

    class KitchenOrderPriority(models.TextChoices):
        LOW = "LOW", _("Низкий")
        NORMAL = "NORMAL", _("Обычный")
        HIGH = "HIGH", _("Высокий")
        URGENT = "URGENT", _("Срочно")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    queue = models.ForeignKey(
        KitchenQueue,
        on_delete=models.CASCADE,
        related_name="kitchen_orders",
        verbose_name=_("Очередь"),
    )
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="kitchen_order", verbose_name=_("Заказ")
    )
    status = models.CharField(
        max_length=20,
        choices=KitchenOrderStatus.choices,
        default=KitchenOrderStatus.NEW,
        verbose_name=_("Статус"),
    )
    priority = models.CharField(
        max_length=10,
        choices=KitchenOrderPriority.choices,
        default=KitchenOrderPriority.NORMAL,
        verbose_name=_("Приоритет"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_kitchen_orders",
        verbose_name=_("Назначен"),
    )
    notes = models.TextField(blank=True, null=True, verbose_name=_("Примечания кухни"))
    estimated_completion_time = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Расчетное время готовности")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создан в"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Начат в"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Готов в"))
    notification_sent = models.BooleanField(default=False, verbose_name=_("Уведомление отправлено"))

    class Meta:
        verbose_name = _("Заказ на кухне")
        verbose_name_plural = _("Заказы на кухне")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["queue", "status"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return f"Заказ №{self.order.order_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Переопределение метода save для автоматического обновления статусов."""
        if self.status == self.KitchenOrderStatus.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
            if self.order.status != Order.OrderStatus.PREPARING:
                self.order.status = Order.OrderStatus.PREPARING
                self.order.save(update_fields=["status"])

        if self.status == self.KitchenOrderStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
            if self.order.status != Order.OrderStatus.READY:
                self.order.status = Order.OrderStatus.READY
                self.order.save(update_fields=["status"])

        if self.status == self.KitchenOrderStatus.CANCELLED:
            if self.order.status != Order.OrderStatus.CANCELLED:
                self.order.status = Order.OrderStatus.CANCELLED
                self.order.save(update_fields=["status"])

        super().save(*args, **kwargs)

    def get_processing_time(self):
        """Возвращает время обработки заказа в минутах."""
        if not self.started_at:
            return 0

        end_time = self.completed_at or timezone.now()
        processing_time = (end_time - self.started_at).total_seconds() / 60

        return round(processing_time)

    def is_delayed(self):
        """Проверяет, задержан ли заказ."""
        if not self.estimated_completion_time:
            return False

        return (
            timezone.now() > self.estimated_completion_time
            and self.status != self.KitchenOrderStatus.COMPLETED
        )


class KitchenOrderItem(models.Model):
    """
    Модель для отслеживания статуса отдельных позиций заказа на кухне.
    """

    class KitchenItemStatus(models.TextChoices):
        PENDING = "PENDING", _("Ожидает")
        PREPARING = "PREPARING", _("Готовится")
        READY = "READY", _("Готов")
        SERVED = "SERVED", _("Подан")
        CANCELLED = "CANCELLED", _("Отменен")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    kitchen_order = models.ForeignKey(
        KitchenOrder,
        on_delete=models.CASCADE,
        related_name="kitchen_items",
        verbose_name=_("Заказ на кухне"),
    )
    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="kitchen_item",
        verbose_name=_("Позиция заказа"),
    )
    status = models.CharField(
        max_length=20,
        choices=KitchenItemStatus.choices,
        default=KitchenItemStatus.PENDING,
        verbose_name=_("Статус"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_kitchen_items",
        verbose_name=_("Назначен"),
    )
    cooking_station = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Кухонная станция")
    )
    preparation_notes = models.TextField(
        blank=True, null=True, verbose_name=_("Примечания по приготовлению")
    )
    estimated_cooking_time = models.PositiveIntegerField(
        default=0, verbose_name=_("Расчетное время приготовления (мин)")
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Начато в"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Готово в"))
    sequence_number = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("Порядковый номер"), help_text=_("Порядок приготовления блюд")
    )

    class Meta:
        verbose_name = _("Позиция на кухне")
        verbose_name_plural = _("Позиции на кухне")
        ordering = ["kitchen_order", "sequence_number"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["kitchen_order", "status"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self):
        return f"{self.order_item.menu_item.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Переопределение метода save для автоматического обновления статусов."""
        if self.status == self.KitchenItemStatus.PREPARING and not self.started_at:
            self.started_at = timezone.now()

            if self.kitchen_order.status != KitchenOrder.KitchenOrderStatus.IN_PROGRESS:
                self.kitchen_order.status = KitchenOrder.KitchenOrderStatus.IN_PROGRESS
                self.kitchen_order.save(update_fields=["status"])

        if self.status == self.KitchenItemStatus.READY and not self.completed_at:
            self.completed_at = timezone.now()

            if self.all_items_ready():
                self.kitchen_order.status = KitchenOrder.KitchenOrderStatus.COMPLETED
                self.kitchen_order.save(update_fields=["status"])

        super().save(*args, **kwargs)

    def all_items_ready(self):
        """Проверяет, готовы ли все позиции в заказе."""
        pending_items = (
            KitchenOrderItem.objects.filter(kitchen_order=self.kitchen_order)
            .exclude(
                status__in=[
                    self.KitchenItemStatus.READY,
                    self.KitchenItemStatus.SERVED,
                    self.KitchenItemStatus.CANCELLED,
                ]
            )
            .exists()
        )

        return not pending_items

    def get_cooking_time(self):
        """Возвращает фактическое время приготовления в минутах."""
        if not self.started_at:
            return 0

        end_time = self.completed_at or timezone.now()
        cooking_time = (end_time - self.started_at).total_seconds() / 60

        return round(cooking_time)

    def is_delayed(self):
        """Проверяет, задерживается ли приготовление позиции."""
        if not self.started_at or not self.estimated_cooking_time:
            return False

        estimated_completion = self.started_at + timezone.timedelta(
            minutes=self.estimated_cooking_time
        )
        return timezone.now() > estimated_completion and self.status != self.KitchenItemStatus.READY


class CookingStation(models.Model):
    """
    Модель для представления кухонных станций (гриль, фритюр, салаты и т.д.).
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
        related_name="cooking_stations",
        verbose_name=_("Ресторан"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Название станции"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активна"))
    queue = models.ForeignKey(
        KitchenQueue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stations",
        verbose_name=_("Очередь"),
    )
    responsible_roles = models.JSONField(
        default=list,
        verbose_name=_("Ответственные роли"),
        help_text=_("JSON-массив с ролями сотрудников, ответственных за эту станцию"),
    )
    average_prep_time = models.PositiveIntegerField(
        default=0, verbose_name=_("Среднее время приготовления (мин)")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Кухонная станция")
        verbose_name_plural = _("Кухонные станции")
        ordering = ["restaurant", "name"]
        unique_together = [["restaurant", "name"]]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def get_current_workload(self):
        """Возвращает текущую загрузку станции."""
        return KitchenOrderItem.objects.filter(
            cooking_station=self.name, status=KitchenOrderItem.KitchenItemStatus.PREPARING
        ).count()


class KitchenEvent(models.Model):
    """
    Модель для журналирования событий на кухне.
    """

    class EventType(models.TextChoices):
        ORDER_RECEIVED = "ORDER_RECEIVED", _("Заказ получен")
        ORDER_STARTED = "ORDER_STARTED", _("Начато приготовление")
        ORDER_COMPLETED = "ORDER_COMPLETED", _("Заказ готов")
        ORDER_DELAYED = "ORDER_DELAYED", _("Заказ задержан")
        ORDER_CANCELLED = "ORDER_CANCELLED", _("Заказ отменен")
        ITEM_STARTED = "ITEM_STARTED", _("Блюдо начато")
        ITEM_COMPLETED = "ITEM_COMPLETED", _("Блюдо готово")
        STAFF_ASSIGNED = "STAFF_ASSIGNED", _("Назначен сотрудник")
        QUEUE_STATUS_CHANGED = "QUEUE_STATUS_CHANGED", _("Статус очереди изменен")
        NOTE_ADDED = "NOTE_ADDED", _("Добавлено примечание")
        OTHER = "OTHER", _("Другое")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="kitchen_events",
        verbose_name=_("Ресторан"),
    )
    kitchen_order = models.ForeignKey(
        KitchenOrder,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
        verbose_name=_("Заказ на кухне"),
    )
    kitchen_item = models.ForeignKey(
        KitchenOrderItem,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
        verbose_name=_("Позиция на кухне"),
    )
    event_type = models.CharField(
        max_length=30, choices=EventType.choices, verbose_name=_("Тип события")
    )
    description = models.TextField(verbose_name=_("Описание"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kitchen_events",
        verbose_name=_("Кто создал"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP-адрес"))
    user_agent = models.TextField(null=True, blank=True, verbose_name=_("User Agent"))

    class Meta:
        verbose_name = _("Событие на кухне")
        verbose_name_plural = _("События на кухне")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["kitchen_order", "event_type"]),
            models.Index(fields=["kitchen_item", "event_type"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"
