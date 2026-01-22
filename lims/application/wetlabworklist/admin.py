from accessioning.models import Accession, BioPharmaAccession
from util.admin import TZIndependentAdmin
from django.urls import reverse
from django.utils.html import format_html
from controllerapp.views import controller
from .models import AccessionSampleWrapper, AccessionIHCWrapper


def make_patient_field(field_name, label=None):
    def accessor(self, obj):
        patient = getattr(obj, 'patient_id', None)
        return getattr(patient, field_name, "-") if patient else "-"

    accessor.__name__ = f'patient_{field_name}'
    accessor.short_description = label or field_name.replace('_', ' ').title()
    accessor.admin_order_field = f'patient_id__{field_name}'
    return accessor


class AccessionSampleWrapperAdmin(TZIndependentAdmin):
    list_display = ('accession_link',
                    'patient_name',
                    'patient_mrn',
                    'patient_dob',
                    'patient_ssn',
                    'status',
                    'order_dt',
                    'submitter',
                    'sponsor_name',
                    'project_name',
                    'investigator_name',
                    'visit_name',
                    'subject_id')
    list_filter = ['accession_id']

    class Media:
        js = (
            'scanner/generic_scanner.js',  # Core scanner
            'scanner/sample_scanner.js',  # Sample configuration
        )

    def get_queryset(self, request):
        from sample.models import Sample
        from sample.admin import SampleAdmin

        sample_admin = SampleAdmin(Sample, self.admin_site)
        sample_qs = sample_admin.get_queryset(request)
        accession_ids = sample_qs.values_list('accession_id', flat=True).distinct()
        return Accession.objects.filter(accession_id__in=accession_ids)

    def accession_link(self, obj):
        url = reverse('controllerapp:sample_sample_changelist') + f'?q={obj.accession_id}'
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.accession_id)

    def patient_name(self, obj):
        return obj.patient_id

    def order_dt(self, obj):
        return obj.created_dt

    def submitter(self, obj):
        user = obj.created_by
        if user:
            if user.first_name:
                full_name = f"{user.first_name} {user.last_name or ''}".strip()
                return full_name
            return user.username
        return "-"

    def sponsor_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.sponsor:
            return bio_acc.sponsor.sponsor_name
        return "-"

    def project_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.project:
            return bio_acc.project.project_protocol_id
        return "-"

    def investigator_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.investigator:
            return bio_acc.investigator.investigator_name
        return "-"

    def visit_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.visit:
            return bio_acc.visit.visit_id
        return "-"

    def subject_id(self, obj):
        patient = obj.patient_id
        if patient and hasattr(patient, 'subject'):
            return patient.subject.subject_id
        return "-"

    accession_link.short_description = "Case Number"
    accession_link.admin_order_field = 'accession_id'
    patient_mrn = make_patient_field('mrn', 'Patient ID')
    patient_ssn = make_patient_field('ssn', 'External PatientID')
    patient_dob = make_patient_field('birth_dt', 'DOB')
    patient_name.short_description = "Name"
    patient_name.admin_order_field = 'patient_id'
    order_dt.short_description = "Order Date"
    order_dt.admin_order_field = "created_dt"
    submitter.short_description = "Submitter"
    submitter.admin_order_field = "created_by"
    sponsor_name.short_description = "Sponsor"
    sponsor_name.admin_order_field = "accession_id"
    project_name.short_description = "Project"
    project_name.admin_order_field = "accession_id"
    investigator_name.short_description = "Investigator"
    investigator_name.admin_order_field = "accession_id"
    visit_name.short_description = "Visit"
    visit_name.admin_order_field = "accession_id"
    subject_id.short_description = "Subject ID"
    subject_id.admin_order_field = "accession_id"


class AccessionIHCWrapperAdmin(TZIndependentAdmin):
    list_display = ('accession_link',
                    'patient_name',
                    'patient_mrn',
                    'patient_dob',
                    'patient_ssn',
                    'status',
                    'order_dt',
                    'submitter',
                    'sponsor_name',
                    'project_name',
                    'investigator_name',
                    'visit_name',
                    'subject_id')
    list_filter = ['accession_id']

    class Media:
        js = (
            'scanner/generic_scanner.js',  # Core scanner
            'scanner/sample_scanner.js',  # Sample configuration
        )

    def get_queryset(self, request):
        from sample.models import Sample
        from ihcworkflow.models import IhcWorkflow
        from ihcworkflow.admin import IhcWorkflowAdmin

        ihc_admin = IhcWorkflowAdmin(IhcWorkflow, self.admin_site)
        ihc_qs = ihc_admin.get_queryset(request)
        ihc_sample_ids = ihc_qs.values_list('sample_ptr_id', flat=True)

        accession_ids = Sample.objects.filter(
            sample_id__in=ihc_sample_ids
        ).values_list('accession_id', flat=True).distinct()

        return Accession.objects.filter(accession_id__in=accession_ids)

    def accession_link(self, obj):
        url = reverse('controllerapp:ihcworkflow_ihcworkflow_changelist') + f'?q={obj.accession_id}'
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.accession_id)

    def patient_name(self, obj):
        return obj.patient_id

    def order_dt(self, obj):
        return obj.created_dt

    def submitter(self, obj):
        user = obj.created_by
        if user:
            if user.first_name:
                full_name = f"{user.first_name} {user.last_name or ''}".strip()
                return full_name
            return user.username
        return "-"

    def sponsor_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.sponsor:
            return bio_acc.sponsor.sponsor_name
        return "-"

    def project_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.project:
            return bio_acc.project.project_protocol_id
        return "-"

    def investigator_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.investigator:
            return bio_acc.investigator.investigator_name
        return "-"

    def visit_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.accession_id).first()
        if bio_acc and bio_acc.visit:
            return bio_acc.visit.visit_id
        return "-"

    def subject_id(self, obj):
        patient = obj.patient_id
        if patient and hasattr(patient, 'subject'):
            return patient.subject.subject_id
        return "-"

    accession_link.short_description = "Case Number"
    accession_link.admin_order_field = 'accession_id'
    patient_mrn = make_patient_field('mrn', 'Patient ID')
    patient_ssn = make_patient_field('ssn', 'External PatientID')
    patient_dob = make_patient_field('birth_dt', 'DOB')
    patient_name.short_description = "Name"
    patient_name.admin_order_field = 'patient_id'
    order_dt.short_description = "Order Date"
    order_dt.admin_order_field = "created_dt"
    submitter.short_description = "Submitter"
    submitter.admin_order_field = "created_by"
    sponsor_name.short_description = "Sponsor"
    sponsor_name.admin_order_field = "accession_id"
    project_name.short_description = "Project"
    project_name.admin_order_field = "accession_id"
    investigator_name.short_description = "Investigator"
    investigator_name.admin_order_field = "accession_id"
    visit_name.short_description = "Visit"
    visit_name.admin_order_field = "accession_id"
    subject_id.short_description = "Subject ID"
    subject_id.admin_order_field = "accession_id"



controller.register(AccessionSampleWrapper, AccessionSampleWrapperAdmin)
controller.register(AccessionIHCWrapper, AccessionIHCWrapperAdmin)
