from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from process.models import SampleTypeContainerType, ContainerType
from sample.models import SampleTestMap
from tests.models import TestWorkflowStep, Test, Analyte
from workflows.models import WorkflowStep
from masterdata.models import BodySubSiteMap
from django.conf import settings


def get_steps(request):
    workflow_id = request.GET.get('workflow_id')
    if workflow_id:
        steps = WorkflowStep.objects.filter(workflow_id=workflow_id).values('workflow_step_id', 'step_id')
        return JsonResponse(list(steps), safe=False)
    return JsonResponse([], safe=False)


def get_step_no(request):
    step_id = request.GET.get('step_id')
    if step_id:
        steps = WorkflowStep.objects.filter(workflow_step_id=step_id).values('step_no')
        return JsonResponse(list(steps), safe=False)
    return JsonResponse([], safe=False)


def get_analyte_unit_by_analyte_id(request):
    analyte_id = request.GET.get('analyte_id')
    if not analyte_id:
        return JsonResponse({'error': 'Missing analyte_id'}, status=400)

    analyte = get_object_or_404(Analyte, pk=analyte_id)
    unit_obj = analyte.unit_id  # ← your FK
    unit_name = unit_obj.unit if unit_obj else ''

    return JsonResponse({'unit': unit_name})


def get_workflow_type(request):
    step_id = request.GET.get('step_id')
    if step_id:
        workflow_types = WorkflowStep.objects.filter(workflow_step_id=step_id).values('workflow_type')
        return JsonResponse(list(workflow_types), safe=False)
    return JsonResponse([], safe=False)


def get_container_type_id(request):
    sample_type_id = request.GET.get('sampletype_id')
    print(sample_type_id, "Sample Type ID from Script")
    if sample_type_id:
        container_types = SampleTypeContainerType.objects.filter(sample_type_id=sample_type_id).values(
            'container_type_id')

        print(container_types, "Container Types")
        response_data = [
            {
                'value': str(ct['container_type_id']),  # Since TestWorkflowStep stores it as a CharField
                'label': str(ContainerType.objects.get(pk=ct['container_type_id']))  # Display value
            }
            for ct in container_types if ct['container_type_id']  # Ensure non-null values
        ]
        print(str(response_data), "Response Data ")

        return JsonResponse(response_data, safe=False)

    return JsonResponse([], safe=False)


def get_test_workflow_steps(request):
    test_id = request.GET.get('test_id')
    print(str(test_id))
    if test_id:
        steps = TestWorkflowStep.objects.filter(test_id=test_id).values('test_workflow_step_id',
                                                                        'workflow_id__workflow_name',
                                                                        'workflow_step_id__step_id',
                                                                        'sample_type_id__sample_type',
                                                                        'container_type__container_type')
        print("get_test_workflow_steps : " + str(steps))
        return JsonResponse(list(steps), safe=False)
    return JsonResponse([], safe=False)


def get_model_fields(request):
    model_name = request.GET.get('model')
    if not model_name:
        return JsonResponse({'error': 'No model name provided'}, status=400)

        # Fetch all models across all installed apps
    all_models = {model.__name__: model for model in apps.get_models()}

    # Find the model class by name (independent of app)
    model_class = all_models.get(model_name)
    if not model_class:
        return JsonResponse({'error': 'Invalid model name'}, status=400)

    # Extract database fields
    field_choices = [
        {'value': field.name, 'display': field.name}
        for field in model_class._meta.get_fields() if hasattr(field, 'attname')
    ]

    return JsonResponse({'field_choices': field_choices})


def get_test_by_test_name(request):
    gulf_test_name = getattr(settings, "TEST_ID_GULF", "GulfTest")
    test = request.GET.get("term", "")
    sample_id = request.GET.get("sample_id", "")
    listexistingtests = SampleTestMap.objects.filter(sample_id=sample_id)
    results = (
        Test.objects
        .filter(test_name__icontains=test)
        .exclude(test_name__iexact=gulf_test_name)
        .values("test_id", "test_name")
    )
    if listexistingtests is not None and len(listexistingtests) > 0:
        for objtest in results:
            test_id = objtest["test_id"]
            for existing_sample_test_obj in listexistingtests:
                if existing_sample_test_obj is not None:
                    if existing_sample_test_obj.test_id_id == test_id:
                        test_name = objtest["test_name"] + "|" + "Y"
                        objtest["test_name"] = test_name
                        break
    return JsonResponse({"results": list(results)})


def get_subsites_by_bodysite(request):
    """
    Returns SubSites based on selected BodySite
    """
    body_site_id = request.GET.get('body_site_id')
    if body_site_id:
        subsites = BodySubSiteMap.objects.filter(body_site_id=body_site_id).values(
            'body_subsite_id', 'sub_site'
        )
        return JsonResponse(list(subsites), safe=False)
    return JsonResponse([], safe=False)
