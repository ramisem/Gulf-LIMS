import pytz
from django import forms
from django.utils import timezone

from security.models import SiteTimezone
from util.models import SequenceGen
from workflows.models import Workflow
from .models import Accession, BioPharmaAccession
from util.util import UtilClass
from controllerapp import settings
from process.models import SampleType, ContainerType
from sample.models import Sample, SampleTestMap
from masterdata.models import Client, BodySubSiteMap, BodySite, BioProject, Sponsor, BioSite, ProjectVisitMap, Subject, \
    AccessionPrefix
from tests.models import ICDCode
from django.db import models, transaction
from .widgets import LookupWidget, NextLinkWidget, FinishLinkWidget, PrevLinkNextLinkWidget, MagnifyingTextInput, \
    PartNoInputWidget
from django.forms import BaseInlineFormSet


# Form for the Accession Page
class AccessionForm(forms.ModelForm):
    filter_patient_without_subject = True  # default behavior for normal accessions

    insurance_group = forms.CharField(label='Group', max_length=40, required=False,
                                      widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    street_address = forms.CharField(label='Street Address', max_length=40, required=False,
                                     widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    apt = forms.CharField(label='Apt/Unit/Suite', max_length=40, required=False,
                          widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    city = forms.CharField(label='City', max_length=40, required=False,
                           widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    zipcode = forms.CharField(label='Zipcode', max_length=40, required=False,
                              widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    state = forms.CharField(label='State', max_length=40, required=False,
                            widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    phone_number = forms.CharField(label='Phone Number', max_length=40, required=False,
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    fax_number = forms.CharField(label='Fax Number', max_length=40, required=False,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    email = forms.CharField(label='Email Address', max_length=40, required=False,
                            widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    accession_id = forms.CharField(label='Accession ID', max_length=40, required=False, widget=forms.HiddenInput())
    case_id = forms.CharField(label='Accession ID', max_length=40, required=False)

    status = forms.CharField(label='Accession Status', max_length=40, required=False,
                             widget=forms.HiddenInput())
    client_address_line1 = forms.CharField(label='Address Line 1', max_length=40, required=False,
                                           widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_address_line2 = forms.CharField(label='Address Line 2', max_length=40, required=False,
                                           widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_city = forms.CharField(label='City', max_length=40, required=False,
                                  widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_state = forms.CharField(label='State', max_length=40, required=False,
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_postalcode = forms.CharField(label='Postal Code', max_length=40, required=False,
                                        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_country = forms.CharField(label='Country', max_length=40, required=False,
                                     widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_phone_number = forms.CharField(label='Phone Number', max_length=40, required=False,
                                          widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_fax_number = forms.CharField(label='Fax Number', max_length=40, required=False,
                                        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    client_email = forms.CharField(label='Email', max_length=40, required=False,
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    sample_type = forms.ChoiceField(choices=[(None, "Select an Option")], label="Sample Type", required=False,
                                    widget=forms.Select(
                                        attrs={'class': 'form-control', 'onchange': 'updateContainerDropdown(this)'}))
    container_type = forms.ChoiceField(choices=[(None, "Select an Option")], label="Container Type", required=False,
                                       widget=forms.Select(
                                           attrs={'class': 'form-control',
                                                  'onchange': 'populateContainerDetails(this)'})
                                       )
    count = forms.CharField(
        label='Count',
        required=False,
        initial='',
        widget=forms.TextInput(),
        max_length=5
    )
    associate_test = forms.CharField(
        label='Associate Test',
        max_length=40,
        required=False,
        widget=LookupWidget(attrs={
            'id': 'id_associate_test',
            'size': '20',
            'style': 'width: 200px;',
            'onmouseover': "showMagnifier(this);",
            'onmouseout': "hideMagnifier();"
        })
    )

    workflow = forms.ModelChoiceField(
        queryset=Workflow.objects.all(),
        label="Workflow",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Workflow"
    )

    test_id = forms.CharField(widget=forms.HiddenInput(), required=False, )
    previous_accession = forms.CharField(widget=forms.HiddenInput(), required=False)
    isupdate_accession_prefix = forms.CharField(widget=forms.HiddenInput(), required=False)
    hidden_auto_gen_pk = forms.CharField(widget=forms.HiddenInput(), required=False)
    hidden_accession_prefix = forms.CharField(widget=forms.HiddenInput(), required=False)
    hidden_accession_template = forms.CharField(widget=forms.HiddenInput(), required=False)
    move_next_to_client_info_tab = forms.CharField(widget=NextLinkWidget(next_tab='client-tab'), required=False,
                                                   label=" ")
    move_prev_next_from_client_info_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(prev_tab='accession-info-tab', next_tab='reporting-doctor-tab'), required=False,
        label=" ")
    move_prev_next_from_reporting_doc_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(prev_tab='client-tab', next_tab='payment-tab'), required=False, label=" ")
    move_prev_next_from_payment_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(prev_tab='reporting-doctor-tab', next_tab='sample-creation-tab'), required=False,
        label=" ")
    move_finish_from_sample_creation_tab = forms.CharField(
        widget=FinishLinkWidget(prev_tab='payment-tab', next_tab='samples-tab'), required=False, label=" ")
    part_no = forms.CharField(
        label='Part No',
        max_length=10,
        required=False,
        widget=PartNoInputWidget()
    )
    is_child_sample_creation = forms.CharField(widget=forms.HiddenInput(), required=False)
    is_gen_slide_seq = forms.CharField(widget=forms.HiddenInput(), required=False)
    is_create_samples = forms.CharField(widget=forms.HiddenInput(), required=False)
    parent_seq = forms.ChoiceField(
        choices=[(None, 'Select')],
        required=False, label='Block/Cassette No.'
    )
    is_generate_parent_seq = forms.CharField(widget=forms.HiddenInput(), required=False)
    receive_dt_timezone = forms.CharField(  # display Char instead of hidden as it cannot print anything
        label='Receive Date Timezone',
        widget=forms.TextInput(
            attrs={'readonly': 'readonly', 'style': 'border: none; background-color: transparent; text-align: left;'}),
        required=False  # Make it not required to avoid validation issues
    )
    collection_dt_timezone = forms.ChoiceField(
        choices=[(None, 'Select')],
        required=False
    )
    reporting_type = forms.CharField(label='Reporting Type', max_length=40, required=False,
                                     widget=forms.HiddenInput())

    # This is for providing validation on submission of the accession form
    def clean(self):
        cleaned_data = super().clean()
        is_auto_gen_pk = cleaned_data.get('is_auto_gen_pk')
        accession_prefix = cleaned_data.get('accession_prefix')
        case_id = cleaned_data.get('case_id')
        accession_id = cleaned_data.get('accession_id')
        accession_template = cleaned_data.get('accession_template')

        if not accession_prefix and not accession_id:
            if not accession_template:
                self.add_error('accession_prefix', "Accession Prefix is required.")

        if is_auto_gen_pk != True:
            if not case_id:
                self.add_error('case_id', "Accession ID is required.")

        return cleaned_data

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Only apply this for forms that want the filter
        if getattr(self, 'filter_patient_without_subject', False) and 'patient_id' in self.fields:
            subject_patient_ids = Subject.objects.values_list('patient_id', flat=True).distinct()
            self.fields['patient_id'].queryset = (
                self.fields['patient_id'].queryset.exclude(
                    patient_id__in=subject_patient_ids
                )
            )

        self.request = request
        session_timezone = request.session.get('currenttimezone',
                                               getattr(settings, 'SERVER_TIME_ZONE',
                                                       'UTC'))

        if request and not self.instance.pk:  # Only set during creation, not editing

            if 'receive_dt' in self.fields and not self.initial.get('receive_dt'):
                try:
                    tz = pytz.timezone(session_timezone)
                    self.initial['receive_dt'] = timezone.now().astimezone(tz)
                except Exception:
                    self.initial['receive_dt'] = timezone.now()

            if 'receive_dt_timezone' not in self.fields:
                self.fields['receive_dt_timezone'] = forms.CharField(
                    required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'})
                )
            self.fields['receive_dt_timezone'].initial = session_timezone

        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        self.fields["active_flag"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False,
        )
        required_reftype = getattr(settings, 'APPLICATION_ACCESSION_CATEGORY_REFERENCE', '')
        self.fields["accession_category"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=True, label="Accession Category",
            widget=forms.Select(attrs={'onchange': 'onChangeAccessionCategory()'}),
        )

        self.fields["accession_template"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + [(obj.accession_id, obj.accession_id) for obj in
                                                    Accession.objects.filter(is_template=True).exclude(
                                                        accession_category='Pharma')],
            required=False, label="Accession Template"
        )

        self.fields["accession_prefix"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + [(obj.accession_prefix, obj.accession_prefix) for
                                                    obj in AccessionPrefix.objects.all()],
            required=False, label="Accession Prefix"
        )
        self.fields["collection_dt_timezone"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + [(obj.name, obj.name) for
                                                    obj in SiteTimezone.objects.all()],
            required=False,
        )
        self.fields['collection_dt_timezone'].initial = session_timezone
        required_reftype = getattr(settings, 'APPLICATION_PAYMENT_TYPE_REFERENCE', '')
        self.fields["payment_type"] = forms.ChoiceField(
            choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
            required=False, label="Payment Type", widget=forms.Select(attrs={'onchange': 'populatePaymentDetails()'}),
        )

        # Default to 'Insurance'
        if 'payment_type' in self.fields:
            self.fields['payment_type'].initial = 'Insurance'

        self.fields['sample_type'].choices = [(None, "Select an Option")] + [(obj.sample_type_id, obj.sample_type) for
                                                                             obj in SampleType.objects.all()]
        if 'client_id' in self.fields:
            self.fields['client_id'].choices = [(None, "Select an Option")] + [(obj.client_id, obj.name) for
                                                                               obj in Client.objects.all()]
        if self.instance.accession_id is not None:
            self.fields['case_id'].initial = self.instance.accession_id
            self.fields["accession_id"].initial = self.instance.accession_id

        if 'accession_template' in self.data:
            accession_template = self.data.get('accession_template')
            if accession_template:
                if not self.instance.accession_id:
                    list_required_fields = ["patient_id", "receive_dt", "collection_dt", "collection_dt_timezone",
                                            "payment_type"]
                    accession_template_instance = Accession.objects.get(accession_id=accession_template)
                    for field_name, field in self.fields.items():
                        if field_name not in list_required_fields:
                            if field.required == True:
                                value = getattr(accession_template_instance, field_name, None)
                                if value:
                                    field.required = False

        if 'reporting_doctor' in self.fields:
            self.fields['reporting_doctor'].required = True

        if 'doctor' in self.fields:
            self.fields['doctor'].required = True

    class Meta:
        model = Accession
        fields = ['patient_id', 'insurance_id', 'client_id', 'doctor', 'accession_id', 'case_id',
                  'accession_type', 'accession_template', 'accession_prefix', 'accession_lab',
                  'status', 'insurance_group', 'payment_type', 'move_next_to_client_info_tab', 'hidden_auto_gen_pk',
                  'hidden_accession_prefix', 'hidden_accession_template', 'receive_dt_timezone', 'accession_type']
        widgets = {
            'patient_id': forms.Select(attrs={'class': 'form-control', 'onchange': 'populateInsuranceDetails()'}),
            'insurance_id': forms.Select(attrs={'class': 'form-control', 'onchange': 'populateInsuranceGroup()'}),
            'client_id': forms.Select(attrs={'class': 'form-control', 'onchange': 'populateDoctorsBasedOnClient()'}),
            'is_auto_gen_pk': forms.CheckboxInput(attrs={'onclick': 'checkuncheckautogenprimarykey(this)'}),
            'accession_type': forms.Select(attrs={'class': 'form-control', 'onchange': 'populateAccessionTypeInfo()'}),
        }


class SubjectChoiceField(forms.ModelChoiceField):
    """
    A custom ModelChoiceField that displays the subject_id in the dropdown
    instead of the default string representation of the Subject object.
    """

    def label_from_instance(self, obj):
        return obj.subject_id


class BioPharmaAccessionForm(AccessionForm):
    # Disable parent patient filtering for this form
    filter_patient_without_subject = False

    patient_id = SubjectChoiceField(
        queryset=Subject.objects.all().order_by('subject_id'),
        label='Subject',
    )

    sponsor_name = forms.CharField(label='Sponsor Name', required=False,
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    sponsor_number = forms.CharField(label='Sponsor Number', required=False,
                                     widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    sponsor_description = forms.CharField(label='Sponsor Description', required=False,
                                          widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': 4}))
    sponsor_address_info = forms.CharField(label='Sponsor Address Info', required=False,
                                           widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': 4}))

    move_next_to_client_info_tab = forms.CharField(widget=NextLinkWidget(next_tab='sponsor-tab'), required=False,
                                                   label=" ")
    move_prev_next_from_client_info_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(prev_tab='accession-info-tab', next_tab='reporting-doctor-tab'), required=False,
        label=" ")
    move_prev_next_from_sponsor_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(
            prev_tab='accession-info-tab',
            next_tab='reporting-doctor-tab'
        ),
        required=False,
        label=" "
    )
    move_prev_next_from_reporting_doc_tab = forms.CharField(
        widget=PrevLinkNextLinkWidget(prev_tab='sponsor-tab', next_tab='sample-creation-tab'), required=False,
        label=" ")
    move_finish_from_sample_creation_tab = forms.CharField(
        widget=FinishLinkWidget(prev_tab='reporting-doctor-tab', next_tab='samples-tab'), required=False, label=" ")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'accession_template' in self.fields:
            template_choices = [
                (obj.accession_id, obj.accession_id)
                for obj in BioPharmaAccession.objects.filter(is_template=True, accession_category='Pharma')
            ]
            self.fields['accession_template'].choices = [
                                                            (None, "Select an Option")
                                                        ] + template_choices

        self.fields['accession_category'] = forms.CharField(
            label='Accession Category',
            initial='Pharma',
            required=False,
            widget=forms.HiddenInput()
        )

        self.fields['sponsor'].choices = [(None, "Select an Option")] + [(obj.pk, obj) for obj in Sponsor.objects.all()]

        self.fields['project'].queryset = BioProject.objects.none()
        self.fields['visit'].queryset = ProjectVisitMap.objects.none()
        self.fields['investigator'].queryset = BioSite.objects.none()

        instance = kwargs.get('instance', None)

        if instance and instance.pk:
            if instance.sponsor:
                self.fields['project'].queryset = BioProject.objects.filter(sponsor_id=instance.sponsor)
            if instance.project:
                self.fields['visit'].queryset = ProjectVisitMap.objects.filter(bioproject_id=instance.project)
                self.fields['investigator'].queryset = BioSite.objects.filter(bioproject_id=instance.project)

        if self.data:
            try:
                sponsor_id = int(self.data.get('sponsor'))
                project_id = self.data.get('project')  # This is a string like 'BPR-00001'

                if sponsor_id:
                    self.fields['project'].queryset = BioProject.objects.filter(sponsor_id=sponsor_id, qc_status='Pass',
                                                                                is_active=True)
                if project_id:
                    self.fields['visit'].queryset = ProjectVisitMap.objects.filter(bioproject_id=project_id)
                    self.fields['investigator'].queryset = BioSite.objects.filter(bioproject_id=project_id)
            except (ValueError, TypeError):
                pass

    class Meta(AccessionForm.Meta):
        model = BioPharmaAccession
        fields = AccessionForm.Meta.fields + ['project', 'sponsor', 'investigator', 'visit']

        widgets = {
            'sponsor': forms.Select(attrs={
                'onchange': 'sponsorChanged(this)',
                'class': 'admin-autocomplete form-control select2',
                'style': 'width: 100%',
            }),
            'project': forms.Select(attrs={
                'onchange': 'projectChanged(this)',
                'class': 'admin-autocomplete form-control select2',
                'style': 'width: 100%',
            }),
            'visit': forms.Select(attrs={
                'class': 'admin-autocomplete form-control select2',
                'style': 'width: 100%',
            }),
            'investigator': forms.Select(attrs={
                'class': 'admin-autocomplete form-control select2',
                'style': 'width: 100%',
            }),
        }


# Form for the Sample Inline
class SampleInlineForm(forms.ModelForm):
    sample_id = forms.CharField(label='Sample ID', max_length=40, required=False,
                                widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    part_no = forms.CharField(label='Part', max_length=10, required=False,
                              widget=forms.TextInput(attrs={
                                  'oninput': 'convertToUppercase(this)'
                              })
                              )
    sample_type_info = forms.CharField(label='Sample Type', max_length=40, required=False,
                                       widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    container_type_info = forms.CharField(label='Container Type', max_length=40, required=False,
                                          widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    test_code = forms.CharField(
        label='Test',
        max_length=40,
        required=False,
        widget=MagnifyingTextInput(attrs={'readonly': 'readonly', 'class': 'my-custom-class'})
    )

    test_id = forms.CharField(
        label='Test ID',
        max_length=40,
        required=False,
        widget=forms.HiddenInput()
    )

    block_or_cassette_seq = forms.CharField(label='Block/Cassette #', max_length=10, required=False,
                                            widget=forms.TextInput())
    slide_seq = forms.CharField(label='Slide #', max_length=10, required=False, widget=forms.TextInput())

    child_sample_creation = forms.CharField(label='Child Sample Creation', max_length=10, required=False,
                                            widget=forms.HiddenInput())
    gen_slide_seq = forms.CharField(label='Generate Slide Sequence', max_length=10, required=False,
                                    widget=forms.HiddenInput())
    gen_block_or_cassette_seq = forms.CharField(label='Generate Block/Cassette #', max_length=10, required=False,
                                                widget=forms.HiddenInput())
    sample_status = forms.CharField(label='Sample Status', max_length=20, required=False,
                                    widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    accession_category = forms.CharField(label='Accession Category', max_length=40, required=False,
                                         widget=forms.HiddenInput())

    workflow_id = forms.ModelChoiceField(
        queryset=Workflow.objects.all(),
        label="Workflow",
        required=False,
        widget=forms.Select(),
        empty_label="Select a Workflow"
    )

    # This is for providing validation on th part no
    def clean_part_no(self):
        part_no = self.cleaned_data.get('part_no')
        accession_id = self.instance.accession_id
        accession_category = Accession.objects.get(
            accession_id=accession_id).accession_category
        if not part_no and accession_category != 'Clinical':
            raise forms.ValidationError("Part No is required.")
        return part_no

    # This is for providing validation on Block/Cassette Sequence
    def clean_block_or_cassette_seq(self):
        block_or_cassette_seq = self.cleaned_data.get('block_or_cassette_seq')
        container_type = self.instance.container_type
        accession_id = self.instance.accession_id
        accession_category = Accession.objects.get(
            accession_id=accession_id).accession_category
        if container_type is not None and accession_category != 'Clinical':
            try:
                container_Type = ContainerType.objects.get(
                    container_type=container_type)
                gen_block_or_cassette_seq = container_Type.gen_block_or_cassette_seq
                gen_slide_seq = container_Type.gen_slide_seq
            except ContainerType.DoesNotExist:
                raise forms.ValidationError("Invalid container type. Please select a valid one.")
            if gen_block_or_cassette_seq or gen_slide_seq:
                if not block_or_cassette_seq:
                    raise forms.ValidationError("Block/Cassette # is required.")
                accession_id = self.instance.accession_id
                part_no = self.cleaned_data.get('part_no')
                prefix_id = str(accession_id) + '-' + str(part_no)
                max_block_cassette_seq = SequenceGen.objects.filter(
                    prefix_id=prefix_id
                ).aggregate(max_seq=models.Max('seq_no'))['max_seq'] or 0
                if max_block_cassette_seq is not None and int(block_or_cassette_seq) > int(max_block_cassette_seq):
                    with transaction.atomic():
                        sequence_gen, created = SequenceGen.objects.update_or_create(
                            model_id='Sample',
                            prefix_id=prefix_id,
                            defaults={'seq_no': int(block_or_cassette_seq)}
                        )
            elif not gen_block_or_cassette_seq and not gen_slide_seq:
                if block_or_cassette_seq is not None and block_or_cassette_seq != '':
                    raise forms.ValidationError('Block/Cassette # is not required.')
        return block_or_cassette_seq

    # This for providing validation on the slide seq
    def clean_slide_seq(self):
        slide_seq = self.cleaned_data.get('slide_seq')
        container_type = self.instance.container_type
        accession_id = self.instance.accession_id
        accession_category = Accession.objects.get(
            accession_id=accession_id).accession_category
        if container_type is not None and accession_category != 'Clinical':
            try:
                container_Type = ContainerType.objects.get(container_type=container_type)
                child_sample_creation = container_Type.child_sample_creation
                gen_slide_seq = container_Type.gen_slide_seq
            except ContainerType.DoesNotExist:
                raise forms.ValidationError("Invalid container type. Please select a valid one.")

            if gen_slide_seq:
                if slide_seq is None or slide_seq == '':
                    raise forms.ValidationError("Slide # is required")
                else:
                    accession_id = self.instance.accession_id
                    part_no = self.cleaned_data.get('part_no')
                    block_or_cassette_seq = self.cleaned_data.get('block_or_cassette_seq')
                    prefix_id = str(accession_id) + '-' + str(part_no) + '-' + str(block_or_cassette_seq)
                    max_slide_seq = SequenceGen.objects.filter(
                        prefix_id=prefix_id
                    ).aggregate(max_seq=models.Max('seq_no'))['max_seq'] or 0
                    if max_slide_seq is not None and int(slide_seq) > int(max_slide_seq):
                        with transaction.atomic():
                            sequence_gen, created = SequenceGen.objects.update_or_create(
                                model_id='Sample',
                                prefix_id=prefix_id,
                                defaults={'seq_no': int(slide_seq)}
                            )
            else:
                if slide_seq is not None and slide_seq != '':
                    raise forms.ValidationError("Slide # is not required")

        return slide_seq

    def save(self, commit=True):
        instance = super().save(commit)
        test_id = self.cleaned_data.get("test_id")
        set_test_id = None
        if test_id:
            list_test_id = [x.strip() for x in test_id.split(",") if x.strip()]
            set_test_id = set(map(int, list_test_id))

        sample_id = self.cleaned_data.get("sample_id")
        if sample_id:
            # Get current test_ids from DB
            existing_ids = set(
                SampleTestMap.objects.filter(sample_id=sample_id)
                .values_list("test_id_id", flat=True)
            )
            # Create new mappings for test_ids not already in DB
            if set_test_id:
                new_ids = set_test_id - existing_ids
                SampleTestMap.objects.bulk_create(
                    [SampleTestMap(sample_id_id=sample_id, test_id_id=tid) for tid in new_ids]
                )

        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.sample_id is not None:
            sample_type_instance = self.instance.sample_type
            if sample_type_instance is not None:
                self.fields['sample_type_info'].initial = self.instance.sample_type.sample_type
            container_type_instance = self.instance.container_type
            if container_type_instance is not None:
                self.fields['container_type_info'].initial = self.instance.container_type.container_type
                self.fields['child_sample_creation'].initial = self.instance.container_type.child_sample_creation
                self.fields['gen_slide_seq'].initial = self.instance.container_type.gen_slide_seq
                self.fields[
                    'gen_block_or_cassette_seq'].initial = self.instance.container_type.gen_block_or_cassette_seq
            sample_test_maps = SampleTestMap.objects.filter(sample_id=self.instance.sample_id)
            test_names = [sample_test_map.test_id.test_name for sample_test_map in sample_test_maps]
            test_names_joined = ", ".join(test_names)
            self.fields['test_code'].initial = test_names_joined
            test_ids = [str(sample_test_map.test_id_id) for sample_test_map in sample_test_maps]
            test_ids_joined = ", ".join(test_ids)
            self.fields['test_id'].initial = test_ids_joined
            body_site_choices = list(BodySite.objects.values_list('body_site', 'body_site'))
            self.fields["body_site"] = forms.ChoiceField(
                choices=[(None, "Select an Option")] + body_site_choices,
                required=False,
                widget=forms.Select(attrs={'onchange': 'populateSubSite(this); populateRelatedTest(this);'})
            )
            self.fields["sub_site"] = forms.ChoiceField(
                choices=[(None, "Select Sub Site")],
                required=False,
            )
            body_site_value = None
            if self.data:
                body_site_value = self.data.get(self.add_prefix('body_site'))
            elif self.initial:
                body_site_value = self.initial.get('body_site')
            elif hasattr(self.instance, 'body_site'):
                body_site_value = self.instance.body_site

            if body_site_value:
                sub_sites_qs = BodySubSiteMap.objects.filter(body_site__body_site=body_site_value).values_list(
                    'sub_site',
                    flat=True).distinct()
                sub_site_choices = [(val, val) for val in sub_sites_qs]
                self.fields['sub_site'].choices = [(None, "Select Sub Site")] + sub_site_choices
            required_reftype = getattr(settings, 'APPLICATION_COLLECTION_METHOD', '')
            self.fields["collection_method"] = forms.ChoiceField(
                choices=[(None, "Select an Option")] + UtilClass.get_refvalues_for_field(required_reftype),
                required=False,
            )

        if self.instance and self.instance.pk and self.instance.accession_generated:
            self.fields['workflow_id'].disabled = True


class Meta:
    model = Sample
    fields = ['sample_id', 'sample_type_info', 'container_type_info', 'test_code']


# For the ICD Code Inline
class AccessionICDCodeMapForm(forms.ModelForm):
    description = forms.CharField(label='Description', max_length=200, required=False,
                                  widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        icd_code_id = kwargs.pop('icd_code_id', None)
        self.fields['icd_code_id'].choices = [('', 'Select An Option')] + [
            (icdcode.icd_code_id,
             icdcode.icd_code) for icdcode in
            ICDCode.objects.filter()]

        if not icd_code_id:
            icd_code_id = self.initial.get('icd_code_id')

        if icd_code_id:
            try:
                icdcode_obj = ICDCode.objects.get(icd_code_id=icd_code_id)
                self.fields['description'].initial = icdcode_obj.description

            except ICDCode.DoesNotExist:
                pass

    class Meta:
        model = ICDCode
        fields = ['icd_code_id', 'description']

        widgets = {
            'icd_code_id': forms.Select(attrs={'class': 'form-control', 'onchange': 'updateICDDetails(this)'}),
        }


class SampleInlineFormSet(BaseInlineFormSet):
    # This is for validating the fields in the sample inline
    def clean(self):
        accession_id = self.instance.accession_id
        if accession_id is None or accession_id == '':
            return
        accession_category = Accession.objects.get(
            accession_id=accession_id).accession_category
        if accession_category != 'Clinical':
            sample_dict = {}
            sampleid_duplicate_seq = ""
            list_samples = []
            list_part_block_cassette_seq_comb = []
            sample_dict_slide = {}
            sampleid_duplicate_slide_seq = ""
            list_part_block_cassette_slide_seq_comb = []
            is_sample_status_initial = True;
            for form in self.forms:
                if form.cleaned_data and form.cleaned_data.get('DELETE', False):
                    sample_status = form.instance.sample_status
                    if 'Initial' != sample_status:
                        form.add_error('sample_status', f"This Sample could be deleted as status is not Initial")
                        is_sample_status_initial = False
                elif form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    sample_id = form.cleaned_data.get('sample_id')
                    list_samples.append(sample_id)
                    part_no = form.cleaned_data.get('part_no')
                    block_or_cassette_seq = form.cleaned_data.get('block_or_cassette_seq')
                    slide_seq = form.cleaned_data.get('slide_seq')
                    child_sample_creation = form.cleaned_data.get('child_sample_creation')
                    gen_block_or_cassette_seq = form.cleaned_data.get('gen_block_or_cassette_seq')
                    gen_slide_seq = form.cleaned_data.get('gen_slide_seq')
                    if part_no is not None and block_or_cassette_seq is not None and "True" == gen_block_or_cassette_seq and "True" == child_sample_creation:
                        part_block_cassette_seq_comb = part_no + "#" + block_or_cassette_seq
                        list_part_block_cassette_seq_comb.append(part_block_cassette_seq_comb)
                        key = f"{part_no}-{block_or_cassette_seq}"
                        if len(sample_dict) == 0:
                            sample_dict[key] = sample_id
                        else:
                            if key not in sample_dict:
                                sample_dict[key] = sample_id
                            else:
                                sampleid_duplicate_seq = sampleid_duplicate_seq + "," + sample_id
                                form.add_error('block_or_cassette_seq',
                                               f"For the Part'{part_no}', "
                                               f"Block/Cassette # '{block_or_cassette_seq}' is duplicated. Please Correct.")
                    elif part_no is not None and block_or_cassette_seq is not None and slide_seq is not None and "True" == gen_slide_seq and "True" != child_sample_creation:
                        part_block_cassette_slide_seq_comb = part_no + "#" + block_or_cassette_seq + "#" + slide_seq
                        list_part_block_cassette_slide_seq_comb.append(part_block_cassette_slide_seq_comb)
                        key = f"{part_no}-{block_or_cassette_seq}-{slide_seq}"
                        if len(sample_dict_slide) == 0:
                            sample_dict_slide[key] = sample_id
                        else:
                            if key not in sample_dict_slide:
                                sample_dict_slide[key] = sample_id
                            else:
                                sampleid_duplicate_slide_seq = sampleid_duplicate_slide_seq + "," + sample_id
                                form.add_error('slide_seq',
                                               f"For the Part and Block/Cassette # '{part_no}{block_or_cassette_seq}', "
                                               f"Slide # '{slide_seq}' is duplicated. Please Correct.")
            if not is_sample_status_initial:
                raise forms.ValidationError(
                    "One or more sample(s) could not be deleted as their status is not Initial.")

            if list_samples is not None and len(
                    list_samples) > 0 and list_part_block_cassette_seq_comb is not None and len(
                list_part_block_cassette_seq_comb) > 0:
                accession_id = self.instance.accession_id
                existing_samples = Sample.objects.filter(
                    accession_id=accession_id
                ).exclude(sample_id__in=list_samples)

                if existing_samples.exists():
                    for samples in existing_samples:
                        if samples.container_type.child_sample_creation == True and samples.container_type.gen_block_or_cassette_seq == True:
                            part_block_cassette_seq = samples.part_no + "#" + samples.block_or_cassette_seq
                            if part_block_cassette_seq in list_part_block_cassette_seq_comb:
                                raise forms.ValidationError(f"One or more sample(s) have duplicate Cassette #")

            if list_samples is not None and len(
                    list_samples) > 0 and list_part_block_cassette_slide_seq_comb is not None and len(
                list_part_block_cassette_seq_comb) > 0:
                accession_id = self.instance.accession_id
                existing_samples = Sample.objects.filter(
                    accession_id=accession_id
                ).exclude(sample_id__in=list_samples)

                if existing_samples.exists():
                    for samples in existing_samples:
                        if not samples.container_type.child_sample_creation and samples.container_type.gen_slide_seq == True:
                            part_block_cassette_slide_seq = samples.part_no + "#" + samples.block_or_cassette_seq + "#" + samples.slide_seq
                            if part_block_cassette_slide_seq in list_part_block_cassette_slide_seq_comb:
                                raise forms.ValidationError(f"One or more sample(s) have duplicate Slide #")
