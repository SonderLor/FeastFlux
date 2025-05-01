from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import format_html
from .models import KitchenQueue, KitchenOrder, KitchenOrderItem, CookingStation, KitchenEvent


class KitchenOrderItemInline(admin.TabularInline):
    model = KitchenOrderItem
    extra = 0
    fields = (
        "order_item",
        "status",
        "cooking_station",
        "assigned_to",
        "sequence_number",
        "estimated_cooking_time",
        "get_cooking_time",
        "is_delayed",
    )
    readonly_fields = ("order_item", "get_cooking_time", "is_delayed")
    show_change_link = True

    def get_cooking_time(self, obj):
        if obj.pk:
            return f"{obj.get_cooking_time()} мин."
        return "-"

    get_cooking_time.short_description = _("Фактическое время")

    def is_delayed(self, obj):
        if obj.pk and obj.is_delayed():
            return format_html('<span style="color: red; font-weight: bold;">Да</span>')
        return format_html('<span style="color: green;">Нет</span>')

    is_delayed.short_description = _("Задержка")


class KitchenEventInline(admin.TabularInline):
    model = KitchenEvent
    extra = 0
    fields = ("event_type", "description", "created_by", "created_at")
    readonly_fields = ("event_type", "description", "created_by", "created_at")
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KitchenQueue)
class KitchenQueueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "restaurant",
        "status",
        "is_default",
        "active_orders_count",
        "average_processing_time",
    )
    list_filter = ("restaurant", "status", "is_default")
    search_fields = ("name", "description", "restaurant__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("restaurant", "name", "description", "status", "is_default", "order")}),
        (_("Ответственность"), {"fields": ("responsible_roles",)}),
        (_("Система"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["open_queue", "close_queue", "pause_queue"]

    def open_queue(self, request, queryset):
        queryset.update(status=KitchenQueue.QueueStatus.OPEN)
        self.message_user(request, _("Выбранные очереди открыты."))

    open_queue.short_description = _("Открыть выбранные очереди")

    def close_queue(self, request, queryset):
        queryset.update(status=KitchenQueue.QueueStatus.CLOSED)
        self.message_user(request, _("Выбранные очереди закрыты."))

    close_queue.short_description = _("Закрыть выбранные очереди")

    def pause_queue(self, request, queryset):
        queryset.update(status=KitchenQueue.QueueStatus.PAUSED)
        self.message_user(request, _("Выбранные очереди приостановлены."))

    pause_queue.short_description = _("Приостановить выбранные очереди")


@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "queue",
        "status",
        "priority",
        "assigned_to",
        "created_at",
        "get_processing_time",
        "is_delayed_display",
    )
    list_filter = ("queue", "status", "priority", "assigned_to")
    search_fields = ("order__order_number", "notes", "assigned_to__username")
    readonly_fields = (
        "created_at",
        "started_at",
        "completed_at",
        "get_processing_time",
        "is_delayed_display",
    )
    inlines = [KitchenOrderItemInline, KitchenEventInline]
    fieldsets = (
        (None, {"fields": ("queue", "order", "status", "priority", "assigned_to")}),
        (_("Дополнительная информация"), {"fields": ("notes", "estimated_completion_time")}),
        (
            _("Временные отметки"),
            {
                "fields": (
                    "created_at",
                    "started_at",
                    "completed_at",
                    "get_processing_time",
                    "is_delayed_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_as_in_progress", "mark_as_completed", "mark_as_delayed", "mark_as_cancelled"]

    def get_processing_time(self, obj):
        return f"{obj.get_processing_time()} мин." if obj.started_at else "-"

    get_processing_time.short_description = _("Время обработки")

    def is_delayed_display(self, obj):
        if obj.is_delayed():
            return format_html('<span style="color: red; font-weight: bold;">Да</span>')
        return format_html('<span style="color: green;">Нет</span>')

    is_delayed_display.short_description = _("Задержка")

    def mark_as_in_progress(self, request, queryset):
        for order in queryset.filter(status=KitchenOrder.KitchenOrderStatus.NEW):
            order.status = KitchenOrder.KitchenOrderStatus.IN_PROGRESS
            order.started_at = timezone.now()
            order.save()
            KitchenEvent.objects.create(
                restaurant=order.queue.restaurant,
                kitchen_order=order,
                event_type=KitchenEvent.EventType.ORDER_STARTED,
                description=_('Заказ переведен в статус "Готовится"'),
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные заказы отмечены как "Готовится".'))

    mark_as_in_progress.short_description = _("Начать приготовление")

    def mark_as_completed(self, request, queryset):
        for order in queryset.filter(status=KitchenOrder.KitchenOrderStatus.IN_PROGRESS):
            order.status = KitchenOrder.KitchenOrderStatus.COMPLETED
            order.completed_at = timezone.now()
            order.save()
            KitchenEvent.objects.create(
                restaurant=order.queue.restaurant,
                kitchen_order=order,
                event_type=KitchenEvent.EventType.ORDER_COMPLETED,
                description=_('Заказ переведен в статус "Готов"'),
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные заказы отмечены как "Готовы".'))

    mark_as_completed.short_description = _("Отметить как готовые")

    def mark_as_delayed(self, request, queryset):
        for order in queryset.exclude(
            status__in=[
                KitchenOrder.KitchenOrderStatus.COMPLETED,
                KitchenOrder.KitchenOrderStatus.CANCELLED,
            ]
        ):
            order.status = KitchenOrder.KitchenOrderStatus.DELAYED
            order.save()
            KitchenEvent.objects.create(
                restaurant=order.queue.restaurant,
                kitchen_order=order,
                event_type=KitchenEvent.EventType.ORDER_DELAYED,
                description=_('Заказ отмечен как "Задержан"'),
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные заказы отмечены как "Задержаны".'))

    mark_as_delayed.short_description = _("Отметить как задержанные")

    def mark_as_cancelled(self, request, queryset):
        for order in queryset.exclude(
            status__in=[
                KitchenOrder.KitchenOrderStatus.COMPLETED,
                KitchenOrder.KitchenOrderStatus.CANCELLED,
            ]
        ):
            order.status = KitchenOrder.KitchenOrderStatus.CANCELLED
            order.save()
            KitchenEvent.objects.create(
                restaurant=order.queue.restaurant,
                kitchen_order=order,
                event_type=KitchenEvent.EventType.ORDER_CANCELLED,
                description=_("Заказ отменен"),
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные заказы отмечены как "Отменены".'))

    mark_as_cancelled.short_description = _("Отменить заказы")


@admin.register(KitchenOrderItem)
class KitchenOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order_item",
        "kitchen_order",
        "status",
        "cooking_station",
        "assigned_to",
        "estimated_cooking_time",
        "get_cooking_time",
        "is_delayed_display",
    )
    list_filter = ("status", "cooking_station", "assigned_to")
    search_fields = ("order_item__menu_item__name", "preparation_notes")
    readonly_fields = (
        "started_at",
        "completed_at",
        "get_cooking_time",
        "is_delayed_display",
        "kitchen_order",
        "order_item",
    )
    fieldsets = (
        (None, {"fields": ("kitchen_order", "order_item", "status", "sequence_number")}),
        (
            _("Приготовление"),
            {
                "fields": (
                    "cooking_station",
                    "assigned_to",
                    "estimated_cooking_time",
                    "preparation_notes",
                )
            },
        ),
        (
            _("Временные отметки"),
            {
                "fields": ("started_at", "completed_at", "get_cooking_time", "is_delayed_display"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_item_as_preparing", "mark_item_as_ready", "mark_item_as_served"]

    def get_cooking_time(self, obj):
        return f"{obj.get_cooking_time()} мин." if obj.started_at else "-"

    get_cooking_time.short_description = _("Время приготовления")

    def is_delayed_display(self, obj):
        if obj.is_delayed():
            return format_html('<span style="color: red; font-weight: bold;">Да</span>')
        return format_html('<span style="color: green;">Нет</span>')

    is_delayed_display.short_description = _("Задержка")

    def mark_item_as_preparing(self, request, queryset):
        for item in queryset.filter(status=KitchenOrderItem.KitchenItemStatus.PENDING):
            item.status = KitchenOrderItem.KitchenItemStatus.PREPARING
            item.started_at = timezone.now()
            item.save()
            KitchenEvent.objects.create(
                restaurant=item.kitchen_order.queue.restaurant,
                kitchen_order=item.kitchen_order,
                kitchen_item=item,
                event_type=KitchenEvent.EventType.ITEM_STARTED,
                description=f"Начато приготовление позиции: {item.order_item.menu_item.name}",
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные позиции отмечены как "Готовятся".'))

    mark_item_as_preparing.short_description = _("Начать приготовление")

    def mark_item_as_ready(self, request, queryset):
        for item in queryset.filter(status=KitchenOrderItem.KitchenItemStatus.PREPARING):
            item.status = KitchenOrderItem.KitchenItemStatus.READY
            item.completed_at = timezone.now()
            item.save()
            KitchenEvent.objects.create(
                restaurant=item.kitchen_order.queue.restaurant,
                kitchen_order=item.kitchen_order,
                kitchen_item=item,
                event_type=KitchenEvent.EventType.ITEM_COMPLETED,
                description=f"Позиция готова: {item.order_item.menu_item.name}",
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные позиции отмечены как "Готовы".'))

    mark_item_as_ready.short_description = _("Отметить как готовые")

    def mark_item_as_served(self, request, queryset):
        for item in queryset.filter(status=KitchenOrderItem.KitchenItemStatus.READY):
            item.status = KitchenOrderItem.KitchenItemStatus.SERVED
            item.save()
            KitchenEvent.objects.create(
                restaurant=item.kitchen_order.queue.restaurant,
                kitchen_order=item.kitchen_order,
                kitchen_item=item,
                event_type=KitchenEvent.EventType.ITEM_COMPLETED,
                description=f"Позиция подана: {item.order_item.menu_item.name}",
                created_by=request.user,
            )
        self.message_user(request, _('Выбранные позиции отмечены как "Поданы".'))

    mark_item_as_served.short_description = _("Отметить как поданные")


@admin.register(CookingStation)
class CookingStationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "restaurant",
        "queue",
        "is_active",
        "get_current_workload",
        "average_prep_time",
    )
    list_filter = ("restaurant", "is_active", "queue")
    search_fields = ("name", "description", "restaurant__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("restaurant", "name", "description", "is_active")}),
        (_("Настройки"), {"fields": ("queue", "responsible_roles", "average_prep_time")}),
        (_("Система"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_current_workload(self, obj):
        workload = obj.get_current_workload()
        return workload

    get_current_workload.short_description = _("Текущая загрузка")


@admin.register(KitchenEvent)
class KitchenEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "restaurant",
        "get_order_number",
        "get_item_name",
        "created_by",
        "created_at",
    )
    list_filter = ("restaurant", "event_type", "created_at")
    search_fields = ("description", "kitchen_order__order__order_number")
    readonly_fields = (
        "restaurant",
        "kitchen_order",
        "kitchen_item",
        "event_type",
        "description",
        "created_by",
        "created_at",
        "ip_address",
        "user_agent",
    )
    fieldsets = (
        (None, {"fields": ("event_type", "description", "created_by", "created_at")}),
        (_("Связи"), {"fields": ("restaurant", "kitchen_order", "kitchen_item")}),
        (
            _("Техническая информация"),
            {"fields": ("ip_address", "user_agent"), "classes": ("collapse",)},
        ),
    )

    def get_order_number(self, obj):
        if obj.kitchen_order:
            return obj.kitchen_order.order.order_number
        return "-"

    get_order_number.short_description = _("Номер заказа")

    def get_item_name(self, obj):
        if obj.kitchen_item:
            return obj.kitchen_item.order_item.menu_item.name
        return "-"

    get_item_name.short_description = _("Позиция")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
