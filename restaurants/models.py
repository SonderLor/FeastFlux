import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator


class Restaurant(models.Model):
    """
    Модель для представления ресторана в сети.
    Содержит основную информацию о ресторане.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название ресторана')
    )
    address = models.CharField(
        max_length=255,
        verbose_name=_('Адрес')
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_('Город')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Почтовый индекс')
    )
    country = models.CharField(
        max_length=100,
        default='Россия',
        verbose_name=_('Страна')
    )
    phone = models.CharField(
        max_length=20,
        verbose_name=_('Телефон')
    )
    email = models.EmailField(
        verbose_name=_('Email')
    )
    website = models.URLField(
        blank=True,
        null=True,
        verbose_name=_('Веб-сайт')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Описание')
    )
    opening_hours = models.JSONField(
        default=dict,
        verbose_name=_('Часы работы'),
        help_text=_('Формат: {"monday": {"open": "09:00", "close": "22:00"}, ...}')
    )
    logo = models.ImageField(
        upload_to='restaurant_logos/',
        blank=True,
        null=True,
        verbose_name=_('Логотип')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='managed_restaurants',
        limit_choices_to={'role': 'MANAGER'},
        blank=True,
        verbose_name=_('Менеджеры')
    )

    class Meta:
        verbose_name = _('Ресторан')
        verbose_name_plural = _('Рестораны')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"

    def get_table_count(self):
        """Возвращает количество столиков в ресторане"""
        return self.tables.count()

    def get_active_tables(self):
        """Возвращает активные столики"""
        return self.tables.filter(is_active=True)

    def get_reservations_today(self):
        """Возвращает сегодняшние бронирования"""
        today = timezone.now().date()
        return self.reservations.filter(
            reservation_date=today
        )

    def get_current_occupancy(self):
        """Возвращает текущую занятость ресторана"""
        return self.tables.filter(status=Table.TableStatus.OCCUPIED).count()


class Table(models.Model):
    """
    Модель для представления столика в ресторане.
    """

    class TableStatus(models.TextChoices):
        FREE = 'FREE', _('Свободен')
        OCCUPIED = 'OCCUPIED', _('Занят')
        RESERVED = 'RESERVED', _('Зарезервирован')
        UNAVAILABLE = 'UNAVAILABLE', _('Недоступен')

    class TableShape(models.TextChoices):
        ROUND = 'ROUND', _('Круглый')
        SQUARE = 'SQUARE', _('Квадратный')
        RECTANGULAR = 'RECTANGULAR', _('Прямоугольный')
        OVAL = 'OVAL', _('Овальный')
        CUSTOM = 'CUSTOM', _('Нестандартный')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='tables',
        verbose_name=_('Ресторан')
    )
    number = models.PositiveIntegerField(
        verbose_name=_('Номер столика')
    )
    capacity = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1)],
        verbose_name=_('Вместимость')
    )
    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.FREE,
        verbose_name=_('Статус')
    )
    shape = models.CharField(
        max_length=20,
        choices=TableShape.choices,
        default=TableShape.SQUARE,
        verbose_name=_('Форма')
    )
    width = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Ширина (см)')
    )
    length = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Длина (см)')
    )
    min_spend = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Минимальный чек')
    )
    location_description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Описание расположения')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен')
    )
    position_x = models.FloatField(
        default=0,
        verbose_name=_('Позиция X на карте')
    )
    position_y = models.FloatField(
        default=0,
        verbose_name=_('Позиция Y на карте')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )

    class Meta:
        verbose_name = _('Столик')
        verbose_name_plural = _('Столики')
        ordering = ['restaurant', 'number']
        unique_together = [['restaurant', 'number']]

    def __str__(self):
        return f"Столик №{self.number} ({self.restaurant.name})"

    def is_available(self, reservation_date, reservation_time, duration=2):
        """
        Проверяет, доступен ли столик на указанную дату и время с учетом продолжительности.
        По умолчанию продолжительность = 2 часа.
        """
        if not self.is_active or self.status == self.TableStatus.UNAVAILABLE:
            return False

        reservation_datetime = timezone.datetime.combine(
            reservation_date,
            reservation_time
        )
        end_datetime = reservation_datetime + timezone.timedelta(hours=duration)

        overlapping_reservations = self.reservations.filter(
            status__in=[Reservation.ReservationStatus.CONFIRMED, Reservation.ReservationStatus.PENDING],
            reservation_date=reservation_date,
            reservation_time__lt=end_datetime.time(),
            end_time__gt=reservation_time
        )

        return not overlapping_reservations.exists()


class Reservation(models.Model):
    """
    Модель для бронирования столиков в ресторане.
    """

    class ReservationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Ожидает подтверждения')
        CONFIRMED = 'CONFIRMED', _('Подтверждено')
        CANCELLED = 'CANCELLED', _('Отменено')
        COMPLETED = 'COMPLETED', _('Завершено')
        NO_SHOW = 'NO_SHOW', _('Не пришли')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Уникальный идентификатор')
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name=_('Ресторан')
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name=_('Столик')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reservations',
        null=True,
        blank=True,
        verbose_name=_('Пользователь')
    )
    customer_name = models.CharField(
        max_length=100,
        verbose_name=_('Имя клиента')
    )
    customer_email = models.EmailField(
        verbose_name=_('Email клиента')
    )
    customer_phone = models.CharField(
        max_length=20,
        verbose_name=_('Телефон клиента')
    )
    number_of_guests = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество гостей')
    )
    reservation_date = models.DateField(
        verbose_name=_('Дата бронирования')
    )
    reservation_time = models.TimeField(
        verbose_name=_('Время бронирования')
    )
    end_time = models.TimeField(
        verbose_name=_('Время окончания')
    )
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        verbose_name=_('Статус')
    )
    special_requests = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Особые пожелания')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_reservations',
        null=True,
        blank=True,
        verbose_name=_('Кто создал')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата обновления')
    )
    dietary_preferences = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Диетические предпочтения'),
        help_text=_('Например: вегетарианство, веганство, безглютеновая диета')
    )
    allergy_information = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Информация об аллергии'),
        help_text=_('Список аллергенов для компании гостей')
    )

    class Meta:
        verbose_name = _('Бронирование')
        verbose_name_plural = _('Бронирования')
        ordering = ['-reservation_date', 'reservation_time']
        indexes = [
            models.Index(fields=['reservation_date', 'status']),
            models.Index(fields=['customer_phone']),
        ]

    def __str__(self):
        return f"Бронь {self.customer_name} на {self.reservation_date} {self.reservation_time} (Столик №{self.table.number})"

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для автоматического расчета end_time,
        если он не был указан явно.
        """
        if self.reservation_time and not self.end_time:
            reservation_datetime = timezone.datetime.combine(
                timezone.datetime.today(),
                self.reservation_time
            )
            end_datetime = reservation_datetime + timezone.timedelta(hours=2)
            self.end_time = end_datetime.time()

        if self.status == self.ReservationStatus.CONFIRMED:
            self.table.status = Table.TableStatus.RESERVED
            self.table.save(update_fields=['status'])

        super().save(*args, **kwargs)

    def calculate_duration(self):
        """Рассчитывает продолжительность бронирования в минутах"""
        if not self.reservation_time or not self.end_time:
            return 0

        start_datetime = timezone.datetime.combine(timezone.datetime.today(), self.reservation_time)
        end_datetime = timezone.datetime.combine(timezone.datetime.today(), self.end_time)

        if end_datetime < start_datetime:
            end_datetime += timezone.timedelta(days=1)

        duration = end_datetime - start_datetime
        return duration.seconds // 60
