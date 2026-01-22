import json

from django.contrib import admin, messages
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from controllerapp.views import controller
from security.models import User
from tests.forms import TestForm, TestWorkflowStepInlineForm, TestWFSTPInstrumentMapInlineForm, \
    TestWFSTPConsumableMapInlineForm, WorkflowStepConfigFieldForm, TestAnalyteForm
from tests.models import Test, Units, Analyte, ICDCode, CPTCode, TestAnalyte, TestCPTCodeMap, TestAttribute, \
    TestWorkflowStep, TestWFSTPInstrumentMap, TestWFSTPConsumableMap, WorkflowStepConfigField, TestWorkflowStepActionMap
from tests.resources import TestResource, UnitsResource, AnalyteResource, ICDCodeResource, CPTCodeResource, \
    TestWorkflowStepResource
from django.conf import settings

# Register your models here.

class TestAnalyteInline(admin.StackedInline):
    model = TestAnalyte
    fields = (
        "analyte_id",
        "input_mode",
        "data_type",
        "dropdown_reference_type",
        "dropdown_sql",
        "decimal_precision",
        "operator1",
        "value1",
        "value1_unit",
        "condition",
        "operator2",
        "value2",
        "value2_unit",
        "value_text",
        "is_reportable",
    )
    extra = 0
    form = TestAnalyteForm

    class Media:
        js = ('js/tests/test_analyte.js', 'js/util/util.js',)


class TestCPTCodeMapInline(admin.StackedInline):
    model = TestCPTCodeMap
    fields = (
        "cpt_code_id",
    )
    extra = 0


class TestAttributeInline(admin.StackedInline):
    model = TestAttribute
    fields = (
        "test_attribute_id",
        "test_workflow_step_id",
        "test_attribute",
        "value",
    )
    extra = 0

    class Media:
        js = ('js/tests/test_attribute.js', 'js/util/util.js',)


class TestWorkflowStepInline(admin.StackedInline):
    model = TestWorkflowStep
    fields = (
        "test_workflow_step_id",
        "test_id",
        "workflow_id",
        "sample_type_id",
        "container_type",
        "workflow_step_id",
        'step_no', 'workflow_type', 'backward_movement'
    )
    extra = 0
    readonly_fields = ['step_no', 'workflow_type']
    form = TestWorkflowStepInlineForm

    class Media:
        js = ('js/tests/test_workflow_step.js', 'js/util/util.js',)


class TestWFSTPInstrumentMapInline(admin.StackedInline):
    model = TestWFSTPInstrumentMap
    fields = (
        "test_wf_stp_instrument_map_id",
        "test_id",
        "workflow_id",
        "sample_type_id",
        "container_type",
        "workflow_step_id",
        'step_no',
        'workflow_type',
        "instrument_type_id",
    )
    extra = 0
    readonly_fields = ['step_no', 'workflow_type']
    form = TestWFSTPInstrumentMapInlineForm

    class Media:
        js = ('js/tests/test_wf_stp_instrument_map.js', 'js/util/util.js',)


class TestWFSTPConsumableMapInline(admin.StackedInline):
    model = TestWFSTPConsumableMap
    fields = (
        "test_wf_stp_consumable_map_id",
        "test_id",
        "workflow_id",
        "sample_type_id",
        "container_type",
        "workflow_step_id",
        'step_no',
        'workflow_type',
        "consumable_type_id",
    )
    extra = 0
    readonly_fields = ['step_no', 'workflow_type']
    form = TestWFSTPConsumableMapInlineForm

    class Media:
        js = ('js/tests/test_wf_stp_consumable_map.js', 'js/util/util.js',)


class TestAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "test_name",
                    "version",
                    "description",
                    "active_flag",
                    "smear_process"
                ),
            },
        ),
    )
    list_display = (
        "test_name",
        "version",
        "description",
        "active_flag_display",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "test_name",
    ]
    date_hierarchy = 'created_dt'
    inlines = [TestAnalyteInline, TestCPTCodeMapInline, TestWorkflowStepInline, TestAttributeInline,
               TestWFSTPInstrumentMapInline, TestWFSTPConsumableMapInline]
    resource_classes = [TestResource]
    actions = ['return_selected_values']
    form = TestForm
    change_form_template = 'admin/change_form.html'

    def has_module_permission(self, request):
        user_jobtype = request.session.get('currentjobtype', '')
        if '-' in user_jobtype:
            user_jobtype = request.session.get('currentjobtype', '').split('-')[1]
        if user_jobtype in ['Accessioning']:
            return False
        return True

    def active_flag_display(self, obj):
        return "Yes" if obj.active_flag == 'Y' else "No" if obj.active_flag == 'N' else obj.active_flag

    active_flag_display.short_description = "Active Flag"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "_popup" in request.GET:
            if "return_selected_values" not in actions:
                actions["return_selected_values"] = (
                    self.__class__.return_selected_values,
                    "return_selected_values",
                    "Return Selected Values",
                )
            if "export_admin_action" in actions:
                del actions['export_admin_action']
        else:
            del actions['return_selected_values']
        return actions

    def return_selected_values(self, request, queryset):
        selected_values = list(queryset.values_list("test_name", "test_id"))
        if "_popup" in request.GET:
            return render(request, "admin/return_selected_values.html",
                          {"selected_values": mark_safe(json.dumps(selected_values))})
        return JsonResponse({"selected_values": selected_values})

    return_selected_values.short_description = "Return selected values"

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        gulf_test_name = getattr(settings, "TEST_ID_GULF", "GulfTest")
        # If GulfTest is stored as test_id, change to test_id=gulf_test_name
        return qs.exclude(test_name=gulf_test_name)

class UnitsAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "unit",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "unit",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "unit",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [UnitsResource]
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


class AnalyteAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "analyte",
                    "description",
                    "unit_id",
                ),
            },
        ),
    )
    list_display = (
        "analyte",
        "description",
        "unit_id",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "analyte",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [AnalyteResource]
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


class ICDCodeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "icd_code",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "icd_code",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "icd_code",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [ICDCodeResource]
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


class CPTCodeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "cpt_code",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "cpt_code",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "cpt_code",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [CPTCodeResource]
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


class WorkflowStepConfigFieldAdmin(admin.StackedInline):
    model = WorkflowStepConfigField
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "test_workflow_step_id",
                    "model",
                    "field_id",
                ),
            },
        ),
    )
    extra = 0
    form = WorkflowStepConfigFieldForm

    class Media:
        js = ('js/tests/workflow_step_config_field.js', 'js/util/util.js',)


class TestWorkflowStepActionMapInline(admin.StackedInline):
    model = TestWorkflowStepActionMap
    fields = (
        "action",
        "action_method",
        "sequence",
    )
    extra = 0


class TestWorkflowStepAdmin(ImportExportActionModelAdmin):
    fields = (
        "test_id",
        "version",
        "sample_type_id",
        "container_type",
        "workflow_id",
        "workflow_step_id",
        'step_no',
        "backward_movement"
    )
    extra = 0
    readonly_fields = ['test_id',
                       'version',
                       'sample_type_id',
                       "container_type",
                       'workflow_id',
                       'workflow_step_id',
                       'step_no']
    list_display = (
        "test_id",
        "version",
        "sample_type_id",
        "container_type",
        "workflow_id",
        "workflow_step_id",
        'step_no',

    )
    list_filter = [
        "test_id"
    ]
    date_hierarchy = 'created_dt'
    inlines = [WorkflowStepConfigFieldAdmin, TestWorkflowStepActionMapInline]
    resource_classes = [TestWorkflowStepResource]
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


controller.register(Test, TestAdmin)
controller.register(Units, UnitsAdmin)
controller.register(Analyte, AnalyteAdmin)
controller.register(ICDCode, ICDCodeAdmin)
controller.register(CPTCode, CPTCodeAdmin)
controller.register(TestWorkflowStep, TestWorkflowStepAdmin)
