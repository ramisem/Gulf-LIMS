from django.http import JsonResponse
from sample.models import Sample, SampleTestMap
from sample.util import SampleUtilClass
from template.models import GrossCodeTemplate


def get_unique_partno(request):
    part_no = request.GET.get("term", "")
    accessionid = request.GET.get("accessionid", "")
    list_partno = []
    distinct_partno = []
    if part_no is not None and accessionid is not None:
        list_partno = Sample.objects.filter(part_no__icontains=part_no, accession_id=accessionid).values(
            "part_no")
        for item in list_partno:
            if item not in distinct_partno:
                distinct_partno.append(item)

    return JsonResponse({"results": list(distinct_partno)})


def update_test_in_sample_test_map(request):
    if request.method == "POST":
        obj_id = request.POST.get("id")
        field = request.POST.get("field")
        value = request.POST.get("value")
        try:
            obj_sampletestmap = SampleTestMap.objects.filter(sample_id_id=obj_id, test_id_id=value)
            if obj_sampletestmap is not None and len(obj_sampletestmap) > 0:
                obj_sampletestmap.delete()
                return JsonResponse({"status": "success", "message": "Test deleted successfully"})
            else:
                obj_sample = Sample.objects.get(sample_id=obj_id)
                if obj_sample is not None:
                    obj_sampletestmap = SampleTestMap.objects.filter(sample_id_id=obj_id)
                    if obj_sampletestmap is not None and len(
                            obj_sampletestmap) > 0 and True != obj_sample.container_type.child_sample_creation:
                        return JsonResponse(
                            {"status": "error", "message": "Multiple testcodes could not be associated to this sample"})
                    list_sample = []
                    list_sample.append(obj_sample)
                    SampleUtilClass.associateTest(value, obj_sample.sample_type_id, obj_sample.container_type_id,
                                                  list_sample, obj_sample.accession_id.accession_type)

                return JsonResponse({"status": "success", "message": "Test added successfully"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


def get_gross_description(request):
    gross_code = request.GET.get('gross_code')
    try:
        template = GrossCodeTemplate.objects.get(gross_code=gross_code)
        return JsonResponse({'description': template.gross_description})
    except GrossCodeTemplate.DoesNotExist:
        return JsonResponse({'description': ''})
