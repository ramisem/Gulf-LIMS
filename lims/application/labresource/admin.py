from django.contrib import messages
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from controllerapp.views import controller
from labresource.models import InstrumentType, InstrumentModel
from labresource.resources import InstrumentTypeResource, InstrumentModelResource
from security.models import User


class InstrumentTypeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "instrument_type",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "instrument_type",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "instrument_type",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [InstrumentTypeResource]
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


class InstrumentModelAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "instrument_model",
                    "instrument_type",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "instrument_model",
        "instrument_type",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "instrument_model",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [InstrumentModelResource]
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


controller.register(InstrumentType, InstrumentTypeAdmin)
controller.register(InstrumentModel, InstrumentModelAdmin)
