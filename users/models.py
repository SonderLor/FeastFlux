from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    """
    Расширенная модель пользователя, которая включает
    дополнительные поля для ролей и статуса в ресторане.
    """

    class UserRole(models.TextChoices):
        ADMIN = "ADMIN", _("Администратор")
        MANAGER = "MANAGER", _("Менеджер")
        WAITER = "WAITER", _("Официант")
        KITCHEN = "KITCHEN", _("Повар/Кухня")
        BARTENDER = "BARTENDER", _("Бармен")
        CASHIER = "CASHIER", _("Кассир")
        CUSTOMER = "CUSTOMER", _("Клиент")

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        verbose_name=_("Роль в системе"),
    )
    is_active_employee = models.BooleanField(
        default=True,
        verbose_name=_("Активный сотрудник"),
        help_text=_("Указывает, активен ли пользователь как сотрудник ресторана"),
    )
    employee_id = models.CharField(
        max_length=20, blank=True, null=True, unique=True, verbose_name=_("ID сотрудника")
    )

    # TODO добавить связь с рестораном когда я его добавлю
    # restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        permissions = [
            ("can_manage_users", "Может управлять пользователями"),
            ("can_view_reports", "Может просматривать отчеты"),
            ("can_manage_menu", "Может управлять меню"),
            ("can_process_payments", "Может проводить оплату"),
        ]

    def is_admin(self):
        return self.role == self.UserRole.ADMIN or self.is_superuser

    def is_manager(self):
        return self.role == self.UserRole.MANAGER

    def is_waiter(self):
        return self.role == self.UserRole.WAITER

    def is_kitchen(self):
        return self.role == self.UserRole.KITCHEN

    def is_bartender(self):
        return self.role == self.UserRole.BARTENDER

    def is_kitchen_staff(self):
        """Проверяет, относится ли пользователь к кухонному персоналу"""
        return self.role in [self.UserRole.KITCHEN, self.UserRole.BARTENDER]

    def __str__(self):
        role_display = self.get_role_display()
        return f"{self.get_full_name() or self.username} ({role_display})"


class UserProfile(models.Model):
    """
    Расширенный профиль пользователя для хранения дополнительной информации,
    которая не обязательно должна быть в основной модели пользователя.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("Пользователь"),
    )
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Номер телефона")
    )
    address = models.TextField(blank=True, null=True, verbose_name=_("Адрес"))
    bio = models.TextField(blank=True, null=True, verbose_name=_("О себе"))
    date_of_birth = models.DateField(blank=True, null=True, verbose_name=_("Дата рождения"))
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True, verbose_name=_("Фотография профиля")
    )
    hire_date = models.DateField(blank=True, null=True, verbose_name=_("Дата найма"))
    dietary_preferences = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Пищевые предпочтения"),
        help_text=_("Например: вегетарианство, веганство, безглютеновая диета"),
    )
    allergens = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Аллергены"),
        help_text=_("Список аллергенов пользователя"),
    )

    class Meta:
        verbose_name = _("Профиль пользователя")
        verbose_name_plural = _("Профили пользователей")

    def __str__(self):
        return f"Профиль {self.user.username}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Создает или обновляет профиль пользователя при создании или обновлении модели User.
    """
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()
