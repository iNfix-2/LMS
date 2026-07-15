from django import template

register = template.Library()

@register.filter(name='dict_key')
def dict_key(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key) or dictionary.get(str(key))
