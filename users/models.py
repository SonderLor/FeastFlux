from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from restaurants.models import Restaurant


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
    external_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Внешний ID")
    )

    email_verified = models.BooleanField(default=False, verbose_name=_("Email подтвержден"))

    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        permissions = [
            ("can_manage_users", "Может управлять пользователями"),
            ("can_view_reports", "Может просматривать отчеты"),
            ("can_manage_menu", "Может управлять меню"),
            ("can_process_payments", "Может проводить оплату"),
            ("view_public_tables", "Может просматривать столики публично"),
            ("view_own_orders", "Может просматривать свои заказы"),
            ("view_own_profile", "Может просматривать свой профиль"),
            ("view_own_cart", "Может просматривать свою корзину"),
            ("add_customer_order", "Может создавать клиентские заказы"),
            ("checkout_order", "Может оформлять заказы"),
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

    def is_customer(self):
        return self.role == self.UserRole.CUSTOMER

    def is_kitchen_staff(self):
        """Проверяет, относится ли пользователь к кухонному персоналу"""
        return self.role in [self.UserRole.KITCHEN, self.UserRole.BARTENDER]

    def is_restaurant_staff(self):
        """Проверяет, является ли пользователь сотрудником ресторана"""
        return self.role in [
            self.UserRole.ADMIN,
            self.UserRole.MANAGER,
            self.UserRole.WAITER,
            self.UserRole.KITCHEN,
            self.UserRole.BARTENDER,
        ]

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

    favorite_dishes = models.JSONField(
        blank=True,
        null=True,
        default=list,
        verbose_name=_("Любимые блюда"),
        help_text=_("Список ID любимых блюд"),
    )
    saved_delivery_addresses = models.JSONField(
        blank=True,
        null=True,
        default=list,
        verbose_name=_("Сохраненные адреса доставки"),
    )
    notification_preferences = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Настройки уведомлений"),
    )

    loyalty_points = models.PositiveIntegerField(default=0, verbose_name=_("Баллы лояльности"))

    taste_profile = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        verbose_name=_("Профиль вкусов"),
        help_text=_("Данные о предпочтениях для рекомендаций"),
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
        UserProfile.objects.get_or_create(user=instance)
        instance.profile.save()


class VerificationToken(models.Model):
    """
    Модель для хранения токенов верификации email и сброса пароля.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
        verbose_name=_("Пользователь"),
    )
    token = models.CharField(max_length=100, unique=True, verbose_name=_("Токен"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    expires_at = models.DateTimeField(verbose_name=_("Дата истечения"))
    token_type = models.CharField(
        max_length=20,
        choices=[
            ("EMAIL_VERIFICATION", _("Верификация Email")),
            ("PASSWORD_RESET", _("Сброс пароля")),
        ],
        verbose_name=_("Тип токена"),
    )
    is_used = models.BooleanField(default=False, verbose_name=_("Использован"))

    class Meta:
        verbose_name = _("Токен верификации")
        verbose_name_plural = _("Токены верификации")
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "token_type"]),
        ]

    def __str__(self):
        return f"Токен {self.token_type} для {self.user.username}"

    def is_valid(self):
        """Проверяет, действителен ли токен."""
        from django.utils import timezone

        now = timezone.now()
        return not self.is_used and now < self.expires_at
