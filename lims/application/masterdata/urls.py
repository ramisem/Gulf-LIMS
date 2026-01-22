from django.urls import path
from masterdata.ajax import ajax

app_name = 'masterdata'


class URLS:
    urlpatterns = [
        path('ajax/get_physician_details_by_physician/', ajax.get_physician_details_by_physician,
             name='ajax_get_physician_details_by_physician'),
        path('ajax/get-sub-sites/', ajax.get_sub_sites, name='ajax_get_sub_sites'),
        path(
            'ajax/get_tests_based_on_bodysite_and_sample/',
            ajax.get_tests_based_on_bodysite_and_sample,
            name='ajax_get_tests_based_on_bodysite_and_sample'
        ),
        path('ajax/get_projects_by_sponsor/', ajax.get_projects_by_sponsor,
             name='ajax_get_projects_by_sponsor'),
        path('ajax/push_to_qc/', ajax.push_to_qc_ajax, name='push_to_qc_ajax'),
        path('ajax/ajax_perform_qc/', ajax.ajax_perform_qc, name='ajax_perform_qc'),
    ]
