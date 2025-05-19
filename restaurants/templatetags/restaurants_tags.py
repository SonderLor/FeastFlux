from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name="split")
def split(value, arg):
    """
    Разделяет строку на список по указанному разделителю.
    """
    return value.split(arg)


@register.filter(name="getattribute")
def getattribute(obj, attr):
    """
    Получает значение атрибута объекта по имени.
    """
    try:
        return getattr(obj, attr)
    except AttributeError:
        try:
            return obj[attr]
        except (KeyError, TypeError):
            return ""


@register.filter(name='get_field')
def get_field(form, field_name):
    """
    Получает поле формы по имени.
    Возвращает полный HTML виджет поля.
    """
    try:
        return form[field_name]
    except (KeyError, TypeError):
        return None


@register.filter
def filter_by_status(queryset, status):
    """
    Фильтрует QuerySet по указанному статусу.
    """
    return queryset.filter(status=status)
