import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from restaurants.models import Restaurant, Table
from menu.models import MenuItem, Modifier


class Discount(models.Model):
    """
    Модель для представления скидок и промокодов.
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", _("Процент")
        FIXED = "FIXED", _("Фиксированная сумма")
        FREE_ITEM = "FREE_ITEM", _("Бесплатная позиция")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Код скидки/промокод"))
    name = models.CharField(max_length=100, verbose_name=_("Название"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание"))
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        verbose_name=_("Тип скидки"),
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Значение скидки"),
        help_text=_("Процент или сумма, в зависимости от типа скидки"),
    )
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Минимальная сумма заказа"),
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Максимальная сумма скидки"),
    )

    valid_from = models.DateTimeField(default=timezone.now, verbose_name=_("Действует с"))
    valid_to = models.DateTimeField(null=True, blank=True, verbose_name=_("Действует до"))
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Лимит использований")
    )
    times_used = models.PositiveIntegerField(default=0, verbose_name=_("Количество использований"))

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="discounts",
        null=True,
        blank=True,
        verbose_name=_("Ресторан"),
    )

    applicable_categories = models.ManyToManyField(
        "menu.Category",
        blank=True,
        related_name="discounts",
        verbose_name=_("Применимо к категориям"),
    )
    applicable_items = models.ManyToManyField(
        "menu.MenuItem", blank=True, related_name="discounts", verbose_name=_("Применимо к блюдам")
    )

    free_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="free_item_discounts",
        verbose_name=_("Бесплатное блюдо"),
    )

    is_active = models.BooleanField(default=True, verbose_name=_("Активна"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_discounts",
        verbose_name=_("Кто создал"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Скидка/Промокод")
        verbose_name_plural = _("Скидки/Промокоды")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["valid_from", "valid_to", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def is_valid(self):
        """Проверяет, действительна ли скидка на текущий момент."""
        now = timezone.now()

        if not self.is_active:
            return False

        if self.valid_from and self.valid_from > now:
            return False

        if self.valid_to and self.valid_to < now:
            return False

        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False

        return True

    def calculate_discount_amount(self, subtotal):
        """
        Рассчитывает сумму скидки для указанной суммы заказа.
        """
        if not self.is_valid() or subtotal < self.min_order_value:
            return Decimal("0.00")

        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount_amount = subtotal * (self.value / Decimal("100.00"))

            if self.max_discount_amount is not None:
                discount_amount = min(discount_amount, self.max_discount_amount)

            return discount_amount

        elif self.discount_type == self.DiscountType.FIXED:
            return min(self.value, subtotal)

        return Decimal("0.00")


class Order(models.Model):
    """
    Модель для представления заказа.
    """

    class OrderStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Черновик")
        PLACED = "PLACED", _("Размещен")
        PREPARING = "PREPARING", _("Готовится")
        READY = "READY", _("Готов")
        SERVED = "SERVED", _("Подан")
        COMPLETED = "COMPLETED", _("Выполнен")
        CANCELLED = "CANCELLED", _("Отменен")

    class OrderType(models.TextChoices):
        DINE_IN = "DINE_IN", _("В ресторане")
        TAKEAWAY = "TAKEAWAY", _("На вынос")
        DELIVERY = "DELIVERY", _("Доставка")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    order_number = models.CharField(max_length=20, unique=True, verbose_name=_("Номер заказа"))
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.PROTECT, related_name="orders", verbose_name=_("Ресторан")
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Столик"),
    )
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waiter_orders",
        verbose_name=_("Официант"),
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_orders",
        verbose_name=_("Клиент"),
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        verbose_name=_("Статус заказа"),
    )
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DINE_IN,
        verbose_name=_("Тип заказа"),
    )

    customer_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Имя клиента")
    )
    customer_phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Телефон клиента")
    )
    delivery_address = models.TextField(blank=True, null=True, verbose_name=_("Адрес доставки"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    placed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Время размещения"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Время выполнения"))

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Сумма без скидки"),
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Сумма налога"),
    )
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Скидка/Промокод"),
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Сумма скидки"),
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Итоговая сумма"),
    )

    special_requests = models.TextField(blank=True, null=True, verbose_name=_("Особые пожелания"))

    nutritional_preferences = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Предпочтения по питанию"),
        help_text=_("JSON с предпочтениями клиента (вегетарианец, аллергии и т.д.)"),
    )

    class Meta:
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["table"]),
            models.Index(fields=["waiter"]),
        ]

    def __str__(self):
        return f"Заказ №{self.order_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Переопределение метода save для автоматической генерации номера заказа."""
        if not self.order_number:
            last_order = Order.objects.order_by("-order_number").first()
            today = timezone.now()
            prefix = today.strftime("%y%m-")

            if last_order and last_order.order_number.startswith(prefix):
                last_number = int(last_order.order_number.split("-")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.order_number = f"{prefix}{new_number:04d}"

        if self.status == self.OrderStatus.PLACED and not self.placed_at:
            self.placed_at = timezone.now()

        if self.status == self.OrderStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Рассчитывает все суммы заказа и обновляет их."""
        self.subtotal = sum(item.get_total_price() for item in self.items.all())

        if self.discount and self.discount.is_valid():
            self.discount_amount = self.discount.calculate_discount_amount(self.subtotal)
        else:
            self.discount_amount = Decimal("0.00")

        self.tax_amount = (self.subtotal - self.discount_amount) * Decimal("0.13")

        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount

        self.save(update_fields=["subtotal", "discount_amount", "tax_amount", "total_amount"])

    def get_order_nutrition(self):
        """Возвращает суммарную пищевую ценность для всего заказа."""
        total_nutrition = {
            "calories": Decimal("0.00"),
            "protein": Decimal("0.00"),
            "fat": Decimal("0.00"),
            "carbs": Decimal("0.00"),
            "fiber": Decimal("0.00"),
            "sugar": Decimal("0.00"),
        }

        for item in self.items.select_related("menu_item").all():
            item_nutrition = item.get_nutrition()
            for key in total_nutrition:
                if key in item_nutrition:
                    total_nutrition[key] += item_nutrition[key]

        for key in total_nutrition:
            total_nutrition[key] = round(total_nutrition[key], 2)

        return total_nutrition

    def get_order_allergens(self):
        """Возвращает список всех аллергенов, присутствующих в заказе."""
        allergens = set()

        for item in self.items.select_related("menu_item").all():
            menu_item_allergens = item.menu_item.get_allergens()
            for allergen in menu_item_allergens:
                allergens.add(allergen)

        return list(allergens)


class OrderItem(models.Model):
    """
    Модель для представления позиции в заказе.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("Заказ")
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("Позиция меню"),
    )
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name=_("Количество")
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Цена за единицу"),
    )
    modifiers = models.ManyToManyField(
        Modifier,
        through="OrderItemModifier",
        related_name="order_items",
        blank=True,
        verbose_name=_("Модификаторы"),
    )
    notes = models.TextField(blank=True, null=True, verbose_name=_("Примечания"))
    status = models.CharField(
        max_length=20,
        choices=Order.OrderStatus.choices,
        default=Order.OrderStatus.DRAFT,
        verbose_name=_("Статус позиции"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Позиция заказа")
        verbose_name_plural = _("Позиции заказа")
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} (Заказ №{self.order.order_number})"

    def save(self, *args, **kwargs):
        """Переопределение метода save для автоматического заполнения цены."""
        if not self.pk or not self.unit_price:
            self.unit_price = self.menu_item.price

        super().save(*args, **kwargs)

        self.order.calculate_totals()

    def get_total_price(self):
        """Возвращает общую стоимость позиции с учетом модификаторов."""
        base_price = self.unit_price * self.quantity

        modifier_cost = sum(
            mod.modifier.price_change * mod.quantity for mod in self.order_item_modifiers.all()
        )

        return base_price + modifier_cost

    def get_nutrition(self):
        """Возвращает пищевую ценность для позиции заказа с учетом количества."""
        base_nutrition = self.menu_item.calculate_total_nutrition()

        nutrition = {}
        for key, value in base_nutrition.items():
            nutrition[key] = value * self.quantity

        for modifier_relation in self.order_item_modifiers.select_related("modifier").all():
            mod = modifier_relation.modifier
            if mod.nutrition_impact:
                for key, value in mod.nutrition_impact.items():
                    if key in nutrition:
                        nutrition[key] += Decimal(str(value)) * modifier_relation.quantity

        return nutrition


class OrderItemModifier(models.Model):
    """
    Промежуточная модель для связи между OrderItem и Modifier
    с указанием количества модификатора.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="order_item_modifiers",
        verbose_name=_("Позиция заказа"),
    )
    modifier = models.ForeignKey(
        Modifier,
        on_delete=models.PROTECT,
        related_name="order_item_modifiers",
        verbose_name=_("Модификатор"),
    )
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name=_("Количество")
    )
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Примечания"))

    class Meta:
        verbose_name = _("Модификатор позиции")
        verbose_name_plural = _("Модификаторы позиций")
        unique_together = ["order_item", "modifier"]

    def __str__(self):
        return f"{self.modifier.name} для {self.order_item}"

    def save(self, *args, **kwargs):
        """При сохранении модификатора пересчитываем стоимость заказа."""
        super().save(*args, **kwargs)
        self.order_item.order.calculate_totals()


class Payment(models.Model):
    """
    Модель для представления платежа.
    """

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Наличные")
        CREDIT_CARD = "CREDIT_CARD", _("Кредитная карта")
        DEBIT_CARD = "DEBIT_CARD", _("Дебетовая карта")
        BANK_TRANSFER = "BANK_TRANSFER", _("Банковский перевод")
        MOBILE_PAYMENT = "MOBILE_PAYMENT", _("Мобильный платеж")
        GIFT_CARD = "GIFT_CARD", _("Подарочная карта")
        OTHER = "OTHER", _("Другое")

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Ожидает")
        COMPLETED = "COMPLETED", _("Выполнен")
        FAILED = "FAILED", _("Ошибка")
        REFUNDED = "REFUNDED", _("Возвращен")
        PARTIAL_REFUND = "PARTIAL_REFUND", _("Частичный возврат")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Уникальный идентификатор"),
    )
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="payments", verbose_name=_("Заказ")
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, verbose_name=_("Способ оплаты")
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Сумма"),
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Статус платежа"),
    )
    transaction_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("ID транзакции")
    )
    payment_date = models.DateTimeField(default=timezone.now, verbose_name=_("Дата платежа"))
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payments",
        verbose_name=_("Кто обработал"),
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Сумма возврата"),
    )
    refund_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата возврата"))
    additional_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Дополнительная информация"),
        help_text=_("JSON с дополнительными данными платежа"),
    )
    notes = models.TextField(blank=True, null=True, verbose_name=_("Примечания"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        verbose_name = _("Платеж")
        verbose_name_plural = _("Платежи")
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"Платеж {self.amount} {self.get_payment_method_display()} для Заказа №{self.order.order_number}"

    def save(self, *args, **kwargs):
        """Переопределение метода save для обновления статуса заказа."""
        super().save(*args, **kwargs)

        if self.status == self.PaymentStatus.COMPLETED:
            total_paid = sum(
                p.amount for p in self.order.payments.filter(status=self.PaymentStatus.COMPLETED)
            )

            if total_paid >= self.order.total_amount and self.order.status in [
                Order.OrderStatus.SERVED,
                Order.OrderStatus.READY,
            ]:
                self.order.status = Order.OrderStatus.COMPLETED
                self.order.completed_at = timezone.now()
                self.order.save(update_fields=["status", "completed_at"])

    def process_refund(self, amount=None, notes=None):
        """Обрабатывает возврат платежа."""
        if self.status not in [self.PaymentStatus.COMPLETED, self.PaymentStatus.PARTIAL_REFUND]:
            raise ValueError(_("Возврат возможен только для выполненных платежей."))

        if amount is None:
            amount = self.amount - self.refund_amount
        else:
            if amount > (self.amount - self.refund_amount):
                raise ValueError(_("Сумма возврата превышает доступную сумму."))

        self.refund_amount += amount
        self.refund_date = timezone.now()

        if notes:
            self.notes = f"{self.notes}\n{notes}" if self.notes else notes

        if self.refund_amount == self.amount:
            self.status = self.PaymentStatus.REFUNDED
        else:
            self.status = self.PaymentStatus.PARTIAL_REFUND

        self.save(update_fields=["refund_amount", "refund_date", "notes", "status"])
