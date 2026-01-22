from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AdminSplitDateTime
from django.db import models
from django.forms import SplitDateTimeField

from sample.models import Sample, SampleTestMap, SampleType, ContainerType
from template.models import GrossCodeTemplate
from tests.models import WorkflowStepConfigField
from util.util import UtilClass
from workflows.models import WorkflowStep


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = [
            "sample_type",
            "container_type",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._set_choice_field('gross_code', 'APPLICATION_GROSS_CODE_REFERENCE')
        gross_codes = GrossCodeTemplate.objects.values_list("gross_code", "gross_code")
        self.fields["gross_code"] = forms.ChoiceField(
            choices=[('', '---------')] + list(gross_codes),
            required=False,
            label="Gross Code"
        )

        # Set initial value for gross_code
        if self.instance and self.instance.gross_code:
            self.fields["gross_code"].initial = self.instance.gross_code

        self._set_choice_field('descriptive', 'APPLICATION_DESCRIPTIVE_REFERENCE')

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
            required=False
        )


class SampleBulkEditForm(forms.ModelForm):
    # Read-only display fields for human-readable names
    sample_type_display = forms.CharField(label="Sample Type", required=False, disabled=True)
    container_type_display = forms.CharField(label="Container", required=False, disabled=True)

    # Hidden fields to store primary key values
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
        model = Sample
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

    def __init__(self, *args, **kwargs):
        # Optionally accept a custom ordering list from kwargs
        custom_order = kwargs.pop('custom_order', None)
        super().__init__(*args, **kwargs)

        # Set initial values for display fields.
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
                    model="Sample"
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
                            model="Sample"
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

        # Make all meta fields read-only without affecting display fields.
        for field_name in self.Meta.fields:
            if field_name in self.fields:
                self.fields[field_name].disabled = True

        # Determine the desired field order.
        if custom_order is None:
            custom_order = self.get_custom_field_order()
        # Ensure we only include fields that actually exist in the form.
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
        """
        Ensures FK fields are properly populated using hidden fields.
        """
        cleaned_data = super().clean()

        # Ensure proper assignment of sample_type
        sample_type_obj = cleaned_data.get("sample_type_pk")
        if not sample_type_obj and self.instance and self.instance.sample_type:
            sample_type_obj = self.instance.sample_type
        cleaned_data["sample_type"] = sample_type_obj

        # Ensure proper assignment of container_type
        container_type_obj = cleaned_data.get("container_type_pk")
        if not container_type_obj and self.instance and self.instance.container_type:
            container_type_obj = self.instance.container_type
        cleaned_data["container_type"] = container_type_obj

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save the values for dynamic fields.
        for field_name in getattr(self, 'dynamic_fields', []):
            setattr(instance, field_name, self.cleaned_data.get(field_name))

        # Ensure proper assignment for FK fields.
        instance.sample_type = self.cleaned_data.get("sample_type", self.instance.sample_type)
        instance.container_type = self.cleaned_data.get("container_type", self.instance.container_type)

        if commit:
            instance.save()
        return instance

    def get_custom_field_order(self):
        """
        Return a list of field names in the desired custom order.
        This list can mix display fields and meta fields arbitrarily.
        For instance, you might want one display field, then a meta field,
        then two display fields, and finally one meta field.
        """
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
