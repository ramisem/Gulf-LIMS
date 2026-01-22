import functools
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.db.models import Q, Value, Case, When, IntegerField, CharField
from django.db.models.functions import Coalesce, Cast
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from import_export.formats import base_formats

from controllerapp.views import controller
from hl7.sender import send_hl7_for_staining_complete
from ihcworkflow.models import IhcWorkflow
from logutil.log import log
from reporting.models import ContainerTypeLabelMethodMap
from routinginfo.util import UtilClass as RoutingUtilClass
from sample.models import SampleTestMap, Sample
from security.models import User, JobType
from tests.models import WorkflowStepConfigField
from util.actions import GenericAction
from util.util import GenerateLabel, UtilClass as CommonUtilClass, \
    get_user_printer_selection_data
from workflows.models import WorkflowStep


@admin.action(description="Route Sample")
def execute_routing(self, request, queryset):
    sample_ids = queryset.values_list('sample_id', flat=True)
    log.info(f"sample_ids ---> {sample_ids}")
    if sample_ids:
        success_samples = RoutingUtilClass.process_workflow_steps_wetlab(self, request, sample_ids, accession_flag='N')
        if success_samples:
            table_rows = "".join(
                [f"<tr><td>{sample['sample_id']}</td><td>{sample['current_step']}</td></tr>" for sample in
                 success_samples]
            )

            message = f"""
               <p><strong>Routed samples to below step:</strong></p>
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
            log.info(f"Successful IHC Sample routing ---> {success_samples}")
            self.message_user(request, mark_safe(message), level="INFO")

    else:
        log.error("No sample(s) found")
        self.message_user(request, "No sample(s) found")


@admin.action(description="Send Complete Staining Response")
def send_response_for_complete_staining(self, request, queryset):
    log.info(f"Sending response for complete staining start")
    sample_ids = queryset.values_list('sample_id', flat=True)
    sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
    executor = ThreadPoolExecutor(max_workers=settings.HL7_THREADPOOL_MAX_WORKERS_SENDER)
    log.info(f"Selected sample ids for complete staining ---> {sample_ids}")
    for sample in sample_maps:
        slide_id = f"{sample.accession_id.accession_id}-{sample.part_no}-{sample.block_or_cassette_seq}-{sample.slide_seq}"
        executor.submit(send_hl7_for_staining_complete, slide_id)


@admin.action(description="Send to Stainer")
def send_to_staining(self, request, queryset):
    log.info(f"Sending request to staining start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("send_to_staining", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="SendToStaining", action_desc=action_desc)


@admin.action(description="Start Staining(Manual)")
def start_staining(self, request, queryset):
    log.info(f"Start staining action start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("start_staining", (None, None, None))[2]
    sample_ids = queryset.values_list('sample_id', flat=True)
    if sample_ids:
        sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
        qs_ihcworkflow = IhcWorkflow.objects.filter(
            sample_id__in=[sample.sample_id for sample in sample_maps]
        )
        if qs_ihcworkflow:
            if qs_ihcworkflow.filter(staining_status__in=["In Progress"]).exists():
                messages.error(request,
                               "Staining cannot be started as Staining Status is already In Progress for one or more sample(s)")
                return

        action_instance = GenericAction()
        action_instance.start_staining_method(request, queryset, sample_maps)
    else:
        messages.error(request, "Error: No sample(s) found")


@admin.action(description="Complete Staining(Manual)")
def complete_staining(self, request, queryset):
    log.info(f"Complete staining action start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("complete_staining", (None, None, None))[2]
    sample_ids = queryset.values_list('sample_id', flat=True)
    if sample_ids:
        sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
        action_instance = GenericAction()
        action_instance.complete_staining_method(request, queryset, sample_maps)
    else:
        messages.error(request, "Error: No sample(s) found")


@admin.action(description="Start Imaging")
def start_imaging(self, request, queryset):
    log.info(f"Start Imaging action start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("start_imaging", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="StartImaging", action_desc=action_desc)


@admin.action(description="Complete Imaging")
def complete_imaging(self, request, queryset):
    log.info(f"Complete Imaging action start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("complete_imaging", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="CompleteImaging",
                                        action_desc=action_desc)


@admin.action(description="Image QC")
def image_qcstatus(self, request, queryset):
    log.info(f"Image QC Status action start")
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("image_qcstatus", (None, None, None))[2]
    action_instance = GenericAction()
    form_type, form = action_instance.generic_action_call(request, queryset,
                                                          desired_action="PerformImageQC",
                                                          action_desc=action_desc)
    if form_type == 'render_form':
        return render(request, 'admin/qc_status_form.html', {'samples': queryset, 'form': form})
    if form_type == 'render_submit':
        return HttpResponseRedirect(request.get_full_path())


@admin.action(description="Edit")
def bulk_edit_action(self, request, queryset):
    sample_ids = queryset.values_list('sample_id', flat=True)
    log.info(f"Bulk edit form for sample ids --> {sample_ids}")
    url = reverse("controllerapp:ihc_sample_bulk_edit")
    q = request.GET.get('q', '')
    params = {'ids': ','.join(sample_ids)}
    if q:
        params['q'] = q

    return HttpResponseRedirect(f"{url}?{urlencode(params)}")


@admin.action(description="Print Labels")
def print_label_popup(self, request, queryset):
    pass


@admin.action(description="Perform Backward Movement")
def perform_backward_movement(self, request, queryset):
    pass


@admin.action(description="Update Test")
def update_test(self, request, queryset):
    return None


class IhcWorkflowAdmin(admin.ModelAdmin):
    # def get_import_resource_kwargs(self, request, *args, **kwargs):
    #     # Pass the user to the resource
    #     return {"context": {"user": request.user}}

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    tz_independent_fields = ['receive_dt', 'collection_dt']
    fieldsets = (
        (
            None,
            {
                "fields": (
                ),
            },
        ),
    )
    list_display = (
        "accession_id",
        "part_no",
        "block_or_cassette_seq",
        "slide_seq",
        "sample_type",
        "container_type",
        "previous_step",
        "current_step",
        "next_step",
        "avail_at",
        "pending_action",
        "staining_status",
        "sample_status",
        "sample_id",
        "test_names",
        "label_count",
    )
    readonly_fields = ["sample_type",
                       "container_type",
                       "current_step",
                       "avail_at",
                       "part_no",
                       "body_site",
                       "sub_site",
                       "collection_method",
                       "receive_dt",
                       "receive_dt_timezone",
                       "collection_dt",
                       "collection_dt_timezone",
                       ]
    search_fields = ['accession_id__accession_id']
    date_hierarchy = 'created_dt'
    actions = [print_label_popup, bulk_edit_action, execute_routing, update_test, send_to_staining, start_staining,
               complete_staining, start_imaging,
               image_qcstatus,
               complete_imaging, perform_backward_movement]
    change_form_template = 'admin/sample_change_form.html'
    change_list_template = 'admin/sample_change_list.html'

    def has_module_permission(self, request):
        user_jobtype = request.session.get('currentjobtype', '')
        if '-' in user_jobtype:
            user_jobtype = request.session.get('currentjobtype', '').split('-')[1]
        if user_jobtype in ['IHC']:
            return False
        return True

    class Media:
        js = (
            'js/sample/sample.js',
            'js/util/disable_breadcrumb_links.js',
            'scanner/generic_scanner.js',  # Core scanner
            'scanner/sample_scanner.js',  # Sample configuration
        )

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
        """Override to filter samples based on user's department."""
        qs = super().get_queryset(request)
        qs = qs.exclude(pending_action='MoveToStorage') \
            .filter(custodial_storage_id__isnull=True) \
            .exclude(sample_status__in=['Completed', 'Cancelled']).prefetch_related('sampletestmap_set__test_id')

        if request.user.is_superuser:
            return qs.order_by(
                'accession_id',
                'part_no',
                self.safe_cast('block_or_cassette_seq'),
                self.safe_cast('slide_seq'), 'sample_id',
            )

        user_jobtype = request.session.get('currentjobtype', '')
        user_site = user_jobtype.split('-')[0]
        try:
            jobtype = JobType.objects.get(name=user_jobtype)
            department_id = jobtype.departmentid_id
            department_filter = Q(custodial_department_id=department_id)
            global_storage_filter = Q(
                custodial_department__name__endswith="-Global",  # Global department
                custodial_department__name__startswith=user_site  # Site prefix should match
            )
            return qs.filter(department_filter | global_storage_filter).order_by(
                'accession_id',
                'part_no',
                self.safe_cast('block_or_cassette_seq'),
                self.safe_cast('slide_seq'), 'sample_id',
            )

        except JobType.DoesNotExist:
            return qs.none()

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': [
                    "sample_type",
                    "container_type",
                    "current_step",
                    "avail_at",
                    "part_no",
                    "body_site",
                    "sub_site",
                    "collection_method",
                    "receive_dt",
                    "receive_dt_timezone",
                    "collection_dt",
                    "collection_dt_timezone",
                ]
            })
        ]

        if obj:
            try:
                stm = SampleTestMap.objects.filter(sample_id=obj).first()
            except SampleTestMap.DoesNotExist:
                stm = None

            config_fields = None

            if stm and stm.workflow_id:
                # Existing logic if workflow_id is present in SampleTestMap
                config_fields = WorkflowStepConfigField.objects.filter(
                    test_workflow_step_id__test_id=stm.test_id,
                    test_workflow_step_id__workflow_id=stm.workflow_id,
                    test_workflow_step_id__workflow_step_id__step_id=obj.current_step,
                    test_workflow_step_id__sample_type_id=obj.sample_type,
                    test_workflow_step_id__container_type=obj.container_type,
                    model="IhcWorkflow"
                ).order_by('pk')
            else:
                # Fetch workflow_id via fallback logic from Sample model
                sample_obj = obj
                selected_workflow_id = None
                if not sample_obj.accession_generated:
                    if sample_obj.accession_sample and sample_obj.accession_sample.workflow_id:
                        selected_workflow_id = sample_obj.accession_sample.workflow_id
                else:
                    selected_workflow_id = sample_obj.workflow_id

                # Now find WorkflowStep
                if selected_workflow_id:
                    workflow_step = WorkflowStep.objects.filter(
                        workflow_id=selected_workflow_id,
                        step_id=obj.current_step
                    ).first()
                    if workflow_step:
                        config_fields = WorkflowStepConfigField.objects.filter(
                            workflow_step_id=workflow_step,
                            model="IhcWorkflow"
                        ).order_by('pk')

            if config_fields is not None and config_fields.exists():
                dynamic_fields = list(config_fields.values_list('field_id', flat=True))
                fieldsets.append((f'Attributes for {obj.current_step}', {'fields': dynamic_fields}))

        return fieldsets

    def get_urls(self):
        urls = super().get_urls()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        custom_urls = [
            path('print-label-prompt/', self.admin_site.admin_view(print_label_prompt), name='print_label_prompt'),
            path('print-label-submit/', self.admin_site.admin_view(print_label_submit), name='print_label_submit'),
            path('validate-label-popup/', self.admin_site.admin_view(validate_label_popup),
                 name='validate_label_popup'),
            path(
                'backward-movement-prompt/',
                self.admin_site.admin_view(functools.partial(CommonUtilClass.backward_movement_prompt_view, self)),
                name=f'{app_label}_{model_name}_backward_movement_prompt_view'
            ),
            path(
                'backward-movement-submit/',
                self.admin_site.admin_view(functools.partial(CommonUtilClass.backward_movement_submit_view, self)),
                name=f'{app_label}_{model_name}_backward_movement_submit_view'
            ),
            path(
                'validate-backward-movement-popup/',
                self.admin_site.admin_view(functools.partial(CommonUtilClass.validate_backward_movement_popup, self)),
                name=f'{app_label}_{model_name}_validate_backward_movement_popup'
            ),
            path(
                'validate-update-test-popup/',
                self.admin_site.admin_view(validate_update_test_popup),
                name='validate_update_test_popup'
            ),
            path("update-test-popup/", self.admin_site.admin_view(functools.partial(update_test_popup, self)), name=f"{app_label}_{model_name}_update_test_popup"),
            path("update-test-submit/", self.admin_site.admin_view(functools.partial(update_test_submit, self)), name=f"{app_label}_{model_name}_update_test_submit"),

        ]
        return custom_urls + urls

    def test_names(self, obj):
        return ", ".join(
            stm.test_id.test_name for stm in obj.sampletestmap_set.all() if stm.test_id
        )

    test_names.short_description = "Test Name(s)"
    test_names.admin_order_field = 'sample_id'


def validate_update_test_popup(request):
    ids = request.GET.get('ids', '')
    sample_ids = [s for s in ids.split(',') if s]
    invalid_samples = list(
        IhcWorkflow.objects.filter(
            sample_ptr_id__in=sample_ids
        ).exclude(
            Q(staining_status__isnull=True) | Q(staining_status="")
        ).values_list('sample_ptr_id', flat=True)
    )
    return JsonResponse({'invalid_samples': invalid_samples})


def validate_label_popup(request):
    ids = request.GET.get('ids', '').split(',')
    log.info(f"Validate label popup for sample ids --> {ids}")
    samples = Sample.objects.filter(pk__in=ids)
    if not samples.exists():
        log.error(f"No valid samples found.")
        return JsonResponse({'success': False, 'message': 'No valid samples found.'})

    steps = samples.values_list('current_step', flat=True).distinct()

    if steps.count() > 1:
        log.error(f"Please select samples with the same Current Step.")
        return JsonResponse({
            'success': False,
            'message': 'Please select samples with the same Current Step.'
        })
    log.info(f"Samples Found")
    return JsonResponse({'success': True, 'message': 'Samples Found'})


def print_label_prompt(request):
    ids = request.GET.get('ids', '').split(',')
    printer_category = request.GET.get('printercategory', 'Enterprise Samples')

    samples = Sample.objects.filter(pk__in=ids).select_related('container_type', 'accession_id')

    if printer_category != 'Accessioning':
        printer_category = samples.first().current_step

    printer_selection_data = get_user_printer_selection_data(request, printer_category)

    container_type_ids = [s.container_type_id for s in samples if s.container_type_id]

    clinical_maps = ContainerTypeLabelMethodMap.objects.filter(
        container_type_id__in=container_type_ids
    ).select_related('label_method')

    pharma_maps = ContainerTypePharmaLabelMethodMap.objects.filter(
        container_type_id__in=container_type_ids
    ).select_related('label_method')

    clinical_map_dict = defaultdict(list)
    for ctlm in clinical_maps:
        clinical_map_dict[ctlm.container_type_id].append(ctlm)

    pharma_map_dict = defaultdict(list)
    for ctlm in pharma_maps:
        pharma_map_dict[ctlm.container_type_id].append(ctlm)

    sample_data = []
    for sample in samples:

        label_method_maps = []
        if sample.accession_id and sample.accession_id.accession_category == 'Pharma':
            label_method_maps = pharma_map_dict.get(sample.container_type_id, [])
        else:
            label_method_maps = clinical_map_dict.get(sample.container_type_id, [])

        label_methods = []
        for lm in label_method_maps:
            label_methods.append({
                'id': lm.label_method.label_method_id,
                'name': str(lm.label_method),
                'default': lm.is_default
            })

        sample_data.append({
            'sample': sample,
            'label_methods': label_methods
        })

    return render(request, 'admin/sample/print_label_prompt.html',
                  {'sample_data': sample_data, 'printer_category': printer_category,
                   'printer_selection_data': printer_selection_data})


@csrf_exempt
def print_label_submit(request):
    log.info(f"request.method --> {request.method}")
    if request.method != "POST":
        log.error(f"invalid method")
        return JsonResponse({"status": "invalid method"}, status=405)
    try:
        data = json.loads(request.body)
        rows = data.get("rows", [])
        printer_category = data.get("printer_category", "Enterprise Samples")
        selected_printer_id = data.get("selected_printer_id")
        selected_communication_type = data.get("selected_communication_type")

        if not isinstance(rows, list):
            log.error(f"Invalid data format")
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)

        if not selected_printer_id:
            log.error(f"No printer selected. Please choose a printer to proceed.")
            messages.error(request, "No printer selected. Please choose a printer to proceed.")
            return JsonResponse({"status": "error", "message": "No printer selected"}, status=400)
        if not selected_communication_type:
            log.error(f"Printer communication type is not available. Please select a printer.")
            messages.error(request, "Printer communication type is not available. Please select a printer.")
            return JsonResponse({"status": "error", "message": "Printer communication type not available"}, status=400)

        grouped = defaultdict(list)

        for entry in rows:
            sample_id = entry.get("sample_id")
            label_method_id = entry.get("label_method_id")
            accession_id = entry.get("accession_id")
            part_no = entry.get("part_no")
            container_type = entry.get("container_type")
            block_or_cassette_seq = entry.get("block_or_cassette_seq")  # Ensure this is extracted

            log.info(
                f"Sample: {sample_id}, Accession: {accession_id}, Part: {part_no}, Container: {container_type}, Label Method ID: {label_method_id}")

            grouped[label_method_id].append({
                "sample_id": sample_id,
                "container_type": container_type,
                "accession_id": accession_id,  # Corrected typo here
                "part_no": part_no,
                "block_or_cassette_seq": block_or_cassette_seq
            })

        obj = GenerateLabel()

        all_results = []
        for label_method_id, entries in grouped.items():
            sample_ids = [e["sample_id"] for e in entries]
            result = obj.print_label(request,
                                     sample_ids,
                                     model_pk=sample_ids, model_app_id="sample/Sample",
                                     label_method_id=label_method_id,
                                     communication_type=selected_communication_type,
                                     printer=selected_printer_id,
                                     count=1)
            all_results.append(result)

        successful_prints = 0
        failed_prints = 0
        error_messages = []
        warning_messages = []

        for res in all_results:
            if res and res.get('status') == 'success':
                successful_prints += 1
            elif res and res.get('status') == 'error':
                failed_prints += 1
                error_messages.append(res.get('message', 'An unknown error occurred.'))
            elif res and res.get('status') == 'warning':
                warning_messages.append(res.get('message', 'A warning occurred.'))

        if successful_prints > 0 and failed_prints == 0 and not warning_messages:
            log.info(f"Successfully initiated print jobs for {successful_prints} label method(s).")
            messages.success(request, f"Successfully initiated print jobs for {successful_prints} label method(s).")
        elif successful_prints > 0 and (failed_prints > 0 or warning_messages):
            summary_message = f"Printed {successful_prints} label method(s) successfully."
            if failed_prints > 0:
                summary_message += f" However, {failed_prints} label method(s) failed: {'; '.join(error_messages)}."
            if warning_messages:
                summary_message += f" Warnings: {'; '.join(warning_messages)}."
            log.warning(f"{summary_message}")
            messages.warning(request, summary_message)
        elif failed_prints > 0:
            log.error(f"Failed to print for all selected items. Errors: {'; '.join(error_messages)}")
            messages.error(request, f"Failed to print for all selected items. Errors: {'; '.join(error_messages)}")
        else:
            log.info("No print jobs were initiated or processed.")
            messages.info(request, "No print jobs were initiated or processed.")

        return JsonResponse({"status": "ok"})

    except json.JSONDecodeError:
        log.error("Invalid JSON data received.")
        messages.error(request, "Invalid JSON data received.")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        log.error(f"An unexpected server error occurred during label printing: {e}")
        messages.error(request, f"An unexpected server error occurred during label printing: {e}")
        return JsonResponse({"status": "error", "message": f"Server error: {e}"}, status=500)


def update_test_popup(admin_self, request):
    Sample = apps.get_model("sample", "Sample")
    Test = apps.get_model("tests", "Test")
    SampleTestMap = apps.get_model("sample", "SampleTestMap")
    BodySite = apps.get_model("masterdata", "BodySite")
    BodySiteTestMap = apps.get_model("masterdata", "BodySiteTestMap")

    ids = request.GET.get("ids", "")
    sample_ids = [s for s in ids.split(",") if s]

    samples = list(Sample.objects.filter(sample_id__in=sample_ids))
    # Map: bodysite_name (string) => bodysite_id
    bodysite_qs = BodySite.objects.all()
    bodysite_name_to_id = {b.body_site: b.body_site_id for b in bodysite_qs}
    # For all bodysite IDs used in this batch, bulk fetch test ids
    samples_bodysite_ids = [
        bodysite_name_to_id.get(s.body_site) for s in samples if s.body_site
    ]
    all_bodysite_ids = set([bid for bid in samples_bodysite_ids if bid])
    testmap_qs = BodySiteTestMap.objects.filter(body_site_id__in=all_bodysite_ids)
    # Map: bodysite_id => set([test_id_id, ...])
    bodysite_id_to_tests = {}
    for tm in testmap_qs:
        bodysite_id_to_tests.setdefault(tm.body_site_id, set()).add(tm.test_id_id)

    # Map: sample_id => allowed tests (as Test queryset)
    sample_to_tests = {}
    test_ids_needed = set()
    for s in samples:
        bs_id = bodysite_name_to_id.get(s.body_site)
        allowed_ids = bodysite_id_to_tests.get(bs_id, set())
        if allowed_ids:
            test_ids_needed.update(allowed_ids)
    tests_queryset = Test.objects.filter(pk__in=test_ids_needed)

    # Precompute all Test objects needed
    test_id_to_obj = {t.pk: t for t in tests_queryset}

    # Prepare for template: per sample, get allowed test objects
    sample_rows = []

    # Build a mapping: sample_id -> test_id
    existing_tests = {
        str(stm.sample_id): stm.test_id_id
        for stm in SampleTestMap.objects.filter(sample_id__in=sample_ids)
    }
    for sample in samples:
        bs_id = bodysite_name_to_id.get(sample.body_site)
        allowed_ids = bodysite_id_to_tests.get(bs_id, set())
        test_objs = [test_id_to_obj[tid] for tid in allowed_ids if tid in test_id_to_obj]
        sample_rows.append({
            "sample": sample,
            "tests": test_objs,
            "existing_test_id": existing_tests.get(str(sample.sample_id))
        })

    # the rest of your original code
    accession_filter = request.GET.get('q')
    redirect_url = reverse('controllerapp:ihcworkflow_ihcworkflow_changelist')
    if accession_filter:
        redirect_url += f'?q={accession_filter}'

    is_popup = request.GET.get('_popup') == '1'
    base_template = "admin/popup_base.html" if is_popup else "admin/base_site.html"

    return render(
        request,
        "admin/sample/update_test_popup.html",
        {
            "sample_rows": sample_rows,
            "ids": ids,
            "accession_filter": accession_filter,
            "base_template": base_template,
            "redirect_url": redirect_url,
        }
    )


def update_test_submit(admin_self, request):
    Sample = apps.get_model("sample", "Sample")
    SampleTestMap = apps.get_model("sample", "SampleTestMap")
    IhcWorkflow = apps.get_model("ihcworkflow", "IhcWorkflow")
    Test = apps.get_model("tests", "Test")

    ids = request.POST.get("ids", "")
    sample_ids = [s for s in ids.split(",") if s]
    accession_filter = request.POST.get('q', '')
    redirect_url = reverse('controllerapp:ihcworkflow_ihcworkflow_changelist')
    if accession_filter:
        redirect_url += f'?q={accession_filter}'

    existing_mappings = {
        str(stm.sample_id): stm.test_id_id
        for stm in SampleTestMap.objects.filter(sample_id__in=sample_ids)
    }
    # Collect only samples where a new test is selected (non-blank)
    sample_to_new_test = {}
    for sample_id in sample_ids:
        new_test_id_str = request.POST.get(f"test_{sample_id}")
        if new_test_id_str:
            new_test_id = int(new_test_id_str)
            existing_test_id = existing_mappings.get(sample_id)
            if existing_test_id != new_test_id:
                sample_to_new_test[sample_id] = new_test_id

    if not sample_to_new_test:
        messages.warning(request, "No new test was selected for any sample.")
        return HttpResponse("""
            <script type="text/javascript">
              window.opener.location.reload();
              window.close();
            </script>
            """)

    samples = Sample.objects.filter(sample_id__in=sample_to_new_test.keys())

    # Group child samples by root
    root_to_children = defaultdict(list)
    for sample in samples:
        root_sample = sample.accession_sample_id or sample  # root
        root_to_children[root_sample].append(sample)

    for root_sample, child_samples_list in root_to_children.items():
        # Update only those selected children
        for child_sample in child_samples_list:
            SampleTestMap.objects.filter(sample_id=child_sample).delete()
            test_id = sample_to_new_test.get(str(child_sample.sample_id))
            if test_id:
                SampleTestMap.objects.create(
                    sample_id=child_sample,
                    test_id_id=test_id,
                    test_status="Pending"
                )

        # Sync root with all (not just updated) current children
        all_child_samples = IhcWorkflow.objects.filter(
            sample_ptr_id__accession_sample_id=root_sample
        ).values_list("sample_ptr_id", flat=True)

        child_tests = list(
            SampleTestMap.objects.filter(sample_id__in=all_child_samples)
            .values_list("test_id", flat=True)
            .distinct()
        )

        root_sample_obj = (
            Sample.objects.get(sample_id=root_sample)
            if isinstance(root_sample, str)
            else root_sample
        )
        # Remove extra tests from root
        SampleTestMap.objects.filter(sample_id=root_sample_obj).exclude(
            test_id__in=child_tests
        ).delete()
        # Add missing tests to root with test_status="Initial"
        existing_tests = set(
            SampleTestMap.objects.filter(sample_id=root_sample_obj)
            .values_list("test_id", flat=True)
        )
        for t in child_tests:
            if t not in existing_tests:
                SampleTestMap.objects.create(
                    sample_id=root_sample_obj,
                    test_id_id=t,
                    test_status="Initial"
                )

    messages.success(request, f"Tests updated for {len(sample_to_new_test)} sample(s).")
    return HttpResponse("""
    <script type="text/javascript">
      window.opener.location.reload();
      window.close();
    </script>
    """)


controller.register(IhcWorkflow, IhcWorkflowAdmin)
