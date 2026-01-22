from django.apps import apps
from django.http import JsonResponse

from logutil.log import log


def get_staining_techniques(request):
    # This is for getting the list of Staining Techniques
    RefValues = apps.get_model('configuration', 'RefValues')
    ReferenceType = apps.get_model('configuration', 'ReferenceType')

    try:
        log.info(f"Get reference values for reference type ---> StainingTechniques")
        reftype = ReferenceType.objects.get(name="StainingTechniques")
        staining_techniques = RefValues.objects.filter(reftype_id_id=reftype.reference_type_id).values('value',
                                                                                                       'display_value')
        return JsonResponse({"staining_techniques": list(staining_techniques)})
    except ReferenceType.DoesNotExist:
        return JsonResponse({"staining_techniques": []})
