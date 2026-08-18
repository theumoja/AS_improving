from .models import Institution

def institution_info(request):
    """
    Makes the primary institution object globally available to all templates
    without passing it through individual view functions.
    """
    return {'institution': Institution.objects.first()}