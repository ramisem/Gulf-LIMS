from django.urls import path
from sample.ajax import ajax
from sample.views import SampleRouteView, admin_scan_submit, admin_scan_validate

app_name = 'sample'


class URLS:
    urlpatterns = [
        path('ajax/update_test_in_sample_test_map/', ajax.update_test_in_sample_test_map,
             name="ajax_update_test_in_sample_test_map"),
        path('ajax/get_unique_partno/', ajax.get_unique_partno,
             name="ajax_get_unique_partno"),
        path('route_samples/', SampleRouteView.as_view(), name='sample_route'),
        path('ajax/gross-description/', ajax.get_gross_description, name='ajax_get_gross_description'),
        path("admin/scan-submit/", admin_scan_submit, name="admin_scan_submit"),
        path("admin/scan-validate/", admin_scan_validate, name="admin_scan_validate"),
    ]
