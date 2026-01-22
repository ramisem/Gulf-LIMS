import copy
import threading

from django.contrib import admin, messages
from controllerapp.views import controller
from masterdata.models import AccessionType, Subject
from security.models import User, Department, JobType
from util.admin import TZIndependentAdmin, GulfModelAdmin
from util.util import get_printer_by_category, GenerateLabel, generate_automatic_sample_labels
from accessioning.models import AccessionICDCodeMap
from .models import AccessionTemplate, PathologyTemplate, GrossCodeTemplate, BioPharmaAccessionTemplate, Macros
from accessioning.forms import SampleInlineForm, AccessionICDCodeMapForm, SampleInlineFormSet
from .forms import AccessionTemplateForm, PathologyTemplateForm, BioPharmaAccessionTemplateForm, MacrosForm
from sample.models import Sample, SampleTestMap
from routinginfo.util import UtilClass
from process.models import ContainerType
from django.db import connection
from django.utils.safestring import mark_safe
from workflows.models import Workflow, ModalityModelMap
from django.apps import apps
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db import transaction, OperationalError
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.encoding import force_str
from django.db.models.functions import Coalesce, Cast
from django.db.models import Q, Value, Case, When, IntegerField, CharField
from .forms import MacrosForm

MODEL_APP_MAP = {model.__name__: model._meta.app_label for model in apps.get_models()}


def get_app_name_from_model(model_name):
    return MODEL_APP_MAP.get(model_name)


class SampleInline(admin.TabularInline):
    model = Sample
    form = SampleInlineForm
    formset = SampleInlineFormSet

    extra = 0
    max_num = 1
    show_change_link = False
    classes = ['scrollable-inline']

    class Media:
        css = {'all': ('css/admin_custom.css',)}

    def get_fields(self, request, obj=None):
        """Dynamically control fields based on accession_category"""
        fields = ['part_no', 'block_or_cassette_seq', 'slide_seq',
                  'sample_type_info', 'container_type_info', 'test_code', 'test_id', 'body_site', 'sub_site',
                  'collection_method', 'workflow_id', 'child_sample_creation', 'sample_status', 'sample_id',
                  'gen_block_or_cassette_seq', 'gen_slide_seq']

        if obj and obj.accession_category == "Clinical":
            # Remove these fields for Clinical category
            # fields.remove('part_no')
            fields.remove('block_or_cassette_seq')
            fields.remove('slide_seq')
            fields.remove('part_no')

        return fields

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
        queryset = super().get_queryset(request)
        object_id = request.resolver_match.kwargs.get('object_id', None)

        if object_id:
            try:
                accession_obj = AccessionTemplate.objects.get(pk=object_id)
                if accession_obj.accession_category != "Clinical":
                    return queryset.filter(accession_sample__isnull=True).order_by(
                        'part_no',
                        self.safe_cast('block_or_cassette_seq'),
                        self.safe_cast('slide_seq')
                    )
                else:
                    return queryset.filter(accession_sample__isnull=True).order_by('sample_id')

            except AccessionTemplate.DoesNotExist:
                pass
            except Exception as e:
                print(f"Error retrieving Accession or filtering SampleInline: {e}")
                pass


class AccessionICDCodeMapInline(admin.StackedInline):
    model = AccessionICDCodeMap
    form = AccessionICDCodeMapForm
    fields = (
        "icd_code_id",
        "description",
    )
    extra = 0

    class Media:
        js = ('js/accessioning/accessioningtemplate.js', 'js/util/util.js')


class AccessionTemplateAdmin(TZIndependentAdmin, GulfModelAdmin):
    tz_independent_fields = ['receive_dt', 'collection_dt']
    search_fields = ("accession_id",)
    ordering = ("accession_id",)
    readonly_fields = ['created_dt', 'complete_dt']
    form = AccessionTemplateForm
    inlines = [SampleInline, AccessionICDCodeMapInline]
    fieldsets = (
        (
            'Accession Info',
            {
                "fields": (
                    "accession_prefix",
                    "case_id",
                    "accession_id",
                    "accession_category",
                    "accession_type",
                    "reporting_type",
                    "status",
                    "created_dt",
                    "previous_accession",
                    "isupdate_accession_prefix",
                    "move_next_to_client_info_tab",
                    "hidden_auto_gen_pk",
                    "hidden_accession_prefix",
                    "is_template",
                    "count_accession",
                ),
            },
        ),

        (
            'Client',
            {
                "fields": (
                    "client_id",
                    "doctor",
                    "client_address_line1",
                    "client_address_line2",
                    "client_city",
                    "client_state",
                    "client_postalcode",
                    "client_country",
                    "client_phone_number",
                    "client_fax_number",
                    "client_email",
                    "move_prev_next_from_client_info_tab",
                ),
            },
        ),
        (
            'Assignment',
            {
                "fields": (
                    "reporting_doctor",
                    "move_prev_next_from_reporting_doc_tab",
                ),
            },
        ),

        (
            'Sample Creation',
            {
                "fields": (
                    "sample_type",
                    "container_type",
                    "part_no",
                    "parent_seq",
                    "is_child_sample_creation",
                    "associate_test",
                    "workflow",
                    "count",
                    "test_id",
                    "move_finish_from_sample_creation_tab",
                    "is_generate_parent_seq",
                    "is_gen_slide_seq"
                ),
            },
        ),

    )
    list_display = ('accession_id',
                    'accession_category',
                    'accession_type',
                    'active_flag',
                    'created_dt',
                    'created_by',
                    'status',
                    'client_id',
                    'is_template',
                    )

    change_form_template = 'admin/accessioning/accession_change_form.html'
    actions = [GulfModelAdmin.delete_custom]

    def get_queryset(self, request):
        """Override to filter accessions based on is_template column."""
        qs = super().get_queryset(request)
        qs = qs.filter(
            is_template=True
        ).exclude(accession_category='Pharma')
        return qs

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)
        return lambda *args, **form_kwargs: FormClass(*args, request=request, **form_kwargs)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            if extra_context is None:
                extra_context = {}
            extra_context['accession_id'] = obj.accession_id
            extra_context['status'] = obj.status
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)

                if not change:
                    obj.created_by = user_map_obj
                    obj.status = "Initial"
                    obj.accession_id = request.POST.get('case_id')

                else:
                    obj.mod_by = user_map_obj
                    obj.accession_prefix = request.POST.get('hidden_accession_prefix')

                super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, f"An error occurred while saving: {e}", level=messages.ERROR)
        finally:
            return

    def response_change(self, request, obj):
        change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
        is_create_samples = request.POST.get('is_create_samples')
        if "Y" == is_create_samples:
            return HttpResponseRedirect(f"{change_url}?move_to_sample_creation_tab=Y")
        else:
            messages.success(request, "Operation successful.")
            return HttpResponseRedirect(f"{change_url}")

    def response_add(self, request, obj):
        change_url = f"/gulfcoastpathologists/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/"
        return HttpResponseRedirect(f"{change_url}?move_to_sample_creation_tab=Y")

    def save_related(self, request, form, formset, change):
        user_map_obj = None
        if request.user.is_authenticated:
            username = request.user.username
            user_map_obj = User.objects.get(username=username)
            for formsetobj in formset:
                formset_model = formsetobj.model.__name__  # Get the model name
                if formset_model == "AccessionICDCodeMap":
                    accessionicdcodemapinstances = formsetobj.save(commit=False)
                    for instances in accessionicdcodemapinstances:
                        if instances.created_by is None:
                            instances.created_by = user_map_obj
                        instances.mod_by = user_map_obj
                        instances.save()

        super().save_related(request, form, formset, change)

    def get_deleted_objects(self, objs, request):
        samples = Sample.objects.filter(accession_id__in=objs)
        if samples.exists():
            raise ValidationError("One or more sample(s) are associated with this accession.")
        else:
            deletable_objects = []
            model_count = {self.model._meta.verbose_name_plural: 0}
            for obj in objs:
                try:
                    with transaction.atomic():
                        obj_display = format_html(
                            '{}: {}'.format(force_str(obj._meta.verbose_name), obj)
                        )
                        deletable_objects.append(obj_display)
                        model_count[self.model._meta.verbose_name_plural] += 1
                except ValidationError as e:
                    self.message_user(request, f"Error: {e}", level='error')

            return deletable_objects, model_count, [], []

    def delete_model(self, request, obj):
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(
                            "DELETE FROM accessioning_accession WHERE accession_id = %s",
                            [obj.pk]
                        )
                    except OperationalError as e:
                        self.message_user(request, f"Error deleting accession: {str(e)}. Standard delete used.",
                                          messages.WARNING)
                        raise
        except Exception as e:
            self.message_user(request, f"Error deleting accession: {str(e)}. Standard delete used.",
                              messages.WARNING)

    def delete_view(self, request, object_id, extra_context=None):
        try:
            obj = self.get_object(request, object_id)
            if not obj:
                self.message_user(request, "Object not found.", level='error')
                return HttpResponseRedirect(reverse('admin:accessioning_accession_changelist'))

            return super().delete_view(request, object_id, extra_context)

        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", level='error')
            return HttpResponseRedirect(reverse('admin:accessioning_accession_change', args=[obj.pk]))

    class Media:
        css = {'all': ('css/admin.css',)}
        js = ('js/template/accessioningtemplate.js', 'js/util/util.js')


original_template_fieldsets = copy.deepcopy(AccessionTemplateAdmin.fieldsets)

fieldsets_to_keep = [fs for fs in original_template_fieldsets if fs[0] != 'Client']

final_template_fieldsets = []
for title, options in fieldsets_to_keep:
    if title == 'Accession Info':
        current_fields = options.get('fields', ())
        filtered_fields = [f for f in current_fields if f != 'accession_type']
        options['fields'] = ('sponsor', 'project', 'visit', 'investigator') + tuple(filtered_fields)
        final_template_fieldsets.append((title, options))
    elif title == 'Sample Creation':
        # Add the crucial hidden field to the Sample Creation tab
        current_fields = options.get('fields', ())
        options['fields'] = current_fields + ('is_create_samples',)
        final_template_fieldsets.append((title, options))
    else:
        final_template_fieldsets.append((title, options))

sponsor_tab = ('Sponsor', {
    'fields': (
        'sponsor_name',
        'sponsor_number',
        'sponsor_description',
        'sponsor_address_info',
        'move_prev_next_from_sponsor_tab',
    )
})

final_template_fieldsets.insert(1, sponsor_tab)


class BioPharmaAccessionTemplateAdmin(AccessionTemplateAdmin):
    form = BioPharmaAccessionTemplateForm
    inlines = [
        inline for inline in AccessionTemplateAdmin.inlines
        if inline is not AccessionICDCodeMapInline
    ]

    def get_queryset(self, request):
        """
        Override to filter for accessions that are templates AND have the 'Pharma' category.
        """
        qs = super(AccessionTemplateAdmin, self).get_queryset(request)
        qs = qs.filter(is_template=True, accession_category='Pharma')
        return qs

    list_display = (
        'accession_id',
        'accession_category',
        'accession_type',
        'active_flag',
        'created_dt',
        'created_by',
        'status',
        'complete_dt',
        'sponsor',
        'project',
        'display_visit_id',
        'investigator'
    )

    def display_visit_id(self, obj):
        """
        Custom method to display the visit_id from the related ProjectVisitMap object.
        """
        if obj.visit:
            return obj.visit.visit_id
        return None

    display_visit_id.short_description = 'Visit ID'


    fieldsets = tuple(final_template_fieldsets)

    def save_model(self, request, obj, form, change):
        try:
            global_type = AccessionType.objects.get(accession_type='Global')
            obj.accession_type = global_type
        except AccessionType.DoesNotExist:
            messages.error(request, "Critical Error: 'Global' Accession Type not found. Cannot save.")
            return
        super().save_model(request, obj, form, change)


class PathologyTemplateAdmin(admin.ModelAdmin):
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
                    "dx_code",
                    "diagnosis",
                    "microscopic_desc",
                    "category",
                ),
            },
        ),
    )
    list_display = (
        "dx_code",
        "diagnosis",
        "microscopic_desc",
        "category",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "dx_code",
    ]
    date_hierarchy = 'created_dt'
    change_form_template = 'admin/change_form.html'
    form = PathologyTemplateForm

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


class GrossCodeTemplateAdmin(admin.ModelAdmin):
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
                    "gross_code",
                    "gross_description",
                ),
            },
        ),
    )
    list_display = (
        "gross_code",
        "gross_description",
        "created_dt",
        "created_by",
    )
    list_filter = [
        "gross_code",
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

class MacrosAdmin(admin.ModelAdmin):
    form = MacrosForm

    fieldsets = (
        (None, {
            "fields": (
                "macros_name",
                "macros_type",
                "actual_content",
            ),
        }),
    )

    list_display = (
        "macros_name",
        "macros_type",
        "created_dt",
        "created_by",
    )

    list_filter = ("macros_type",)

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                if not change:
                    obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return


controller.register(AccessionTemplate, AccessionTemplateAdmin)
controller.register(BioPharmaAccessionTemplate, BioPharmaAccessionTemplateAdmin)
controller.register(PathologyTemplate, PathologyTemplateAdmin)
controller.register(GrossCodeTemplate, GrossCodeTemplateAdmin)
controller.register(Macros, MacrosAdmin)
