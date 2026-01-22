from django.contrib import admin

from accessioning.models import Accession, BioPharmaAccession
from analysis.models import MergeReporting
from util.admin import TZIndependentAdmin
from django.urls import reverse, path
from django.utils.html import format_html
from controllerapp.views import controller
from .models import AccessionReportsWrapper, AccessionHistoricalReportsWrapper, AttachmentMergeReport
from util.util import UtilClass as GenericUtilClass


class AccessionReportsWrapperAdmin(TZIndependentAdmin):
    list_display = ('accession_link',
                    'date_received',
                    'case_status',
                    'date_collected',
                    'patient_id',
                    'doctor_name',
                    'reviewed_by',
                    'pathologist_name',
                    'sponsor_name',
                    'project_name',
                    'investigator_name',
                    'visit_name',
                    'subject_id')
    list_filter = ['accession_id']

    def get_queryset(self, request):
        from analysis.models import ReportOption
        from analysis.admin import ReportOptionAdmin

        reportoption_admin = ReportOptionAdmin(ReportOption, self.admin_site)
        reportoption_qs = reportoption_admin.get_queryset(request)
        accession_ids = reportoption_qs.values_list('accession_id', flat=True).distinct()
        return Accession.objects.filter(accession_id__in=accession_ids)

    def accession_link(self, obj):
        url = reverse('controllerapp:analysis_reportoption_changelist') + f'?q={obj.accession_id}'
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.accession_id)

    def date_received(self, obj):
        return obj.receive_dt

    def date_collected(self, obj):
        return obj.collection_dt

    def case_status(self, obj):
        return obj.status

    def doctor_name(self, obj):
        physician = obj.doctor
        if physician:
            full_name = f"{physician.first_name} {physician.last_name or ''}".strip()
            return full_name
        return "-"

    def pathologist_name(self, obj):
        merge = MergeReporting.objects.filter(accession_id=obj.accession_id).order_by('-mod_dt').first()
        if merge and merge.assign_pathologist:
            user = merge.assign_pathologist
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
        return "-"

    def reviewed_by(self, obj):
        merge = MergeReporting.objects.filter(accession_id=obj.accession_id).order_by('-last_signed_dt').first()
        if merge and merge.last_signed_by:
            user = merge.last_signed_by
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
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
    date_received.short_description = "Date Received"
    date_received.admin_order_field = "receive_dt"
    case_status.short_description = "Case Status"
    case_status.admin_order_field = "status"
    date_collected.short_description = "Date Collected"
    date_collected.admin_order_field = "collection_dt"
    doctor_name.short_description = "Physician"
    doctor_name.admin_order_field = "doctor_id"
    pathologist_name.short_description = "Pathologist"
    pathologist_name.admin_order_field = "accession_id"
    reviewed_by.short_description = "Reviewed By"
    reviewed_by.admin_order_field = "accession_id"
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


class AccessionHistoricalReportsWrapperAdmin(TZIndependentAdmin):
    list_display = ('accession_link',
                    'date_received',
                    'case_status',
                    'date_collected',
                    'patient_id',
                    'doctor_name',
                    'reviewed_by',
                    'pathologist_name',
                    'sponsor_name',
                    'project_name',
                    'investigator_name',
                    'visit_name',
                    'subject_id')
    list_filter = ['accession_id']

    def get_queryset(self, request):
        from analysis.models import ReportOption
        from analysis.admin import HistoricalReportOptionAdmin

        reportoption_admin = HistoricalReportOptionAdmin(ReportOption, self.admin_site)
        reportoption_qs = reportoption_admin.get_queryset(request)
        accession_ids = reportoption_qs.values_list('accession_id', flat=True).distinct()
        return Accession.objects.filter(accession_id__in=accession_ids)

    def accession_link(self, obj):
        url = reverse('controllerapp:analysis_historicalreportoption_changelist') + f'?q={obj.accession_id}'
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.accession_id)

    def date_received(self, obj):
        return obj.receive_dt

    def date_collected(self, obj):
        return obj.collection_dt

    def case_status(self, obj):
        return obj.status

    def doctor_name(self, obj):
        physician = obj.doctor
        if physician:
            full_name = f"{physician.first_name} {physician.last_name or ''}".strip()
            return full_name
        return "-"

    def pathologist_name(self, obj):
        merge = MergeReporting.objects.filter(accession_id=obj.accession_id).order_by('-mod_dt').first()
        if merge and merge.assign_pathologist:
            user = merge.assign_pathologist
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
        return "-"

    def reviewed_by(self, obj):
        merge = MergeReporting.objects.filter(accession_id=obj.accession_id).order_by('-last_signed_dt').first()
        if merge and merge.last_signed_by:
            user = merge.last_signed_by
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
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
    date_received.short_description = "Date Received"
    date_received.admin_order_field = "receive_dt"
    case_status.short_description = "Case Status"
    case_status.admin_order_field = "status"
    date_collected.short_description = "Date Collected"
    date_collected.admin_order_field = "collection_dt"
    doctor_name.short_description = "Physician"
    doctor_name.admin_order_field = "doctor_id"
    pathologist_name.short_description = "Pathologist"
    pathologist_name.admin_order_field = "accession_id"
    reviewed_by.short_description = "Reviewed By"
    reviewed_by.admin_order_field = "accession_id"
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


class AttachmentAdmin(TZIndependentAdmin):
    list_display = (
        "get_accession_id",
        "version_id",
        "date_received",
        "case_status",
        "date_collected",
        "patient_id",
        "doctor_name",
        "reviewed_by",
        "pathologist_name",
        "merge_reporting_id",
        'sponsor_name',
        'project_name',
        'investigator_name',
        'visit_name',
        'subject_id',
        "download_link",

    )
    list_display_links = None

    list_filter = [
        'merge_reporting_id__accession_id__accession_id',
    ]
    date_hierarchy = 'created_dt'
    change_form_template = 'admin/sample_change_form.html'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(merge_reporting_id__isnull=False).select_related('merge_reporting_id__accession_id') \
            .order_by('merge_reporting_id__accession_id', '-version_id')

    @admin.display(description="Case Number", ordering='merge_reporting_id__accession_id')
    def get_accession_id(self, obj):
        return obj.merge_reporting_id.accession_id.accession_id if obj.merge_reporting_id else None

    @admin.display(description="Date Received", ordering='merge_reporting_id__accession_id__receive_dt')
    def date_received(self, obj):
        return obj.merge_reporting_id.accession_id.receive_dt if obj.merge_reporting_id else None

    @admin.display(description="Date Collected", ordering='merge_reporting_id__accession_id__collection_dt')
    def date_collected(self, obj):
        return obj.merge_reporting_id.accession_id.collection_dt if obj.merge_reporting_id else None

    @admin.display(description="Case Status", ordering='merge_reporting_id__accession_id__status')
    def case_status(self, obj):
        return obj.merge_reporting_id.accession_id.status if obj.merge_reporting_id else None

    @admin.display(description="Patient ID", ordering='merge_reporting_id__accession_id__patient_id')
    def patient_id(self, obj):
        return obj.merge_reporting_id.accession_id.patient_id if obj.merge_reporting_id else None

    @admin.display(description="Doctor Name", ordering='merge_reporting_id__accession_id__reporting_doctor_id')
    def doctor_name(self, obj):
        physician = obj.merge_reporting_id.accession_id.reporting_doctor if obj.merge_reporting_id else None
        if physician:
            return f"{physician.first_name} {physician.last_name or ''}".strip()
        return "-"

    @admin.display(description="Pathologist", ordering='merge_reporting_id__assign_pathologist')
    def pathologist_name(self, obj):
        user = obj.merge_reporting_id.assign_pathologist if obj.merge_reporting_id else None
        if user:
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
        return "-"

    @admin.display(description="Reviewed By", ordering='merge_reporting_id__last_signed_by')
    def reviewed_by(self, obj):
        user = obj.merge_reporting_id.last_signed_by if obj.merge_reporting_id else None
        if user:
            return f"{user.first_name} {user.last_name or ''}".strip() or user.username
        return "-"

    @admin.display(description="Sponsor", ordering='merge_reporting_id__accession_id')
    def sponsor_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.merge_reporting_id.accession_id).first()
        if bio_acc and bio_acc.sponsor:
            return bio_acc.sponsor.sponsor_name
        return "-"

    @admin.display(description="Project", ordering='merge_reporting_id__accession_id')
    def project_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.merge_reporting_id.accession_id).first()
        if bio_acc and bio_acc.project:
            return bio_acc.project.project_protocol_id
        return "-"

    @admin.display(description="Investigator", ordering='merge_reporting_id__accession_id')
    def investigator_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.merge_reporting_id.accession_id).first()
        if bio_acc and bio_acc.investigator:
            return bio_acc.investigator.investigator_name
        return "-"

    @admin.display(description="Visit", ordering='merge_reporting_id__accession_id')
    def visit_name(self, obj):
        bio_acc = BioPharmaAccession.objects.filter(accession_id=obj.merge_reporting_id.accession_id).first()
        if bio_acc and bio_acc.visit:
            return bio_acc.visit.visit_id
        return "-"

    @admin.display(description="Subject ID", ordering='merge_reporting_id__accession_id')
    def subject_id(self, obj):
        patient = obj.merge_reporting_id.accession_id.patient_id
        if patient and hasattr(patient, 'subject'):
            return patient.subject.subject_id
        return "-"

    @admin.display(description="Download")
    def download_link(self, obj):
        if obj.pk and obj.file_path:
            url = reverse(f'{self.admin_site.name}:download_attachment', args=[obj.pk])
            return format_html(
                '<a href="{}" title="Download file" target="_blank">'
                '<img src="/static/assets/imgs/download_icon.png" alt="Download" width="20" height="20">'
                '</a>', url
            )
        return "-"

    download_link.admin_order_field = 'attachment_id'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'download_attachment/<int:attachment_id>/',
                self.admin_site.admin_view(GenericUtilClass.download_attachment),
                name='download_attachment',
            ),
        ]
        return custom_urls + urls


controller.register(AccessionReportsWrapper, AccessionReportsWrapperAdmin)
controller.register(AccessionHistoricalReportsWrapper, AccessionHistoricalReportsWrapperAdmin)
controller.register(AttachmentMergeReport, AttachmentAdmin)
