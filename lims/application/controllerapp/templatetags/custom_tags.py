from django import template
from django.conf import settings

from configuration.models import RefValues

register = template.Library()


@register.simple_tag
def get_module_images():
    required_reftype = getattr(settings, 'APPLICATION_MODULE_IMAGES_REFERENCE', '')
    module_images = RefValues.objects.filter(reftype_id__name=required_reftype).values_list('value',
                                                                                            'display_value')
    module_images_dict = {value: display_value for value, display_value in module_images}
    return module_images_dict
