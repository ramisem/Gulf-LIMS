from django.db.models import Q
from django.http import JsonResponse

from reporting.models import Printer
from security.models import JobType, DepartmentPrinter
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt


def load_job_types_by_site(request):
    site_id = request.GET.get('site_id')
    job_types = JobType.objects.filter(
        Q(departmentid__siteid__name=site_id) | Q(site_independent=True)
    ).order_by('name').distinct()
    job_types = job_types.values('name', 'name')
    return JsonResponse(list(job_types), safe=False)


def get_printer_path(request):
    printer_id = request.GET.get('printer_id')
    if printer_id:
        printer = Printer.objects.filter(printer_id=printer_id).values('printer_id', 'printer_path')
        return JsonResponse(list(printer), safe=False)
    return JsonResponse([], safe=False)


def get_printers_by_jobtype(request):
    jobtype_id = request.GET.get('jobtype_id')
    printers = []
    if jobtype_id:
        department_printers = DepartmentPrinter.objects.filter(jobtype_id=jobtype_id).select_related('printer_id')
        for dp in department_printers:
            printers.append({'id': dp.printer_id.printer_id, 'name': dp.printer_id.printer_name})
    return JsonResponse(dict((printer['id'], printer['name']) for printer in printers))


# This is for authenticating the user via AJAX call
@csrf_exempt
def ajax_authenticate_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            return JsonResponse({'success': True, 'message': 'Authentication successful'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid credentials'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})
