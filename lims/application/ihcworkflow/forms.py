from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AdminSplitDateTime
from django.db import models
from django.forms import SplitDateTimeField, TextInput

from ihcworkflow.models import IhcWorkflow
from sample.models import SampleTestMap, SampleType, ContainerType
from template.models import GrossCodeTemplate
from tests.models import WorkflowStepConfigField
from util.util import UtilClass
from workflows.models import WorkflowStep


class IhcSampleBulkEditForm(forms.ModelForm):
    # Display fields (read-only) for human-readable names
    sample_type_display = forms.CharField(label="Sample Type", required=False, disabled=True)
    container_type_display = forms.CharField(label="Container", required=False, disabled=True)

    # Hidden fields to store the primary key values
    sample_type_pk = forms.ModelChoiceField(
        queryset=SampleType.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )
    container_type_pk = forms.ModelChoiceField(
        queryset=ContainerType.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = IhcWorkflow
        fields = [
            "current_step",
            "avail_at",
            "part_no",
            "body_site",
            "sub_site",
            "collection_method",
            "receive_dt",
            "receive_dt_timezone",
            "collection_dt",
            "collection_dt_timezone",
        ]
        readonly_fields = ["current_step", "avail_at", "receive_dt", "receive_dt_timezone", "collection_dt",
                           "collection_dt_timezone" ]

    def __init__(self, *args, **kwargs):
        custom_order = kwargs.pop('custom_order', None)
        super().__init__(*args, **kwargs)

        # --- Process parent (Meta-declared) fields ---
        for field_name in list(self.fields):
            try:
                model_field = self.instance._meta.get_field(field_name)
                original_field = self.fields[field_name]

                if isinstance(model_field, models.DateTimeField):
                    if field_name in getattr(self.Meta, 'readonly_fields', []):
                        self.fields[field_name].widget = TextInput(attrs={"readonly": True})
                        self.fields[field_name].initial = getattr(self.instance, field_name, None)
                    else:
                        initial_value = original_field.initial if original_field.initial else None
                        if initial_value:
                            initial_value = AdminSplitDateTime().decompress(initial_value)
                        self.fields[field_name] = SplitDateTimeField(
                            label=original_field.label,
                            required=original_field.required,
                            widget=AdminSplitDateTime(),
                            input_date_formats=settings.DATE_INPUT_FORMATS,
                            input_time_formats=settings.TIME_INPUT_FORMATS,
                            initial=initial_value,
                        )

            except Exception:
                pass

        # --- Set initial values for display and hidden FK fields ---
        if self.instance and self.instance.pk:
            if self.instance.sample_type:
                self.fields["sample_type_display"].initial = str(self.instance.sample_type)
                self.fields["sample_type_pk"].initial = self.instance.sample_type.pk
            if self.instance.container_type:
                self.fields["container_type_display"].initial = str(self.instance.container_type)
                self.fields["container_type_pk"].initial = self.instance.container_type.pk

                # Handle dynamic fields
                if self.instance and self.instance.pk:
                    try:
                        stm = SampleTestMap.objects.filter(sample_id=self.instance).first()
                    except SampleTestMap.DoesNotExist:
                        stm = None

                    config_fields = None

                    # If SampleTestMap.workflow_id exists, use existing precise logic
                    if stm and stm.workflow_id:
                        config_fields = WorkflowStepConfigField.objects.filter(
                            test_workflow_step_id__test_id=stm.test_id,
                            test_workflow_step_id__workflow_id=stm.workflow_id,
                            test_workflow_step_id__workflow_step_id__step_id=self.instance.current_step,
                            test_workflow_step_id__sample_type_id=self.instance.sample_type,
                            test_workflow_step_id__container_type=self.instance.container_type,
                            model="IhcWorkflow"
                        ).order_by('pk')
                    else:
                        # Fallback using Sample model's workflow_id resolution via accession_sample
                        fallback_workflow_id = None
                        if not self.instance.accession_generated:
                            if self.instance.accession_sample and self.instance.accession_sample.workflow_id:
                                fallback_workflow_id = self.instance.accession_sample.workflow_id
                        else:
                            fallback_workflow_id = self.instance.workflow_id

                        if fallback_workflow_id:
                            workflow_step = WorkflowStep.objects.filter(
                                workflow_id=fallback_workflow_id,
                                step_id=self.instance.current_step
                            ).first()

                            if workflow_step:
                                config_fields = WorkflowStepConfigField.objects.filter(
                                    workflow_step_id=workflow_step,
                                    model="IhcWorkflow"
                                ).order_by('pk')

                    if config_fields and config_fields.exists():
                        dynamic_field_names = list(config_fields.values_list('field_id', flat=True))
                        self.dynamic_fields = dynamic_field_names
                        self.dynamic_fieldset_title = f"Attributes for {self.instance.current_step}"
                        for field_name in dynamic_field_names:
                            if field_name not in self.fields:
                                try:
                                    model_field = self.instance._meta.get_field(field_name)
                                    form_field = model_field.formfield()
                                    if isinstance(model_field, models.DateTimeField):
                                        initial_val = form_field.initial
                                        if initial_val:
                                            initial_val = AdminSplitDateTime().decompress(initial_val)
                                        else:
                                            initial_val = None
                                        form_field = SplitDateTimeField(
                                            label=model_field.verbose_name,
                                            required=False,
                                            widget=AdminSplitDateTime(),
                                            input_date_formats=settings.DATE_INPUT_FORMATS,
                                            input_time_formats=settings.TIME_INPUT_FORMATS,
                                            initial=initial_val,
                                        )
                                except Exception:
                                    form_field = forms.CharField(
                                        required=False,
                                        label=field_name.replace('_', ' ').capitalize()
                                    )
                                form_field.required = False
                                try:
                                    if hasattr(model_field, 'verbose_name'):
                                        form_field.label = model_field.verbose_name
                                except Exception:
                                    pass
                                form_field.initial = getattr(self.instance, field_name, '')
                                self.fields[field_name] = form_field

                    for extra_field in ['descriptive']:
                        if extra_field in dynamic_field_names:
                            self._set_choice_field(extra_field, f'APPLICATION_{extra_field.upper()}_REFERENCE')
                    if 'gross_code' in dynamic_field_names:
                        gross_codes = GrossCodeTemplate.objects.values_list('gross_code', 'gross_code')
                        choices = [('', '---------')] + list(gross_codes)
                        self.fields['gross_code'] = forms.ChoiceField(
                            choices=choices,
                            required=False,
                            label="Gross Code"
                        )
                        if self.instance and self.instance.gross_code:
                            self.fields['gross_code'].initial = self.instance.gross_code
        # --- Make all Meta-declared fields read-only ---
        for field_name in self.Meta.fields:
            if field_name in self.Meta.readonly_fields:
                self.fields[field_name].disabled = True

        # --- Determine and apply field order ---
        if custom_order is None:
            custom_order = self.get_custom_field_order()
        custom_order = [f for f in custom_order if f in self.fields]
        self.order_fields(custom_order)

    def _set_choice_field(self, field_name, setting_name):
        required_reftype = getattr(settings, setting_name, None)
        if not required_reftype:
            self.fields[field_name] = forms.ChoiceField(
                choices=[(None, "---------")],
                required=False
            )
            return

        choices = [(None, "---------")] + UtilClass.get_refvalues_for_field(required_reftype)
        self.fields[field_name] = forms.ChoiceField(
            choices=choices,
            required=False,
            initial=getattr(self.instance, field_name, None)
        )

    def clean(self):
        cleaned_data = super().clean()

        sample_type_obj = cleaned_data.get("sample_type_pk") or self.instance.sample_type
        cleaned_data["sample_type"] = sample_type_obj

        container_type_obj = cleaned_data.get("container_type_pk") or self.instance.container_type
        cleaned_data["container_type"] = container_type_obj

        for field_name in getattr(self.Meta, 'readonly_fields', []):
            cleaned_data[field_name] = getattr(self.instance, field_name)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        for field_name in self.dynamic_fields:
            if field_name in self.cleaned_data:
                setattr(instance, field_name, self.cleaned_data[field_name])

        instance.sample_type = self.cleaned_data.get("sample_type", self.instance.sample_type)
        instance.container_type = self.cleaned_data.get("container_type", self.instance.container_type)

        if commit:
            instance.save()
        return instance

    def get_custom_field_order(self):
        return [
            "sample_type_display",
            "container_type_display",
            "current_step",
            "avail_at",
            "part_no",
            "body_site",
            "sub_site",
            "collection_method",
            "receive_dt",
            "receive_dt_timezone",
            "collection_dt",
            "collection_dt_timezone",
        ]


class QCStatusForm(forms.Form):
    qc_status_choices = [
        ('Pass', 'Pass'),
        ('Fail', 'Fail'),
    ]
    qc_status = forms.ChoiceField(choices=qc_status_choices, required=True, label='')
