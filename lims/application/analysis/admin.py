import importlib
import os
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Q, CharField, Case, When, Value, F
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from controllerapp.views import controller
import json
from django.template import loader
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.admin import helpers

from analysis.forms import ReportOptionDtlForm, MergeReportingDtlForm, MergeReportingForm, ReportOptionForm, \
    HistoricMergeReportingForm
from analysis.models import ReportOption, ReportOptionDtl, HistoricalReportOption, MergeReporting, MergeReportingDtl, \
    HistoricalMergeReporting
from controllerapp.views import controller
from routinginfo.util import UtilClass
from security.forms import User
from util.actions import GenericAction
from util.admin import TZIndependentAdmin
from logutil.log import log


@admin.action(description="Route Report Option")
def execute_routing(self, request, queryset):
    report_option_id = queryset.values_list('report_option_id', flat=True)
    log.info(f"report_option_id ---> {report_option_id}")
    if report_option_id:
        success_report_options = UtilClass.process_workflow_steps_drylab(self, request, queryset, report_option_id,
                                                                         accession_flag='N')
        if success_report_options:
            table_rows = "".join(
                [f"<tr><td>{reportoption['report_option_id']}</td><td>{reportoption['current_step']}</td></tr>" for
                 reportoption in
                 success_report_options]
            )

            message = f"""
               <p><strong>Routed Report Options to below step:</strong></p>
                        <button onclick="toggleTable()" style="margin-bottom: 10px; padding: 5px 10px; background-color: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px;">
                            Expand/Collapse
                        </button>
                        <div id="reportOptionTable" style="display: none;">
                            <table border="1" cellpadding="2" cellspacing="0" style="border-collapse: collapse; width: 50%;">
                                <tr><th>Report Option ID</th><th>Next Step</th></tr>
                                {table_rows}
                            </table>
                        </div>


                    <script>
                        function toggleTable() {{
                            var table = document.getElementById("reportOptionTable");
                            if (table.style.display === "none") {{
                                table.style.display = "block";
                            }} else {{
                                table.style.display = "none";
                            }}
                        }}
                    </script>
                """
            log.info(f"Successful Reportoption routing ---> {success_report_options}")
            self.message_user(request, mark_safe(message), level="INFO")

    else:
        log.error("No reportoption(s) found")
        self.message_user(request, "No reportoption(s) found")


@admin.action(description="Amend Report")
def amend_merge_report(self, request, queryset):
    """
    This is for amending merge report.

    """
    pass


@admin.action(description="Generate Report")
def generate_report(self, request, queryset):
    # This will remain as is or call generic actions as implemented in your actions.py
    # This is a placeholder for manual admin action integration if needed
    pass


class ReportOptionDtlAdmin(admin.TabularInline):
    model = ReportOptionDtl
    fields = (
        "hidden_report_option_dtl_id",
        "analyte_id",
        "analyte_value",
    )
    readonly_fields = ["analyte_id",
                       ]
    form = ReportOptionDtlForm
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if obj is None or obj.assign_pathologist != request.user:
            # If obj is None or the assigned pathologist is not the current user,
            # make both fields readonly
            return ["analyte_id", "analyte_value"]
        else:
            # If the current user is the assigned pathologist,
            # only make analyte_id readonly
            return ["analyte_id"]


class ReportOptionAdmin(TZIndependentAdmin):
    form = ReportOptionForm

    def get_form(self, request, obj=None, **kwargs):
        """
        Wrap the form to inject the `request` object so it can be used inside the form's __init__ method.
        """
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __init__(self2, *args, **kw):
                kw['request'] = request  # Inject request
                super().__init__(*args, **kw)

        return FormWithRequest

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "accession_id",
                    "get_part_no",
                    "current_step",
                    "pending_action",
                    "reporting_status",
                    "root_sample_id",
                    "report_option_id",
                    "version_id",
                    "hidden_reportoption_id",
                    "assign_pathologist",
                    "current_user",

                ),
            },
        ),
    )
    list_display = (
        "accession_id",
        "get_part_no",
        "current_step",
        "pending_action",
        "next_step",
        "reporting_status",
        "root_sample_id",
        "report_option_id",
        "version_id",
        "methodology",

    )
    readonly_fields = ["accession_id",
                       "get_part_no",
                       "current_step",
                       "pending_action",
                       "reporting_status",
                       "report_option_id",
                       "root_sample_id",
                       "version_id",
                       ]
    list_display_links = None
    search_fields = ['accession_id__accession_id']
    date_hierarchy = 'created_dt'
    actions = [generate_report]
    inlines = [ReportOptionDtlAdmin]
    change_form_template = 'admin/analysis/reportoption/reportoption_change_form.html'
    change_list_template = "admin/change_list.html"
    ordering = ['root_sample_id__part_no']

    class Media:
        js = ('js/util/disable_breadcrumb_links.js',
              'js/analysis/reportoption.js',)

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_part_no(self, obj):
        return obj.root_sample_id.part_no if obj.root_sample_id else None

    get_part_no.short_description = 'Part No'
    get_part_no.admin_order_field = 'root_sample_id__part_no'

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(reporting_status="In-progress")

        try:
            user_id = request.user.id
            return qs.filter(Q(assign_pathologist__isnull=True) | Q(assign_pathologist__id=user_id))
        except Exception:
            return qs.none()

    def get_urls(self):
        urls = super().get_urls()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        custom_urls = [
            path('generate-report-prompt/',
                 self.admin_site.admin_view(generate_report_prompt),
                 name='generate_report_prompt'),
            path('validate-generate-report-selection/',
                 self.admin_site.admin_view(validate_generate_report_selection),
                 name='validate_generate_report_selection'),
        ]
        return custom_urls + urls


class ReportSignOutAdmin(TZIndependentAdmin):
    pass


class HistoricalReportOptionAdmin(TZIndependentAdmin):
    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "accession_id",
                    "get_part_no",
                    "current_step",
                    "pending_action",
                    "reporting_status",
                    "root_sample_id",
                    "report_option_id",
                    "version_id",
                ),
            },
        ),
    )
    list_display = (
        "accession_id",
        "get_part_no",
        "reporting_status",
        "root_sample_id",
        "report_option_id",
        "version_id",
        "methodology"

    )
    readonly_fields = ["accession_id",
                       "root_sample_id",
                       "current_step",
                       "pending_action",
                       "reporting_status",
                       "report_option_id",
                       "version_id",
                       ]
    list_display_links = None
    search_fields = ['accession_id__accession_id']
    date_hierarchy = 'created_dt'
    actions = [amend_merge_report]
    inlines = [ReportOptionDtlAdmin]
    change_form_template = 'admin/change_form.html'
    change_list_template = "admin/analysis/reportoption/change_list.html"
    ordering = ['root_sample_id__part_no']

    class Media:
        js = ('js/util/disable_breadcrumb_links.js',
              'js/analysis/reportoption.js',)

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_part_no(self, obj):
        return obj.root_sample_id.part_no if obj.root_sample_id else None

    get_part_no.short_description = 'Part No'
    get_part_no.admin_order_field = 'root_sample_id__part_no'

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

    def get_queryset(self, request):
        """Override to filter Report Options based on user's department."""
        qs = super().get_queryset(request)
        qs = qs.filter(Q(reporting_status="Completed") | Q(reporting_status="Cancelled"))
        user_jobtype = request.session.get('currentjobtype', '')
        try:
            JobType = apps.get_model('security', 'JobType')
            jobtype = JobType.objects.get(name=user_jobtype)
            department_id = jobtype.departmentid_id
            return qs.filter(custodial_department_id=department_id)
        except JobType.DoesNotExist:
            return qs.none()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'validate-amend-report-selection/',
                self.admin_site.admin_view(validate_amend_report_selection),
                name='validate_amend_report_selection'
            ),
            path(
                'amend-generate-report-prompt/',
                self.admin_site.admin_view(amend_generate_report_prompt),
                name='amend_generate_report_prompt'
            ),
            path(
                'amend-generate-report-confirm/',
                self.admin_site.admin_view(amend_generate_report_confirm),
                name='amend_generate_report_confirm',
            ),
        ]
        return custom_urls + urls


class MergeReportingDtlAdmin(admin.TabularInline):
    model = MergeReportingDtl
    fields = (
        "hidden_merge_reporting_dtl_id",
        "analyte_id",
        "analyte_value",
    )
    readonly_fields = ["analyte_id",
                       ]
    form = MergeReportingDtlForm
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("report_option_id")

    def get_readonly_fields(self, request, obj=None):
        if obj is None or obj.assign_pathologist != request.user:
            # If obj is None or the assigned pathologist is not the current user,
            # make both fields readonly
            return ["analyte_id", "analyte_value"]
        else:
            # If the current user is the assigned pathologist,
            # only make analyte_id readonly
            return ["analyte_id"]


class MergeReportingAdmin(TZIndependentAdmin):
    form = MergeReportingForm

    def get_form(self, request, obj=None, **kwargs):
        """
        Wrap the form to inject the `request` object so it can be used inside the form's __init__ method.
        """
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __init__(self2, *args, **kw):
                kw['request'] = request  # Inject request
                super().__init__(*args, **kw)

        return FormWithRequest

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("accession_id_display", "patient_name"),
                    ("accession_category", "accession_type_display"),
                    ("doctor_name", "pathologist_name"),
                    "case_status",
                    "hidden_merge_reporting_id",
                    "assign_pathologist",
                    "current_user",

                ),
            },
        ),
    )
    list_display = (
        "accession_id_display",
    )
    readonly_fields = ["accession_id_display",
                       "patient_name",
                       "accession_category",
                       "accession_type_display",
                       "doctor_name",
                       "pathologist_name",
                       "case_status",
                       ]
    list_filter = [
        "accession_id"
    ]
    date_hierarchy = 'created_dt'
    inlines = [MergeReportingDtlAdmin]
    change_form_template = 'admin/analysis/mergereporting/mergereporting_change_form.html'
    change_list_template = "admin/change_list.html"

    class Media:
        css = {
            "all": ("css/analysis_reporting_form.css",)
        }
        js = ('js/util/disable_breadcrumb_links.js',)

    # ─── Methods to fetch & format each value ───
    def accession_id_display(self, obj):
        return obj.accession_id_id

    accession_id_display.short_description = "Case Number"

    def patient_name(self, obj):
        p = obj.accession_id.patient_id
        name_parts = [p.first_name, p.middle_initial or "", p.last_name]
        return " ".join(filter(None, name_parts))

    patient_name.short_description = "Patient Name"

    def accession_category(self, obj):
        return obj.accession_id.accession_category

    accession_category.short_description = "Accession Category"

    def accession_type_display(self, obj):
        return obj.accession_id.accession_type.accession_type

    accession_type_display.short_description = "Accession Type"

    def doctor_name(self, obj):
        d = obj.accession_id.doctor
        return f"{d.first_name} {d.last_name}" if d else "-"

    doctor_name.short_description = "Physician"

    def pathologist_name(self, obj):
        u = obj.assign_pathologist
        return f"{u.first_name} {u.last_name}" if u else "-"

    pathologist_name.short_description = "Pathologist"

    def case_status(self, obj):
        return obj.accession_id.status

    case_status.short_description = "Case Status"

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_formsets_with_inlines(self, request, obj=None):
        if obj:
            from itertools import groupby
            from operator import attrgetter
            from django.utils.text import slugify

            inline_instances = []
            label_group = []

            # Gather all groups
            for inline in self.get_inline_instances(request, obj):
                if isinstance(inline, MergeReportingDtlAdmin):
                    qs = inline.get_queryset(request).filter(
                        merge_reporting_id=obj.pk
                    ).order_by("report_option_id_id", "merge_reporting_id_id")

                    grouped = groupby(
                        qs, key=attrgetter("report_option_id_id", "merge_reporting_id_id")
                    )

                    for (report_option_id, merge_reporting_id), _ in grouped:
                        try:
                            ro = ReportOption.objects.select_related('test_id', 'root_sample_id').get(
                                pk=report_option_id
                            )
                            test_name = ro.test_id.test_name if ro.test_id else "NoTest"
                            part_no = ro.root_sample_id.part_no if ro.root_sample_id else "NoPart"
                            if test_name == settings.TEST_ID_GULF:
                                base_label = f"{part_no}"
                            else:
                                base_label = f"{part_no} - {test_name}"
                        except ReportOption.DoesNotExist:
                            base_label = f"{report_option_id} - {merge_reporting_id}"

                        label_group.append({
                            "base_label": base_label,
                            "report_option_id": report_option_id,
                            "merge_reporting_id": merge_reporting_id,
                            "inline": inline
                        })
                else:
                    inline_instances.append((inline.get_formset(request, obj), inline))

            # Determine if any base_label is duplicated
            labels = [g["base_label"] for g in label_group]
            duplicate_exists = any(count > 1 for count in __import__('collections').Counter(labels).values())

            # Sort groups alphabetically by base_label
            label_group.sort(key=lambda g: g["base_label"].lower())

            # Create and number (if needed)
            def make_get_queryset(inline, r_id, m_id):
                def get_queryset(self, request):
                    return inline.get_queryset(request).filter(
                        report_option_id_id=r_id,
                        merge_reporting_id_id=m_id
                    )

                return get_queryset

            for idx, group in enumerate(label_group, start=1):
                inline = group["inline"]
                base_label = group["base_label"]
                ro_id = group["report_option_id"]
                mr_id = group["merge_reporting_id"]

                if duplicate_exists:
                    display_label = f"{base_label} (#{idx})"
                    # ensure unique classname even if base_label duplicates
                    uniq = idx
                else:
                    display_label = base_label
                    # use report_option_id to differentiate classes uniquely
                    uniq = ro_id

                dynamic_class_name = f"{inline.__class__.__name__}_{slugify(base_label)}_{uniq}"

                InlineGrouped = type(
                    dynamic_class_name,
                    (MergeReportingDtlAdmin,),
                    {
                        'verbose_name_plural': display_label,
                        'get_queryset': make_get_queryset(inline, ro_id, mr_id),
                        'has_add_permission': staticmethod(lambda request, obj=None: False),
                        'has_delete_permission': staticmethod(lambda request, obj=None: False),
                        'extra': 0,
                        'max_num': 0,
                    }
                )

                inline_instance = InlineGrouped(self.model, self.admin_site)
                inline_instances.append((inline_instance.get_formset(request, obj), inline_instance))

            # Yield all in the sorted order
            for formset, inline in inline_instances:
                yield formset, inline

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(reporting_status="In-progress")

        try:
            user_id = request.user.id
            return qs.filter(Q(assign_pathologist__isnull=True) | Q(assign_pathologist__id=user_id))
        except Exception:
            return qs.none()


class HistoricMergeReportingAdmin(TZIndependentAdmin):
    form = HistoricMergeReportingForm

    def get_form(self, request, obj=None, **kwargs):
        """
        Wrap the form to inject the `request` object so it can be used inside the form's __init__ method.
        """
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __init__(self2, *args, **kw):
                kw['request'] = request  # Inject request
                super().__init__(*args, **kw)

        return FormWithRequest

    def get_resource_class(self):
        resource = super().get_resource_class()()
        resource.context = {"user": self.request.user}
        return resource

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("accession_id_display", "patient_name"),
                    ("accession_category", "accession_type_display"),
                    ("doctor_name", "pathologist_name"),
                    "case_status",
                    "hidden_merge_reporting_id",
                    "assign_pathologist",
                    "current_user",

                ),
            },
        ),
    )
    list_display = (
        "accession_id_display",
    )
    readonly_fields = [
        "accession_id_display",
        "patient_name",
        "accession_category",
        "accession_type_display",
        "doctor_name",
        "pathologist_name",
        "case_status",
    ]
    list_filter = [
        "accession_id"
    ]
    date_hierarchy = 'created_dt'
    inlines = [MergeReportingDtlAdmin]
    change_form_template = 'admin/analysis/mergereporting/amendmergereporting_change_form.html'
    change_list_template = "admin/change_list.html"

    class Media:
        css = {
            "all": ("css/analysis_reporting_form.css",)
        }
        js = ('js/util/disable_breadcrumb_links.js',)

    # ─── Methods to fetch & format each value ───
    def accession_id_display(self, obj):
        return obj.accession_id_id

    accession_id_display.short_description = "Case Number"

    def patient_name(self, obj):
        p = obj.accession_id.patient_id
        name_parts = [p.first_name, p.middle_initial or "", p.last_name]
        return " ".join(filter(None, name_parts))

    patient_name.short_description = "Patient Name"

    def accession_category(self, obj):
        return obj.accession_id.accession_category

    accession_category.short_description = "Accession Category"

    def accession_type_display(self, obj):
        return obj.accession_id.accession_type.accession_type

    accession_type_display.short_description = "Accession Type"

    def doctor_name(self, obj):
        d = obj.accession_id.doctor
        return f"{d.first_name} {d.last_name}" if d else "-"

    doctor_name.short_description = "Physician"

    def pathologist_name(self, obj):
        u = obj.assign_pathologist
        return f"{u.first_name} {u.last_name}" if u else "-"

    pathologist_name.short_description = "Pathologist"

    def case_status(self, obj):
        return obj.accession_id.status

    case_status.short_description = "Case Status"

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_formsets_with_inlines(self, request, obj=None):
        if obj:
            from itertools import groupby
            from operator import attrgetter
            from django.utils.text import slugify

            inline_instances = []
            label_group = []

            # Gather all groups
            for inline in self.get_inline_instances(request, obj):
                if isinstance(inline, MergeReportingDtlAdmin):
                    qs = inline.get_queryset(request).filter(
                        merge_reporting_id=obj.pk
                    ).order_by("report_option_id_id", "merge_reporting_id_id")

                    grouped = groupby(
                        qs, key=attrgetter("report_option_id_id", "merge_reporting_id_id")
                    )

                    for (report_option_id, merge_reporting_id), _ in grouped:
                        try:
                            ro = ReportOption.objects.select_related('test_id', 'root_sample_id').get(
                                pk=report_option_id
                            )
                            test_name = ro.test_id.test_name if ro.test_id else "NoTest"
                            part_no = ro.root_sample_id.part_no if ro.root_sample_id else "NoPart"
                            if test_name == settings.TEST_ID_GULF:
                                base_label = f"{part_no}"
                            else:
                                base_label = f"{part_no} - {test_name}"
                        except ReportOption.DoesNotExist:
                            base_label = f"{report_option_id} - {merge_reporting_id}"

                        label_group.append({
                            "base_label": base_label,
                            "report_option_id": report_option_id,
                            "merge_reporting_id": merge_reporting_id,
                            "inline": inline
                        })
                else:
                    inline_instances.append((inline.get_formset(request, obj), inline))

            # Determine if any base_label is duplicated
            labels = [g["base_label"] for g in label_group]
            duplicate_exists = any(count > 1 for count in __import__('collections').Counter(labels).values())

            # Sort groups alphabetically by base_label
            label_group.sort(key=lambda g: g["base_label"].lower())

            # Create and number (if needed)
            def make_get_queryset(inline, r_id, m_id):
                def get_queryset(self, request):
                    return inline.get_queryset(request).filter(
                        report_option_id_id=r_id,
                        merge_reporting_id_id=m_id
                    )

                return get_queryset

            for idx, group in enumerate(label_group, start=1):
                inline = group["inline"]
                base_label = group["base_label"]
                ro_id = group["report_option_id"]
                mr_id = group["merge_reporting_id"]

                if duplicate_exists:
                    display_label = f"{base_label} (#{idx})"
                    # ensure unique classname even if base_label duplicates
                    uniq = idx
                else:
                    display_label = base_label
                    # use report_option_id to differentiate classes uniquely
                    uniq = ro_id

                dynamic_class_name = f"{inline.__class__.__name__}_{slugify(base_label)}_{uniq}"

                InlineGrouped = type(
                    dynamic_class_name,
                    (MergeReportingDtlAdmin,),
                    {
                        'verbose_name_plural': display_label,
                        'get_queryset': make_get_queryset(inline, ro_id, mr_id),
                        'has_add_permission': staticmethod(lambda request, obj=None: False),
                        'has_delete_permission': staticmethod(lambda request, obj=None: False),
                        'extra': 0,
                        'max_num': 0,
                    }
                )

                inline_instance = InlineGrouped(self.model, self.admin_site)
                inline_instances.append((inline_instance.get_formset(request, obj), inline_instance))

            # Yield all in the sorted order
            for formset, inline in inline_instances:
                yield formset, inline

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(reporting_status="Completed")

        try:
            user_id = request.user.id
            return qs.filter(Q(assign_pathologist__isnull=True) | Q(assign_pathologist__id=user_id))
        except Exception:
            return qs.none()


def validate_generate_report_selection(request):
    ids_str = request.GET.get('ids', '')
    selected_ids = parse_ids(ids_str)
    log.info(f"Selected Ids ---> {selected_ids}")
    queryset = ReportOption.objects.filter(report_option_id__in=selected_ids)

    accession_ids = list(queryset.values_list('accession_id', flat=True).distinct())
    if len(accession_ids) != 1:
        return JsonResponse({'valid': False, 'message': "Please select only one accession."})

    accession_id = accession_ids[0]
    unique_methodologies = list(queryset.values_list('methodology', flat=True).distinct())
    if not unique_methodologies:
        return JsonResponse({'valid': False, 'message': "No methodologies found for selected records."})

    count_exists = MergeReporting.objects.filter(accession_id=accession_id,
                                                 methodology__in=unique_methodologies).count()

    if MergeReporting.objects.filter(accession_id=accession_id,
                                     methodology__in=unique_methodologies).exists() and count_exists == len(
        unique_methodologies):
        in_progress_count = ReportOption.objects.filter(
            accession_id=accession_id,
            reporting_status='In-progress',
            methodology__in=unique_methodologies
        ).count()
        selected_count = queryset.count()
        if in_progress_count != selected_count:
            log.error(f"Please select all the tests with status 'In-progress' to generate the report.")
            return JsonResponse({'valid': False,
                                 'message': "Please select all the tests with status 'In-progress' to generate the report."})

        # *** Instead of direct redirect, force popup to select methodology ***
        if len(unique_methodologies) > 1:
            popup_url = f"/gulfcoastpathologists/analysis/reportoption/generate-report-prompt/?ids={ids_str}"
            return JsonResponse({'valid': True, 'multiple_methodologies': True, 'popup_url': popup_url})

        # fallback for single methodology (keep direct redirect)
        merge_reporting_instance = MergeReporting.objects.filter(accession_id=accession_id,
                                                                 methodology=unique_methodologies[0]).first()
        if merge_reporting_instance and not merge_reporting_instance.reporting_status == "Completed":
            module = importlib.import_module("util.util")
            GenericUtilClass = getattr(module, "UtilClass")
            username = request.user.username
            user_map_obj = User.objects.get(username=username)

            queryset_report_option = queryset.filter(methodology__in=unique_methodologies) \
                .order_by('report_option_id') \
                .values_list('report_option_id', flat=True).distinct()
            existing_report_option_ids = list(MergeReportingDtl.objects.filter(
                merge_reporting_id=merge_reporting_instance,
                report_option_id__in=queryset_report_option
            ).values_list('report_option_id', flat=True).distinct())

            missing_report_option_ids = list(set(queryset_report_option) - set(existing_report_option_ids))

            if missing_report_option_ids:
                queryset.filter(report_option_id__in=missing_report_option_ids).update(assign_pathologist=user_map_obj)

                existing_version_id = MergeReportingDtl.objects.filter(
                    merge_reporting_id=merge_reporting_instance
                ).values_list('version_id', flat=True).first()
                missing_details = ReportOptionDtl.objects.filter(report_option_id__in=missing_report_option_ids)

                list_merge_reporting_dtl = []

                for report_option_id in missing_report_option_ids:
                    current_details = missing_details.filter(report_option_id=report_option_id)
                    for detail in current_details:
                        dtl_seq_no = GenericUtilClass.get_next_sequence("MRD", "MergeReportingDtl",
                                                                        user_map_obj.id)
                        merge_reporting_dtl_id = f"MRD-{dtl_seq_no:08}"
                        merge_reporting_dtl_instance = MergeReportingDtl()
                        merge_reporting_dtl_instance.merge_reporting_dtl_id = merge_reporting_dtl_id
                        merge_reporting_dtl_instance.version_id = existing_version_id
                        merge_reporting_dtl_instance.merge_reporting_id = merge_reporting_instance
                        merge_reporting_dtl_instance.report_option_id = detail.report_option_id
                        merge_reporting_dtl_instance.analyte_id = detail.analyte_id
                        merge_reporting_dtl_instance.analyte_value = detail.analyte_value
                        merge_reporting_dtl_instance.created_by = user_map_obj
                        merge_reporting_dtl_instance.mod_by = user_map_obj
                        list_merge_reporting_dtl.append(merge_reporting_dtl_instance)

                if list_merge_reporting_dtl:
                    MergeReportingDtl.objects.bulk_create(list_merge_reporting_dtl)

            redirect_url = f"/gulfcoastpathologists/{merge_reporting_instance._meta.app_label}/{merge_reporting_instance._meta.model_name}/{merge_reporting_instance.pk}/change/"
            return JsonResponse({'valid': True, 'multiple_methodologies': False, 'direct_url': redirect_url})

        elif merge_reporting_instance and merge_reporting_instance.reporting_status == "Completed":
            log.error(f"Merge Reporting Id for selected case and methodology is already Completed")
            return JsonResponse({'valid': False,
                                 'message': "Merge Reporting Id for selected case and methodology is already Completed"})

    queryset_report_option = queryset.order_by('report_option_id').values_list('report_option_id', flat=True).distinct()
    Sample = apps.get_model('sample', 'Sample')
    list_accession_samples = (
        Sample.objects
        .filter(
            accession_id__accession_id=accession_id,
            accession_sample__isnull=True,
        )
        .values_list('pk', flat=True)
        .distinct()
    )
    if list_accession_samples:
        SampleTestMap = apps.get_model('sample', 'SampleTestMap')

        qs_sample_test_info = SampleTestMap.objects.select_related('sample_id', 'workflow_id').filter(
            sample_id__in=list_accession_samples
        ).annotate(
            effective_methodology=Case(
                When(sample_id__workflow_id__isnull=False, then=F('sample_id__workflow_id__methodology')),
                When(workflow_id__isnull=False, then=F('workflow_id__methodology')),
                default=Value(None),
                output_field=CharField()
            )
        ).filter(
            effective_methodology__in=unique_methodologies
        )
        if qs_sample_test_info.exists():
            count_with_workflowid = qs_sample_test_info.filter(
                sample_id__workflow_id__isnull=False
            ).values('sample_id').distinct().count()

            count_without_workflowid = qs_sample_test_info.filter(
                sample_id__workflow_id__isnull=True
            ).count()

            total_expected = count_with_workflowid + count_without_workflowid
            total_selected = len(queryset_report_option)

            if total_selected != total_expected:
                methodology_list_str = ", ".join(sorted(unique_methodologies))
                return JsonResponse({
                    'valid': False,
                    'message': (
                        f"Merge Operation is only allowed when you select all the "
                        f"Report Options of {methodology_list_str} that are associated "
                        f"with the accession sample(s) for this case"
                    )
                })

    non_in_progress = queryset.exclude(reporting_status='In-progress')
    if non_in_progress.exists():
        log.error(f"All selected tests must have status 'In-progress' to generate the report.")
        return JsonResponse(
            {'valid': False, 'message': "All selected tests must have status 'In-progress' to generate the report."})

    # If single methodology, direct, else popup
    if len(unique_methodologies) == 1:
        selected_methodology = unique_methodologies[0]
        # Building direct URL to submit (to be handled by a direct redirect or fresh page load)
        direct_url = f"/gulfcoastpathologists/analysis/reportoption/generate-report-prompt/?ids={ids_str}&auto_direct=Y"
        return JsonResponse({'valid': True, 'multiple_methodologies': False, 'direct_url': direct_url})
    else:
        popup_url = f"/gulfcoastpathologists/analysis/reportoption/generate-report-prompt/?ids={ids_str}"
        return JsonResponse({'valid': True, 'multiple_methodologies': True, 'popup_url': popup_url})


def parse_ids(ids_str):
    if not ids_str:
        return []
    return [id_.strip() for id_ in ids_str.split(',') if id_.strip()]


def handle_generate_report_get(request, *args, **kwargs):
    """
    Serve the popup page to select methodology.
    Assumes all validations done in AJAX validation endpoint.
    """
    ids_str = request.GET.get('ids', '')
    selected_ids = parse_ids(ids_str)
    log.info(f"Selected Ids ---> {selected_ids}")
    queryset = ReportOption.objects.filter(report_option_id__in=selected_ids)
    accession_id = queryset.first().accession_id if queryset.exists() else None
    # Extracting unique methodologies
    unique_methodologies = list(queryset.values_list('methodology', flat=True).distinct())

    # if no methodologies or only one (should not happen here), fallback to error or redirect
    if not unique_methodologies:
        log.error(f"No methodologies found for selected records.")
        messages.error(request, "No methodologies found for selected records.")
        # Redirecting to changelist
        url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
            'controllerapp:analysis_reportoption_changelist')
        return HttpResponseRedirect(url)

    if len(unique_methodologies) == 1:
        # if only one methodology is sent here, no need for popup,
        # redirecting directly
        selected_methodology = unique_methodologies[0]
        filtered_queryset = queryset.filter(methodology=selected_methodology)

        action_instance = GenericAction()
        try:
            redirect_url = action_instance.generic_action_call_for_report_option_routing(
                request,
                filtered_queryset,
                desired_action="GenerateReport",
                action_desc="Generate Report",
            )
            if redirect_url:
                return HttpResponseRedirect(redirect_url)
            else:
                log.info(f"Report generation completed successfully.")
                messages.success(request, "Report generation completed successfully.")
                url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
                    'controllerapp:analysis_reportoption_changelist')
                return HttpResponseRedirect(url)
        except Exception as e:
            log.error(f"Error generating report: {e}")
            messages.error(request, f"Error generating report: {e}")
            url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
                'controllerapp:analysis_reportoption_changelist')
            return HttpResponseRedirect(url)
    else:
        # Normal expected flow: multiple methodologies present — show the popup
        return render(request,
                      'admin/analysis/reportoption/generate_report_prompt.html',
                      {
                          'methodologies': unique_methodologies,
                          'queryset': queryset,
                          'action_checkbox_name': ACTION_CHECKBOX_NAME,
                      })


def handle_generate_report_post(request, *args, **kwargs):
    selected_ids = request.POST.getlist(ACTION_CHECKBOX_NAME)
    log.info(f"Selected Ids ---> {selected_ids}")
    queryset = ReportOption.objects.filter(report_option_id__in=selected_ids)
    methodologies = list(queryset.values_list('methodology', flat=True).distinct())

    selected_methodology = request.POST.get('selected_methodology')
    if selected_methodology not in methodologies:
        log.error(f"Invalid methodology selected.")
        messages.error(request, "Invalid methodology selected.")
        return render(
            request,
            'admin/analysis/reportoption/generate_report_prompt.html',
            {
                'methodologies': methodologies,
                'queryset': queryset,
                'action_checkbox_name': ACTION_CHECKBOX_NAME,
            }
        )

    filtered_queryset = queryset.filter(methodology=selected_methodology)

    action_instance = GenericAction()
    try:
        redirect_url = action_instance.generic_action_call_for_report_option_routing(
            request,
            filtered_queryset,
            desired_action="GenerateReport",
            action_desc="Generate Report",
        )
        if redirect_url:
            # Instead of redirecting directly, respond with page to redirect parent and close popup
            template = loader.get_template('admin/popup_redirect_and_close.html')
            context = {
                'redirect_url': redirect_url
            }
            return HttpResponse(template.render(context, request))

        log.info(f"Report generation completed successfully.")
        messages.success(request, "Report generation completed successfully.")
    except Exception as e:
        log.error(f"Error generating report: {e}")
        messages.error(request, f"Error generating report: {e}")

    return render(
        request,
        'admin/analysis/reportoption/generate_report_prompt.html',
        {
            'methodologies': methodologies,
            'queryset': queryset,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
        }
    )


def generate_report_prompt(request, *args, **kwargs):
    log.info(f"Request Method ---> {request.method}")
    if request.method == 'POST':
        return handle_generate_report_post(request, *args, **kwargs)
    else:
        auto_direct = request.GET.get('auto_direct', 'N')
        if auto_direct == 'Y':
            # Emulate a POST with provided IDs and single methodology
            ids_str = request.GET.get('ids', '')
            selected_ids = parse_ids(ids_str)
            log.info(f"auto_direct == 'Y', selected_ids ---> {selected_ids}")
            queryset = ReportOption.objects.filter(report_option_id__in=selected_ids)
            accession_id = queryset.first().accession_id if queryset.exists() else None
            unique_methodologies = list(queryset.values_list('methodology', flat=True).distinct())
            if not unique_methodologies:
                log.error(f"No methodologies found for selected records.")
                messages.error(request, "No methodologies found for selected records.")
                url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
                    'controllerapp:analysis_reportoption_changelist')
                return HttpResponseRedirect(url)

            # Use filtered queryset (should all be same methodology)
            selected_methodology = unique_methodologies[0]
            filtered_queryset = queryset.filter(methodology=selected_methodology)

            action_instance = GenericAction()
            try:
                redirect_url = action_instance.generic_action_call_for_report_option_routing(
                    request,
                    filtered_queryset,
                    desired_action="GenerateReport",
                    action_desc="Generate Report",
                )
                if redirect_url:
                    return HttpResponseRedirect(redirect_url)
                else:
                    log.info(f"Report generation completed successfully.")
                    messages.success(request, "Report generation completed successfully.")
                    url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
                        'controllerapp:analysis_reportoption_changelist')
                    return HttpResponseRedirect(url)
            except Exception as e:
                log.error(f"Error generating report: {e}")
                messages.error(request, f"Error generating report: {e}")
                url = f"{reverse('controllerapp:analysis_reportoption_changelist')}?q={accession_id}" if accession_id else reverse(
                    'controllerapp:analysis_reportoption_changelist')
                return HttpResponseRedirect(url)

        # The default (for popup, multiple methodologies)
        return handle_generate_report_get(request, *args, **kwargs)


def validate_amend_report_selection(request):
    ids_param = request.GET.get('ids')
    log.info(f"request.GET.get('ids') ---> {ids_param}")
    if not ids_param:
        log.error(f"No ReportOption IDs provided.")
        return JsonResponse({
            'valid': False,
            'message': 'No ReportOption IDs provided.'
        })

    ro_ids = [i.strip() for i in ids_param.split(',') if i.strip()]

    if not ro_ids:
        log.error(f"No valid ReportOption IDs received.")
        return JsonResponse({
            'valid': False,
            'message': 'No valid ReportOption IDs received.'
        })

    HistoricalReportOption = apps.get_model('analysis', 'HistoricalReportOption')
    HistoricalMergeReporting = apps.get_model('analysis', 'HistoricalMergeReporting')

    queryset = HistoricalReportOption.objects.filter(report_option_id__in=ro_ids)

    if not queryset.exists():
        log.error(f"No matching HistoricalReportOption records found for the selected IDs.")
        return JsonResponse({
            'valid': False,
            'message': 'No matching HistoricalReportOption records found for the selected IDs.'
        })

    accession_ids = list(queryset.values_list('accession_id', flat=True).distinct())
    if len(accession_ids) != 1:
        log.error(f"Selected reports must belong to the same accession ID.")
        return JsonResponse({
            'valid': False,
            'message': 'Selected reports must belong to the same accession ID.'
        })

    accession_id = accession_ids[0]
    selected_methodologies = list(queryset.values_list('methodology', flat=True).distinct())

    completed_reports = HistoricalReportOption.objects.filter(
        accession_id=accession_id,
        reporting_status="Completed",
        methodology__in=selected_methodologies
    )

    completed_ids_set = set(completed_reports.values_list('report_option_id', flat=True))
    selected_ids_set = set(ro_ids)

    if selected_ids_set != completed_ids_set:
        return JsonResponse({
            'valid': False,
            'message': 'Please select all completed reports for amendments.'
        })

    if len(selected_methodologies) == 1:
        methodology = selected_methodologies[0]
        try:
            # Lookup merge reporting instance only for the single methodology selected
            merge_reporting_instance = HistoricalMergeReporting.objects.get(
                accession_id=accession_id,
                methodology=methodology
            )
        except HistoricalMergeReporting.DoesNotExist:
            log.error(f"No HistoricalMergeReporting instance found for this accession and methodology.")
            return JsonResponse({
                'valid': False,
                'message': 'No HistoricalMergeReporting instance found for this accession and methodology.'
            })

        change_url = f"/gulfcoastpathologists/{merge_reporting_instance._meta.app_label}/" \
                     f"{merge_reporting_instance._meta.model_name}/{merge_reporting_instance.pk}/change/"

        return JsonResponse({
            'valid': True,
            'multiple_methodologies': False,
            'direct_url': change_url,
        })
    else:
        # Multiple methodologies
        # Just returning popup URL for user to select methodology
        popup_url = reverse('controllerapp:amend_generate_report_prompt') + f'?ids={ids_param}'
        return JsonResponse({
            'valid': True,
            'multiple_methodologies': True,
            'popup_url': popup_url,
        })


@csrf_protect
def amend_generate_report_confirm(request):
    log.info(f"request.method ---> {request.method}")
    if request.method != 'POST':
        log.error("Invalid request method.")
        messages.error(request, "Invalid request method.")
        return amend_generate_report_prompt(request)

    selected_methodology = request.POST.get('selected_methodology')
    log.info(f"selected_methodology ---> {selected_methodology}")
    ids_param = request.POST.get('ids')
    log.info(f"ids ---> {ids_param}")

    # Parse selected IDs early for re-rendering if needed
    ro_ids = [i.strip() for i in ids_param.split(',') if i.strip()] if ids_param else []

    HistoricalReportOption = apps.get_model('analysis', 'HistoricalReportOption')
    queryset = HistoricalReportOption.objects.filter(report_option_id__in=ro_ids)
    methodologies = list(queryset.values_list('methodology', flat=True).distinct())

    errors = []

    if not selected_methodology:
        log.error(f"Please select a methodology.")
        errors.append("Please select a methodology.")

    if not ro_ids:
        log.error(f"No valid Report Option IDs provided.")
        errors.append("No valid Report Option IDs provided.")

    accession_ids = list(queryset.values_list('accession_id', flat=True).distinct())
    if len(accession_ids) != 1:
        log.error(f"Selected reports must belong to the same accession ID.")
        errors.append("Selected reports must belong to the same accession ID.")

    if errors:
        context = {
            'queryset': queryset,
            'methodologies': methodologies,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'popup_action': 'amend',
            'ids_param': ids_param,
            'form_action_url': reverse('controllerapp:amend_generate_report_confirm'),
            'errors': errors,
        }
        return render(request, 'generate_report_prompt.html', context)

    accession_id = accession_ids[0]

    HistoricalMergeReporting = apps.get_model('analysis', 'HistoricalMergeReporting')
    try:
        merge_reporting_instance = HistoricalMergeReporting.objects.get(
            accession_id=accession_id,
            methodology=selected_methodology
        )
    except HistoricalMergeReporting.DoesNotExist:
        log.error(f"No merge reporting found for the selected accession and methodology.")
        errors.append("No merge reporting found for the selected accession and methodology.")

    if errors:
        context = {
            'queryset': queryset,
            'methodologies': methodologies,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'popup_action': 'amend',
            'ids_param': ids_param,
            'form_action_url': reverse('controllerapp:amend_generate_report_confirm'),
            'errors': errors,
        }
        return render(request, 'generate_report_prompt.html', context)

    # Success: redirect to reporting portal page
    change_url = f"/gulfcoastpathologists/{merge_reporting_instance._meta.app_label}/" \
                 f"{merge_reporting_instance._meta.model_name}/{merge_reporting_instance.pk}/change/"
    return HttpResponse(f"""
        <html>
          <head>
            <script type="text/javascript">
                if (window.opener) {{
                    window.opener.location = '{change_url}';
                }}
                window.close();
            </script>
          </head>
          <body>
            <p>Operation successful.</p>
          </body>
        </html>
    """)


def amend_generate_report_prompt(request):
    ids_param = request.GET.get('ids')
    error_messages = []
    log.info(f"reportoption ids ---> {ids_param}")
    if not ids_param:
        log.error(f"No ReportOption IDs provided.")
        error_messages.append("No ReportOption IDs provided.")

    ro_ids = [i.strip() for i in ids_param.split(',')] if ids_param else []
    HistoricalReportOption = apps.get_model('analysis', 'HistoricalReportOption')
    queryset = HistoricalReportOption.objects.filter(report_option_id__in=ro_ids) if ro_ids else []

    if ro_ids and not queryset.exists():
        log.error(f"No matching reports found for the selected IDs.")
        error_messages.append("No matching reports found for the selected IDs.")

    methodologies = list(queryset.values_list('methodology', flat=True).distinct()) if queryset else []

    context = {
        'queryset': queryset,
        'methodologies': methodologies,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'popup_action': 'amend',
        'ids_param': ids_param if ids_param else '',
        'form_action_url': reverse('controllerapp:amend_generate_report_confirm'),
        'errors': error_messages,
    }

    return render(request, 'admin/analysis/reportoption/generate_report_prompt.html', context)


controller.register(ReportOption, ReportOptionAdmin)
controller.register(MergeReporting, MergeReportingAdmin)
controller.register(HistoricalReportOption, HistoricalReportOptionAdmin)
controller.register(HistoricalMergeReporting, HistoricMergeReportingAdmin)
