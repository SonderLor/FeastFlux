from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _("Профиль")
    fk_name = "user"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Личная информация"), {"fields": ("first_name", "last_name", "email")}),
        (_("Работа в ресторане"), {"fields": ("role", "is_active_employee", "employee_id")}),
        (
            _("Права доступа"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active_employee",
        "is_staff",
    )
    list_filter = ("role", "is_active_employee", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "employee_id")
    ordering = ("username",)
