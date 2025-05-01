from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from restaurants.models import Table
from menu.models import MenuItem, Modifier

class Order(models.Model):
    class OrderStatus(models.TextChoices):
        NEW = 'NEW', _('Новый')
        ACCEPTED = 'ACC', _('Принят')
        PREPARING = 'PRE', _('Готовится')
        READY = 'RDY', _('Готов к подаче')
        SERVED = 'SRV', _('Подан')
        PAID = 'PAD', _('Оплачен')
        CANCELLED = 'CAN', _('Отменен')

    class OrderType(models.TextChoices):
        DINE_IN = 'DIN', _('В зале')
        TAKEAWAY = 'TAK', _('Навынос')
        DELIVERY = 'DEL', _('Доставка')

    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        related_name='orders',
        verbose_name=_('Столик'),
        null=True, blank=True
    )
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='served_orders',
        verbose_name=_('Официант'),
        null=True, blank=True
    )
    # Если в будущем будет интерфейс для клиента:
    # customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, ...)

    status = models.CharField(
        max_length=3,
        choices=OrderStatus.choices,
        default=OrderStatus.NEW,
        verbose_name=_('Статус заказа')
    )
    order_type = models.CharField(
        max_length=3,
        choices=OrderType.choices,
        default=OrderType.DINE_IN,
        verbose_name=_('Тип заказа')
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name=_('Время создания'))
    last_modified = models.DateTimeField(auto_now=True, verbose_name=_('Время последнего изменения'))

    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Итоговая сумма')
    )
    # Можно добавить скидку, если нужно
    # discount = models.DecimalField(...)
    # final_amount = models.DecimalField(...)

    comments = models.TextField(blank=True, null=True, verbose_name=_('Комментарии к заказу'))

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['waiter']),
            models.Index(fields=['table']),
        ]

    def __str__(self):
        if self.table:
            return f"Заказ №{self.id} ({self.table}) - {self.get_status_display()}"
        else:
            return f"Заказ №{self.id} ({self.get_order_type_display()}) - {self.get_status_display()}"

    def update_total_amount(self):
        """Пересчитывает и сохраняет общую стоимость заказа на основе его позиций."""
        total = sum(item.get_item_total() for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount', 'last_modified'])


    def get_total_nutrition(self):
        """Возвращает суммарные КБЖУ для всего заказа."""
        total_calories = Decimal('0.0')
        total_protein = Decimal('0.0')
        total_fat = Decimal('0.0')
        total_carbs = Decimal('0.0')

        for item in self.items.prefetch_related('menu_item__menuitemingredient_set__ingredient'):
            item_nutrition = item.get_item_nutrition_totals()
            total_calories += item_nutrition.get('calories', Decimal('0.0'))
            total_protein += item_nutrition.get('protein', Decimal('0.0'))
            total_fat += item_nutrition.get('fat', Decimal('0.0'))
            total_carbs += item_nutrition.get('carbs', Decimal('0.0'))

        return {
            'calories': round(total_calories, 2),
            'protein': round(total_protein, 2),
            'fat': round(total_fat, 2),
            'carbs': round(total_carbs, 2),
        }

    def get_order_allergens(self):
        """Возвращает список уникальных аллергенов, присутствующих в заказе."""
        order_allergens = set()
        for item in self.items.prefetch_related('menu_item__ingredients__allergens'):
            allergens = item.get_item_allergens()
            order_allergens.update(allergens)
        return sorted([allergen.name for allergen in order_allergens])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Заказ')
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Позиция меню')
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество')
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Цена за единицу')
    )
    item_name_at_order = models.CharField(max_length=200, blank=True, verbose_name=_('Название на момент заказа'))
    nutrition_at_order = models.JSONField(null=True, blank=True, verbose_name=_('КБЖУ на момент заказа'))
    modifiers = models.ManyToManyField(Modifier, blank=True, verbose_name=_('Модификаторы'))

    comment = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Комментарий к позиции'))

    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказа')
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} (Заказ №{self.order.id})"

    def save(self, *args, **kwargs):
        if not self.pk or not self.unit_price:
            self.unit_price = self.menu_item.price
        if not self.pk or not self.item_name_at_order:
             self.item_name_at_order = self.menu_item.name
        # Сохраняем КБЖУ/аллергены - TODO
        # if not self.pk or not self.nutrition_at_order:
        #   self.nutrition_at_order = {
        #       'calories': self.menu_item.calculated_calories, ...
        #       'allergens': [a.id for a in self.menu_item.present_allergens]
        #   }

        super().save(*args, **kwargs)
        self.order.update_total_amount()

    def get_item_total(self):
        """Возвращает стоимость этой позиции (количество * цена за единицу)."""
        return self.quantity * self.unit_price

    def get_item_nutrition_totals(self):
        """Возвращает КБЖУ для этой позиции заказа (КБЖУ блюда * количество)."""
        # TODO: Нужна реализация расчета КБЖУ в модели MenuItem!
        calories = getattr(self.menu_item, 'calculated_calories', Decimal('0.0'))
        protein = getattr(self.menu_item, 'calculated_protein', Decimal('0.0'))
        fat = getattr(self.menu_item, 'calculated_fat', Decimal('0.0'))
        carbs = getattr(self.menu_item, 'calculated_carbs', Decimal('0.0'))

        return {
            'calories': calories * self.quantity,
            'protein': protein * self.quantity,
            'fat': fat * self.quantity,
            'carbs': carbs * self.quantity,
        }

    def get_item_allergens(self):
        """Возвращает список аллергенов для этой позиции заказа."""
        # TODO: Нужна реализация получения аллергенов в модели MenuItem!
        return getattr(self.menu_item, 'present_allergens', [])

