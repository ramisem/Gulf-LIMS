import functools
import json
import traceback
from collections import defaultdict
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import admin, messages
from django.db.models import Q, Value, Case, When, IntegerField, CharField, Prefetch
from django.db.models.functions import Coalesce, Cast
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from import_export.formats import base_formats

from controllerapp.views import controller
from reporting.models import ContainerTypeLabelMethodMap, ContainerTypePharmaLabelMethodMap
from routinginfo.util import UtilClass as RoutingUtilClass
from sample.forms import SampleForm
from sample.models import Sample, SampleTestMap, HistoricalSample, StoredSample
from security.models import User, JobType
from tests.models import WorkflowStepConfigField
from util.actions import GenericAction
from util.admin import TZIndependentAdmin, GulfModelAdmin
from util.util import GenerateLabel, UtilClass as CommonUtilClass, \
    get_user_printer_selection_data
from workflows.models import WorkflowStep


class SampleTestAssociation:
    def __init__(self, sample_id, test_codes):
        self._sample_id = sample_id
        self._test_codes = test_codes

    @property
    def sample_id(self):
        return self._sample_id

    @sample_id.setter
    def sample_id(self, value):
        self._sample_id = value

    @property
    def test_codes(self):
        return self._test_codes

    @test_codes.setter
    def test_codes(self, value):
        if not isinstance(value, list):
            raise ValueError("test_codes must be a list")
        self._test_codes = value

    def __repr__(self):
        return f"Sample(sample_id={self.sample_id}, test_codes={self.test_codes})"


@admin.action(description="Route Sample")
def execute_routing(self, request, queryset):
    sample_ids = queryset.values_list('sample_id', flat=True)
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
            self.message_user(request, mark_safe(message), level="INFO")

    else:
        self.message_user(request, "No sample(s) found")


@admin.action(description="Edit")
def bulk_edit_action(self, request, queryset):
    sample_ids = list(queryset.values_list('sample_id', flat=True))
    url = reverse("controllerapp:sample_bulk_edit")
    q = request.GET.get('q', '')
    params = {'ids': ','.join(sample_ids)}
    if q:
        params['q'] = q

    return HttpResponseRedirect(f"{url}?{urlencode(params)}")


@admin.action(description="Perform Microtomy")
def perform_microtomy(self, request, queryset):
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("perform_microtomy", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="PerformMicrotomy", action_desc=action_desc)


@admin.action(description="Move To Storage")
def move_to_storage(self, request, queryset):
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("move_to_storage", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="MoveToStorage", action_desc=action_desc)


@admin.action(description="Create Cassette")
def create_cassette_method(self, request, queryset):
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("create_cassette_method", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="CreateCassette", action_desc=action_desc)


@admin.action(description="Complete Embedding")
def complete_embedding_method(self, request, queryset):
    actions_dict = dict(self.get_actions(request))
    action_desc = actions_dict.get("complete_embedding_method", (None, None, None))[2]
    action_instance = GenericAction()
    action_instance.generic_action_call(request, queryset, desired_action="CompleteEmbedding", action_desc=action_desc)


@admin.action(description="Move To Storage")
def assign_storage(self, request, queryset):
    queryset.update(custodial_storage_id='S-001245')
    self.message_user(request, "Assigned Storage successfully")


@admin.action(description="Prepare Liquid Sample")
def prepare_liquid_sample(self, request, queryset):
    pass


@admin.action(description="Print Labels")
def print_label_popup(self, request, queryset):
    pass


@admin.action(description="Perform Backward Movement")
def perform_backward_movement(self, request, queryset):
    pass


class SampleAdmin(TZIndependentAdmin, GulfModelAdmin):
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
    actions = [bulk_edit_action, execute_routing, create_cassette_method, complete_embedding_method,
               perform_microtomy,
               perform_backward_movement,
               move_to_storage, GulfModelAdmin.delete_custom, prepare_liquid_sample, print_label_popup
               ]
    form = SampleForm
    change_form_template = 'admin/sample_change_form.html'

    def has_module_permission(self, request):
        user_jobtype = request.session.get('currentjobtype', '')
        if '-' in user_jobtype:
            user_jobtype = request.session.get('currentjobtype', '').split('-')[1]
        if user_jobtype in ['IHC', 'Accessioning']:
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
        if "_popup" in request.GET:
            queryset = super().get_queryset(request)
            return queryset.filter(accession_sample__isnull=True).order_by(
                'part_no',
                self.safe_cast('block_or_cassette_seq'),
                self.safe_cast('slide_seq'), 'sample_id',
            )
            return queryset

        """Override to filter samples based on user's department."""
        qs = super().get_queryset(request).exclude(isvisible=False)
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
                custodial_department__name__endswith="-Global",
                custodial_department__name__startswith=user_site
            )
            return qs.filter(department_filter | global_storage_filter).order_by(
                'accession_id',
                'part_no',
                self.safe_cast('block_or_cassette_seq'),
                self.safe_cast('slide_seq'), 'sample_id',
            )

        except JobType.DoesNotExist:
            return qs.none()

    def get_search_fields(self, request):
        if "_popup" in request.GET:
            return ['part_no']
        return self.search_fields

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            accession_id = request.GET.get('accession_id__exact')
            if accession_id:
                part = [part_no.strip() for part_no in search_term.split(',') if part_no.strip()]
                if part:
                    queryset = self.model.objects.filter(part_no__in=part, accession_id=accession_id)
                    if "_popup" in request.GET:
                        queryset = queryset.filter(accession_sample__isnull=True).order_by(
                            'part_no',
                            self.safe_cast('block_or_cassette_seq'),
                            self.safe_cast('slide_seq'), 'sample_id',
                        )

        return queryset, use_distinct

    def changelist_view(self, request, extra_context=None):
        if request.GET.get('_popup'):
            self.list_filter = []
        return super().changelist_view(request, extra_context)

    def get_list_display(self, request):
        if request.GET.get('_popup'):
            return (
                'sample_id', 'part_no', 'block_or_cassette_seq', 'slide_seq', 'container_type', 'sample_type',
                'editable_test_id')
        return super().get_list_display(request)

    def editable_test_id(self, obj):
        if obj.sample_id:
            listsampletestmap = SampleTestMap.objects.filter(sample_id=obj.sample_id)
            listtests = []
            strtests = None
            if listsampletestmap is not None:
                for instance in listsampletestmap:
                    listtests.append(instance.test_id.test_name)
                if listtests is not None:
                    strtests = ",".join(listtests)
                sample_test_association_instance = SampleTestAssociation(obj.sample_id, strtests)
                if sample_test_association_instance is not None:
                    return mark_safe(f"""
                        <input type="text" class="autocomplete-field"
                               data-id="{sample_test_association_instance.sample_id}"
                               data-field="test_id"
                               value="{sample_test_association_instance.test_codes}" readonly style="border: none; background: transparent; cursor: pointer;"/>
                    """)
        return ""

    editable_test_id.short_description = "Test(s)"

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
                    model="Sample"
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
                            model="Sample"
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
            path('smearing-selection-prompt/', self.admin_site.admin_view(smearing_selection_prompt),
                 name='smearing_selection_prompt'),
            path('send-to-prepare-liquid-sample/', self.admin_site.admin_view(send_to_prepare_liquid_sample),
                 name='send_to_prepare_liquid_sample'),
            path('validate-label-popup/', self.admin_site.admin_view(validate_label_popup),
                 name='validate_label_popup'),
            path('validate-smearing-popup/', self.admin_site.admin_view(validate_smearing_popup),
                 name='validate_smearing_popup'),
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
        ]
        return custom_urls + urls

    def test_names(self, obj):
        return ", ".join(
            stm.test_id.test_name for stm in obj.sampletestmap_set.all() if stm.test_id
        )

    test_names.short_description = "Test Name(s)"
    test_names.admin_order_field = 'sample_id'


class SampleTestMapAdmin(admin.ModelAdmin):
    list_display = (
        'sample_id',
        'get_sample_type',
        'get_container_type',
        'editable_test_id',
    )
    list_filter = [
        "sample_id", "sample_id__accession_id"
    ]

    actions = ['delete_selected']

    class Media:
        js = ('js/sample/sample.js',)

    change_form_template = 'admin/change_form.html'

    def get_sample_type(self, obj):
        return obj.sample_id.sample_type.sample_type if obj.sample_id and obj.sample_id.sample_type else "-"

    get_sample_type.short_description = "Sample Type"

    def get_container_type(self, obj):
        return obj.sample_id.container_type.container_type if obj.sample_id and obj.sample_id.container_type else "-"

    get_container_type.short_description = "Container Type"

    def editable_test_id(self, obj):
        if obj.test_id:
            return mark_safe(f"""
                <input type="text" class="autocomplete-field" 
                       data-id="{obj.sample_test_map_id}" 
                       data-field="test_id" 
                       value="{obj.test_id.test_name if obj.test_id else ''}" readonly style="border: none; background: transparent; cursor: pointer;"/>
            """)
        return ""

    editable_test_id.short_description = "Test ID"

    def delete_selected(self, request, queryset):
        queryset.delete()

    delete_selected.short_description = "Delete selected products"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "_popup" in request.GET:
            if "delete_selected" not in actions:
                actions["delete_selected"] = (
                    self.__class__.delete_selected,
                    "delete_selected",
                    "Delete selected products",
                )
        else:
            del actions['delete_selected']
        return actions


IhcWorkflow = apps.get_model('ihcworkflow', 'IhcWorkflow')


class IhcWorkflowInline(admin.StackedInline):
    model = IhcWorkflow
    fk_name = 'sample_ptr'
    verbose_name_plural = "IHC Workflow Attributes"
    extra = 0
    can_delete = False

    def get_fields(self, request, obj=None):
        if not obj:
            return []

        try:
            stm = SampleTestMap.objects.filter(sample_id=obj).first()
            if not stm:
                return []

            allowed_models = ["IhcWorkflow"]
            config_fields = WorkflowStepConfigField.objects.filter(
                test_workflow_step_id__test_id=stm.test_id,
                test_workflow_step_id__workflow_id=stm.workflow_id,
                model__in=allowed_models,
            ).order_by('pk')

            dynamic_fields = list(config_fields.values_list('field_id', flat=True))
            return dynamic_fields

        except Exception as e:
            # Log the error if needed
            return []

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)


class HistoricalSampleAdmin(TZIndependentAdmin):
    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    inlines = [IhcWorkflowInline]

    tz_independent_fields = ['receive_dt', 'collection_dt']
    fieldsets = (
        (
            "",
            {
                "fields": (
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
        "sample_status",
        "sample_id",
        "test_names",

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
    list_filter = [
        "accession_id",
    ]
    date_hierarchy = 'created_dt'
    actions = [bulk_edit_action, assign_storage
               ]
    form = SampleForm
    change_form_template = 'admin/sample_change_form.html'

    class Media:
        js = ('js/sample/sample.js',)

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
        qs = qs.filter(
            sample_status__in=['Completed', 'Cancelled'],
            custodial_storage_id__isnull=True
        ).exclude(pending_action='MoveToStorage').prefetch_related('sampletestmap_set__test_id')
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
                custodial_department__name__endswith="-Global",
                custodial_department__name__startswith=user_site
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

            if stm:
                allowed_models = ["Sample"]
                base_qs = WorkflowStepConfigField.objects.filter(
                    test_workflow_step_id__test_id=stm.test_id,
                    test_workflow_step_id__workflow_id=stm.workflow_id,
                    # test_workflow_step_id__sample_type_id=obj.sample_type,
                    # test_workflow_step_id__container_type=obj.container_type,
                    model__in=allowed_models,
                )

                config_fields = base_qs

                if config_fields.exists():
                    dynamic_fields = list(config_fields.values_list('field_id', flat=True))
                    fieldsets.append((f'Enterprise Attributes', {'fields': dynamic_fields}))

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        # Append dynamic fields only if obj is present
        dynamic_fields = []
        if obj:
            try:
                stm = SampleTestMap.objects.filter(sample_id=obj).first()
                if stm:
                    allowed_models = ["Sample"]
                    config_fields = WorkflowStepConfigField.objects.filter(
                        test_workflow_step_id__test_id=stm.test_id,
                        test_workflow_step_id__workflow_id=stm.workflow_id,
                        model__in=allowed_models,
                    )
                    dynamic_fields = list(config_fields.values_list('field_id', flat=True))
            except SampleTestMap.DoesNotExist:
                pass

        return self.readonly_fields + dynamic_fields

    def test_names(self, obj):
        return ", ".join(
            stm.test_id.test_name for stm in obj.sampletestmap_set.all() if stm.test_id
        )

    test_names.short_description = "Test Name(s)"
    test_names.admin_order_field = 'sample_id'


class StoredSampleAdmin(TZIndependentAdmin):
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
        "sample_status",
        "sample_id",
        "test_names",
        "label_count",
    )
    list_display_links = None
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
    list_filter = [
        "accession_id",
    ]
    date_hierarchy = 'created_dt'
    actions = [assign_storage, print_label_popup]
    form = SampleForm
    change_form_template = 'admin/sample_change_form.html'

    class Media:
        js = ('js/sample/sample.js',)

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
        qs = qs.filter(
            Q(custodial_storage_id__isnull=False) | Q(pending_action='MoveToStorage')
        ).prefetch_related('sampletestmap_set__test_id')
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
                custodial_department__name__endswith="-Global",
                custodial_department__name__startswith=user_site
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
                stm = SampleTestMap.objects.get(sample_id=obj)
            except SampleTestMap.DoesNotExist:
                stm = None

            if stm:
                # One single queryset: using Django’s double-underscore lookup to filter through the
                # foreign key relationship from WorkflowStepConfigField to TestWorkflowStep.
                config_fields = WorkflowStepConfigField.objects.filter(
                    test_workflow_step_id__test_id=stm.test_id,
                    test_workflow_step_id__workflow_id=stm.workflow_id,
                    test_workflow_step_id__workflow_step_id__step_id=obj.current_step,
                    test_workflow_step_id__sample_type_id=obj.sample_type,
                    test_workflow_step_id__container_type=obj.container_type,
                    model="Sample"
                )

                if config_fields.exists():
                    dynamic_fields = list(config_fields.values_list('field_id', flat=True))
                    fieldsets.append((f'Attributes for {obj.current_step}', {'fields': dynamic_fields}))

        return fieldsets

    def test_names(self, obj):
        return ", ".join(
            stm.test_id.test_name for stm in obj.sampletestmap_set.all() if stm.test_id
        )

    test_names.short_description = "Test Name(s)"
    test_names.admin_order_field = 'sample_id'


def smearing_selection_prompt(request):
    ids = request.GET.get('ids', '').split(',')
    samples = Sample.objects.filter(pk__in=ids).order_by('pk')

    sample_data = []
    for sample in samples:
        sample_data.append({
            'sample': sample
        })

    sample_test_data = []
    sample_tests = Sample.objects.filter(sample_id__in=ids).prefetch_related(
        Prefetch(
            'sampletestmap_set',
            queryset=SampleTestMap.objects.select_related('test_id')
        )
    ).order_by('sample_id')

    for sample in sample_tests:
        for test_map in sample.sampletestmap_set.all():
            test = test_map.test_id
            sample_test_data.append({
                'sample': sample,
                'test_name': test.test_name,
                'test_id': test.test_id,
                'default_smearing': test.smear_process,
                'sample_test_map_id': test_map.sample_test_map_id
            })

    return render(request, 'admin/sample/smearing_selection_prompt.html',
                  {'sample_data': sample_data, 'sample_test_data': sample_test_data, 'base_template': "admin/popup_base.html"})


@csrf_exempt
def send_to_prepare_liquid_sample(request):
    if request.method != "POST":
        return JsonResponse({"status": "invalid method"}, status=405)
    try:
        data = json.loads(request.body)
        prep_type_dict = data
        if not isinstance(prep_type_dict, list):
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)

        if prep_type_dict:
            sample_ids = [row["sample_id"] for row in prep_type_dict if "sample_id" in row]
            queryset = Sample.objects.filter(pk__in=sample_ids)
            samples_by_id = {sample.sample_id: sample for sample in queryset}

            smear_counts = {}
            for row in prep_type_dict:
                prep_type = row.get("prep_type")
                sample_id = row.get("sample_id")

                if prep_type in ["Manual", "Thin Prep"]:
                    if sample_id not in smear_counts:
                        smear_counts[sample_id] = 0
                    smear_counts[sample_id] += 1

            validation_errors = []

            for sample_id, actual_smear_count in smear_counts.items():
                sample = samples_by_id.get(sample_id)
                if sample is None:
                    validation_errors.append(f"Sample with ID {sample_id} not found.")
                    continue

                expected_smear_count = (sample.num_of_manualsmear_slides or 0) + (sample.num_of_thinprep_slides or 0)

                if actual_smear_count != expected_smear_count:
                    validation_errors.append(
                        f"Sample ID {sample_id}: Slide# and test count mismatch found. Number of tests associated with a selected sample(s) should match with total number of Thin Prep and Manual Smear Slides."
                    )

            if validation_errors:
                return JsonResponse({
                    "status": "error",
                    "message": "Smear count validation failed.",
                    "details": validation_errors
                }, status=400)

            action_instance = GenericAction()
            action_instance.generic_action_call(request, queryset, desired_action="PrepareLiquidSample",
                                                action_desc="Prepare Liquid Sample", prep_type_dict=prep_type_dict)
        else:
            messages.error(request, "No Sample Data Submitted for Processing.")
            return JsonResponse({"status": "No data"})
        return JsonResponse({"status": "ok"})
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def validate_label_popup(request):
    ids = request.GET.get('ids', '').split(',')
    samples = Sample.objects.filter(pk__in=ids)
    if not samples.exists():
        return JsonResponse({'success': False, 'message': 'No valid samples found.'})

    steps = samples.values_list('current_step', flat=True).distinct()

    if steps.count() > 1:
        return JsonResponse({
            'success': False,
            'message': 'Please select samples with the same Current Step.'
        })
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
    if request.method != "POST":
        return JsonResponse({"status": "invalid method"}, status=405)
    try:
        data = json.loads(request.body)
        rows = data.get("rows", [])
        printer_category = data.get("printer_category", "Enterprise Samples")
        selected_printer_id = data.get("selected_printer_id")
        selected_communication_type = data.get("selected_communication_type")

        if not isinstance(rows, list):
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)

        if not selected_printer_id:
            messages.error(request, "No printer selected. Please choose a printer to proceed.")
            return JsonResponse({"status": "error", "message": "No printer selected"}, status=400)
        if not selected_communication_type:
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

            print(
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
            messages.success(request, f"Successfully initiated print jobs for {successful_prints} label method(s).")
        elif successful_prints > 0 and (failed_prints > 0 or warning_messages):
            summary_message = f"Printed {successful_prints} label method(s) successfully."
            if failed_prints > 0:
                summary_message += f" However, {failed_prints} label method(s) failed: {'; '.join(error_messages)}."
            if warning_messages:
                summary_message += f" Warnings: {'; '.join(warning_messages)}."
            messages.warning(request, summary_message)
        elif failed_prints > 0:
            messages.error(request, f"Failed to print for all selected items. Errors: {'; '.join(error_messages)}")
        else:
            messages.info(request, "No print jobs were initiated or processed.")

        return JsonResponse({"status": "ok"})

    except json.JSONDecodeError:
        messages.error(request, "Invalid JSON data received.")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        messages.error(request, f"An unexpected server error occurred during label printing: {e}")
        return JsonResponse({"status": "error", "message": f"Server error: {e}"}, status=500)


def validate_smearing_popup(request):
    ids = request.GET.get('ids', '').split(',')
    samples = Sample.objects.filter(pk__in=ids)
    if not samples.exists():
        return JsonResponse({'success': False, 'message': 'No valid samples found.'})

    pending_action = samples.values_list('pending_action', flat=True).distinct()

    if pending_action.count() > 1:
        return JsonResponse({
            'success': False,
            'message': 'Please select only the samples Pending for Prepare Liquid Sample.'
        })
    else:
        if pending_action[0] == 'PrepareLiquidSample':
            missing_gross_desc = samples.filter(gross_description__isnull=True).count() + samples.filter(
                gross_description="").count()
            if missing_gross_desc > 0:
                return JsonResponse({
                    'success': False,
                    'message': 'All selected samples must have Gross Description populated.'
                })
            else:
                return JsonResponse({'success': True, 'message': 'Samples Found'})
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please select only the samples Pending for Prepare Liquid Sample.'
            })


controller.register(Sample, SampleAdmin)
controller.register(HistoricalSample, HistoricalSampleAdmin)
controller.register(StoredSample, StoredSampleAdmin)
