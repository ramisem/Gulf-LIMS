from django.urls import path
from security.ajax.ajax import get_printer_path, get_printers_by_jobtype, ajax_authenticate_user

app_name = 'security'


class URLS:
    urlpatterns = [
        path('ajax/get_printer_path/', get_printer_path,
             name='admin_get_printer_path'),
        path('ajax/get_printers_by_jobtype/', get_printers_by_jobtype,
             name='admin_get_printer_path'),
        path('ajax/ajax_authenticate_user/', ajax_authenticate_user,
             name='ajax_authenticate_user'),
    ]
