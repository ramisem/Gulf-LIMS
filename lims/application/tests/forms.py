from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError

from controllerapp import settings
from util.util import UtilClass
from .models import Test, TestWorkflowStep, TestWFSTPInstrumentMap, TestWFSTPConsumableMap, WorkflowStepConfigField, \
    TestAnalyte


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,  # Allow null or blank if needed
        )


class TestWorkflowStepInlineForm(forms.ModelForm):
    step_no = forms.CharField(label="Step Number", disabled=True, required=False)
    workflow_type = forms.CharField(label="Workflow Type", disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.workflow_step_id:
            workflow_step = self.instance.workflow_step_id
            if workflow_step:
                self.fields['step_no'].initial = workflow_step.step_no
                self.fields['workflow_type'].initial = workflow_step.workflow_type

    class Meta:
        model = TestWorkflowStep
        fields = "__all__"


class TestWFSTPInstrumentMapInlineForm(forms.ModelForm):
    step_no = forms.CharField(label="Step Number", disabled=True, required=False)
    workflow_type = forms.CharField(label="Workflow Type", disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.workflow_step_id:
            workflow_step = self.instance.workflow_step_id
            if workflow_step:
                self.fields['step_no'].initial = workflow_step.step_no
                self.fields['workflow_type'].initial = workflow_step.workflow_type

    class Meta:
        model = TestWFSTPInstrumentMap
        fields = "__all__"


class TestWFSTPConsumableMapInlineForm(forms.ModelForm):
    step_no = forms.CharField(label="Step Number", disabled=True, required=False)
    workflow_type = forms.CharField(label="Workflow Type", disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.workflow_step_id:
            workflow_step = self.instance.workflow_step_id
            if workflow_step:
                self.fields['step_no'].initial = workflow_step.step_no
                self.fields['workflow_type'].initial = workflow_step.workflow_type

    class Meta:
        model = TestWFSTPConsumableMap
        fields = "__all__"


class WorkflowStepConfigFieldForm(forms.ModelForm):
    class Meta:
        model = WorkflowStepConfigField
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(WorkflowStepConfigFieldForm, self).__init__(*args, **kwargs)

        # Explicitly define `field_id` as a ChoiceField before modifying it
        self.fields['field_id'] = forms.ChoiceField(
            choices=[],  # Initially empty
            label="Column Id",
            help_text="Select a model above to see its columns.",
            required=True
        )

        # First, update the "model" field choices.
        required_reftype = getattr(settings, 'APPLICATION_MODEL_REFERENCE', '')
        self.fields["model"] = forms.ChoiceField(
            choices=[("", "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True,
        )

        model_names = [name_tuple[0] for name_tuple in UtilClass.get_refvalues_for_field(required_reftype)]
        print("model_names : ", str(model_names))
        field_choices = []  # Aggregate fields for all models
        if model_names:
            for model_class in apps.get_models():  # Fetch all models across all apps
                if model_class.__name__ in model_names:
                    try:
                        print(f"✅ Found model: {model_class.__name__} (App: {model_class._meta.app_label})")

                        # Extract valid fields
                        for field in model_class._meta.get_fields():
                            if hasattr(field, 'attname'):  # Ensure it's a valid DB field
                                # field_choices.append((field.name, f"{model_class.__name__} - {field.name}"))
                                field_choices.append((field.name, field.name))

                    except Exception as e:
                        print(f"⚠️ Error processing model {model_class.__name__}: {e}")

            print("Final field_choices:", field_choices)
            self.fields['field_id'].choices = field_choices  # Assign aggregated field choices
        else:
            # If no model name is provided, initialize with an empty dropdown.
            self.fields['field_id'] = forms.ChoiceField(
                choices=[],
                label="Column Id",
                help_text="Select a model above to see its columns.",
                required=True
            )


class TestAnalyteForm(forms.ModelForm):
    value1_unit = forms.CharField(label='Unit of Value-1', max_length=10, required=False,
                                  widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    value2_unit = forms.CharField(label='Unit of Value-2', max_length=10, required=False,
                                  widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = TestAnalyte
        fields = "__all__"

        widgets = {
            'value1': forms.TextInput(attrs={'onchange': 'populateAnalyteUnit(this.id)'}),
            'value2': forms.TextInput(attrs={'onchange': 'populateAnalyteUnit(this.id)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_INPUT_MODE_OPTION_REFERENCE', '')
        self.fields["input_mode"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,  # Allow null or blank if needed
        )
        required_reftype = getattr(settings, 'APPLICATION_DATA_TYPE_REFERENCE', '')
        self.fields["data_type"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,  # Allow null or blank if needed
        )

        if self.instance and self.instance.pk:
            unit_obj = self.instance.unit_id
            unit_name = unit_obj.unit if unit_obj else ''
            self.fields['value1_unit'].initial = unit_name
            self.fields['value2_unit'].initial = unit_name

    def clean(self):
        cleaned_data = super().clean()
        operator1 = cleaned_data.get('operator1', '')
        value1 = cleaned_data.get('value1', '')
        condition = cleaned_data.get('condition', '')
        operator2 = cleaned_data.get('operator2', '')
        value2 = cleaned_data.get('value2', '')

        # Perform your validation logic here
        if (operator1 is not None and operator1 != '') and (value1 is None or value1 == ''):
            raise ValidationError("Value1 cannot be empty.")
        if (condition is not None and condition != '') and (operator2 is None or operator2 == ''):
            raise ValidationError(
                "Operator-2 cannot be blank.")
        elif (operator2 is not None and operator2 != '') and (value2 is None or value2 == ''):
            raise ValidationError("Value2 cannot be empty.")

        # Return cleaned data
        return cleaned_data
