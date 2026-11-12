from django import template
import builtins

register = template.Library()

@register.filter
def sub(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter(name='abs')
def abs_value(value):
    try:
        return builtins.abs(float(value))
    except (ValueError, TypeError):
        return ''
 
