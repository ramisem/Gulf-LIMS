from django.urls import path

from tests.ajax.ajax import get_steps, get_step_no, get_container_type_id, get_workflow_type, get_test_workflow_steps, \
    get_model_fields, get_test_by_test_name, get_analyte_unit_by_analyte_id

app_name = 'tests'


class URLS:
    urlpatterns = [
        path('ajax/get-steps/', get_steps,
             name='admin_get_steps'),

        path('ajax/get-step-no/', get_step_no,
             name='admin_get_step_no'),

        path('ajax/get-workflow-type/', get_workflow_type,
             name='admin_get_workflow_type'),

        path('ajax/get-container-type-id/', get_container_type_id,
             name='admin_get-container-type'),

        path('ajax/get-test-workflow-steps/', get_test_workflow_steps,
             name='admin_get_test_workflow_steps'),

        path('ajax/get-model-fields/', get_model_fields,
             name='admin_get_model_fields'),

        path('ajax/get_test_by_test_name/', get_test_by_test_name,
             name='get_test_by_test_name'),

        path('ajax/get_analyte_unit_by_analyte_id/', get_analyte_unit_by_analyte_id,
             name='get_analyte_unit_by_analyte_id'),

    ]
