from django.contrib import admin, messages
from import_export.formats import base_formats
from controllerapp.views import controller
from security.models import User
from routinginfo.models import RoutingInfo


class RoutingInfoAdmin(admin.ModelAdmin):

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

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
        "sample_id",
        "from_step",
        "to_step",
        "from_department",
        "to_department",
        "from_user",
        "to_user",
    )
    list_display_links = None
    list_filter = [
        "sample_id",
    ]
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

    def get_import_formats(self):
        formats = (
            base_formats.CSV,
        )
        return [f for f in formats if f().can_export()]


controller.register(RoutingInfo, RoutingInfoAdmin)
