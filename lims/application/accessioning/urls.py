from django.urls import path
from accessioning.ajax import ajax

app_name = 'accessioning'


class URLS:
    urlpatterns = [
        path('ajax/get_insurance_by_patient/', ajax.get_insurance_by_patient,
             name='ajax_get_insurance_by_patient'),
        path('ajax/get_patient_details_by_patient/', ajax.get_patient_details_by_patient,
             name='ajax_get_patient_details_by_patient'),
        path('ajax/get_insurance_details_by_insurance_id/', ajax.get_insurance_details_by_insurance_id,
             name='ajax_get_insurance_details_by_insurance_id'),
        path('ajax/get_internal_external_doctors/', ajax.get_internal_external_doctors,
             name='ajax_get_internal_external_doctors'),
        path('ajax/get_client_details_by_client/', ajax.get_client_details_by_client,
             name='ajax_get_client_details_by_client'),
        path('ajax/get_containertype_by_sampletype/', ajax.get_containertype_by_sampletype,
             name='ajax_get_containertype_by_sampletype'),
        path('ajax/createSample/', ajax.createSample, name="ajax_create_sample"),
        path('ajax/get_doctors_by_client/', ajax.get_doctors_by_client, name="ajax_get_doctors_by_client"),
        path('ajax/get_details_by_icdcode/', ajax.get_details_by_icdcode, name="ajax_get_details_by_icdcode"),
        path('ajax/get_containerdetails_by_containertype/', ajax.get_containerdetails_by_containertype,
             name='ajax_get_containerdetails_by_containertype'),
        path('ajax/get_parent_seq/', ajax.get_parent_seq,
             name="ajax_get_parent_seq"),
        path('ajax/get_samples_created/', ajax.get_samples_created, name="ajax_get_samples_created"),
        path('ajax/get_reportingtype_by_accessiontype/', ajax.get_reportingtype_by_accessiontype,
             name="ajax_get_reportingtype_by_accessiontype"),
        path('ajax/get_sponsor_details_by_sponsor/', ajax.get_sponsor_details_by_sponsor,
             name='ajax_get_sponsor_details_by_sponsor'),
        path('ajax/get_projects_by_sponsor/', ajax.get_projects_by_sponsor,
             name='ajax_get_projects_by_sponsor'),
        path('ajax/get_visits_by_project/', ajax.get_visits_by_project,
             name='ajax_get_visits_by_project'),
        path('ajax/get_investigators_by_project/', ajax.get_investigators_by_project,
             name='ajax_get_investigators_by_project'),
        path('ajax/get_project_field_demographics/', ajax.get_project_field_demographics,
             name='ajax_get_project_field_demographics'),
        path('ajax/get_physicians_by_project/', ajax.get_physicians_by_project,
             name='ajax_get_physicians_by_project'),
        path('ajax/upload_scanned_images/', ajax.upload_scanned_images,
             name='ajax_upload_scanned_images'),

    ]
