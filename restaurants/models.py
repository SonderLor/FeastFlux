from django.db import models
from django.utils.translation import gettext_lazy as _


class Table(models.Model):
    class TableStatus(models.TextChoices):
        FREE = 'FR', _('Свободен')
        OCCUPIED = 'OC', _('Занят')
        RESERVED = 'RS', _('Зарезервирован')
        UNAVAILABLE = 'UN', _('Недоступен')

    number = models.PositiveIntegerField(unique=True, verbose_name=_('Номер столика'))
    capacity = models.PositiveSmallIntegerField(default=2, verbose_name=_('Вместимость'))
    status = models.CharField(
        max_length=2,
        choices=TableStatus.choices,
        default=TableStatus.FREE,
        verbose_name=_('Статус столика')
    )
    location_description = models.CharField(max_length=255, blank=True, null=True,
                                            verbose_name=_('Расположение/Описание'))

    class Meta:
        verbose_name = _('Столик')
        verbose_name_plural = _('Столики')
        ordering = ['number']

    def __str__(self):
        return f"Столик №{self.number} ({self.get_status_display()})"


class Restaurant(models.Model):
    name = models.CharField(max_length=150, verbose_name=_('Название'))
    address = models.CharField(max_length=255, verbose_name=_('Адрес'))
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Телефон'))
    table = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
