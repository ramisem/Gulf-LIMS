from django import forms

from controllerapp import settings
from util.util import UtilClass
from workflows.models import WorkflowStep, ModalityModelMap, Workflow


class WorkflowStepInlineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_DEPARTMENT_NAME_REFERENCE', '')
        self.fields["department"] = forms.ChoiceField(
            choices=[(None, "---------")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True,  # Allow null or blank if needed
        )

    class Meta:
        model = WorkflowStep
        fields = "__all__"


class ModalityModelMapForm(forms.ModelForm):
    modality = forms.ChoiceField(choices=(), required=True, label="Modality")
    model = forms.ChoiceField(choices=(), required=True, label="Model")

    class Meta:
        model = ModalityModelMap
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) Populate modality choices from Workflow.workflow_name
        workflows = Workflow.objects.order_by('workflow_name').values_list(
            'workflow_name', 'workflow_name'
        )
        self.fields['modality'].choices = [("", "---------")] + list(workflows)

        # 2) Populate model choices as before
        required_reftype = getattr(settings, 'APPLICATION_MODEL_REFERENCE', '')
        ref_choices = UtilClass.get_refvalues_for_field(required_reftype)
        self.fields['model'].choices = [("", "---------")] + ref_choices
