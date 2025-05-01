from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from .models import Discount, Order, OrderItem, OrderItemModifier, Payment


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "discount_type",
        "value",
        "is_valid_display",
        "valid_from",
        "valid_to",
        "times_used",
        "is_active",
    )
    list_filter = ("discount_type", "is_active", "valid_from", "valid_to", "restaurant")
    search_fields = ("code", "name", "description")
    filter_horizontal = ("applicable_categories", "applicable_items")
    readonly_fields = ("times_used", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("code", "name", "description", "discount_type", "value", "is_active")}),
        (
            _("Ограничения"),
            {
                "fields": (
                    "min_order_value",
                    "max_discount_amount",
                    "valid_from",
                    "valid_to",
                    "usage_limit",
                    "times_used",
                )
            },
        ),
        (
            _("Применение"),
            {"fields": ("restaurant", "applicable_categories", "applicable_items", "free_item")},
        ),
        (
            _("Система"),
            {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def is_valid_display(self, obj):
        return obj.is_valid()

    is_valid_display.boolean = True
    is_valid_display.short_description = _("Действительна")


class OrderItemModifierInline(admin.TabularInline):
    model = OrderItemModifier
    extra = 1
    fields = ("modifier", "quantity", "notes")
    autocomplete_fields = ["modifier"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ("menu_item", "quantity", "unit_price", "status", "notes", "get_total_price_display")
    readonly_fields = ("unit_price", "get_total_price_display")
    autocomplete_fields = ["menu_item"]
    show_change_link = True

    def get_total_price_display(self, obj):
        if obj.pk:
            return obj.get_total_price()
        return "-"

    get_total_price_display.short_description = _("Итого")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("payment_method", "amount", "status", "payment_date", "processed_by", "refund_amount")
    readonly_fields = ("refund_amount",)
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "restaurant",
        "get_table_display",
        "waiter",
        "status",
        "order_type",
        "total_amount",
        "payment_status",
        "created_at",
    )
    list_filter = ("restaurant", "status", "order_type", "created_at")
    search_fields = ("order_number", "customer_name", "customer_phone", "special_requests")
    readonly_fields = (
        "order_number",
        "created_at",
        "updated_at",
        "placed_at",
        "completed_at",
        "subtotal",
        "tax_amount",
        "discount_amount",
        "total_amount",
        "display_nutrition",
        "display_allergens",
    )
    inlines = [OrderItemInline, PaymentInline]
    actions = [
        "mark_as_placed",
        "mark_as_preparing",
        "mark_as_ready",
        "mark_as_served",
        "mark_as_completed",
        "mark_as_cancelled",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "order_number",
                    "restaurant",
                    "table",
                    "waiter",
                    "customer",
                    "status",
                    "order_type",
                )
            },
        ),
        (
            _("Информация о клиенте"),
            {
                "fields": (
                    "customer_name",
                    "customer_phone",
                    "delivery_address",
                    "special_requests",
                ),
                "classes": (
                    ("collapse",) if not Order._meta.get_field("delivery_address") else tuple()
                ),
            },
        ),
        (
            _("Суммы"),
            {"fields": ("subtotal", "discount", "discount_amount", "tax_amount", "total_amount")},
        ),
        (
            _("Пищевая ценность и аллергены (фишка)"),
            {
                "fields": ("nutritional_preferences", "display_nutrition", "display_allergens"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Даты и время"),
            {
                "fields": ("created_at", "updated_at", "placed_at", "completed_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_table_display(self, obj):
        if obj.table:
            return f"№{obj.table.number}"
        return "-"

    get_table_display.short_description = _("Столик")

    def payment_status(self, obj):
        total_paid = sum(
            p.amount for p in obj.payments.filter(status=Payment.PaymentStatus.COMPLETED)
        )

        if total_paid == 0:
            return format_html('<span style="color: red;">Не оплачен</span>')
        elif total_paid < obj.total_amount:
            percentage = (total_paid / obj.total_amount) * 100
            return format_html(
                '<span style="color: orange;">Частично оплачен ({:.0f}%)</span>', percentage
            )
        else:
            return format_html('<span style="color: green;">Оплачен</span>')

    payment_status.short_description = _("Статус оплаты")

    def display_nutrition(self, obj):
        nutrition = obj.get_order_nutrition()
        return format_html(
            "<table style='width:100%; border-collapse:collapse;'>"
            "<tr style='background-color:#f9f9f9;'><th style='padding:8px; text-align:left; border:1px solid #ddd;'>Показатель</th><th style='padding:8px; text-align:right; border:1px solid #ddd;'>Значение</th></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Калории</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} ккал</td></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Белки</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} г</td></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Жиры</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} г</td></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Углеводы</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} г</td></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Клетчатка</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} г</td></tr>"
            "<tr><td style='padding:8px; border:1px solid #ddd;'>Сахара</td><td style='padding:8px; text-align:right; border:1px solid #ddd;'>{} г</td></tr>"
            "</table>",
            nutrition.get("calories", 0),
            nutrition.get("protein", 0),
            nutrition.get("fat", 0),
            nutrition.get("carbs", 0),
            nutrition.get("fiber", 0),
            nutrition.get("sugar", 0),
        )

    display_nutrition.short_description = _("Пищевая ценность заказа")

    def display_allergens(self, obj):
        allergens = obj.get_order_allergens()
        if not allergens:
            return _("Аллергены не обнаружены")

        allergen_list = "</li><li>".join([allergen.name for allergen in allergens])
        return format_html("<ul><li>{}</li></ul>", format_html(allergen_list))

    display_allergens.short_description = _("Аллергены в заказе")

    def mark_as_placed(self, request, queryset):
        for order in queryset.filter(status=Order.OrderStatus.DRAFT):
            order.status = Order.OrderStatus.PLACED
            order.placed_at = timezone.now()
            order.save(update_fields=["status", "placed_at"])
        self.message_user(request, _("Выбранные заказы отмечены как размещенные."))

    mark_as_placed.short_description = _("Отметить как размещенные")

    def mark_as_preparing(self, request, queryset):
        queryset.filter(status=Order.OrderStatus.PLACED).update(status=Order.OrderStatus.PREPARING)
        self.message_user(request, _("Выбранные заказы отмечены как готовящиеся."))

    mark_as_preparing.short_description = _("Отметить как готовящиеся")

    def mark_as_ready(self, request, queryset):
        queryset.filter(status=Order.OrderStatus.PREPARING).update(status=Order.OrderStatus.READY)
        self.message_user(request, _("Выбранные заказы отмечены как готовые."))

    mark_as_ready.short_description = _("Отметить как готовые")

    def mark_as_served(self, request, queryset):
        queryset.filter(status=Order.OrderStatus.READY).update(status=Order.OrderStatus.SERVED)
        self.message_user(request, _("Выбранные заказы отмечены как поданные."))

    mark_as_served.short_description = _("Отметить как поданные")

    def mark_as_completed(self, request, queryset):
        now = timezone.now()
        for order in queryset.filter(status=Order.OrderStatus.SERVED):
            order.status = Order.OrderStatus.COMPLETED
            order.completed_at = now
            order.save(update_fields=["status", "completed_at"])
        self.message_user(request, _("Выбранные заказы отмечены как выполненные."))

    mark_as_completed.short_description = _("Отметить как выполненные")

    def mark_as_cancelled(self, request, queryset):
        queryset.exclude(status=Order.OrderStatus.COMPLETED).update(
            status=Order.OrderStatus.CANCELLED
        )
        self.message_user(request, _("Выбранные заказы отмечены как отмененные."))

    mark_as_cancelled.short_description = _("Отметить как отмененные")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "order",
        "menu_item",
        "quantity",
        "unit_price",
        "get_total_price",
        "status",
    )
    list_filter = ("status", "order__restaurant")
    search_fields = ("order__order_number", "menu_item__name", "notes")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemModifierInline]
    fieldsets = (
        (None, {"fields": ("order", "menu_item", "quantity", "unit_price", "status")}),
        (
            _("Дополнительная информация"),
            {"fields": ("notes", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    autocomplete_fields = ["order", "menu_item"]

    def get_total_price(self, obj):
        return obj.get_total_price()

    get_total_price.short_description = _("Итого")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "payment_method",
        "amount",
        "status",
        "payment_date",
        "refund_amount",
    )
    list_filter = ("status", "payment_method", "payment_date")
    search_fields = ("order__order_number", "transaction_id", "notes")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("order", "payment_method", "amount", "status", "payment_date")}),
        (
            _("Информация о транзакции"),
            {"fields": ("transaction_id", "processed_by", "additional_info")},
        ),
        (_("Возврат"), {"fields": ("refund_amount", "refund_date"), "classes": ("collapse",)}),
        (
            _("Дополнительная информация"),
            {"fields": ("notes", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    actions = ["process_refund"]

    def process_refund(self, request, queryset):
        """Действие для обработки возврата платежа."""
        if queryset.count() != 1:
            self.message_user(
                request, _("Выберите только один платеж для возврата."), level=messages.ERROR
            )
            return

        payment = queryset.first()
        if payment.status not in [
            Payment.PaymentStatus.COMPLETED,
            Payment.PaymentStatus.PARTIAL_REFUND,
        ]:
            self.message_user(
                request,
                _("Возврат возможен только для выполненных платежей."),
                level=messages.ERROR,
            )
            return

        return redirect(
            f"/admin/orders/payment/{payment.id}/refund/"
        )  # TODO когда реализую урлы, приду сюда и сделаю норм ссылку с ленивой загрузкой

    process_refund.short_description = _("Обработать возврат")
