from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Category, Allergen, Ingredient, MenuItem, MenuItemIngredient, Modifier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "parent", "order", "is_active", "get_active_items_count")
    list_filter = ("restaurant", "is_active", "parent")
    search_fields = ("name", "description")
    list_editable = ("order", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "parent", "restaurant", "is_active", "order")}),
        (_("Изображение"), {"fields": ("image",), "classes": ("collapse",)}),
        (
            _("Дополнительная информация"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_active_items_count(self, obj):
        return obj.get_active_items_count()

    get_active_items_count.short_description = _("Активные позиции")


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ("name", "severity_level", "get_menu_items_count")
    list_filter = ("severity_level",)
    search_fields = ("name", "description")
    list_editable = ("severity_level",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "severity_level")}),
        (_("Изображение"), {"fields": ("icon",), "classes": ("collapse",)}),
        (
            _("Дополнительная информация"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_menu_items_count(self, obj):
        return obj.get_menu_items_count()

    get_menu_items_count.short_description = _("Использований в блюдах")


class AllergenInline(admin.TabularInline):
    model = Ingredient.allergens.through
    extra = 1
    verbose_name = _("Аллерген")
    verbose_name_plural = _("Аллергены")


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "restaurant",
        "display_allergens",
        "calories_per_100g",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
    )
    list_filter = ("restaurant", "is_vegetarian", "is_vegan", "is_gluten_free", "allergens")
    search_fields = ("name", "description")
    filter_horizontal = ("allergens",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 20
    fieldsets = (
        (None, {"fields": ("name", "description", "restaurant", "created_by")}),
        (
            _("Пищевая ценность (на 100г)"),
            {
                "fields": (
                    "calories_per_100g",
                    "protein_per_100g",
                    "fat_per_100g",
                    "carbs_per_100g",
                    "fiber_per_100g",
                    "sugar_per_100g",
                )
            },
        ),
        (
            _("Диетические ограничения"),
            {"fields": ("is_vegetarian", "is_vegan", "is_gluten_free", "allergens")},
        ),
        (_("Изображение"), {"fields": ("image",), "classes": ("collapse",)}),
        (
            _("Дополнительная информация"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def display_allergens(self, obj):
        allergens = obj.get_allergens_list()
        if not allergens:
            return "-"
        return ", ".join(allergens)

    display_allergens.short_description = _("Аллергены")


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1
    autocomplete_fields = ["ingredient"]
    fields = ("ingredient", "amount_grams", "is_main", "is_visible", "order", "notes")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "restaurant",
        "price",
        "status",
        "display_nutrition",
        "is_vegetarian",
        "is_vegan",
        "is_active",
    )
    list_filter = (
        "restaurant",
        "category",
        "status",
        "is_active",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
        "is_signature",
    )
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "display_nutrition_details", "display_allergens")
    inlines = [MenuItemIngredientInline]
    actions = ["update_dietary_flags", "mark_as_available", "mark_as_unavailable"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "category",
                    "restaurant",
                    "price",
                    "status",
                    "is_active",
                    "created_by",
                )
            },
        ),
        (
            _("Диетические ограничения"),
            {
                "fields": (
                    "is_vegetarian",
                    "is_vegan",
                    "is_gluten_free",
                    "is_lactose_free",
                    "spicy_level",
                )
            },
        ),
        (_("Изображения"), {"fields": ("image", "additional_images"), "classes": ("collapse",)}),
        (
            _("Дополнительная информация"),
            {"fields": ("is_signature", "serving_size", "preparation_time", "order_in_category")},
        ),
        (
            _("Пищевая ценность (рассчитывается автоматически)"),
            {
                "fields": ("display_nutrition_details", "display_allergens"),
                "classes": ("collapse",),
            },
        ),
        (_("Система"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def display_nutrition(self, obj):
        nutrition = obj.calculate_total_nutrition()
        return f"Ккал: {nutrition['calories']}, Б/Ж/У: {nutrition['protein']}/{nutrition['fat']}/{nutrition['carbs']}"

    display_nutrition.short_description = _("КБЖУ")

    def display_nutrition_details(self, obj):
        nutrition = obj.calculate_total_nutrition()
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
            nutrition["calories"],
            nutrition["protein"],
            nutrition["fat"],
            nutrition["carbs"],
            nutrition["fiber"],
            nutrition["sugar"],
        )

    display_nutrition_details.short_description = _("Подробная пищевая ценность")

    def display_allergens(self, obj):
        allergens = obj.get_allergens()
        if not allergens:
            return "Аллергены не обнаружены"

        allergen_list = "</li><li>".join([allergen.name for allergen in allergens])
        return format_html("<ul><li>{}</li></ul>", format_html(allergen_list))

    display_allergens.short_description = _("Аллергены в блюде")

    def update_dietary_flags(self, request, queryset):
        for menu_item in queryset:
            menu_item.update_dietary_flags()
        self.message_user(request, _("Диетические флаги обновлены для выбранных элементов."))

    update_dietary_flags.short_description = _("Обновить диетические флаги")

    def mark_as_available(self, request, queryset):
        queryset.update(status=MenuItem.MenuItemStatus.AVAILABLE)
        self.message_user(request, _("Выбранные позиции отмечены как доступные."))

    mark_as_available.short_description = _("Отметить как доступные")

    def mark_as_unavailable(self, request, queryset):
        queryset.update(status=MenuItem.MenuItemStatus.UNAVAILABLE)
        self.message_user(request, _("Выбранные позиции отмечены как недоступные."))

    mark_as_unavailable.short_description = _("Отметить как недоступные")


@admin.register(MenuItemIngredient)
class MenuItemIngredientAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "ingredient", "amount_grams", "is_main", "is_visible", "order")
    list_filter = ("is_main", "is_visible", "menu_item__restaurant")
    search_fields = ("menu_item__name", "ingredient__name", "notes")
    raw_id_fields = ("menu_item", "ingredient")
    fieldsets = (
        (None, {"fields": ("menu_item", "ingredient", "amount_grams")}),
        (_("Отображение"), {"fields": ("is_main", "is_visible", "order", "notes")}),
    )


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "restaurant",
        "modifier_type",
        "price_change",
        "related_ingredient",
        "is_active",
    )
    list_filter = ("restaurant", "modifier_type", "is_active")
    search_fields = ("name", "description")
    filter_horizontal = ("applicable_items",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "restaurant", "modifier_type", "is_active")}),
        (_("Цена и связи"), {"fields": ("price_change", "related_ingredient", "applicable_items")}),
        (
            _("Влияние на пищевую ценность"),
            {"fields": ("nutrition_impact",), "classes": ("collapse",)},
        ),
        (
            _("Дополнительная информация"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
