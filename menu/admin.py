from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Category, Allergen, Ingredient, MenuItem, MenuItemIngredient

admin.site.register(Category)
admin.site.register(Allergen)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "calories_per_100g",
        "protein_per_100g",
        "fat_per_100g",
        "carbs_per_100g",
    )
    search_fields = ("name",)
    filter_horizontal = ("allergens",)


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1
    autocomplete_fields = ["ingredient"]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "status",
        "calculated_calories",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
    )
    list_filter = ("category", "status", "is_vegetarian", "is_vegan", "is_gluten_free")
    search_fields = ("name", "description", "category__name")
    list_editable = ("price", "status")
    readonly_fields = (
        "calculated_calories",
        "calculated_protein",
        "calculated_fat",
        "calculated_carbs",
        "allergens_display",
    )
    inlines = [MenuItemIngredientInline]
    fieldsets = (
        (None, {"fields": ("name", "description", "category", "price", "status", "image")}),
        (
            _("Диетические маркеры"),
            {
                "fields": ("is_vegetarian", "is_vegan", "is_gluten_free", "is_lactose_free"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Расчетные характеристики (только чтение)"),
            {
                "fields": (
                    "calculated_calories",
                    "calculated_protein",
                    "calculated_fat",
                    "calculated_carbs",
                    "allergens_display",
                ),
            },
        ),
    )

    def allergens_display(self, obj):
        return ", ".join([a.name for a in obj.present_allergens])

    allergens_display.short_description = _("Аллергены в блюде")
