from django.contrib import admin, messages
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from controllerapp.views import controller
from security.models import User
from tests.forms import WorkflowStepConfigFieldForm
from tests.models import WorkflowStepConfigField, TestWorkflowStepActionMap
from workflows.forms import WorkflowStepInlineForm, ModalityModelMapForm
from workflows.models import Workflow, WorkflowStep, ModalityModelMap
from workflows.resources import WorkflowResource, ModalityModelMapResource


class WorkflowStepInline(admin.StackedInline):
    model = WorkflowStep
    fields = (
        "step_id",
        "step_no",
        "department",
        "workflow_type",
        "backward_movement"
    )
    form = WorkflowStepInlineForm
    extra = 0


class WorkflowAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "workflow_name",
                    "description",
                    "methodology",
                ),
            },
        ),
    )
    list_display = (
        "workflow_name",
        "description",
        "methodology",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "workflow_name",
    ]
    date_hierarchy = 'created_dt'
    inlines = [WorkflowStepInline]
    resource_classes = [WorkflowResource]
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


class ModalityModelMapAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "modality",
                    "model",
                ),
            },
        ),
    )
    list_display = (
        "modality",
        "model",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "modality",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [ModalityModelMapResource]
    form = ModalityModelMapForm
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
                    "workflow_step_id",
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


class WorkflowStepAdmin(ImportExportActionModelAdmin):
    fields = (
        "workflow_id",
        "step_id",
        "step_no",
        "department",
        "workflow_type",
    )
    extra = 0
    readonly_fields = ["workflow_id",
                       "step_id",
                       "step_no",
                       "department",
                       "workflow_type", ]
    list_display = (
        "step_id",
        "step_no",
        "department",
        "workflow_type",
        "workflow_id",

    )
    list_filter = [
        "workflow_id"
    ]
    date_hierarchy = 'created_dt'
    inlines = [WorkflowStepConfigFieldAdmin, TestWorkflowStepActionMapInline]
    # resource_classes = [WorkflowStepResource]
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


controller.register(Workflow, WorkflowAdmin)
controller.register(ModalityModelMap, ModalityModelMapAdmin)
controller.register(WorkflowStep, WorkflowStepAdmin)
