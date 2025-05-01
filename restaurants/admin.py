from django.contrib import admin
from .models import Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'capacity', 'status', 'location_description')
    list_filter = ('status', 'capacity')
    search_fields = ('number', 'location_description')
    list_editable = ('status', 'capacity')
    ordering = ('number',)
