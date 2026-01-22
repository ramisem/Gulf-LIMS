import datetime
from django.db import connection
from django.contrib import admin, messages

from controllerapp.views import controller
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats
from reporting.forms import LabelMethodForm, PrinterForm
from security.models import User
from reporting.models import LabelMethod, Printer
from util.util import GenerateLabel, get_printer_by_category

from reporting.resources import LabelMethodResource


class PrinterAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "printer_id",
                    "printer_name",
                    "printer_path",
                    "communication_type",
                ),
            },
        ),
    )
    list_display = (
        "printer_id",
        "printer_name",
        "printer_path",
        "communication_type",
    )
    form = PrinterForm
    date_hierarchy = 'created_dt'
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


class LabelMethodAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "label_method_name",
                    "label_method_version_id",
                    "label_method_desc",
                    "s3bucket",
                    "export_location",
                    "designer_format",
                    "is_bio_pharma_label",
                    "label_query",
                    "delimiter",
                    "file_format",
                    "show_header",
                    "show_fields",
                ),
            },
        ),
    )
    list_display = (
        "label_method_name",
        "label_method_version_id",
        "label_method_desc",
        "s3bucket",
        "export_location",
        "designer_format",
        "is_bio_pharma_label",
        "created_dt",
        "created_by",
    )
    search_fields = ['label_method_name', 'label_method_version_id']
    date_hierarchy = 'created_dt'
    resource_classes = [LabelMethodResource]
    form = LabelMethodForm
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


controller.register(LabelMethod, LabelMethodAdmin)
controller.register(Printer, PrinterAdmin)
