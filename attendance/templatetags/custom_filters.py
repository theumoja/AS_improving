from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Retrieves a value from a dictionary given a key.
    Usage in template: {{ marks_dict|get_item:student.reg_number }}
    """
    if isinstance(dictionary, dict):
        # Convert key to string/int lookup fallback if needed
        return dictionary.get(key) or dictionary.get(str(key))
    return None