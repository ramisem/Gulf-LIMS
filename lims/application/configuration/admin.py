from django.contrib import admin, messages
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from configuration.models import RefValues, ReferenceType
from configuration.resources import ReferenceTypeResource
from controllerapp.views import controller
from security.models import User


class RefValuesInline(admin.TabularInline):
    model = RefValues
    fields = (
        "value",
        "display_value",
    )
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        """
        Make inline fields read-only if the parent ReferenceType is system-level
        and the user is not a superuser.
        """
        if obj and obj.is_system_level and not request.user.is_superuser:
            return self.fields
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        """
        Prevent adding new RefValues if the parent ReferenceType is system-level
        and the user is not a superuser.
        """
        if obj and obj.is_system_level and not request.user.is_superuser:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deleting existing RefValues if the parent ReferenceType is system-level
        and the user is not a superuser.
        """
        if obj and obj.is_system_level and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


class ReferenceTypeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "is_system_level",
                ),
            },
        ),
    )
    list_display = (
        "name",
        "description",
        "created_dt",
        "created_by",
        "is_system_level",
    )
    list_filter = [
        "is_system_level",
        "name",
    ]
    date_hierarchy = 'created_dt'
    inlines = [RefValuesInline]
    resource_classes = [ReferenceTypeResource]
    change_form_template = 'admin/change_form.html'

    def get_form(self, request, obj=None, **kwargs):
        """
        Dynamically creates the form for the admin, excluding the 'is_system_level'
        field for any user who is not a superuser.
        """
        if not request.user.is_superuser:
            kwargs['exclude'] = ['is_system_level']

        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        """
        Dynamically removes the 'is_system_level' field from the form's layout
        for any user who is not a superuser.
        """
        fieldsets = super().get_fieldsets(request, obj)

        if not request.user.is_superuser:
            new_fieldsets = []
            for name, options in fieldsets:
                new_options = options.copy()
                new_options['fields'] = tuple(f for f in options.get('fields', ()) if f != 'is_system_level')
                new_fieldsets.append((name, new_options))
            return tuple(new_fieldsets)

        return fieldsets


    def get_readonly_fields(self, request, obj=None):
        """
        - Superusers can edit everything.
        - Non-superusers cannot edit existing system-level objects.
        """
        if request.user.is_superuser:
            return []

        if obj and obj.is_system_level:
            all_fields = [field.name for field in self.model._meta.fields if field.name != self.model._meta.pk.name]
            return all_fields

        return []

    def has_delete_permission(self, request, obj=None):
        """
        Prevent non-superusers from deleting system-level objects.
        """
        if not super().has_delete_permission(request, obj):
            return False

        if obj and obj.is_system_level and not request.user.is_superuser:
            return False

        return True

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
        """
        Show all Reference Types to everyone. Permissions are handled by other methods.
        """
        return super().get_queryset(request)


controller.register(ReferenceType, ReferenceTypeAdmin)
