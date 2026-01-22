from django import forms

from controllerapp import settings
from reporting.models import LabelMethod, Printer
from util.util import UtilClass


class LabelMethodForm(forms.ModelForm):

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_DELIMITER', '')
        self.fields["delimiter"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False, label="Delimiter",
        )
        required_reftype = getattr(settings, 'APPLICATION_FILE_FORMAT', '')
        self.fields["file_format"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False, label="Label File Format",
        )

    class Meta:
        model = LabelMethod
        fields = "__all__"


class PrinterForm(forms.ModelForm):

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_PRINTER_COMMUNICATION_TYPE', '')
        self.fields["communication_type"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False, label="Printer Communication Type",
        )

    class Meta:
        model = Printer
        fields = "__all__"
