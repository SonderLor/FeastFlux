from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sub(value, arg):
    """Вычитает arg из value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError):
        return value
