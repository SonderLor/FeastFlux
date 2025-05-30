# Generated by Django 5.2 on 2025-05-01 19:23

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("menu", "0001_initial"),
        ("restaurants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Discount",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Уникальный идентификатор",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="Код скидки/промокод"
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Название")),
                ("description", models.TextField(blank=True, null=True, verbose_name="Описание")),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("PERCENTAGE", "Процент"),
                            ("FIXED", "Фиксированная сумма"),
                            ("FREE_ITEM", "Бесплатная позиция"),
                        ],
                        default="PERCENTAGE",
                        max_length=20,
                        verbose_name="Тип скидки",
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Процент или сумма, в зависимости от типа скидки",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                        verbose_name="Значение скидки",
                    ),
                ),
                (
                    "min_order_value",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        verbose_name="Минимальная сумма заказа",
                    ),
                ),
                (
                    "max_discount_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name="Максимальная сумма скидки",
                    ),
                ),
                (
                    "valid_from",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Действует с"
                    ),
                ),
                (
                    "valid_to",
                    models.DateTimeField(blank=True, null=True, verbose_name="Действует до"),
                ),
                (
                    "usage_limit",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Лимит использований"
                    ),
                ),
                (
                    "times_used",
                    models.PositiveIntegerField(default=0, verbose_name="Количество использований"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "applicable_categories",
                    models.ManyToManyField(
                        blank=True,
                        related_name="discounts",
                        to="menu.category",
                        verbose_name="Применимо к категориям",
                    ),
                ),
                (
                    "applicable_items",
                    models.ManyToManyField(
                        blank=True,
                        related_name="discounts",
                        to="menu.menuitem",
                        verbose_name="Применимо к блюдам",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_discounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Кто создал",
                    ),
                ),
                (
                    "free_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="free_item_discounts",
                        to="menu.menuitem",
                        verbose_name="Бесплатное блюдо",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discounts",
                        to="restaurants.restaurant",
                        verbose_name="Ресторан",
                    ),
                ),
            ],
            options={
                "verbose_name": "Скидка/Промокод",
                "verbose_name_plural": "Скидки/Промокоды",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Уникальный идентификатор",
                    ),
                ),
                (
                    "order_number",
                    models.CharField(max_length=20, unique=True, verbose_name="Номер заказа"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Черновик"),
                            ("PLACED", "Размещен"),
                            ("PREPARING", "Готовится"),
                            ("READY", "Готов"),
                            ("SERVED", "Подан"),
                            ("COMPLETED", "Выполнен"),
                            ("CANCELLED", "Отменен"),
                        ],
                        default="DRAFT",
                        max_length=20,
                        verbose_name="Статус заказа",
                    ),
                ),
                (
                    "order_type",
                    models.CharField(
                        choices=[
                            ("DINE_IN", "В ресторане"),
                            ("TAKEAWAY", "На вынос"),
                            ("DELIVERY", "Доставка"),
                        ],
                        default="DINE_IN",
                        max_length=20,
                        verbose_name="Тип заказа",
                    ),
                ),
                (
                    "customer_name",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Имя клиента"
                    ),
                ),
                (
                    "customer_phone",
                    models.CharField(
                        blank=True, max_length=20, null=True, verbose_name="Телефон клиента"
                    ),
                ),
                (
                    "delivery_address",
                    models.TextField(blank=True, null=True, verbose_name="Адрес доставки"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "placed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Время размещения"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Время выполнения"),
                ),
                (
                    "subtotal",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Сумма без скидки",
                    ),
                ),
                (
                    "tax_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Сумма налога",
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Сумма скидки",
                    ),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Итоговая сумма",
                    ),
                ),
                (
                    "special_requests",
                    models.TextField(blank=True, null=True, verbose_name="Особые пожелания"),
                ),
                (
                    "nutritional_preferences",
                    models.JSONField(
                        blank=True,
                        help_text="JSON с предпочтениями клиента (вегетарианец, аллергии и т.д.)",
                        null=True,
                        verbose_name="Предпочтения по питанию",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="customer_orders",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Клиент",
                    ),
                ),
                (
                    "discount",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="orders.discount",
                        verbose_name="Скидка/Промокод",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="restaurants.restaurant",
                        verbose_name="Ресторан",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="restaurants.table",
                        verbose_name="Столик",
                    ),
                ),
                (
                    "waiter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="waiter_orders",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Официант",
                    ),
                ),
            ],
            options={
                "verbose_name": "Заказ",
                "verbose_name_plural": "Заказы",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Уникальный идентификатор",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Количество",
                    ),
                ),
                (
                    "unit_price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                        verbose_name="Цена за единицу",
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True, verbose_name="Примечания")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Черновик"),
                            ("PLACED", "Размещен"),
                            ("PREPARING", "Готовится"),
                            ("READY", "Готов"),
                            ("SERVED", "Подан"),
                            ("COMPLETED", "Выполнен"),
                            ("CANCELLED", "Отменен"),
                        ],
                        default="DRAFT",
                        max_length=20,
                        verbose_name="Статус позиции",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "menu_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="menu.menuitem",
                        verbose_name="Позиция меню",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Позиция заказа",
                "verbose_name_plural": "Позиции заказа",
                "ordering": ["order", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderItemModifier",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Уникальный идентификатор",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Количество",
                    ),
                ),
                (
                    "notes",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Примечания"
                    ),
                ),
                (
                    "modifier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_item_modifiers",
                        to="menu.modifier",
                        verbose_name="Модификатор",
                    ),
                ),
                (
                    "order_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_item_modifiers",
                        to="orders.orderitem",
                        verbose_name="Позиция заказа",
                    ),
                ),
            ],
            options={
                "verbose_name": "Модификатор позиции",
                "verbose_name_plural": "Модификаторы позиций",
            },
        ),
        migrations.AddField(
            model_name="orderitem",
            name="modifiers",
            field=models.ManyToManyField(
                blank=True,
                related_name="order_items",
                through="orders.OrderItemModifier",
                to="menu.modifier",
                verbose_name="Модификаторы",
            ),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="Уникальный идентификатор",
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("CASH", "Наличные"),
                            ("CREDIT_CARD", "Кредитная карта"),
                            ("DEBIT_CARD", "Дебетовая карта"),
                            ("BANK_TRANSFER", "Банковский перевод"),
                            ("MOBILE_PAYMENT", "Мобильный платеж"),
                            ("GIFT_CARD", "Подарочная карта"),
                            ("OTHER", "Другое"),
                        ],
                        max_length=20,
                        verbose_name="Способ оплаты",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                        verbose_name="Сумма",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Ожидает"),
                            ("COMPLETED", "Выполнен"),
                            ("FAILED", "Ошибка"),
                            ("REFUNDED", "Возвращен"),
                            ("PARTIAL_REFUND", "Частичный возврат"),
                        ],
                        default="PENDING",
                        max_length=20,
                        verbose_name="Статус платежа",
                    ),
                ),
                (
                    "transaction_id",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="ID транзакции"
                    ),
                ),
                (
                    "payment_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Дата платежа"
                    ),
                ),
                (
                    "refund_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Сумма возврата",
                    ),
                ),
                (
                    "refund_date",
                    models.DateTimeField(blank=True, null=True, verbose_name="Дата возврата"),
                ),
                (
                    "additional_info",
                    models.JSONField(
                        blank=True,
                        help_text="JSON с дополнительными данными платежа",
                        null=True,
                        verbose_name="Дополнительная информация",
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True, verbose_name="Примечания")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
                (
                    "processed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="processed_payments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Кто обработал",
                    ),
                ),
            ],
            options={
                "verbose_name": "Платеж",
                "verbose_name_plural": "Платежи",
                "ordering": ["-payment_date"],
            },
        ),
        migrations.AddIndex(
            model_name="discount",
            index=models.Index(fields=["code"], name="orders_disc_code_6de799_idx"),
        ),
        migrations.AddIndex(
            model_name="discount",
            index=models.Index(
                fields=["valid_from", "valid_to", "is_active"],
                name="orders_disc_valid_f_b9fce5_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["restaurant", "created_at"], name="orders_orde_restaur_763bf4_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["status"], name="orders_orde_status_c6dd84_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["order_number"], name="orders_orde_order_n_f3ada5_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["table"], name="orders_orde_table_i_37b1ad_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["waiter"], name="orders_orde_waiter__270a78_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="orderitemmodifier",
            unique_together={("order_item", "modifier")},
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["order", "status"], name="orders_paym_order_i_e3de73_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["payment_date"], name="orders_paym_payment_9e5ac0_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["transaction_id"], name="orders_paym_transac_29fb2b_idx"),
        ),
    ]
