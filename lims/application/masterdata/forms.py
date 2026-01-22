from django import forms

from controllerapp import settings
from util.util import UtilClass
from .models import ClientDoctorInfo, Physician, Client, Patient, BioSite, BodySite, ReportImgPropInfo, \
    AttachmentConfiguration, Sponsor, BioProject, ProjectVisitMap, QCPendingBioProject, EmailConfig, ProjectPhysicianMap
from .widgets import LargeTextarea
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class ClientDoctorInfoForm(forms.ModelForm):
    phone_number = forms.CharField(label='Phone Number', max_length=40, required=False,
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    fax_number = forms.CharField(label='Fax Number', max_length=40, required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    email = forms.CharField(label='Email Address', max_length=40, required=False,
                            widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        physician_id = kwargs.pop('physician_id', None)
        self.fields['physician_id'].choices = [
            (physician.physician_id,
             (physician.first_name + " " + physician.last_name)) for physician in
            Physician.objects.filter(external=True)]
        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        if not physician_id:
            physician_id = self.initial.get('physician_id')

        if physician_id:
            try:
                physician_obj = Physician.objects.get(physician_id=physician_id)
                self.fields['phone_number'].initial = physician_obj.phone_number
                self.fields['fax_number'].initial = physician_obj.fax_number
                self.fields['email'].initial = physician_obj.email
            except Physician.DoesNotExist:
                pass

    class Meta:
        model = ClientDoctorInfo
        fields = ['physician_id']

        widgets = {
            'physician_id': forms.Select(attrs={'class': 'form-control', 'onchange': 'updatePhysicianDetails(this)'}),
        }


class ClientForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )

    class Meta:
        model = Client
        fields = ['client_id']


class PatientForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        required_reftype = getattr(settings, 'APPLICATION_GENDER_TYPE_REFERENCE', '')
        self.fields["gender"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        required_reftype = getattr(settings, 'APPLICATION_MARITAL_STATUS_REFERENCE', '')
        self.fields["marital_status"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        required_reftype = getattr(settings, 'APPLICATION_SMOKING_STATUS_REFERENCE', '')
        self.fields["smoking_status"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )

    class Meta:
        model = Patient
        fields = ['patient_id']


class PhysicianForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        category_ref_type = getattr(settings, 'APPLICATION_DOCTOR_CATEGORY', '')
        self.fields["category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(category_ref_type),
            required=False,
        )

    class Meta:
        model = Physician
        fields = ['physician_id']


class BodySiteForm(forms.ModelForm):
    class Meta:
        model = BodySite
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_BODY_SITE', '')
        self.fields["body_site"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True,  # Allow null or blank if needed
        )


class BodySubSiteMapForm(forms.ModelForm):
    class Meta:
        model = BodySite
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        subsite_ref_type = getattr(settings, 'APPLICATION_SUB_SITE_REFERENCE', '')
        self.fields["sub_site"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(subsite_ref_type),
            required=True,
        )


class ReportImgPropInfoForm(forms.ModelForm):
    class Meta:
        model = ReportImgPropInfo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_CATEGORY_REFERENCE', '')
        self.fields["category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True,
        )


class AttachmentConfigurationForm(forms.ModelForm):
    class Meta:
        model = AttachmentConfiguration
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_reftype = getattr(settings, 'APPLICATION_MODEL_REFERENCE', '')
        self.fields["model_name"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )


class BioProjectForm(forms.ModelForm):
    sponsor_name = forms.ModelChoiceField(
        queryset=Sponsor.objects.all(),
        label="Sponsor Name",
        required=True
    )
    sponsor_name.label_from_instance = lambda obj: f"{obj.sponsor_name} - {obj.sponsor_number}"

    qced_by_str = forms.CharField(label='QCed By', max_length=40, required=False,
                              widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qced_dt_str = forms.CharField(label='QCed Date', max_length=40, required=False,
                              widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    #  Hidden field for bioproject_id
    bioproject_id = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = BioProject
        exclude = ('created_by', 'created_dt', 'mod_by', 'mod_dt')
        widgets = {
            'modification_notes': LargeTextarea(),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial sponsor_name and sponsor_number if editing existing instance
        if self.instance and self.instance.pk:
            self.fields['sponsor_name'].initial = self.instance.sponsor_id
            if self.instance.qced_by:
                self.fields['qced_by_str'].initial = self.instance.qced_by.username
            else:
                self.fields['qced_by_str'].initial = None  # Or ""
            self.fields['qced_dt_str'].initial = self.instance.qced_dt
        if 'sponsor_id' in self.fields:
            self.fields['sponsor_id'].widget.attrs['readonly'] = True
        if 'qc_status' in self.fields:
            self.fields['qc_status'].widget.attrs['readonly'] = True
            self.fields['qc_status'].required = False
        if 'qc_reason' in self.fields:
            self.fields['qc_reason'].widget.attrs['readonly'] = True
            self.fields['qc_reason'].required = False

    def clean(self):
        cleaned_data = super().clean()
        sponsor = cleaned_data.get('sponsor_name')
        project_protocol_id = cleaned_data.get('project_protocol_id')
        if sponsor:
            cleaned_data['sponsor_id'] = sponsor
        if cleaned_data.get('qced_by') == '':
            cleaned_data['qced_by'] = None
        if cleaned_data.get('qced_dt') == '':
            cleaned_data['qced_dt'] = None

        if self.instance.pk:
            # Fetch the original values
            existing = BioProject.objects.get(pk=self.instance.pk)
            if project_protocol_id:
                project_protocol_changed = existing.project_protocol_id != project_protocol_id

        else:
            # New record → always check duplicates
            project_protocol_changed = True

        # Only check duplicates if project_protocol_id is changed
        if project_protocol_changed:
            # Check for duplicate sponsor name
            if BioProject.objects.exclude(pk=self.instance.pk).filter(project_protocol_id=project_protocol_id).exists():
                self.add_error('project_protocol_id', f"Project/Protocol ID '{project_protocol_id}' already exists.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.sponsor_id = self.cleaned_data['sponsor_name']
        if commit:
            instance.save()
        return instance


class ProjectVisitMapForm(forms.ModelForm):
    class Meta:
        model = ProjectVisitMap
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'visit_id' in self.fields:
            self.fields['visit_id'].required = True


class ProjectEmailMapForm(forms.ModelForm):
    class Meta:
        model = ProjectVisitMap
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_reftype = getattr(settings, 'APPLICATION_PROJECT_EMAIL_REFERENCE', '')
        self.fields["email_category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )


# class InvestigatorSiteEmailMapInlineForm(forms.ModelForm):
#     class Meta:
#         model = InvestigatorSiteEmailMap
#         fields = "__all__"
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         required_reftype = getattr(settings, 'INVESTIGATOR_SITE_EMAIL_CATEGORY', '')
#         self.fields["email_category"] = forms.ChoiceField(
#             choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
#             required=False,
#         )

class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = '__all__'
        widgets = {
            'sponsor_description': LargeTextarea(),
            'sponsor_address_info': LargeTextarea(),
        }

    def clean(self):
        cleaned_data = super().clean()
        sponsor_name = cleaned_data.get('sponsor_name')
        sponsor_number = cleaned_data.get('sponsor_number')

        if not sponsor_name or not sponsor_number:
            return cleaned_data  # Skip if fields are empty

        # Check if it's an existing record
        if self.instance.pk:
            # Fetch the original values
            existing = Sponsor.objects.get(pk=self.instance.pk)
            name_changed = existing.sponsor_name != sponsor_name
            number_changed = existing.sponsor_number != sponsor_number
        else:
            # New record → always check duplicates
            name_changed = True
            number_changed = True

        # Only check duplicates if name or number changed
        if name_changed or number_changed:
            # Check for duplicate sponsor name
            if Sponsor.objects.exclude(pk=self.instance.pk).filter(sponsor_name=sponsor_name).exists():
                self.add_error('sponsor_name', f"Sponsor Name '{sponsor_name}' already exists.")
            # Check for duplicate sponsor number
            if Sponsor.objects.exclude(pk=self.instance.pk).filter(sponsor_number=sponsor_number).exists():
                self.add_error('sponsor_number', f"Sponsor Number '{sponsor_number}' already exists.")

        return cleaned_data


class BioSiteForm(forms.ModelForm):

    class Meta:
        model = BioSite
        fields = "__all__"
        widgets = {
            'address': LargeTextarea(),
            'sponsor_id': forms.Select(attrs={'onchange': 'onSponsorChange()'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sponsor_id'].label_from_instance = lambda obj: f"{obj.sponsor_name} - {obj.sponsor_number}"

    def clean(self):
        cleaned_data = super().clean()
        sponsor = cleaned_data.get("sponsor_id")
        bioproject = cleaned_data.get("bioproject_id")
        site_number = cleaned_data.get("site_number")
        investigator_name = cleaned_data.get("investigator_name")

        # Ensure bioproject_id always exists in cleaned_data
        if not bioproject:
            cleaned_data["bioproject_id"] = None

        # Check for duplicates only if all required fields are filled
        if sponsor and bioproject and site_number and investigator_name:
            qs = BioSite.objects.exclude(pk=self.instance.pk)  # exclude current record if editing

            duplicate_exists = qs.filter(
                sponsor_id=sponsor,
                bioproject_id=bioproject,
                site_number=site_number,
                investigator_name__iexact=investigator_name.strip()  # case-insensitive
            ).exists()

            if duplicate_exists:
                # Show ONLY this message in the red banner
                raise ValidationError(
                    f"Duplicate Investigator Site: A record already exists for "
                    f"Sponsor '{sponsor}', Project '{bioproject}', "
                    f"Site '{site_number}', and Investigator '{investigator_name}'."
                )

        return cleaned_data


class QCPendingBioProjectForm(forms.ModelForm):
    # Hidden field for project ID
    bioproject_id = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = QCPendingBioProject  # Proxy model
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only set initial if field exists
        if 'bioproject_id' in self.fields and self.instance and self.instance.pk:
            self.fields['bioproject_id'].initial = self.instance.pk


class DemographicFieldsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Reuse same reference type as ProjectEmailMap
        required_reftype = getattr(settings, 'APPLICATION_ACCESSIONING_DEMOGRAPHIC_FIELDS', '')
        self.fields["model_field_name"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
            label="Model Field Name"
        )


class EmailConfigForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Reuse same reference type as ProjectEmailMap
        required_reftype = getattr(settings, 'APPLICATION_PROJECT_EMAIL_REFERENCE', '')
        self.fields["email_category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
            label="Email Category"
        )

        # Adding placeholders for other fields
        self.fields['email_to'].widget.attrs.update({'placeholder': 'Enter recipient emails (semicolon separated)'})
        self.fields['email_cc'].widget.attrs.update({'placeholder': 'Enter CC emails (semicolon separated)'})
        self.fields['subject'].widget.attrs.update({'placeholder': 'Enter Email Subject'})

    class Meta:
        model = EmailConfig
        fields = "__all__"
        widgets = {
            'body': LargeTextarea(),  # Using custom textarea widget
        }

    # Field-level validation for email_to
    def clean_email_to(self):
        email_to = self.cleaned_data.get('email_to')
        if email_to:
            emails = [email.strip() for email in email_to.split(';') if email.strip()]
            for email in emails:
                try:
                    validate_email(email)
                except ValidationError:
                    raise ValidationError(f"'{email}' is not a valid email address.") 
        return email_to

    # Field-level validation for email_cc
    def clean_email_cc(self):
        email_cc = self.cleaned_data.get('email_cc')
        if email_cc:
            emails = [email.strip() for email in email_cc.split(';') if email.strip()]
            for email in emails:
                try:
                    validate_email(email)
                except ValidationError:
                    raise ValidationError(f"'{email}' is not a valid email address.")
        return email_cc

    # Cross-field validation
    def clean(self):
        cleaned_data = super().clean()
        email_to = cleaned_data.get('email_to')
        email_cc = cleaned_data.get('email_cc')

        if not email_to and not email_cc:
            raise ValidationError("Please provide at least one email address (To or CC).")

        return cleaned_data


class ProjectPhysicianMapForm(forms.ModelForm):
    class Meta:
        model = ProjectPhysicianMap
        fields = ['physician_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Show only physicians whose category is Pathologist
        self.fields['physician_id'].queryset = Physician.objects.filter(
            category__iexact='Pathologist'
        )

        # Dropdown display: "First Last"
        self.fields['physician_id'].label_from_instance = (
            lambda obj: f"{obj.first_name} {obj.last_name}"
        )
