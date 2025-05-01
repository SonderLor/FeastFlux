from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Restaurant, Table, Reservation


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone', 'is_active', 'get_table_count')
    list_filter = ('is_active', 'city', 'country')
    search_fields = ('name', 'address', 'city', 'phone', 'email')
    filter_horizontal = ('managers',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'description', 'is_active')
        }),
        (_('Контактная информация'), {
            'fields': ('address', 'city', 'postal_code', 'country', 'phone', 'email', 'website')
        }),
        (_('Часы работы'), {
            'fields': ('opening_hours',)
        }),
        (_('Управление'), {
            'fields': ('managers',)
        }),
        (_('Дополнительная информация'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'restaurant', 'capacity', 'status', 'shape', 'is_active')
    list_filter = ('restaurant', 'status', 'shape', 'is_active', 'capacity')
    search_fields = ('number', 'restaurant__name', 'location_description')
    list_editable = ('status', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'number', 'capacity', 'status', 'is_active')
        }),
        (_('Расположение и размеры'), {
            'fields': ('shape', 'width', 'length', 'location_description', 'position_x', 'position_y')
        }),
        (_('Финансы'), {
            'fields': ('min_spend',),
            'classes': ('collapse',)
        }),
        (_('Дополнительная информация'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'restaurant', 'table', 'reservation_date', 'reservation_time', 'number_of_guests', 'status')
    list_filter = ('status', 'reservation_date', 'restaurant', 'number_of_guests')
    search_fields = ('customer_name', 'customer_email', 'customer_phone', 'special_requests')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'reservation_date'
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'table', 'status')
        }),
        (_('Клиент'), {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'user')
        }),
        (_('Детали бронирования'), {
            'fields': ('reservation_date', 'reservation_time', 'end_time', 'number_of_guests', 'special_requests')
        }),
        (_('Диета и аллергены (для наших "фишек")'), {
            'fields': ('dietary_preferences', 'allergy_information'),
            'classes': ('collapse',)
        }),
        (_('Система'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
