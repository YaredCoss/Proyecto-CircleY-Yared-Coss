# app_clientes/templatetags/ui_extras.py
import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

register = template.Library()


@register.filter
def currency(value):
    try:
        return f"${float(value):,.2f} MXN"
    except (TypeError, ValueError):
        return value

@register.filter
def highlight(text, search):
    if not search:
        return text
    text = conditional_escape(text)
    pattern = re.compile(re.escape(search), re.IGNORECASE)
    highlighted = pattern.sub(lambda m: f'<span class="resaltado">{m.group(0)}</span>', text)
    return mark_safe(highlighted)

# app_clientes/templatetags/ui_extras.py  (sección adicional)
@register.filter
def attr(obj, attr_name):
    """Devuelve el atributo pedido o vacío si no existe."""
    return getattr(obj, attr_name, '')

@register.filter
def dict_item(mapping, key):
    """Devuelve mapping[key] o '', útil para selects en plantillas."""
    if isinstance(mapping, dict):
        return mapping.get(key, '')
    return '' 

@register.filter
def currency(value, symbol="$", decimals=2):
    """
    Formatea valores numéricos como moneda.
    Ejemplo: currency(1234.5) -> $1,234.50
    """
    try:
        valor = float(value)
    except (TypeError, ValueError):
        return ""
    formato = f"{{:,.{decimals}f}}"
    return f"{symbol}{formato.format(valor)}"

@register.filter
def snake_to_title(value):
    """Convierte un string tipo snake_case a 'Snake Case'"""
    if not isinstance(value, str):
        return value
    return value.replace("_", " ").title()

@register.filter
def ensure_dict(value):
    """Devuelve el mismo valor si es dict, de lo contrario un dict vacío."""
    if isinstance(value, dict):
        return value
    return {}

@register.filter
def contains(value, arg):
    """Devuelve True si `arg` está contenido dentro de `value`."""
    if value is None:
        return False
    return str(arg) in str(value)

@register.filter
def file_url(value):
    """Devuelve value.url si existe, en caso contrario cadena vacía."""
    if not value:
        return ''
    return getattr(value, 'url', '')

@register.filter
def fk_value(instance, field_name):
    """Devuelve el PK del campo foráneo (o el valor directo)."""
    if not instance:
        return ''
    value = getattr(instance, field_name, '')
    if hasattr(value, 'pk'):
        return value.pk
    return value