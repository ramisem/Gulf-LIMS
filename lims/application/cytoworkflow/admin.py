from django.contrib import admin, messages
from django.db.models import Q
from django.utils.safestring import mark_safe
from import_export.formats import base_formats

from controllerapp.views import controller
from cytoworkflow.models import CytoWorkflow
from logutil.log import log
from routinginfo.util import UtilClass
from security.models import User, JobType


@admin.action(description="Execute Routing")
def execute_routing(self, request, queryset):
    sample_ids = queryset.values_list('sample_id', flat=True)
    log.info(f"sample_ids ---> {sample_ids}")
    if sample_ids:
        success_samples = UtilClass.process_workflow_steps_wetlab(self, request, sample_ids, accession_flag='N')
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
            log.info(f"Routing is successful for sample ids ---> {sample_ids}")
            self.message_user(request, mark_safe(message), level="INFO")

    else:
        log.error(f"No sample(s) found")
        self.message_user(request, "No sample(s) found")


class CytoWorkflowAdmin(admin.ModelAdmin):
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

                ),
            },
        ),
    )
    list_display = (
        "sample_id",
        "container_type",
        "sample_type",
        "custodial_department",
        "custodial_user",
        "custodial_storage_id",
        "previous_step",
        "current_step",
        "next_step",
        "avail_at",

    )
    list_filter = [
        "sample_id",
    ]
    date_hierarchy = 'created_dt'
    actions = [execute_routing]
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

    def get_queryset(self, request):
        """Override to filter samples based on user's department."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # Superusers can see all samples

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
            return qs.filter(department_filter | global_storage_filter)

        except JobType.DoesNotExist:
            return qs.none()


controller.register(CytoWorkflow, CytoWorkflowAdmin)
