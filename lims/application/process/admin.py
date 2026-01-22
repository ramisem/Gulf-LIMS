from django.contrib import admin, messages
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats import base_formats

from controllerapp.views import controller
from process.models import SampleType, ContainerType, SampleTypeContainerType, ConsumableType
from process.resources import SampleTypeResource, ContainerTypeResource, ConsumableTypeResource
from reporting.models import ContainerTypeLabelMethodMap, LabelMethod, ContainerTypePharmaLabelMethodMap
from security.models import User


class SampleTypeAdmin(ImportExportActionModelAdmin):
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
                    "sample_type",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "sample_type",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "sample_type",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [SampleTypeResource]
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


class SampleTypeContainerTypeInline(admin.TabularInline):
    model = SampleTypeContainerType
    fields = (
        "sample_type_id",
    )
    extra = 0


class ContainerTypeLabelMethodMapInline(admin.TabularInline):
    model = ContainerTypeLabelMethodMap
    extra = 1
    verbose_name = "Clinical Label Method Mapping"
    verbose_name_plural = "Clinical Label Method Mappings"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restricts the label_method dropdown to show only Clinical labels.
        """
        if db_field.name == "label_method":
            kwargs["queryset"] = LabelMethod.objects.filter(is_bio_pharma_label=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    class Media:
        js = ['js/reporting/label_method_mappings.js']


class ContainerTypePharmaLabelMethodMapInline(admin.TabularInline):
    model = ContainerTypePharmaLabelMethodMap
    extra = 1
    verbose_name = "Pharma Label Method Mapping"
    verbose_name_plural = "Pharma Label Method Mappings"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restricts the label_method dropdown to show only BioPharma labels.
        """
        if db_field.name == "label_method":
            kwargs["queryset"] = LabelMethod.objects.filter(is_bio_pharma_label=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    class Media:
        js = ['js/reporting/label_method_mappings.js']


class ContainerTypeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "container_type",
                    "description",
                    "child_sample_creation",
                    "gen_block_or_cassette_seq",
                    "gen_slide_seq",
                    "is_liquid",
                    "workflow_id"
                ),
            },
        ),
    )
    list_display = (
        "container_type",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "container_type",
    ]
    date_hierarchy = 'created_dt'
    inlines = [SampleTypeContainerTypeInline, ContainerTypeLabelMethodMapInline,
               ContainerTypePharmaLabelMethodMapInline]
    resource_classes = [ContainerTypeResource]
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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # After saving, ensure only one is_default=True exists
        container_type = form.instance
        default_maps = container_type.label_methods.filter(is_default=True)

        if default_maps.count() > 1:
            # Keep the first one, unset others
            first = default_maps.first()
            container_type.label_methods.exclude(pk=first.pk).update(is_default=False)

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


class ConsumableTypeAdmin(ImportExportActionModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "consumable_type",
                    "description",
                ),
            },
        ),
    )
    list_display = (
        "consumable_type",
        "description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "consumable_type",
    ]
    date_hierarchy = 'created_dt'
    resource_classes = [ConsumableTypeResource]
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


controller.register(SampleType, SampleTypeAdmin)
controller.register(ContainerType, ContainerTypeAdmin)
controller.register(ConsumableType, ConsumableTypeAdmin)
