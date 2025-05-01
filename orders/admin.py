from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("menu_item", "quantity", "unit_price", "get_item_total_display", "comment")
    readonly_fields = ("unit_price", "get_item_total_display")
    extra = 1
    autocomplete_fields = ["menu_item"]

    def get_item_total_display(self, obj):
        return obj.get_item_total()

    get_item_total_display.short_description = "Сумма по позиции"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "waiter", "order_type", "status", "total_amount", "created_at")
    list_filter = ("status", "order_type", "created_at", "waiter", "table")
    search_fields = ("id", "table__number", "waiter__username", "comments")
    readonly_fields = (
        "created_at",
        "last_modified",
        "total_amount",
        "nutrition_summary",
        "allergens_summary",
    )
    list_select_related = ("table", "waiter")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]

    fieldsets = (
        (None, {"fields": ("status", "order_type", "table", "waiter", "comments")}),
        (
            "Сумма и время",
            {
                "fields": ("total_amount", "created_at", "last_modified"),
                "classes": ("collapse",),
            },
        ),
        (
            "Пищевая ценность и Аллергены (Весь заказ)",
            {
                "fields": ("nutrition_summary", "allergens_summary"),
                "classes": ("collapse",),
            },
        ),
    )

    def nutrition_summary(self, obj):
        nutrition = obj.get_total_nutrition()
        return (
            f"Ккал: {nutrition['calories']}, "
            f"Б: {nutrition['protein']}г, "
            f"Ж: {nutrition['fat']}г, "
            f"У: {nutrition['carbs']}г"
        )

    nutrition_summary.short_description = "КБЖУ (итого)"

    def allergens_summary(self, obj):
        allergens = obj.get_order_allergens()
        if not allergens:
            return "Нет"
        return ", ".join(allergens)

    allergens_summary.short_description = "Аллергены (итого)"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.update_total_amount()
