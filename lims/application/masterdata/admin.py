import copy
import os

from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils.html import format_html
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats
from django.utils import timezone

from accessioning.models import BioPharmaAccession
from analysis.forms import AttachmentInlineForm, NoLinkFileWidget
from analysis.models import Attachment
from controllerapp.views import controller
from masterdata.models import Client, Patient, Subject, Physician, PatientInsuranceInfo, ClientDoctorInfo, \
    AccessionType, \
    BodySubSiteMap, BodySite, ReportImgPropInfo, AttachmentConfiguration, Sponsor, BioProject, BioSite, ProjectVisitMap, \
    ProjectTestMap, ProjectEmailMap, QCPendingBioProject, EmailConfig, Subject, BodySiteTestMap, AccessionPrefix, \
    ProjectFieldsMap, DemographicFields, ProjectPhysicianMap

from masterdata.resources import AccessionTypeResource, BodySiteResource, ReportImgPropInfoResource, PatientResource, \
    PhysicianResource, ClientResource, SponsorResource, AttachmentConfigurationResource
from security.models import User
from .forms import ClientDoctorInfoForm, PatientForm, ClientForm, PhysicianForm, BodySiteForm, BodySubSiteMapForm, \
    ReportImgPropInfoForm, AttachmentConfigurationForm, BioProjectForm, ProjectVisitMapForm, ProjectEmailMapForm, \
    SponsorForm, BioSiteForm, QCPendingBioProjectForm, EmailConfigForm, ProjectPhysicianMapForm, DemographicFieldsForm
from util.util import UtilClass as GenericUtilClass

from tests.models import Test
from util.admin import GulfModelAdmin
from django import forms
from django.core.exceptions import ValidationError


# Register your models here.
class ClientDoctorInfoInline(admin.StackedInline):
    model = ClientDoctorInfo
    form = ClientDoctorInfoForm
    fields = (
        "physician_id",
        "phone_number",
        "fax_number",
        "email",
    )
    extra = 0

    class Media:
        js = ('js/masterdata/masterdata.js', 'js/util/util.js')


class ClientAttachmentInline(admin.TabularInline):
    model = Attachment
    form = AttachmentInlineForm
    fields = (
        "file_path_display",
        "file_path",
        "attachment_type",
        "download_link",
    )
    readonly_fields = ("file_path_display", "download_link",)
    extra = 0

    def file_path_display(self, obj):
        if obj.file_path:
            return os.path.basename(obj.file_path.name)
        return "-"

    file_path_display.short_description = "File Path"

    def download_link(self, obj):
        if obj.pk and obj.file_path:
            url = reverse(f'{self.admin_site.name}:client_download_attachment', args=[obj.pk])
            return format_html(
                '<a href="{}" title="Download file" target="_blank">'
                '<img src="/static/assets/imgs/download_icon.png" alt="Download" width="20" height="20">'
                '</a>', url
            )

        return "-"

    download_link.short_description = "Download"

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        base_form = formset.form

        class CustomForm(base_form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['file_path'].widget = NoLinkFileWidget()

        formset.form = CustomForm
        return formset


class ClientAdmin(ImportExportActionModelAdmin):
    form = ClientForm
    search_fields = ("name",)
    ordering = ("name",)
    list_display = ('name',
                    'created_dt',
                    'created_by',
                    'address1',
                    'address2',
                    'city',
                    'state',
                    'postalcode',
                    'country',
                    'telephone',
                    'fax_number',
                    'primaryemail'
                    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "address1",
                    "address2",
                    "city",
                    'state',
                    'postalcode',
                    'country',
                    'telephone',
                    'fax_number',
                    'primaryemail'
                ),
            },
        ),
    )
    inlines = [ClientDoctorInfoInline, ClientAttachmentInline]
    resource_classes = [ClientResource]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'client_download_attachment/<int:attachment_id>/',
                self.admin_site.admin_view(GenericUtilClass.download_attachment),
                name='client_download_attachment',
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
        return

    def save_formset(self, request, form, formset, change):
        if formset.model == Attachment:
            instances = formset.save(commit=False)

            for form_instance in formset.forms:
                obj = form_instance.instance

                if isinstance(obj, Attachment):
                    if not obj.pk and not obj.created_by_id:
                        obj.created_by = request.user
                    obj.mod_by = request.user

                    uploaded_file = form_instance.cleaned_data.get('file_path')

                    if uploaded_file and hasattr(uploaded_file, 'content_type'):
                        s3_key = GenericUtilClass.upload_attachment_to_s3(obj, uploaded_file)

                        obj.file_path = None  # Prevent actual file save
                        obj.file_path.name = s3_key  # Store S3 key manually

                        form_instance.cleaned_data['file_path'] = None
                        if 'file_path' in form_instance.files:
                            del form_instance.files['file_path']

                obj.save()

            formset.save_m2m()
            formset.save()
        else:
            formset.save()


class PhysicianAttachmentInline(admin.TabularInline):
    model = Attachment
    form = AttachmentInlineForm
    fields = (
        "file_path_display",
        "file_path",
        "attachment_type",
        "download_link",
    )
    readonly_fields = ("file_path_display", "download_link",)
    extra = 0

    def file_path_display(self, obj):
        if obj.file_path:
            return os.path.basename(obj.file_path.name)
        return "-"

    file_path_display.short_description = "File Path"

    def download_link(self, obj):
        if obj.pk and obj.file_path:
            url = reverse(f'{self.admin_site.name}:physician_download_attachment', args=[obj.pk])
            return format_html(
                '<a href="{}" title="Download file" target="_blank">'
                '<img src="/static/assets/imgs/download_icon.png" alt="Download" width="20" height="20">'
                '</a>', url
            )

        return "-"

    download_link.short_description = "Download"

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        base_form = formset.form

        class CustomForm(base_form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['file_path'].widget = NoLinkFileWidget()

        formset.form = CustomForm
        return formset


class PhysicianAdmin(ImportExportActionModelAdmin):
    form = PhysicianForm
    search_fields = ("first_name",)
    ordering = ("first_name",)
    fieldsets = (
        (
            'Demographics',
            {
                "fields": (
                    "user_id",
                    "first_name",
                    "last_name",
                    "external",
                    "category",
                ),
            },
        ),

        (
            'Phone And Email',
            {
                "fields": (
                    "phone_number",
                    "fax_number",
                    "email",
                ),
            },
        ),

    )
    list_display = (
        'user_id',
        'first_name',
        'last_name',
        'category',
        'created_dt',
        'created_by',
        'phone_number',
        'fax_number',
        'email',
        'external',
    )
    inlines = [PhysicianAttachmentInline]
    resource_classes = [PhysicianResource]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'physician_download_attachment/<int:attachment_id>/',
                self.admin_site.admin_view(GenericUtilClass.download_attachment),
                name='physician_download_attachment',
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
        return

    def save_formset(self, request, form, formset, change):
        if formset.model == Attachment:
            instances = formset.save(commit=False)

            for form_instance in formset.forms:
                obj = form_instance.instance

                if isinstance(obj, Attachment):
                    if not obj.pk and not obj.created_by_id:
                        obj.created_by = request.user
                    obj.mod_by = request.user

                    uploaded_file = form_instance.cleaned_data.get('file_path')

                    if uploaded_file and hasattr(uploaded_file, 'content_type'):
                        s3_key = GenericUtilClass.upload_attachment_to_s3(obj, uploaded_file)

                        obj.file_path = None  # Prevent actual file save
                        obj.file_path.name = s3_key  # Store S3 key manually

                        form_instance.cleaned_data['file_path'] = None
                        if 'file_path' in form_instance.files:
                            del form_instance.files['file_path']

                obj.save()

            formset.save_m2m()
            formset.save()
        else:
            formset.save()


class PatientInsuranceInfoInline(admin.TabularInline):
    model = PatientInsuranceInfo
    fields = (
        "insurance",
        "group",
        "policy"

    )
    extra = 0


class PatientAdmin(ImportExportActionModelAdmin):
    form = PatientForm
    search_fields = ("first_name",)
    ordering = ("first_name",)
    fieldsets = (
        (
            'Demographics',
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "middle_initial",
                    "birth_dt",
                    "gender",
                    "mrn",
                    "ssn",
                ),
            },
        ),
        (
            'Address',
            {
                "fields": (
                    "street_address",
                    "apt",
                    "city",
                    "state",
                    "zipcode",
                ),
            },
        ),
        (
            'Phone And Email',
            {
                "fields": (
                    "phone_number",
                    "fax_number",
                    "email",
                ),
            },
        ),
        (
            'Additional Demographics',
            {
                "fields": (
                    "marital_status",
                    "smoking_status",
                    "race",
                ),
            },
        ),
    )
    list_display = ('first_name',
                    'last_name',
                    'created_dt',
                    'created_by',
                    'birth_dt',
                    'gender',
                    'mrn',
                    'ssn',
                    'street_address',
                    'apt',
                    'city',
                    'zipcode',
                    'state',
                    'phone_number',
                    'fax_number',
                    'email',
                    'marital_status',
                    'smoking_status',
                    'race')

    date_hierarchy = 'created_dt'
    inlines = [PatientInsuranceInfoInline]
    resource_classes = [PatientResource]
    change_form_template = 'admin/change_form.html'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(subject__isnull=True)  # only patients without subject

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
        return


subject_fieldsets = list(copy.deepcopy(PatientAdmin.fieldsets))
for fieldset in subject_fieldsets:
    if fieldset[0] == 'Demographics':
        fieldset[1]['fields'] = ('subject_id',) + fieldset[1]['fields']
        break


class SubjectAdmin(PatientAdmin):
    fieldsets = tuple(subject_fieldsets)
    inlines = []
    list_display = (
        'subject_id',
        'first_name',
        'last_name',
        'birth_dt',
        'gender',
        'mrn'
    )

    readonly_fields = ('subject_id',)

    def get_queryset(self, request):
        qs = super(PatientAdmin, self).get_queryset(request)
        return qs  # no extra filter for Subject


class AccessionTypeAdmin(ImportExportActionModelAdmin):
    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "accession_type",
                    "reporting_type",
                ),
            },
        ),
    )
    list_display = (
        "accession_type",
        "reporting_type",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "accession_type",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [AccessionTypeResource]
    change_form_template = 'admin/change_form.html'

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


class BodySubSiteMapInline(admin.TabularInline):
    model = BodySubSiteMap
    form = BodySubSiteMapForm
    fields = (
        "sub_site",
        "x_axis",
        "y_axis",

    )
    extra = 0


class BodySiteTestMapInlineFormSet(forms.BaseInlineFormSet):

    def clean(self):
        super().clean()

        defaults = 0

        for form in self.forms:
            # Skip deleted rows
            if form.cleaned_data.get("DELETE"):
                continue

            if form.cleaned_data.get("is_default"):
                defaults += 1

        if defaults > 1:
            raise ValidationError(
                "Only one test can be marked as default for this Body Site."
            )


class BodySiteTestMapInline(admin.StackedInline):
    model = BodySiteTestMap
    extra = 0
    formset = BodySiteTestMapInlineFormSet
    show_change_link = True

    # fields you want to display/edit in the inline
    fields = ['test_id', 'is_default']


class BodySiteAdmin(ImportExportActionModelAdmin):
    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "body_site",
                    "base_image",
                    "image_render_category",
                ),
            },
        ),
    )
    list_display = (
        "body_site",
        "base_image",
        "image_render_category",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "body_site",
    ]
    form = BodySiteForm
    date_hierarchy = 'created_dt'
    resource_classes = [BodySiteResource]
    inlines = [BodySubSiteMapInline, BodySiteTestMapInline]
    change_form_template = 'admin/change_form.html'

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


class ReportImgPropInfoAdmin(ImportExportActionModelAdmin):
    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "category",
                    "shape",
                    "color",
                ),
            },
        ),
    )
    list_display = (
        "category",
        "shape",
        "color",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "category",
    ]
    form = ReportImgPropInfoForm
    date_hierarchy = 'created_dt'
    resource_classes = [ReportImgPropInfoResource]
    change_form_template = 'admin/change_form.html'

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


class AttachmentConfigurationAdmin(ImportExportActionModelAdmin):
    # def get_import_resource_kwargs(self, request, *args, **kwargs):
    #     # Pass the user to the resource
    #     return {"context": {"user": request.user}}

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "model_name",
                    "path",
                ),
            },
        ),
    )
    list_display = (
        "model_name",
        "path",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "model_name",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [AttachmentConfigurationResource]
    change_form_template = 'admin/change_form.html'
    form = AttachmentConfigurationForm

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


class ProjectVisitMapInline(admin.TabularInline):
    model = ProjectVisitMap
    form = ProjectVisitMapForm
    fields = (
        "visit_id",
        "client_visit_id",
        "visit_instruction",

    )
    extra = 0


class QCPendingProjectVisitMapInline(admin.TabularInline):
    model = ProjectVisitMap
    form = ProjectVisitMapForm
    readonly_fields = (
        "visit_id",
        "client_visit_id",
        "visit_instruction",

    )
    fields = (
        "visit_id",
        "client_visit_id",
        "visit_instruction",

    )
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProjectTestMapInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        # Skip validation if nothing changed
        has_changes = False
        for form in self.forms:
            if not form.cleaned_data:
                continue

            if self.can_delete and form.cleaned_data.get('DELETE', False):
                has_changes = True
                break
            if form.has_changed() or form.instance.pk is None:
                has_changes = True
                break

        # Validate modification_notes only if inline changed
        if has_changes:
            project = getattr(self, 'instance', None)
            if project and not getattr(project, 'modification_notes', None):
                raise ValidationError(
                    "Please enter Modification Notes"
                )


class ProjectTestMapInline(admin.StackedInline):
    formset = ProjectTestMapInlineFormSet
    model = ProjectTestMap
    fields = (
        "test_id",
    )
    extra = 0


class QCPendingProjectTestMapInline(admin.StackedInline):
    model = ProjectTestMap
    readonly_fields = ("display_test_id",)  # use custom display field
    fields = ("display_test_id",)
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def display_test_id(self, obj):
        return str(obj.test_id)  # plain text, no link

    display_test_id.short_description = "Test ID"  # column label


class ProjectEmailMapInline(admin.StackedInline):
    model = ProjectEmailMap
    form = ProjectEmailMapForm
    fields = (
        "email_id",
        "email_category",
    )
    extra = 0


class QCPendingProjectEmailMapInline(admin.StackedInline):
    model = ProjectEmailMap
    form = ProjectEmailMapForm
    readonly_fields = (
        "email_id",
        "email_category",
    )
    fields = (
        "email_id",
        "email_category",
    )
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SponsorAdmin(GulfModelAdmin):
    form = SponsorForm

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "sponsor_name",
                    "sponsor_number",
                    "sponsor_description",
                    "sponsor_address_info",

                ),
            },
        ),
    )
    list_display = (
        "sponsor_name",
        "sponsor_number",
        "sponsor_description",
        "sponsor_address_info",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "sponsor_name"
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [SponsorResource]
    change_form_template = 'admin/change_form.html'

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                if not change or not obj.pk:
                    obj.created_by = user_map_obj
                    obj.mod_by = user_map_obj
                else:
                    obj.mod_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return


class ProjectFieldsMapInline(admin.TabularInline):
    model = ProjectFieldsMap
    fields = ('field_name', 'is_visible', 'category')
    readonly_fields = ('field_name', 'category')
    extra = 0

    def has_add_permission(self, request, obj=None):
        # Hide "Add another Demographic" button
        return False

    def has_delete_permission(self, request, obj=None):
        # Hide "Add another Demographic" button
        return False


class QCPendingProjectFieldsMapInline(admin.TabularInline):
    model = ProjectFieldsMap
    fields = ('field_name', 'is_visible', 'category')
    readonly_fields = ('field_name',)
    extra = 0

    def has_add_permission(self, request, obj=None):
        # Hide "Add another Demographic" button
        return False

    def has_change_permission(self, request, obj=None):
        # Hide "Add another Demographic" button
        return False

    def has_delete_permission(self, request, obj=None):
        # Hide "Add another Demographic" button
        return False


class ProjectPhysicianMapInline(admin.StackedInline):
    model = ProjectPhysicianMap
    form = ProjectPhysicianMapForm
    extra = 0


class QCPendingProjectPhysicianMapInline(admin.StackedInline):
    model = ProjectPhysicianMap
    extra = 0
    can_delete = False  # disables delete buttons as well

    # show only this read-only field
    readonly_fields = ('get_physician_name',)
    fields = ('get_physician_name',)

    def get_physician_name(self, obj):
        """Return physician name without link"""
        if obj and obj.physician_id:
            return obj.physician_id.first_name + " " + obj.physician_id.last_name  # or str(obj.physician_id)
        return "-"

    get_physician_name.short_description = "Physician"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def push_to_qc_action(self, request, queryset):
    """
    Admin list action to push selected projects to QC.
    Consistent with push_to_qc_ajax:
    - Checks if already 'In Progress'
    - Only updates qc_status
    """
    # Filter out projects that are already in QC
    projects_to_update = queryset.exclude(qc_status='In Progress')

    # Update *only* the qc_status field, just like the AJAX view
    updated_count = projects_to_update.update(
        qc_status='In Progress'
    )

    # Success message
    if updated_count == 1:
        self.message_user(request, '1 project was successfully pushed to QC.', messages.SUCCESS)
    elif updated_count > 1:
        self.message_user(request, f'{updated_count} projects were successfully pushed to QC.', messages.SUCCESS)

    # Warning message for any projects that were skipped
    already_in_progress_count = queryset.filter(qc_status='In Progress').count()
    if already_in_progress_count == 1:
        self.message_user(request, '1 project was already in QC and was not modified.', messages.WARNING)
    elif already_in_progress_count > 1:
        self.message_user(request,
                          f'{already_in_progress_count} projects were already in QC and were not modified.',
                          messages.WARNING)


push_to_qc_action.short_description = "Push to QC"


class BioProjectAdmin(GulfModelAdmin):
    change_form_template = "admin/masterdata/bioproject_change_form.html"
    form = BioProjectForm
    actions = [push_to_qc_action]
    fieldsets = (
        (
            'Project',
            {
                "fields": (
                    "bioproject_id",
                    "sponsor_name",
                    "project_protocol_id",
                    "client_project_protocol_id",
                    "is_active",
                    "instructions",
                    "modification_notes",

                ),
            },
        ),
        (
            'Project QC',
            {
                "fields": (
                    "qc_status",
                    "qced_by_str",
                    "qced_dt_str",
                    "qc_reason",
                ),
            },
        ),
    )
    list_display = (
        "project_protocol_id",
        "get_sponsor_name",
        "is_active",
        "qc_status",
        "qced_by",
        "qced_dt",

    )

    list_filter = [
        "project_protocol_id"
    ]
    inlines = [ProjectVisitMapInline, ProjectTestMapInline, ProjectEmailMapInline, ProjectFieldsMapInline,
               ProjectPhysicianMapInline]

    class Media:
        js = ('js/masterdata/masterdata.js', 'js/masterdata/bioproject.js')

    def get_sponsor_name(self, obj):
        if obj.sponsor_id:
            return obj.sponsor_id.sponsor_name
        return "-"

    get_sponsor_name.short_description = 'Sponsor'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(qc_status="In Progress")

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)

                # Set created_by and mod_by
                if not change or not obj.pk:  # New project (Add mode)
                    obj.created_by = user_map_obj
                    obj.mod_by = user_map_obj
                    # if obj.is_active:
                    #     obj.qc_status = 'In Progress'
                    # else:
                    obj.qc_status = 'Pending'
                else:  # Edit mode
                    obj.mod_by = user_map_obj

            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    def has_delete_permission(self, request, obj=None):
        return False

    def save_formset(self, request, form, formset, change):
        # Save with commit=False to inspect
        instances = formset.save(commit=False)

        project = form.instance  # parent object (Project)
        status_changed = False

        for form_obj in formset.forms:
            obj = form_obj.instance
            if form_obj in formset.deleted_forms:
                obj.delete()
                if formset.model == ProjectTestMap:
                    status_changed = True
            else:  # skip deleted ones
                if not obj.pk:  # new object
                    obj.created_by = request.user
                    obj.mod_by = request.user
                    if formset.model == ProjectTestMap:
                        status_changed = True
                elif form_obj.has_changed():  # existing but modified
                    obj.mod_by = request.user
                    if formset.model == ProjectTestMap:
                        status_changed = True

                obj.save()

        # Save many-to-many relationships
        formset.save_m2m()

        if status_changed:
            project.qc_status = 'In Progress'
            project.save(update_fields=["qc_status"])
            status_changed = False

    def save_related(self, request, form, formsets, change):
        """
           This method is called after the main object (BioProject) is saved.
           Handles creation/update of ProjectFieldsMap records based on DemographicFields.
           """
        super().save_related(request, form, formsets, change)

        project_instance = form.instance
        current_user = request.user
        current_dt = timezone.now()
        if not change:
            demographic_fields = DemographicFields.objects.all()
            list_project_demographics = []

            for demo in demographic_fields:
                list_project_demographics.append(
                    ProjectFieldsMap(
                        project=project_instance,
                        field_name=demo.field_name,
                        model_field_name=demo.model_field_name,
                        category=demo.category,
                        is_visible=True,
                        created_by=current_user,
                        created_dt=current_dt,
                        mod_by=current_user,
                        mod_dt=current_dt,
                    )
                )

            # Bulk insert all mappings
            if list_project_demographics:
                ProjectFieldsMap.objects.bulk_create(list_project_demographics)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        # Hide "Save and continue editing"
        # extra_context['show_save_and_continue'] = False
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


class BioSiteAdmin(GulfModelAdmin):
    form = BioSiteForm
    search_fields = (
        "investigator_name", "site_number", "city", "state", "country", "bioproject_id__project_protocol_id",
        "sponsor_id__sponsor_name")
    ordering = ("investigator_name",)

    list_display = (
        "sponsor_id",
        "bioproject_id",
        "site_number",
        "investigator_name",
        "created_dt",
        "created_by",
        "address",
        "street",
        "city",
        "state",
        "postalcode",
        "country",
        "phone_number",
        "fax_number",
    )

    fieldsets = (
        ("Investigator Site", {
            "fields": (
                "sponsor_id",
                "bioproject_id",
                "site_number",
                "investigator_name",
                "address",
                "street",
                "city",
                "state",
                "postalcode",
                "country",
                "phone_number",
                "fax_number",
            )
        }),
    )

    class Media:
        js = ('js/masterdata/masterdata.js', 'js/masterdata/investigatorsite.js')

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                project = request.POST.get("project")
                if not change or not obj.pk:
                    obj.created_by = user_map_obj
                    obj.mod_by = user_map_obj
                else:
                    obj.mod_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return


class QCPendingBioProjectAdmin(GulfModelAdmin):
    form = QCPendingBioProjectForm
    change_form_template = "admin/masterdata/qcpendingbioproject/qcpending_change_form.html"
    change_list_template = "admin/masterdata/qcpendingbioproject/change_list.html"
    fieldsets = (
        (
            'Project',
            {
                "fields": (
                    "project_protocol_id",
                    "client_project_protocol_id",
                    "instructions",
                    "modification_notes",

                ),
            },
        ),
        (
            'Project QC',
            {
                "fields": (
                    "qc_status",
                    "qced_by",
                    "qced_dt",
                    "qc_reason",
                ),
            },
        ),
    )
    list_display = (
        "project_protocol_id",
        "get_sponsor_name",
        "is_active",
        "qc_status",
    )
    list_filter = [
        "project_protocol_id"
    ]

    inlines = [QCPendingProjectVisitMapInline, QCPendingProjectTestMapInline, QCPendingProjectEmailMapInline,
               QCPendingProjectFieldsMapInline, QCPendingProjectPhysicianMapInline]

    def get_actions(self, request):
        actions = super().get_actions(request) or {}
        actions.pop('delete_selected', None)
        actions.pop('delete_custom', None)
        return actions

    def get_sponsor_name(self, obj):
        if obj.sponsor_id:
            return obj.sponsor_id.sponsor_name
        return "-"

    get_sponsor_name.short_description = "Sponsor Name"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(qc_status="In Progress")

    #  Make all fields read-only
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    #  Optional: Remove Add, Save, Delete permissions (view-only)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# email config admin
class EmailConfigAdmin(GulfModelAdmin):
    form = EmailConfigForm
    search_fields = ("email_category", "email_to", "email_cc", "subject")
    ordering = ("email_category",)

    list_display = (
        "email_category",
        "email_to",
        "email_cc",
        "subject",
        "created_dt",
        "created_by",

    )

    fieldsets = (
        ("Email Configuration", {
            "fields": (
                "email_category",
                "email_to",
                "email_cc",
                "subject",
                "body",
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        try:
            # ✅ Check for duplicate category before saving (only when creating)
            if not change and EmailConfig.objects.filter(email_category__iexact=obj.email_category).exists():
                messages.error(
                    request,
                    f"An Email Config for category '{obj.email_category}' already exists."
                )
                return  # Stop saving and show error
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)

                if not change or not obj.pk:
                    obj.created_by = user_map_obj
                    obj.mod_by = user_map_obj
                else:
                    obj.mod_by = user_map_obj

            super().save_model(request, obj, form, change)

        except Exception as e:
            messages.error(request, f"Error saving Email Config: {e}")
            return


class AccessionPrefixAdmin(admin.ModelAdmin):
    list_display = ('accession_prefix', 'magazine')
    search_fields = ('accession_prefix', 'magazine')
    ordering = ('accession_prefix',)


class DemographicFieldsAdmin(GulfModelAdmin):
    form = DemographicFieldsForm
    list_display = ('field_name', 'model_field_name', 'category')
    search_fields = ('field_name',)


controller.register(Client, ClientAdmin)
controller.register(Patient, PatientAdmin)
controller.register(Subject, SubjectAdmin)
controller.register(Physician, PhysicianAdmin)
controller.register(AccessionType, AccessionTypeAdmin)
controller.register(BodySite, BodySiteAdmin)
controller.register(ReportImgPropInfo, ReportImgPropInfoAdmin)
controller.register(AttachmentConfiguration, AttachmentConfigurationAdmin)
controller.register(Sponsor, SponsorAdmin)
controller.register(BioProject, BioProjectAdmin)
controller.register(BioSite, BioSiteAdmin)
controller.register(QCPendingBioProject, QCPendingBioProjectAdmin)
controller.register(EmailConfig, EmailConfigAdmin)
controller.register(AccessionPrefix, AccessionPrefixAdmin)
controller.register(DemographicFields, DemographicFieldsAdmin)
