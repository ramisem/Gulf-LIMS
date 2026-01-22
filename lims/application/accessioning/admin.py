import copy
import os
import threading
import logging
from django.contrib import admin, messages

from analysis.forms import NoLinkFileWidget, AttachmentInlineForm
from analysis.models import Attachment, ReportOption, MergeReporting
from controllerapp import settings
from controllerapp.views import controller
from security.models import User, Department, JobType
from util.admin import TZIndependentAdmin, GulfModelAdmin
from util.util import get_printer_by_category, GenerateLabel, generate_automatic_sample_labels
from .models import Accession, AccessionICDCodeMap, BioPharmaAccession
from .forms import AccessionForm, SampleInlineForm, AccessionICDCodeMapForm, SampleInlineFormSet, BioPharmaAccessionForm
from sample.models import Sample, SampleTestMap
from routinginfo.util import UtilClass
from process.models import ContainerType
from django.db import connection
from django.utils.safestring import mark_safe
from workflows.models import Workflow, ModalityModelMap
from django.apps import apps
from django.urls import reverse, path
from django.http import HttpResponseRedirect
import importlib
from django.db import transaction, OperationalError
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.encoding import force_str
from django.db.models.functions import Coalesce, Cast
from django.db.models import Q, Value, Case, When, IntegerField, CharField
from util.util import UtilClass as GenericUtilClass
from logutil.log import log
from concurrent.futures import ThreadPoolExecutor
from masterdata.models import ProjectEmailMap, EmailConfig, AccessionType, Subject
import datetime
from pathlib import Path

MODEL_APP_MAP = {model.__name__: model._meta.app_label for model in apps.get_models()}


def get_app_name_from_model(model_name):
    return MODEL_APP_MAP.get(model_name)


@admin.action(description="Generate Accession")
def generate_accession(self, request, queryset):
    """
    Custom admin action to process selected accessions,
    fetch related samples, and execute routing logic based on container type.
    """
    accession_ids = queryset.values_list('accession_id', flat=True)
    log.info(f"accession_ids ---> {accession_ids}")
    samples = Sample.objects.filter(accession_id__in=accession_ids).exclude(
        Q(accession_generated=True) | Q(accession_sample__isnull=False)
    )

    if samples.exists():
        container_map = {c.container_type_id: c.child_sample_creation for c in ContainerType.objects.filter(
            container_type_id__in=samples.values_list('container_type_id', flat=True)
        )}

        workflow_ids_direct = samples.exclude(workflow_id__isnull=True).values_list('workflow_id',
                                                                                    flat=True).distinct()

        # Step 2: Build the mapping of ID → name
        workflow_map_direct = {
            w.workflow_id: w.workflow_name
            for w in Workflow.objects.filter(workflow_id__in=workflow_ids_direct)
        }

        # Inline logic to get workflow_map_testmap (from SampleTestMap)
        workflow_ids_testmap = SampleTestMap.objects.filter(
            sample_id__in=samples.values_list('sample_id', flat=True)
        ).values_list('workflow_id_id', flat=True).distinct()

        # Step 2: Build the mapping of ID → name
        workflow_map_testmap = {
            w.workflow_id: w.workflow_name
            for w in Workflow.objects.filter(workflow_id__in=workflow_ids_testmap)
        }

        workflow_names = list(workflow_map_direct.values()) + list(workflow_map_testmap.values())

        # Get workflow-specific modality table mapping
        modality_map = {
            m.modality: m.model
            for m in ModalityModelMap.objects.filter(modality__in=workflow_names)
        }

        bulk_insert_map = {}
        successfully_inserted_samples = set()
        for sample in samples:
            child_sample_creation = container_map.get(sample.container_type_id, False)
            if sample.workflow_id_id:
                workflow_name = workflow_map_direct.get(sample.workflow_id_id)
            else:
                workflow_id = SampleTestMap.objects.filter(
                    sample_id=sample.sample_id
                ).values_list("workflow_id_id", flat=True).first()
                workflow_name = workflow_map_testmap.get(workflow_id)

            if not child_sample_creation and workflow_name:
                model = modality_map.get(workflow_name)
                if model:
                    app_name = get_app_name_from_model(model)

                    if (app_name, model) not in bulk_insert_map:
                        bulk_insert_map[(app_name, model)] = []

                    bulk_insert_map[(app_name, model)].append(sample.sample_id)
        with connection.cursor() as cursor:
            for (app_name, model), sample_ids in bulk_insert_map.items():
                table_name = f"{app_name}_{model}"
                query = f"INSERT INTO {table_name} (sample_ptr_id) VALUES (%s) ON CONFLICT DO NOTHING;"
                values = [(sample_id,) for sample_id in sample_ids]  # Convert to tuple list
                cursor.executemany(query, values)  # Bulk insert
                successfully_inserted_samples.update(sample_ids)

                if successfully_inserted_samples:
                    Sample.objects.filter(sample_id__in=successfully_inserted_samples).update(isvisible=False)

        module = importlib.import_module("routinginfo.util")
        GenericUtilClass = getattr(module, "UtilClass")
        success_samples = GenericUtilClass.process_workflow_steps_wetlab(self, request, samples, accession_flag='Y')

        if success_samples:
            log.info(f"Sample Ids processed for workflow: ---> {success_samples}")
            sample_ids = [sample["sample_id"] for sample in success_samples if "sample_id" in sample]
            accession_ids = list(Sample.objects.filter(sample_id__in=sample_ids).values_list("accession_id", flat=True))
            if accession_ids:
                Accession.objects.filter(accession_id__in=accession_ids).update(status="In-progress")

            t1 = threading.Thread(target=generate_automatic_sample_labels,
                                  args=(request, sample_ids, "Generate Accession"))
            t1.start()

            table_rows = "".join(
                [f"<tr><td>{sample['sample_id']}</td><td>{sample['current_step']}</td></tr>" for sample in
                 success_samples]
            )

            message = f"""
                        <p><strong>Generate Accession completed. Routed samples to below step:</strong></p>
                        <button onclick="toggleTable()" style="margin-bottom: 10px; padding: 5px 10px; background-color: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px;">
                            Expand/Collapse
                        </button>
                        <div id="sampleTable" style="display: none;">
                            <table border="1" cellpadding="2" cellspacing="0" style="border-collapse: collapse; width: 50%;">
                                <tr><th>Sample ID</th><th>Next Step</th></tr>
                                {table_rows}
                            </table>
                        </div>

                        <script>
                            function toggleTable() {{
                                var table = document.getElementById("sampleTable");
                                if (table.style.display === "none") {{
                                    table.style.display = "block";
                                }} else {{
                                    table.style.display = "none";
                                }}
                            }}
                        </script>
                    """
            log.info(f"Generate Accession Success ---> ")
            self.message_user(request, mark_safe(message), level="INFO")
            log.info("Preparing to send emails for Pharma Accession in a separate thread")
            t2 = threading.Thread(target=send_pharma_emails, args=(accession_ids,))
            t2.start()
        else:
            log.error(f"Generate Accession Failed!")
            self.message_user(request, "Generate Accession failed. ", level="ERROR")
    else:
        log.error(f"No sample(s) to route")
        self.message_user(request, "No sample(s) to route")


@admin.action(description="Print Requisition Label")
def print_req_labels(self, request, queryset):
    accessions = list(queryset)

    if not accessions:
        return

    # 1. Get Printer Info (One-time check)
    printer_info, message_text = get_printer_by_category(request, "Requisition")
    if printer_info is None:
        log.error(f"Error Message ---> {message_text}")
        messages.error(request, message_text)
        return

    printer, communication_type = printer_info.printer_path, printer_info.communication_type

    if not printer or not communication_type:
        msg = f"Please select a Communication Type for the Printer : {printer_info.printer_name}" if not communication_type else "No printer path defined."
        log.error(f"Error Message ---> {msg}")
        messages.error(request, msg)
        return

    obj = GenerateLabel()

    # 2. Separate Accessions into Pharma and Clinical groups
    pharma_accession_ids = []
    clinical_accession_ids = []

    for acc in accessions:
        if acc.accession_category == 'Pharma':
            pharma_accession_ids.append(acc.accession_id)
        else:
            clinical_accession_ids.append(acc.accession_id)

    # 3. Process Pharma Accessions (Batch 1)
    if pharma_accession_ids:
        log.info(f"Printing {len(pharma_accession_ids)} Pharma Requisition Labels")
        result = obj.print_label(
            request,
            pharma_accession_ids,  # Pass ALL Pharma IDs at once
            model_pk=pharma_accession_ids,
            model_app_id="accessioning/Accession",
            label_method_name="Pharma_Requisition",  # Pharma-specific label
            label_method_version="1",
            communication_type=communication_type,
            printer=printer,
            count=1
        )
        _handle_print_result(request, result)

    # 4. Process Clinical Accessions (Batch 2)
    if clinical_accession_ids:
        log.info(f"Printing {len(clinical_accession_ids)} Clinical Requisition Labels")
        result = obj.print_label(
            request,
            clinical_accession_ids,  # Pass ALL Clinical IDs at once
            model_pk=clinical_accession_ids,
            model_app_id="accessioning/Accession",
            label_method_name="Requisition",
            label_method_version="1",
            communication_type=communication_type,
            printer=printer,
            count=1
        )
        _handle_print_result(request, result)


def _handle_print_result(request, result):
    status = result.get('status')
    received_message = result.get('message')

    if status == 'error':
        log.error(f"Print Error ---> {received_message}")
        messages.error(request, received_message)
    elif status == 'warning':
        log.warning(f"Print Warning ---> {received_message}")
        messages.warning(request, received_message)
    elif status == 'success':
        log.info(f"Print Success ---> {received_message}")
        messages.success(request, received_message)
    else:
        msg = received_message if received_message else "Label Probably not Printed. No Response received."
        log.error(f"Print Error ---> {msg}")
        messages.error(request, msg)


class SampleInline(admin.TabularInline):
    model = Sample
    form = SampleInlineForm
    formset = SampleInlineFormSet

    extra = 0
    max_num = 1
    show_change_link = False
    classes = ['scrollable-inline']

    class Media:
        css = {'all': ('css/admin_custom.css',)}

    def get_fields(self, request, obj=None):
        """Dynamically control fields based on accession_category"""
        fields = ['part_no', 'block_or_cassette_seq', 'slide_seq',
                  'sample_type_info', 'container_type_info', 'test_code', 'test_id', 'body_site', 'sub_site',
                  'collection_method', 'workflow_id', 'child_sample_creation', 'sample_status', 'sample_id',
                  'gen_block_or_cassette_seq', 'gen_slide_seq']

        if obj and obj.accession_category == "Clinical":
            # Remove these fields for Clinical category
            # fields.remove('part_no')
            fields.remove('block_or_cassette_seq')
            fields.remove('slide_seq')
            fields.remove('part_no')

        return fields

    def safe_cast(self, field_name):
        return Cast(
            Coalesce(
                Case(
                    When(**{f"{field_name}": ""}, then=Value("0", output_field=CharField())),
                    # Replace empty string with "0"
                    default=Cast(field_name, output_field=CharField()),
                    output_field=CharField()
                ),
                Value("0", output_field=CharField())
            ),
            IntegerField()
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        object_id = request.resolver_match.kwargs.get('object_id', None)

        if object_id:
            try:
                accession_obj = Accession.objects.get(pk=object_id)
                if accession_obj.accession_category != "Clinical":
                    return queryset.filter(accession_sample__isnull=True).order_by(
                        'part_no',
                        self.safe_cast('block_or_cassette_seq'),
                        self.safe_cast('slide_seq')
                    )
                else:
                    return queryset.filter(accession_sample__isnull=True).order_by('sample_id')

            except Accession.DoesNotExist:
                pass
            except Exception as e:
                print(f"Error retrieving Accession or filtering SampleInline: {e}")
                pass


class AccessionICDCodeMapInline(admin.StackedInline):
    model = AccessionICDCodeMap
    form = AccessionICDCodeMapForm
    fields = (
        "icd_code_id",
        "description",
    )
    extra = 0

    class Media:
        js = ('js/accessioning/accessioning.js', 'js/util/util.js')


class AccessionAttachmentInline(admin.TabularInline):
    model = Attachment
    form = AttachmentInlineForm
    fields = (
        "file_path_display",
        "file_path",
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
            url = reverse(f'{self.admin_site.name}:accession_download_attachment', args=[obj.pk])
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


class AccessionAdmin(TZIndependentAdmin, GulfModelAdmin):
    tz_independent_fields = ['receive_dt', 'collection_dt']
    search_fields = ("accession_id",)
    ordering = ("accession_id",)
    readonly_fields = ['created_dt', 'complete_dt']
    form = AccessionForm
    inlines = [SampleInline, AccessionICDCodeMapInline, AccessionAttachmentInline]
    fieldsets = (
        (
            'Accession Info',
            {
                "fields": (
                    "is_auto_gen_pk",
                    "patient_id",
                    "accession_prefix",
                    "case_id",
                    "accession_id",
                    "accession_category",
                    "accession_type",
                    "reporting_type",
                    "accession_template",
                    "status",
                    "created_dt",
                    "complete_dt",
                    "receive_dt",
                    "receive_dt_timezone",
                    "collection_dt",
                    "collection_dt_timezone",
                    "previous_accession",
                    "isupdate_accession_prefix",
                    "move_next_to_client_info_tab",
                    "hidden_auto_gen_pk",
                    "hidden_accession_prefix",
                    "hidden_accession_template",
                ),
            },
        ),

        (
            'Client',
            {
                "fields": (
                    "client_id",
                    "doctor",
                    "client_address_line1",
                    "client_address_line2",
                    "client_city",
                    "client_state",
                    "client_postalcode",
                    "client_country",
                    "client_phone_number",
                    "client_fax_number",
                    "client_email",
                    "move_prev_next_from_client_info_tab",
                ),
            },
        ),
        (
            'Assignment',
            {
                "fields": (
                    "reporting_doctor",
                    "move_prev_next_from_reporting_doc_tab",
                ),
            },
        ),
        (
            'Payment',
            {
                "fields": (
                    "payment_type",
                    "insurance_id",
                    "insurance_group",
                    "street_address",
                    "apt",
                    "city",
                    "zipcode",
                    "state",
                    "phone_number",
                    "fax_number",
                    "email",
                    "move_prev_next_from_payment_tab",
                    "is_create_samples",
                ),
            },
        ),
        (
            'Sample Creation',
            {
                "fields": (
                    "sample_type",
                    "container_type",
                    "part_no",
                    "parent_seq",
                    "is_child_sample_creation",
                    "associate_test",
                    "workflow",
                    "count",
                    "test_id",
                    "move_finish_from_sample_creation_tab",
                    "is_generate_parent_seq",
                    "is_gen_slide_seq"
                ),
            },
        ),

    )
    list_display = ('accession_id',
                    'accession_category',
                    'accession_type',
                    'active_flag',
                    'created_dt',
                    'created_by',
                    'status',
                    'complete_dt',
                    'client_id',
                    'patient_id',
                    'insurance_id',
                    )

    change_form_template = 'admin/accessioning/accession_change_form.html'
    actions = [generate_accession, GulfModelAdmin.delete_custom, print_req_labels]

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """Override to hide 'Save and add another' button"""
        context['show_add_another_button'] = False
        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_queryset(self, request):
        """Override to filter accessions based on is_template column."""
        qs = super().get_queryset(request)
        qs = qs.filter(is_template=False).exclude(accession_category='Pharma')
        return qs

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'accession_download_attachment/<int:attachment_id>/',
                self.admin_site.admin_view(GenericUtilClass.download_attachment),
                name='accession_download_attachment',
            ),
            path(
                '<path:object_id>/generate_accession/',
                self.admin_site.admin_view(self.process_generate_accession),
                name='accession_generate_accession',
            ),
        ]
        return custom_urls + urls

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)
        return lambda *args, **form_kwargs: FormClass(*args, request=request, **form_kwargs)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            if extra_context is None:
                extra_context = {}
            extra_context['accession_id'] = obj.accession_id
            extra_context['status'] = obj.status
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                isupdate_accession_prefix = form.cleaned_data.get('isupdate_accession_prefix')
                accession_template = form.cleaned_data.get('accession_template')
                accession_template_instance = None
                if not obj.pk and not change and "Y" != isupdate_accession_prefix:
                    if accession_template:
                        accession_template_instance = Accession.objects.get(accession_id=accession_template)

                if accession_template_instance:
                    obj.accession_prefix = accession_template_instance.accession_prefix
                    obj.accession_category = accession_template_instance.accession_category
                    obj.accession_type = accession_template_instance.accession_type
                    obj.client_id = accession_template_instance.client_id
                    obj.doctor = accession_template_instance.doctor
                    obj.reporting_doctor = accession_template_instance.reporting_doctor
                    obj.is_template = False

                if 'receive_dt' in form.changed_data:
                    obj.receive_dt_timezone = request.session.get('currenttimezone',
                                                                  getattr(settings, 'SERVER_TIME_ZONE',
                                                                          'UTC'))

                if not change or 'Y' == isupdate_accession_prefix:
                    obj.created_by = user_map_obj
                    if "Y" == isupdate_accession_prefix:
                        obj.object_id = None
                        obj.pk = None

                    obj.status = "Initial"
                    current_jobtype = request.session.get('currentjobtype', '')
                    if current_jobtype is not None:
                        department_id = JobType.objects.filter(name=current_jobtype).values_list('departmentid',
                                                                                                 flat=True).first()
                        if department_id is not None:
                            department_name = Department.objects.filter(id=department_id).values_list('name',
                                                                                                      flat=True).first()
                            if department_name is not None:
                                obj.accession_lab = department_name
                            department_instance = Department.objects.get(id=department_id)
                            if department_instance is not None:
                                obj.created_by_dept = department_instance

                    if obj.is_auto_gen_pk is True:
                        model_name = obj.__class__.__name__
                        if model_name == 'BioPharmaAccession':
                            model_name = 'Accession'
                        accession_prefix = obj.accession_prefix
                        module = importlib.import_module("util.util")
                        GenericUtilClass = getattr(module, "UtilClass")
                        seq_no = GenericUtilClass.get_next_sequence(accession_prefix, model_name, obj.created_by.id)
                        obj.accession_id = f"{accession_prefix}-{seq_no:05}"
                    else:
                        obj.accession_id = obj.accession_prefix + "-" + request.POST.get('case_id')

                else:
                    hidden_auto_gen_pk = request.POST.get('hidden_auto_gen_pk')
                    if hidden_auto_gen_pk == "true":
                        obj.is_auto_gen_pk = True
                    else:
                        obj.is_auto_gen_pk = False

                    obj.accession_prefix = request.POST.get('hidden_accession_prefix')
                    obj.accession_template = request.POST.get('hidden_accession_template')

                if change and 'reporting_doctor' in form.changed_data and obj.pk:
                    new_reporting_doctor = obj.reporting_doctor
                    if new_reporting_doctor:
                        new_pathologist_user = new_reporting_doctor.user_id

                        ReportOption.objects.filter(accession_id=obj).exclude(
                            reporting_status__in=["Completed", "Cancelled"]).update(
                            assign_pathologist=new_pathologist_user)
                        MergeReporting.objects.filter(accession_id=obj).exclude(
                            reporting_status__in=["Completed", "Cancelled"]).update(
                            assign_pathologist=new_pathologist_user)
                        logging.info(
                            f"Assigned pathologist(s) updated in Report Options for Accession ID: {obj.accession_id}")

                if "Y" == isupdate_accession_prefix:
                    super().save_model(request, obj, form, change)
                else:
                    super().save_model(request, obj, form, change)

                if accession_template_instance:
                    list_template_samples = Sample.objects.filter(
                        accession_id_id=accession_template_instance.accession_id)
                    module = importlib.import_module("sample.util")
                    SampleUtilClass = getattr(module, "SampleUtilClass")
                    SampleUtilClass.create_samples_from_existing_list_of_samples(list_template_samples, request, obj)
                    list_accession_icd_code_map = AccessionICDCodeMap.objects.filter(
                        accession_id_id=accession_template_instance.accession_id)
                    if list_accession_icd_code_map:
                        list_new_accession_icd_code_map = []
                        for accession_icd_code_map_instance in list_accession_icd_code_map:
                            new_accession_icd_code_map_instance = AccessionICDCodeMap()
                            new_accession_icd_code_map_instance.accession_id = obj
                            new_accession_icd_code_map_instance.icd_code_id = accession_icd_code_map_instance.icd_code_id
                            new_accession_icd_code_map_instance.created_by = user_map_obj
                            new_accession_icd_code_map_instance.mod_by = user_map_obj
                            list_new_accession_icd_code_map.append(new_accession_icd_code_map_instance)
                        AccessionICDCodeMap.objects.bulk_create(list_new_accession_icd_code_map)

        except Exception as e:
            self.message_user(request, f"An error occurred while saving: {e}", level=messages.ERROR)
        finally:
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

    def response_change(self, request, obj):
        isupdate_accession_prefix = request.POST.get('isupdate_accession_prefix')
        change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
        if "Y" == isupdate_accession_prefix:
            current_accession = obj.accession_id
            try:
                with transaction.atomic():
                    previous_accession = request.POST.get('previous_accession')
                    if previous_accession is None:
                        return
                    Sample.objects.filter(accession_id=previous_accession).update(accession_id=obj.accession_id)
                    AccessionICDCodeMap.objects.filter(accession_id=previous_accession).update(
                        accession_id=obj.accession_id)
                    Attachment.objects.filter(accession_id=previous_accession).update(accession_id=obj.accession_id)
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM accessioning_accession WHERE accession_id = %s",
                            [previous_accession]
                        )
                    return HttpResponseRedirect(f"{change_url}")
            except Exception as e:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM accessioning_accession WHERE accession_id = %s",
                        [current_accession]
                    )
                self.message_user(request, f"Could not update Accession Prefix", level=messages.ERROR)
                change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
                return HttpResponseRedirect(f"{change_url}")

        else:
            is_create_samples = request.POST.get('is_create_samples')
            if "Y" == is_create_samples:
                return HttpResponseRedirect(f"{change_url}?move_to_sample_creation_tab=Y")
            else:
                messages.success(request, "Operation successful.")
                return HttpResponseRedirect(f"{change_url}")

    def response_add(self, request, obj):
        change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
        return HttpResponseRedirect(f"{change_url}?move_to_sample_creation_tab=Y")

    def save_related(self, request, form, formset, change):
        user_map_obj = None
        if request.user.is_authenticated:
            username = request.user.username
            user_map_obj = User.objects.get(username=username)
            for formsetobj in formset:
                formset_model = formsetobj.model.__name__  # Get the model name
                if formset_model == "AccessionICDCodeMap":
                    accessionicdcodemapinstances = formsetobj.save(commit=False)
                    for instances in accessionicdcodemapinstances:
                        if instances.created_by is None:
                            instances.created_by = user_map_obj
                        instances.mod_by = user_map_obj
                        instances.save()

        super().save_related(request, form, formset, change)

    def get_deleted_objects(self, objs, request):
        samples = Sample.objects.filter(accession_id__in=objs)
        if samples.exists():
            raise ValidationError("One or more sample(s) are associated with this accession.")
        else:
            deletable_objects = []
            model_count = {self.model._meta.verbose_name_plural: 0}
            for obj in objs:
                try:
                    with transaction.atomic():
                        obj_display = format_html(
                            '{}: {}'.format(force_str(obj._meta.verbose_name), obj)
                        )
                        deletable_objects.append(obj_display)
                        model_count[self.model._meta.verbose_name_plural] += 1
                except ValidationError as e:
                    self.message_user(request, f"Error: {e}", level='error')

            return deletable_objects, model_count, [], []

    def delete_model(self, request, obj):
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(
                            "DELETE FROM accessioning_accession WHERE accession_id = %s",
                            [obj.pk]
                        )
                    except OperationalError as e:
                        self.message_user(request, f"Error deleting accession: {str(e)}. Standard delete used.",
                                          messages.WARNING)
                        raise
        except Exception as e:
            self.message_user(request, f"Error deleting accession: {str(e)}. Standard delete used.",
                              messages.WARNING)

    def delete_view(self, request, object_id, extra_context=None):
        try:
            obj = self.get_object(request, object_id)
            if not obj:
                self.message_user(request, "Object not found.", level='error')
                return HttpResponseRedirect(reverse('admin:accessioning_accession_changelist'))

            return super().delete_view(request, object_id, extra_context)

        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", level='error')
            change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
            return HttpResponseRedirect(f"{change_url}")

    def process_generate_accession(self, request, object_id):
        try:
            obj = Accession.objects.get(accession_id=object_id)
        except Accession.DoesNotExist:
            self.message_user(request, "Accession not found.", level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:index'))

        try:
            generate_accession(self, request, queryset=Accession.objects.filter(accession_id=obj.accession_id))
        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)

        target_model_name = self.model._meta.model_name

        if obj.accession_category == 'Pharma':
            target_model_name = 'biopharmaaccession'

        change_url = reverse(
            f'{self.admin_site.name}:{self.model._meta.app_label}_{target_model_name}_change',
            args=[obj.pk]
        )

        return HttpResponseRedirect(change_url)

    def get_object(self, request, object_id, from_field=None):
        try:
            return self.model.objects.get(accession_id=object_id)  # if accession_id is PK or unique
        except self.model.DoesNotExist:
            return None

    class Media:
        css = {'all': ('css/admin.css',)}
        js = ('js/accessioning/accessioning.js', 'js/util/util.js')


original_fieldsets = copy.deepcopy(AccessionAdmin.fieldsets)
fieldsets_to_keep = [fs for fs in original_fieldsets if fs[0] not in ('Payment', 'Client')]
final_biopharma_fieldsets = []
for title, options in fieldsets_to_keep:
    if title == 'Accession Info':
        # Add the main BioPharma fields
        current_fields = options.get('fields', ())
        filtered_fields = [f for f in current_fields if f != 'accession_type']
        options['fields'] = ('sponsor', 'project', 'visit', 'investigator') + tuple(filtered_fields)
        # options['fields'] = ('sponsor', 'project', 'visit', 'investigator') + options['fields']
        final_biopharma_fieldsets.append((title, options))
    elif title == 'Sample Creation':
        # Add the crucial hidden field to the Sample Creation tab
        current_fields = options.get('fields', ())
        options['fields'] = current_fields + ('is_create_samples',)
        final_biopharma_fieldsets.append((title, options))
    else:
        final_biopharma_fieldsets.append((title, options))

sponsor_tab = ('Sponsor', {
    'fields': (
        'sponsor_name',
        'sponsor_number',
        'sponsor_description',
        'sponsor_address_info',
        'move_prev_next_from_sponsor_tab',
    )
})

final_biopharma_fieldsets.insert(1, sponsor_tab)


class BioPharmaAccessionAdmin(AccessionAdmin):
    form = BioPharmaAccessionForm
    inlines = [
        inline for inline in AccessionAdmin.inlines
        if inline is not AccessionICDCodeMapInline
    ]

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """Override to hide 'Save and add another' button"""
        context['show_add_another_button'] = False
        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_queryset(self, request):
        qs = super(AccessionAdmin, self).get_queryset(request)
        qs = qs.filter(is_template=False, accession_category='Pharma')
        return qs

    list_display = (
        'accession_id',
        'accession_category',
        'accession_type',
        'active_flag',
        'created_dt',
        'created_by',
        'status',
        'complete_dt',
        'display_subject_id',
        'sponsor',
        'project',
        'display_visit_id',
        'investigator'
    )

    def display_visit_id(self, obj):
        """
        Custom method to display the visit_id from the related ProjectVisitMap object.
        """
        if obj.visit:
            return obj.visit.visit_id
        return None

    display_visit_id.short_description = 'Visit ID'

    def display_subject_id(self, obj):
        """
        Custom method to display the subject_id from the related Subject object.
        """
        if obj.patient_id:
            try:
                subject = Subject.objects.get(pk=obj.patient_id.pk)
                return subject.subject_id
            except Subject.DoesNotExist:
                return "N/A (Subject record missing)"
        return None

    display_subject_id.short_description = 'Subject ID'

    fieldsets = tuple(final_biopharma_fieldsets)

    inlines = [SampleInline, AccessionAttachmentInline]

    def save_model(self, request, obj, form, change):
        try:
            global_type = AccessionType.objects.get(accession_type='Global')
            obj.accession_type = global_type
        except AccessionType.DoesNotExist:
            messages.error(request, "Critical Error: 'Global' Accession Type not found. Cannot save.")
            return
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                isupdate_accession_prefix = form.cleaned_data.get('isupdate_accession_prefix')
                accession_template = form.cleaned_data.get('accession_template')
                accession_template_instance = None
                if not obj.pk and not change and "Y" != isupdate_accession_prefix:
                    if accession_template:
                        try:
                            accession_template_instance = BioPharmaAccession.objects.get(
                                accession_id=accession_template)
                        except BioPharmaAccession.DoesNotExist:
                            accession_template_instance = Accession.objects.get(accession_id=accession_template)

                if accession_template_instance:
                    obj.accession_prefix = accession_template_instance.accession_prefix
                    obj.accession_category = accession_template_instance.accession_category
                    obj.accession_type = accession_template_instance.accession_type
                    obj.client_id = accession_template_instance.client_id
                    obj.doctor = accession_template_instance.doctor
                    obj.reporting_doctor = accession_template_instance.reporting_doctor
                    obj.is_template = False

                    if hasattr(accession_template_instance, 'sponsor'):
                        obj.sponsor = accession_template_instance.sponsor
                        obj.project = accession_template_instance.project
                        obj.visit = accession_template_instance.visit
                        obj.investigator = accession_template_instance.investigator

                if 'receive_dt' in form.changed_data:
                    obj.receive_dt_timezone = request.session.get('currenttimezone',
                                                                  getattr(settings, 'SERVER_TIME_ZONE',
                                                                          'UTC'))

                if not change or 'Y' == isupdate_accession_prefix:
                    obj.created_by = user_map_obj
                    if "Y" == isupdate_accession_prefix:
                        obj.object_id = None
                        obj.pk = None

                    obj.status = "Initial"
                    current_jobtype = request.session.get('currentjobtype', '')
                    if current_jobtype is not None:
                        department_id = JobType.objects.filter(name=current_jobtype).values_list('departmentid',
                                                                                                 flat=True).first()
                        if department_id is not None:
                            department_name = Department.objects.filter(id=department_id).values_list('name',
                                                                                                      flat=True).first()
                            if department_name is not None:
                                obj.accession_lab = department_name
                            department_instance = Department.objects.get(id=department_id)
                            if department_instance is not None:
                                obj.created_by_dept = department_instance

                    if obj.is_auto_gen_pk is True:
                        model_name = obj.__class__.__name__
                        if model_name == 'BioPharmaAccession':
                            model_name = 'Accession'
                        accession_prefix = obj.accession_prefix
                        module = importlib.import_module("util.util")
                        GenericUtilClass = getattr(module, "UtilClass")
                        seq_no = GenericUtilClass.get_next_sequence(accession_prefix, model_name, obj.created_by.id)
                        obj.accession_id = f"{accession_prefix}-{seq_no:05}"
                    else:
                        obj.accession_id = obj.accession_prefix + "-" + request.POST.get('case_id')

                else:
                    hidden_auto_gen_pk = request.POST.get('hidden_auto_gen_pk')
                    if hidden_auto_gen_pk == "true":
                        obj.is_auto_gen_pk = True
                    else:
                        obj.is_auto_gen_pk = False

                    obj.accession_prefix = request.POST.get('hidden_accession_prefix')
                    obj.accession_template = request.POST.get('hidden_accession_template')

                if change and 'reporting_doctor' in form.changed_data and obj.pk:
                    new_reporting_doctor = obj.reporting_doctor
                    if new_reporting_doctor:
                        new_pathologist_user = new_reporting_doctor.user_id

                        ReportOption.objects.filter(accession_id=obj).exclude(
                            reporting_status__in=["Completed", "Cancelled"]).update(
                            assign_pathologist=new_pathologist_user)
                        MergeReporting.objects.filter(accession_id=obj).exclude(
                            reporting_status__in=["Completed", "Cancelled"]).update(
                            assign_pathologist=new_pathologist_user)
                        logging.info(
                            f"Assigned pathologist(s) updated in Report Options for Accession ID: {obj.accession_id}")

                if "Y" == isupdate_accession_prefix:
                    super(AccessionAdmin, self).save_model(request, obj, form, change)
                else:
                    super(AccessionAdmin, self).save_model(request, obj, form, change)

                if accession_template_instance:
                    list_template_samples = Sample.objects.filter(
                        accession_id_id=accession_template_instance.accession_id)
                    module = importlib.import_module("sample.util")
                    SampleUtilClass = getattr(module, "SampleUtilClass")
                    SampleUtilClass.create_samples_from_existing_list_of_samples(list_template_samples, request, obj)
                    list_accession_icd_code_map = AccessionICDCodeMap.objects.filter(
                        accession_id_id=accession_template_instance.accession_id)
                    if list_accession_icd_code_map:
                        list_new_accession_icd_code_map = []
                        for accession_icd_code_map_instance in list_accession_icd_code_map:
                            new_accession_icd_code_map_instance = AccessionICDCodeMap()
                            new_accession_icd_code_map_instance.accession_id = obj
                            new_accession_icd_code_map_instance.icd_code_id = accession_icd_code_map_instance.icd_code_id
                            new_accession_icd_code_map_instance.created_by = user_map_obj
                            new_accession_icd_code_map_instance.mod_by = user_map_obj
                            list_new_accession_icd_code_map.append(new_accession_icd_code_map_instance)
                        AccessionICDCodeMap.objects.bulk_create(list_new_accession_icd_code_map)

        except Exception as e:
            self.message_user(request, f"An error occurred while saving: {e}", level=messages.ERROR)
        finally:
            return


def send_pharma_emails(list_accesssion_id):
    log.info("✅ send_pharma_emails() started...")
    """
    Send emails for all Pharma accessions
    """
    # Step 1️⃣: Filter only Pharma accessions
    pharma_accession_ids = Accession.objects.filter(
        accession_id__in=list_accesssion_id,
        accession_category__iexact="Pharma"
    )

    if not pharma_accession_ids:
        log.info("No Pharma accessions found. Skipping Pharma email notifications.")
        return

    # Step 2️⃣: Fetch Pharma EmailConfig
    try:
        email_config = EmailConfig.objects.get(email_category__iexact="AccessionEmail")
    except EmailConfig.DoesNotExist:
        log.warning("No EmailConfig found for sending email after Accession Generation. Skipping emails.")
        return

    if email_config:
        # Step 3️⃣: Worker function to send one email per accession
        def send_pharma_email(accession_id):
            try:
                accession_obj = BioPharmaAccession.objects.get(accession_id=accession_id)
                if not accession_obj:
                    log.error("Accession not found")
                project = getattr(accession_obj, "project", None)

                # Step 4️⃣: Fetch additional recipients dynamically from ProjectEmailMap
                recipient_list = []
                sponsor_name = ""
                projectprotocol = ""
                if project:
                    project_emails = ProjectEmailMap.objects.filter(
                        bioproject_id=project, email_category__iexact="AccessionEmail"
                    ).values_list("email_id", flat=True)
                    for email_str in project_emails:
                        for e in email_str.replace(",", ";").split(";"):
                            e = e.strip()
                            if e:
                                recipient_list.append(e)

                    projectprotocol = project.project_protocol_id
                    sponsor = project.sponsor_id
                    if sponsor:
                        sponsor_name = sponsor.sponsor_name

                # Combine recipients from EmailConfig and ProjectEmailMap
                if email_config.email_to:
                    recipient_list.extend(
                        [e.strip() for e in email_config.email_to.replace(",", ";").split(";") if e.strip()]
                    )
                recipient_list = list(set(recipient_list))  # Remove duplicates

                if not recipient_list:
                    log.warning(f"No recipients found for Pharma accession {accession_id}")
                    return

                # Step 5️⃣: Prepare HTML email body with placeholders replaced
                current_date = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                email_subject = email_config.subject

                if email_subject:
                    email_subject = email_subject.replace("[accessionid]", accession_obj.pk)

                email_body = email_config.body
                if email_body:
                    if sponsor_name:
                        email_body = email_body.replace("[sponsorname]", sponsor_name)
                    else:
                        log.error("Sponsor Name not found")

                    if projectprotocol:
                        email_body = email_body.replace("[projectprotocolid]", projectprotocol)
                    else:
                        log.error("Project/Protocol ID not found")

                # Step 7️⃣: Prepare mail_data
                mail_data = {
                    "from_email": getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                    "to_email": ";".join(recipient_list),
                    "cc_email": email_config.email_cc or "",
                    "subject": email_subject,
                    "body": email_body,
                }

                # Step 8️⃣: Send email
                GenericUtilClass.send_mail_for_pharma_implementation(mail_data)
                log.info(f"✅ Pharma email sent for accession {accession_id} to {recipient_list}")

            except Exception as e:
                log.error(f"❌ Error sending Pharma email for accession {accession_id}: {e}")

        # Step 9️⃣: Send emails concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            for accession_id in pharma_accession_ids:
                executor.submit(send_pharma_email, accession_id)


controller.register(Accession, AccessionAdmin)
controller.register(BioPharmaAccession, BioPharmaAccessionAdmin)
