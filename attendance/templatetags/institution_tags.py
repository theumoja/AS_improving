from django import template
from attendance.models import Institution

register = template.Library()

@register.simple_tag
def get_institution():
    return Institution.objects.first()