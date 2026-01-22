import inspect
import re

from django import forms
from django.forms import ClearableFileInput
from django.utils.safestring import mark_safe
from django_summernote.widgets import SummernoteWidget

from configuration.models import RefValues
from controllerapp import settings
from tests.models import TestAnalyte, Analyte
from util.util import UtilClass
from .models import ReportOptionDtl, ReportOption, MergeReportingDtl, MergeReporting, Attachment, \
    HistoricalMergeReporting


class ReportOptionDtlForm(forms.ModelForm):
    hidden_report_option_dtl_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ReportOptionDtl
        fields = ['hidden_report_option_dtl_id', 'analyte_id', 'analyte_value']

    class Media:
        js = ('js/analysis/reportoption_autosave.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        is_pathologist_present = True
        self.fields['hidden_report_option_dtl_id'].initial = self.instance.report_option_dtl_id
        if self.instance.pk:
            report_option_id = self.instance.report_option_id
            if not report_option_id.assign_pathologist:
                is_pathologist_present = False

        # Determine test_id and analyte_id
        test_id = None
        analyte_id = None
        if self.instance and self.instance.pk:
            analyte_id = self.instance.analyte_id_id
            test_id = (
                self.instance.report_option_id.test_id_id
                if self.instance.report_option_id else None
            )
        else:
            # For new instances, try to get test_id via the parent ReportOption instance if provided
            report_option = None
            if 'report_option_id' in self.initial:
                report_option = ReportOption.objects.filter(pk=self.initial['report_option_id']).first()

            test_id = report_option.test_id_id if report_option else self.initial.get('test_id')
            analyte_id = self.initial.get('analyte_id')

        if test_id and analyte_id:
            try:
                ta = TestAnalyte.objects.get(test_id_id=test_id, analyte_id_id=analyte_id)
            except TestAnalyte.DoesNotExist:
                ta = None

            if ta and is_pathologist_present == True:
                mode = ta.input_mode
                dtype = ta.data_type

                field = self.fields['analyte_value']

                # Input modes
                if mode == 'input':
                    if dtype == 'integer':
                        self.fields['analyte_value'] = forms.IntegerField(
                            widget=forms.NumberInput(),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    elif dtype == 'decimal':
                        self.fields['analyte_value'] = forms.DecimalField(
                            widget=forms.NumberInput(attrs={'step': 'any'}),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    elif dtype == 'text':
                        field = self.fields['analyte_value']
                        field.widget = forms.Textarea()
                    elif dtype == 'rich_text':
                        self.fields['analyte_value'] = forms.CharField(
                            widget=SummernoteWidget(),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    else:
                        self.fields['analyte_value'].widget = forms.TextInput()

                elif mode == 'dropdown_reftype':
                    # Populate choices from ReferenceType
                    ref_type = ta.dropdown_reference_type
                    choices = []
                    if ref_type:
                        # Assume ReferenceTypeValue model with FK to ReferenceType
                        values = RefValues.objects.filter(reftype_id=ref_type)
                        choices = [('', '')] + [(v.value, v.display_value) for v in values]
                    field.widget = forms.Select(choices=choices)

                elif mode == 'dropdown_sql':
                    # Execute custom SQL to get choices
                    original_sql = ta.dropdown_sql or ''
                    raw_sql = ta.dropdown_sql
                    choices = []

                    if raw_sql:
                        # static params
                        params = {
                            # 'arg1': self.initial.get('arg1'),
                            # …any others like userid, dept,etc…
                        }

                        # get the current report_option_id
                        ro_id = (
                            self.instance.report_option_id_id
                            if self.instance and self.instance.pk
                            else self.initial.get('report_option_id')
                        )

                        # resolve any :param|lookup tokens (Dynamic Analyte ID Tokens)
                        raw_sql = resolve_dynamic_placeholders(raw_sql, ro_id, params, ReportOptionDtl)

                        # execute the final SQL (expands semicolons, lists, etc.)
                        rows = UtilClass.resolve_sql(raw_sql, params)
                        # Use a set to remove duplicates
                        seen = set()
                        unique_rows = []
                        for r in rows:
                            key = (r[0], r[1])
                            if key not in seen:
                                seen.add(key)
                                unique_rows.append(key)

                        choices = [('', '')] + unique_rows

                    # 1) pull out everything after the '|' in each :key|Lookup
                    raw_lookups = re.findall(r':\w+\|([^\'"]+)', original_sql)
                    raw_lookups = [lk.strip() for lk in raw_lookups]

                    widget = forms.Select(attrs={
                        'data-ta-id': str(ta.pk),
                        'data-dropdown-lookups': ';'.join(raw_lookups),
                    })
                    self.fields['analyte_value'] = forms.ChoiceField(
                        choices=choices,
                        required=self.fields['analyte_value'].required,
                        label=self.fields['analyte_value'].label,
                        widget=widget,
                    )

                elif mode == 'input_sql':
                    # Execute custom SQL and show result in a text field
                    original_sql = ta.dropdown_sql or ''
                    raw_sql = ta.dropdown_sql
                    result_value = ""

                    if raw_sql:
                        # static params
                        params = {
                            # 'arg1': self.initial.get('arg1'),
                            # …any others like userid, dept,etc…
                        }

                        # get the current report_option_id
                        ro_id = (
                            self.instance.report_option_id_id
                            if self.instance and self.instance.pk
                            else self.initial.get('report_option_id')
                        )

                        # resolve any :param|lookup tokens (Dynamic Analyte ID Tokens)
                        raw_sql = resolve_dynamic_placeholders(raw_sql, ro_id, params, ReportOptionDtl)

                        # execute the final SQL (expands semicolons, lists, etc.)
                        rows = UtilClass.resolve_sql(raw_sql, params)
                        if rows:
                            result_value = rows[0][0]  # take 2nd column of the first result row

                    # 1) pull out everything after the '|' in each :key|Lookup
                    # extract the *lookup* text, including spaces & symbols
                    raw_lookups = re.findall(r':\w+\|([^\'"]+)', original_sql)
                    raw_lookups = [lk.strip() for lk in raw_lookups]

                    if dtype == 'text':
                        widget = forms.Textarea(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                        })
                        print("Final Textarea widget attrs:", widget.attrs)
                    elif dtype == 'rich_text':
                        widget = CustomSummernoteWidget(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                            'class': 'has-dropdown-sql'
                        })
                        print("Final CustomSummernoteWidget widget attrs:", widget.attrs)
                    else:
                        self.fields['analyte_value'].widget = forms.TextInput(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                        })

                    self.fields['analyte_value'] = forms.CharField(
                        initial=result_value,
                        required=self.fields['analyte_value'].required,
                        label=self.fields['analyte_value'].label,
                        widget=widget,
                    )

                elif mode == 'readonly':
                    field.widget = forms.TextInput(attrs={'readonly': 'readonly'})

                elif mode == 'hidden':
                    field.widget = forms.HiddenInput()

                # Optionally enforce field type conversions/validation
                if dtype == 'integer':
                    field.to_python = lambda value: int(value) if value is not None else None
                elif dtype == 'decimal':
                    from decimal import Decimal
                    field.to_python = lambda value: Decimal(value) if value is not None else None


class CustomSummernoteWidget(SummernoteWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs or {})

        # Extract the attributes you want to preserve
        ta_id = final_attrs.pop("data-ta-id", "")
        dropdown_lookups = final_attrs.pop("data-dropdown-lookups", "")
        css_class = final_attrs.get("class", "")

        render_args = inspect.signature(super().render).parameters
        if 'renderer' in render_args:
            summernote_html = super().render(name, value, final_attrs, renderer)
        else:
            summernote_html = super().render(name, value, final_attrs)

        # Wrap with span for reliable access to data attributes
        wrapped = f'''
            <span class="analyte-value-wrapper" 
                  data-ta-id="{ta_id}" 
                  data-dropdown-lookups="{dropdown_lookups}">
                {summernote_html}
            </span>
        '''
        return mark_safe(wrapped)


class ReportOptionForm(forms.ModelForm):
    hidden_reportoption_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    current_user = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hidden_reportoption_id'].initial = self.instance.report_option_id
        self.fields['assign_pathologist'] = forms.CharField(widget=forms.HiddenInput(), required=False)
        self.fields['current_user'].initial = request.user.pk

    class Meta:
        model = ReportOption
        fields = '__all__'


class MergeReportingDtlForm(forms.ModelForm):
    hidden_merge_reporting_dtl_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = MergeReportingDtl
        fields = [
            'hidden_merge_reporting_dtl_id',
            'analyte_id', 'analyte_value']

    class Media:
        js = ('js/analysis/mergereporting_autosave.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        is_pathologist_present = True
        self.fields['hidden_merge_reporting_dtl_id'].initial = self.instance.merge_reporting_dtl_id
        if self.instance.pk:
            report_option_id = self.instance.report_option_id
            if not report_option_id.assign_pathologist:
                is_pathologist_present = False

        # Determine test_id and analyte_id
        test_id = None
        analyte_id = None
        if self.instance and self.instance.pk:
            analyte_id = self.instance.analyte_id_id
            test_id = (
                self.instance.report_option_id.test_id_id
                if self.instance.report_option_id else None
            )
        else:
            # For new instances, try to get test_id via the parent ReportOption instance if provided
            report_option = None
            if 'report_option_id' in self.initial:
                report_option = ReportOption.objects.filter(pk=self.initial['report_option_id']).first()

            test_id = report_option.test_id_id if report_option else self.initial.get('test_id')
            analyte_id = self.initial.get('analyte_id')

        if test_id and analyte_id:
            try:
                ta = TestAnalyte.objects.get(test_id_id=test_id, analyte_id_id=analyte_id)
            except TestAnalyte.DoesNotExist:
                ta = None

            if ta and is_pathologist_present == True:
                mode = ta.input_mode
                dtype = ta.data_type

                field = self.fields['analyte_value']

                # Input modes
                if mode == 'input':
                    if dtype == 'integer':
                        self.fields['analyte_value'] = forms.IntegerField(
                            widget=forms.NumberInput(),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    elif dtype == 'decimal':
                        self.fields['analyte_value'] = forms.DecimalField(
                            widget=forms.NumberInput(attrs={'step': 'any'}),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    elif dtype == 'text':
                        field = self.fields['analyte_value']
                        field.widget = forms.Textarea()
                    elif dtype == 'rich_text':
                        self.fields['analyte_value'] = forms.CharField(
                            widget=SummernoteWidget(),
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                        )
                    else:
                        self.fields['analyte_value'].widget = forms.TextInput()

                elif mode == 'dropdown_reftype':
                    # Populate choices from ReferenceType
                    ref_type = ta.dropdown_reference_type
                    choices = []
                    if ref_type:
                        # Assume ReferenceTypeValue model with FK to ReferenceType
                        values = RefValues.objects.filter(reftype_id=ref_type)
                        choices = [('', '')] + [(v.value, v.display_value) for v in values]
                    field.widget = forms.Select(choices=choices)

                elif mode == 'dropdown_sql':
                    # Execute custom SQL to get choices
                    original_sql = ta.dropdown_sql or ''
                    raw_sql = ta.dropdown_sql
                    choices = []

                    if raw_sql:
                        # static params
                        params = {
                            # 'arg1': self.initial.get('arg1'),
                            # …any others like userid, dept,etc…
                        }

                        # get the current report_option_id
                        ro_id = (
                            self.instance.report_option_id_id
                            if self.instance and self.instance.pk
                            else self.initial.get('report_option_id')
                        )

                        # resolve any :param|lookup tokens (Dynamic Analyte ID Tokens)
                        raw_sql = resolve_dynamic_placeholders(raw_sql, ro_id, params, MergeReportingDtl)

                        # execute the final SQL (expands semicolons, lists, etc.)
                        rows = UtilClass.resolve_sql(raw_sql, params)
                        # Use a set to remove duplicates
                        seen = set()
                        unique_rows = []
                        for r in rows:
                            key = (r[0], r[1])
                            if key not in seen:
                                seen.add(key)
                                unique_rows.append(key)

                        choices = unique_rows

                        # 1) pull out everything after the '|' in each :key|Lookup
                        raw_lookups = re.findall(r':\w+\|([^\'"]+)', original_sql)
                        raw_lookups = [lk.strip() for lk in raw_lookups]

                        widget = forms.Select(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                        })
                        self.fields['analyte_value'] = forms.ChoiceField(
                            choices=choices,
                            required=self.fields['analyte_value'].required,
                            label=self.fields['analyte_value'].label,
                            widget=widget,
                        )

                elif mode == 'input_sql':
                    # Execute custom SQL and show result in a text field
                    original_sql = ta.dropdown_sql or ''
                    raw_sql = ta.dropdown_sql
                    result_value = ""

                    if raw_sql:
                        # static params
                        params = {
                            # 'arg1': self.initial.get('arg1'),
                            # …any others like userid, dept,etc…
                        }

                        # get the current report_option_id
                        ro_id = (
                            self.instance.report_option_id_id
                            if self.instance and self.instance.pk
                            else self.initial.get('report_option_id')
                        )

                        # resolve any :param|lookup tokens (Dynamic Analyte ID Tokens)
                        raw_sql = resolve_dynamic_placeholders(raw_sql, ro_id, params, MergeReportingDtl)

                        # execute the final SQL (expands semicolons, lists, etc.)
                        rows = UtilClass.resolve_sql(raw_sql, params)
                        if rows:
                            result_value = rows[0][0]  # take 2nd column of the first result row

                    # 1) pull out everything after the '|' in each :key|Lookup
                    # extract the *lookup* text, including spaces & symbols
                    raw_lookups = re.findall(r':\w+\|([^\'"]+)', original_sql)
                    raw_lookups = [lk.strip() for lk in raw_lookups]

                    if dtype == 'text':
                        widget = forms.Textarea(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                        })
                        print("Final Textarea widget attrs:", widget.attrs)
                    elif dtype == 'rich_text':
                        widget = CustomSummernoteWidget(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                            'class': 'has-dropdown-sql'
                        })
                        print("Final CustomSummernoteWidget widget attrs:", widget.attrs)
                    else:
                        self.fields['analyte_value'].widget = forms.TextInput(attrs={
                            'data-ta-id': str(ta.pk),
                            'data-dropdown-lookups': ';'.join(raw_lookups),
                        })

                    self.fields['analyte_value'] = forms.CharField(
                        initial=result_value,
                        required=self.fields['analyte_value'].required,
                        label=self.fields['analyte_value'].label,
                        widget=widget,
                    )

                elif mode == 'readonly':
                    field.widget = forms.TextInput(attrs={'readonly': 'readonly'})

                elif mode == 'hidden':
                    field.widget = forms.HiddenInput()

                # Optionally enforce field type conversions/validation
                if dtype == 'integer':
                    field.to_python = lambda value: int(value) if value is not None else None
                elif dtype == 'decimal':
                    from decimal import Decimal
                    field.to_python = lambda value: Decimal(value) if value is not None else None


def resolve_dynamic_placeholders(raw_sql, report_option_id, params, model_class):
    """
    Dynamically resolves placeholders in SQL using the given model (e.g., ReportOptionDtl or MergeReportingDtl).
    """
    if not isinstance(raw_sql, str):
        raise TypeError(f"Expected raw_sql to be str, got {type(raw_sql).__name__}")

    pattern = re.compile(r"'?:(?P<key>\w+)\|(?P<lookup>[^']+)'?")

    def _replacer(match):
        key = match.group('key')
        lookup = match.group('lookup')
        rod = None

        if lookup.isdigit():
            rod = model_class.objects.filter(
                report_option_id=report_option_id,
                analyte_id=int(lookup)
            ).first()

        if rod is None:
            try:
                analyte_obj = Analyte.objects.get(analyte=lookup)
                rod = model_class.objects.filter(
                    report_option_id=report_option_id,
                    analyte_id=analyte_obj.pk
                ).first()
            except Analyte.DoesNotExist:
                rod = None

        val = rod.analyte_value if rod else None
        safe = re.sub(r'[^0-9A-Za-z]+', '_', lookup).strip('_')
        new_key = f"{key}__{safe}"
        params[new_key] = val

        return f":{new_key}"

    return pattern.sub(_replacer, raw_sql)


class MergeReportingForm(forms.ModelForm):
    hidden_merge_reporting_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    current_user = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hidden_merge_reporting_id'].initial = self.instance.merge_reporting_id
        self.fields['assign_pathologist'] = forms.CharField(widget=forms.HiddenInput(), required=False)
        self.fields['current_user'].initial = request.user.pk

    class Meta:
        model = MergeReporting
        fields = '__all__'


class HistoricMergeReportingForm(forms.ModelForm):
    hidden_merge_reporting_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    current_user = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hidden_merge_reporting_id'].initial = self.instance.merge_reporting_id
        self.fields['assign_pathologist'] = forms.CharField(widget=forms.HiddenInput(), required=False)
        self.fields['current_user'].initial = request.user.pk

    class Meta:
        model = HistoricalMergeReporting
        fields = '__all__'


class NoLinkFileWidget(ClearableFileInput):
    def format_value(self, value):
        if value and hasattr(value, 'name'):
            return value.name  # Just display the filename, no link
        return super().format_value(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value and hasattr(value, 'url'):
            # This is what normally causes the hyperlink to show — remove it
            context['widget']['is_initial'] = False
        return context


class AttachmentInlineForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_path'].label = 'Upload'

        required_reftype = getattr(settings, 'APPLICATION_ATTACHMENT_TYPE', '')
        self.fields["attachment_type"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )


