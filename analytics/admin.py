from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from menu.models import MenuItem
from .models import (
    DailySales, PopularItem, StaffPerformance, TableOccupancy,
    NutritionalAnalytics, CustomerSegment, CustomerInsight
)


@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    list_display = ('date', 'restaurant', 'total_orders', 'completed_orders',
                    'gross_sales', 'net_sales', 'average_order_value')
    list_filter = ('restaurant', 'date')
    search_fields = ('restaurant__name',)
    date_hierarchy = 'date'
    readonly_fields = ('updated_at',)
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'date')
        }),
        (_('Основные метрики'), {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders')
        }),
        (_('Финансовые показатели'), {
            'fields': ('gross_sales', 'discount_amount', 'tax_amount', 'net_sales', 'average_order_value')
        }),
        (_('Пиковая нагрузка'), {
            'fields': ('peak_hour_orders', 'peak_hour_sales')
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['regenerate_daily_sales']

    def regenerate_daily_sales(self, request, queryset):
        """
        Пересчитывает данные для выбранных записей DailySales.
        """
        count = 0
        for sales_record in queryset:
            DailySales.generate_for_date(sales_record.date, sales_record.restaurant)
            count += 1

        self.message_user(request, _(f'Данные успешно пересчитаны для {count} записей.'))

    regenerate_daily_sales.short_description = _('Пересчитать данные о продажах')


@admin.register(PopularItem)
class PopularItemAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'restaurant', 'date_period', 'total_orders',
                    'total_quantity', 'total_revenue', 'average_rating')
    list_filter = ('restaurant', 'date_period', 'menu_item__category')
    search_fields = ('menu_item__name', 'restaurant__name')
    readonly_fields = ('updated_at',)
    autocomplete_fields = ['menu_item']
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'menu_item', 'date_period')
        }),
        (_('Статистика заказов'), {
            'fields': ('total_orders', 'total_quantity', 'total_revenue')
        }),
        (_('Пользовательский опыт'), {
            'fields': ('average_rating', 'last_ordered')
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['update_items_popularity']

    def update_items_popularity(self, request, queryset):
        """
        Пересчитывает данные о популярности выбранных позиций.
        """
        unique_periods = set()
        unique_restaurants = set()

        for record in queryset:
            unique_periods.add(record.date_period)
            unique_restaurants.add(record.restaurant)

        count = 0
        for period in unique_periods:
            for restaurant in unique_restaurants:
                PopularItem.update_for_period(period, restaurant)
                count += 1

        self.message_user(request, _(f'Данные о популярности обновлены для {count} периодов/ресторанов.'))

    update_items_popularity.short_description = _('Обновить данные о популярности')


@admin.register(StaffPerformance)
class StaffPerformanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'restaurant', 'date_period', 'total_orders',
                    'total_sales', 'average_order_value', 'hours_worked', 'get_sales_per_hour')
    list_filter = ('restaurant', 'date_period', 'staff__role')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name', 'restaurant__name')
    readonly_fields = ('updated_at', 'get_sales_per_hour')
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'staff', 'date_period')
        }),
        (_('Показатели для официантов'), {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders',
                       'total_sales', 'average_order_value')
        }),
        (_('Показатели для кухни'), {
            'fields': ('items_prepared', 'average_preparation_time')
        }),
        (_('Общие показатели'), {
            'fields': ('hours_worked', 'get_sales_per_hour')
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def get_sales_per_hour(self, obj):
        return f"{obj.sales_per_hour:.2f}" if obj.sales_per_hour else "0.00"

    get_sales_per_hour.short_description = _('Продажи в час')


@admin.register(TableOccupancy)
class TableOccupancyAdmin(admin.ModelAdmin):
    list_display = ('table', 'restaurant', 'date', 'total_orders',
                    'total_revenue', 'total_guests', 'get_occupancy_rate')
    list_filter = ('restaurant', 'date')
    search_fields = ('table__number', 'restaurant__name')
    readonly_fields = ('updated_at', 'get_occupancy_rate', 'get_revenue_per_hour')
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'table', 'date')
        }),
        (_('Статистика использования'), {
            'fields': ('total_orders', 'total_guests', 'usage_minutes',
                       'peak_usage_hour', 'get_occupancy_rate')
        }),
        (_('Финансовые показатели'), {
            'fields': ('total_revenue', 'get_revenue_per_hour')
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def get_occupancy_rate(self, obj):
        return f"{obj.occupancy_rate:.2f}%"

    get_occupancy_rate.short_description = _('Занятость')

    def get_revenue_per_hour(self, obj):
        return f"{obj.revenue_per_hour:.2f}"

    get_revenue_per_hour.short_description = _('Доход в час')


@admin.register(NutritionalAnalytics)
class NutritionalAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'date_period', 'total_orders',
                    'avg_calories_per_order', 'vegetarian_orders', 'vegan_orders')
    list_filter = ('restaurant', 'date_period')
    search_fields = ('restaurant__name',)
    readonly_fields = ('updated_at', 'format_common_allergens')
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'date_period', 'total_orders')
        }),
        (_('Средние показатели КБЖУ'), {
            'fields': ('avg_calories_per_order', 'avg_protein_per_order',
                       'avg_fat_per_order', 'avg_carbs_per_order')
        }),
        (_('Диетические предпочтения'), {
            'fields': ('vegetarian_orders', 'vegan_orders',
                       'gluten_free_orders', 'lactose_free_orders')
        }),
        (_('Аллергены'), {
            'fields': ('format_common_allergens',)
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def format_common_allergens(self, obj):
        """Форматирует данные об аллергенах в читаемую таблицу"""
        if not obj.common_allergens:
            return "-"

        table_html = '<table style="width:100%; border-collapse:collapse;">'
        table_html += '<tr style="background-color:#f9f9f9;"><th style="padding:8px; text-align:left; border:1px solid #ddd;">Аллерген</th><th style="padding:8px; text-align:right; border:1px solid #ddd;">Количество заказов</th></tr>'

        for allergen, count in obj.common_allergens.items():
            table_html += f'<tr><td style="padding:8px; border:1px solid #ddd;">{allergen}</td><td style="padding:8px; text-align:right; border:1px solid #ddd;">{count}</td></tr>'

        table_html += '</table>'
        return format_html(table_html)

    format_common_allergens.short_description = _('Распространенные аллергены')

    actions = ['regenerate_nutritional_analytics']

    def regenerate_nutritional_analytics(self, request, queryset):
        """
        Пересчитывает данные для выбранных записей NutritionalAnalytics.
        """
        count = 0
        for record in queryset:
            NutritionalAnalytics.generate_for_period(record.date_period, record.restaurant)
            count += 1

        self.message_user(request, _(f'Данные успешно пересчитаны для {count} записей.'))

    regenerate_nutritional_analytics.short_description = _('Пересчитать аналитику питательности')


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'avg_order_value',
                    'visit_frequency', 'get_customer_count', 'loyalty_index', 'churn_risk')
    list_filter = ('restaurant', 'loyalty_index')
    search_fields = ('name', 'description')
    filter_horizontal = ('preferred_categories', 'preferred_items')
    readonly_fields = ('created_at', 'updated_at', 'format_dietary_preferences')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'restaurant')
        }),
        (_('Поведенческие характеристики'), {
            'fields': ('avg_order_value', 'visit_frequency', 'loyalty_index', 'churn_risk')
        }),
        (_('Пищевые предпочтения'), {
            'fields': ('format_dietary_preferences', 'preferred_categories', 'preferred_items')
        }),
        (_('Система'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_customer_count(self, obj):
        return obj.get_customer_count()

    get_customer_count.short_description = _('Клиентов')

    def format_dietary_preferences(self, obj):
        """Форматирует данные о диетических предпочтениях в читаемый вид"""
        if not obj.dietary_preferences:
            return "-"

        preferences_html = '<ul>'
        for pref, value in obj.dietary_preferences.items():
            preferences_html += f'<li><strong>{pref}:</strong> {value}</li>'
        preferences_html += '</ul>'

        return format_html(preferences_html)

    format_dietary_preferences.short_description = _('Диетические предпочтения')


@admin.register(CustomerInsight)
class CustomerInsightAdmin(admin.ModelAdmin):
    list_display = ('customer', 'segment', 'total_visits',
                    'total_spend', 'avg_order_value', 'get_lifetime_value')
    list_filter = ('segment', 'last_visit_date')
    search_fields = ('customer__username', 'customer__first_name', 'customer__last_name')
    readonly_fields = ('updated_at', 'format_favorite_items', 'format_dietary_preferences',
                       'format_allergens', 'format_purchase_patterns', 'get_lifetime_value')
    fieldsets = (
        (None, {
            'fields': ('customer', 'segment')
        }),
        (_('История покупок'), {
            'fields': ('first_visit_date', 'last_visit_date', 'total_visits',
                       'total_spend', 'avg_order_value', 'get_lifetime_value')
        }),
        (_('Предпочтения'), {
            'fields': ('format_favorite_items', 'format_dietary_preferences', 'format_allergens')
        }),
        (_('Поведение'), {
            'fields': ('feedback_rating_avg', 'format_purchase_patterns')
        }),
        (_('Система'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def get_lifetime_value(self, obj):
        return f"{obj.lifetime_value:.2f}"

    get_lifetime_value.short_description = _('LTV')

    def format_favorite_items(self, obj):
        if not obj.favorite_items:
            return "-"

        table_html = '<table style="width:100%; border-collapse:collapse;">'
        table_html += '<tr style="background-color:#f9f9f9;"><th style="padding:8px; text-align:left; border:1px solid #ddd;">Блюдо</th><th style="padding:8px; text-align:right; border:1px solid #ddd;">Заказов</th></tr>'

        for item in obj.favorite_items:
            try:
                menu_item = MenuItem.objects.get(id=item['id'])
                table_html += f'<tr><td style="padding:8px; border:1px solid #ddd;">{menu_item.name}</td><td style="padding:8px; text-align:right; border:1px solid #ddd;">{item["count"]}</td></tr>'
            except MenuItem.DoesNotExist:
                table_html += f'<tr><td style="padding:8px; border:1px solid #ddd;">Блюдо не найдено (ID: {item["id"]})</td><td style="padding:8px; text-align:right; border:1px solid #ddd;">{item["count"]}</td></tr>'

        table_html += '</table>'
        return format_html(table_html)

    format_favorite_items.short_description = _('Любимые блюда')

    def format_dietary_preferences(self, obj):
        if not obj.dietary_preferences:
            return "-"

        preferences_html = '<ul>'
        for pref, value in obj.dietary_preferences.items():
            preferences_html += f'<li><strong>{pref}:</strong> {value}</li>'
        preferences_html += '</ul>'

        return format_html(preferences_html)

    format_dietary_preferences.short_description = _('Диетические предпочтения')

    def format_allergens(self, obj):
        if not obj.allergens:
            return "-"

        allergens_html = '<ul>'
        if isinstance(obj.allergens, list):
            for allergen in obj.allergens:
                allergens_html += f'<li>{allergen}</li>'
        elif isinstance(obj.allergens, dict):
            for allergen, value in obj.allergens.items():
                allergens_html += f'<li><strong>{allergen}:</strong> {value}</li>'
        else:
            allergens_html += f'<li>{obj.allergens}</li>'
        allergens_html += '</ul>'

        return format_html(allergens_html)

    format_allergens.short_description = _('Аллергены')

    def format_purchase_patterns(self, obj):
        if not obj.purchase_patterns:
            return "-"

        table_html = '<table style="width:100%; border-collapse:collapse;">'
        table_html += '<tr style="background-color:#f9f9f9;"><th style="padding:8px; text-align:left; border:1px solid #ddd;">Параметр</th><th style="padding:8px; text-align:right; border:1px solid #ddd;">Значение</th></tr>'

        for param, value in obj.purchase_patterns.items():
            table_html += f'<tr><td style="padding:8px; border:1px solid #ddd;">{param}</td><td style="padding:8px; text-align:right; border:1px solid #ddd;">{value}</td></tr>'

        table_html += '</table>'
        return format_html(table_html)

    format_purchase_patterns.short_description = _('Шаблоны покупок')
