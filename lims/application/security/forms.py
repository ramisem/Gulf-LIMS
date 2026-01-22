from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from controllerapp import settings
from reporting.models import Printer
from security.models import User, JobType, Site, UserPrinterInfo, DepartmentPrinter
from util.util import UtilClass

User = User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name')


class UserGroupAuthenticationForm(AdminAuthenticationForm):
    selectedjobtype = forms.CharField(widget=forms.HiddenInput())
    selectedsite = forms.ChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super(UserGroupAuthenticationForm, self).__init__(*args, **kwargs)
        sites = Site.objects.all()
        site_choices = [(each_site.name, each_site.name) for each_site in sites]
        site_choices.insert(0, ("None", "None"))
        self.fields['selectedsite'].choices = site_choices

    def clean(self):
        username = self.cleaned_data.get("username")
        selectedjobtype = self.cleaned_data.get("selectedjobtype")
        selectedsite = self.cleaned_data.get("selectedsite")
        if username and selectedjobtype:
            user = User.objects.filter(username=username).first()
            jobtype = JobType.objects.filter(name=selectedjobtype).first()

            if not user:
                raise ValidationError("User ID is not valid")

            if user.is_superuser:
                return super().clean()

            if not jobtype:
                raise ValidationError("JobType is not valid")

            if not user.is_superuser:
                if jobtype not in user.jobtypes.all():
                    raise ValidationError("This User does not belong to the specified JobType")
                user.groups.clear()
                user.groups.add(jobtype)
                if 'currentdepartmentid' in self.request.session:
                    del self.request.session['currentdepartmentid']
                if 'currentjobtype' in self.request.session:
                    del self.request.session['currentjobtype']
                if 'currentsite' in self.request.session:
                    del self.request.session['currentsite']
                if 'currenttimezone' in self.request.session:
                    del self.request.session['currenttimezone']
                self.request.session['currentjobtype'] = selectedjobtype
                if jobtype.departmentid:
                    self.request.session['currentdepartmentid'] = jobtype.departmentid.name
                site = Site.objects.get(name=selectedsite)
                timezone = site.timezone.name if site.timezone else getattr(settings, 'SERVER_TIME_ZONE', 'UTC')
                self.request.session['currentsite'] = site.name
                self.request.session['currenttimezone'] = timezone
                return super().clean()

        raise ValidationError("Please provide both userid and job type")


class JobTypeChangeForm(forms.Form):
    selectedjobtype = forms.ChoiceField(choices=(), label="Select JobType",
                                        widget=forms.TextInput(
                                            attrs={"autofocus": True}
                                        ), )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(JobTypeChangeForm, self).__init__(*args, **kwargs)
        if self.user.is_superuser:
            job_type_choices = [
                ("None", "None")
            ]
            self.fields['selectedjobtype'].choices = job_type_choices
        else:
            job_types = self.user.jobtypes.all()
            job_type_choices = [(each_jobtype.name, each_jobtype.name) for each_jobtype in job_types]
            self.fields['selectedjobtype'].choices = job_type_choices

    def clean_selectedjobtype(self):
        selectedjobtype = self.cleaned_data.get("selectedjobtype")
        if not selectedjobtype:
            raise ValidationError("Please select the jobtype.")
        jobtype = JobType.objects.filter(name=selectedjobtype).first()
        if not jobtype:
            raise ValidationError("JobType is not valid")
        return selectedjobtype

    def save(self, commit=True):
        selectedjobtype = self.cleaned_data.get("selectedjobtype")
        if commit and selectedjobtype:
            jobtype = JobType.objects.filter(name=selectedjobtype).first()
            self.user.groups.clear()
            self.user.groups.add(jobtype)
        return self.user


class UserPrinterInfoForm(forms.ModelForm):
    printer_id = forms.ModelChoiceField(
        queryset=Printer.objects.all(),
        label="Printer",
        required=True
    )

    class Meta:
        model = UserPrinterInfo
        fields = "__all__"
        widgets = {
            'jobtype_id': forms.Select(attrs={'class': 'jobtype-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_PRINTERCATEGORY_REFERENCE', '')
        self.fields["printer_category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True,  # Allow null or blank if needed
        )

        if kwargs.get('instance') and kwargs['instance'].jobtype_id:
            self.fields['printer_id'].queryset = Printer.objects.filter(
                departmentprinter__jobtype_id=kwargs['instance'].jobtype_id
            ).distinct()
            # Set the initial value if it exists
            if kwargs['instance'].printer_id:
                self.fields['printer_id'].initial = kwargs['instance'].printer_id

    def clean(self):
        cleaned_data = super().clean()
        jobtype = cleaned_data.get('jobtype_id')
        printer = cleaned_data.get('printer_id')

        if jobtype and printer:
            if not DepartmentPrinter.objects.filter(jobtype_id=jobtype, printer_id=printer).exists():
                raise forms.ValidationError(
                    "The selected printer is not associated with the selected job type in Department Printers."
                )
        return cleaned_data


class DepartmentPrinterInlineForm(forms.ModelForm):
    printer_path = forms.CharField(label="Printer Path", disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "printer_id") and self.instance.printer_id:
            self.fields['printer_path'].initial = self.instance.printer_id.printer_path

    class Meta:
        model = DepartmentPrinter
        fields = "__all__"