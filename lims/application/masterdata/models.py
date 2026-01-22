from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
import importlib
import security
from security.models import User


# Create your models here.
# Client Model
class Client(models.Model):
    client_id = models.AutoField(primary_key=True, verbose_name="Client ID")
    name = models.CharField(max_length=200, verbose_name="Name", unique=True)
    active_flag = models.CharField(max_length=10, blank=False, null=True, default="Y", verbose_name="Active Flag")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")
    address1 = models.CharField(max_length=200, verbose_name="Address Line 1")
    address2 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Address Line 2")
    city = models.CharField(max_length=20, verbose_name="City")
    state = models.CharField(max_length=20, verbose_name="State")
    postalcode = models.CharField(max_length=100, verbose_name="Postal Code")
    country = models.CharField(max_length=100, verbose_name="Country")
    telephone = models.CharField(max_length=20,
                                 validators=[
                                     RegexValidator(
                                         regex=r'^\+?1?\s?-?\(?\d{3}\)?\s?-?\d{3}\s?-?\d{4}$',
                                         message="Enter a valid US phone number (e.g., +1 123-456-7890, (123) 456-7890, or 1234567890)."
                                     )
                                 ],
                                 blank=True, null=True, verbose_name="Phone Number")
    fax_number = models.CharField(max_length=20,
                                  validators=[
                                      RegexValidator(
                                          regex=r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$',
                                          message="Enter a valid fax number in the format (123) 456-7890 or 123-456-7890."
                                      )
                                  ],
                                  blank=True, null=True, verbose_name="Fax Number")

    primaryemail = models.EmailField(max_length=100, verbose_name="Email")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("client")
        verbose_name_plural = _("clients")

    def __str__(self):
        return str(self.name)


# Patient Model
class Patient(models.Model):
    patient_id = models.AutoField(primary_key=True, verbose_name="Patient ID")
    first_name = models.CharField(max_length=200, verbose_name="First Name")
    last_name = models.CharField(max_length=200, verbose_name="Last Name")
    middle_initial = models.CharField(max_length=3, blank=True, null=True, verbose_name="Middel Initial")
    active_flag = models.CharField(max_length=10, blank=False, null=True, verbose_name="Active Flag", default="Y")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")
    birth_dt = models.DateField(verbose_name="Birth Date")
    gender = models.CharField(max_length=10, blank=False, null=True, verbose_name="Gender")
    mrn = models.CharField(max_length=80, blank=True, null=True, verbose_name="MRN")
    ssn = models.CharField(max_length=80, blank=True, null=True, verbose_name="SSN")
    street_address = models.CharField(max_length=100, blank=True, null=True, verbose_name="Street Address")
    apt = models.CharField(max_length=80, blank=True, null=True, verbose_name="Apt/Unit/Suite")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="City")
    zipcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Zipcode")
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name="State")
    phone_number = models.CharField(max_length=20,
                                    validators=[
                                        RegexValidator(
                                            regex=r'^\+?1?\s?-?\(?\d{3}\)?\s?-?\d{3}\s?-?\d{4}$',
                                            message="Enter a valid US phone number (e.g., +1 123-456-7890, (123) 456-7890, or 1234567890)."
                                        )
                                    ],
                                    blank=True, null=True, verbose_name="Phone Number")

    fax_number = models.CharField(max_length=20,
                                  validators=[
                                      RegexValidator(
                                          regex=r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$',
                                          message="Enter a valid fax number in the format (123) 456-7890 or 123-456-7890."
                                      )
                                  ],
                                  blank=True, null=True, verbose_name="Fax Number")
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Email Address")
    marital_status = models.CharField(max_length=20, blank=True, null=True, verbose_name="Marital Status")
    smoking_status = models.CharField(max_length=20, blank=True, null=True, verbose_name="Smoking Status")
    race = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ethenicity/Race")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("patient")
        verbose_name_plural = _("patients")

    def __str__(self):
        return str(self.first_name + " " + self.last_name)


class Subject(Patient):
    """
    Extends the Patient model using multi-table inheritance.
    This creates a new table for Subject-specific fields.
    """
    subject_id = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        verbose_name="Subject ID"
    )

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.subject_id})"

    def save(self, *args, **kwargs):
        if not self.pk:
            model_name = self.__class__.__name__
            prefix = "SUB"
            module = importlib.import_module("util.util")
            UtilClass = getattr(module, "UtilClass")
            seq_no = UtilClass.get_next_sequence(prefix, model_name, self.created_by.id)
            self.subject_id = f"{prefix}-{seq_no:05}"

        super().save(*args, **kwargs)


# Physician model
class Physician(models.Model):
    physician_id = models.AutoField(primary_key=True, verbose_name="Physician ID")
    first_name = models.CharField(max_length=200, verbose_name="First Name")
    last_name = models.CharField(max_length=200, verbose_name="Last Name")
    external = models.BooleanField(default=False, verbose_name="Is External")
    active_flag = models.CharField(max_length=10, blank=False, null=True, verbose_name="Active Flag", default="Y")
    category = models.CharField(max_length=20, blank=False, null=True, verbose_name="Category")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")
    phone_number = models.CharField(max_length=20,
                                    validators=[
                                        RegexValidator(
                                            regex=r'^\+?1?\s?-?\(?\d{3}\)?\s?-?\d{3}\s?-?\d{4}$',
                                            message="Enter a valid US phone number (e.g., +1 123-456-7890, (123) 456-7890, or 1234567890)."
                                        )
                                    ],
                                    blank=True, null=True, verbose_name="Phone Number")

    fax_number = models.CharField(max_length=20,
                                  validators=[
                                      RegexValidator(
                                          regex=r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$',
                                          message="Enter a valid fax number in the format (123) 456-7890 or 123-456-7890."
                                      )
                                  ],
                                  blank=True, null=True, verbose_name="Fax Number")
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Email Address")
    physician_type = models.CharField(max_length=40, blank=True, null=True, default="doctor",
                                      verbose_name="Physician Type")
    user_id = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=False, verbose_name="User ID",
                                related_name="user_id")
    title = models.CharField(max_length=40, blank=True, null=True, verbose_name="Title")
    env_type = models.CharField(max_length=40, blank=True, null=True, default="clinical", verbose_name="Env Type")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("physician")
        verbose_name_plural = _("physicians")

    def __str__(self):
        return str(self.first_name + " " + self.last_name)


# PatientInsuranceInfo model
class PatientInsuranceInfo(models.Model):
    patientinfo_id = models.AutoField(primary_key=True, verbose_name="Patient Info ID")
    insurance = models.CharField(max_length=80, verbose_name="Insurance")
    group = models.CharField(max_length=80, verbose_name="Group")
    policy = models.CharField(max_length=80, unique="True", verbose_name="Policy")
    patient_id = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, verbose_name="Patient ID")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Insurance")
        verbose_name_plural = _("Insurance")
        constraints = [
            models.UniqueConstraint(fields=['patient_id', 'policy'], name='unique_patient_id_policy')
        ]

    def __str__(self):
        return str(self.policy)

    def natural_key(self):
        return self.policy


# ClientDoctorInfo
class ClientDoctorInfo(models.Model):
    client_docinfo_id = models.AutoField(primary_key=True, verbose_name="Client Doctor Info ID")
    client_id = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, verbose_name="Client ID")
    physician_id = models.ForeignKey(Physician, on_delete=models.PROTECT, null=True, verbose_name="Physician ID")
    active_flag = models.CharField(max_length=10, blank=False, null=True, verbose_name="Active Flag", default="Y")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("doctor")
        verbose_name_plural = _("doctor")
        constraints = [
            models.UniqueConstraint(fields=['client_id', 'physician_id'], name='unique_client_id_physician_id')
        ]

    def __str__(self):
        return str(self.client_docinfo_id)


class AccessionType(models.Model):
    accession_type_id = models.AutoField(primary_key=True, verbose_name="Accession Type Id")
    accession_type = models.CharField(max_length=20, unique=True, null=False, verbose_name="Accession Type")
    REPORTING_CHOICES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]
    reporting_type = models.CharField(max_length=20, choices=REPORTING_CHOICES, null=True, blank=True)
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        app_label = 'masterdata'
        verbose_name = _("Accession Type")
        verbose_name_plural = _("Accession Types")

    def __str__(self):
        return self.accession_type

    def natural_key(self):
        return self.accession_type


class BodySite(models.Model):
    body_site_id = models.AutoField(primary_key=True, verbose_name="Body Site Id")
    body_site = models.CharField(max_length=80, verbose_name="Body Site", unique=True)
    base_image = models.CharField(max_length=80, null=True, blank=True, verbose_name="Base Image")
    IMAGE_RENDER_CATEGORY_CHOICES = [
        ('category1', 'Category 1'),
        ('category2', 'Category 2'),
    ]
    image_render_category = models.CharField(max_length=20, choices=IMAGE_RENDER_CATEGORY_CHOICES, null=True,
                                             blank=True, verbose_name="Image Render Category")

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("BodySite")
        verbose_name_plural = _("BodySites")

    def __str__(self):
        return str(self.body_site)

    def natural_key(self):
        return str(self.body_site)


class BodySubSiteMap(models.Model):
    body_subsite_id = models.AutoField(primary_key=True, verbose_name="Body Subsite Id")
    body_site = models.ForeignKey(BodySite, on_delete=models.RESTRICT, verbose_name="Body Site")
    sub_site = models.CharField(verbose_name="SubSite", max_length=80, blank=False, null=False)
    x_axis = models.IntegerField(null=True, blank=True, verbose_name="X Axis")
    y_axis = models.IntegerField(null=True, blank=True, verbose_name="Y Axis")

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Subsite")
        verbose_name_plural = _("Subsites")
        unique_together = ('body_site', 'sub_site')

    def __str__(self):
        return str(self.body_subsite_id)

    def natural_key(self):
        return str(self.body_subsite_id)


class ReportImgPropInfo(models.Model):
    report_img_prop_info_id = models.AutoField(primary_key=True, verbose_name="Report Img Prop Info Id")
    category = models.CharField(max_length=40, verbose_name="Category")
    SHAPE_CHOICES = [
        ('*', 'Star'),
        ('s', 'Square'),
        ('^', 'Triangle'),
        ('D', 'Diamond'),
        ('o', 'Circle'),
    ]
    shape = models.CharField(max_length=10, choices=SHAPE_CHOICES, null=True, blank=True, verbose_name="Shape")
    COLOR_CHOICES = [
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('orange', 'Orange'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
        ('black', 'Black'),
    ]
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, null=True, blank=True, verbose_name="Color")

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Report Image Property")
        verbose_name_plural = _("Report Image Properties")

    def __str__(self):
        return str(self.report_img_prop_info_id)

    def natural_key(self):
        return str(self.report_img_prop_info_id)


class AttachmentConfiguration(models.Model):
    attachment_config_id = models.AutoField(primary_key=True, verbose_name="Attachment Configuration Id")
    model_name = models.CharField(max_length=80, verbose_name="Model", unique=True, null=False, blank=False)
    path = models.CharField(max_length=2000, null=False, blank=False, verbose_name="Path")

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Attachment Configuration")
        verbose_name_plural = _("Attachment Configuration")

    def __str__(self):
        return str(self.model_name)

    def natural_key(self):
        return str(self.model_name)


class Sponsor(models.Model):
    sponsor_id = models.AutoField(primary_key=True, verbose_name="Sponsor Id")
    sponsor_name = models.CharField(max_length=40, blank=False, null=True, verbose_name="Sponsor Name")
    sponsor_number = models.CharField(max_length=40, blank=False, null=True, verbose_name="Sponsor Number")
    sponsor_description = models.TextField(
        max_length=2000,
        blank=True,
        null=True,
        verbose_name="Sponsor Description"
    )
    sponsor_address_info = models.TextField(
        max_length=2000,
        blank=True,
        null=True,
        verbose_name="Sponsor Address Info"
    )
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True)
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT,
                                   verbose_name="Created By", null=True)
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=True)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="SpnModifiedBy",
        verbose_name="Modified By", null=True
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Sponsor")
        verbose_name_plural = _("Sponsors")

    def __str__(self):
        return str(self.sponsor_name)

    def natural_key(self):
        return str(self.sponsor_name)


class BioProject(models.Model):
    bioproject_id = models.CharField(primary_key=True, max_length=40, verbose_name="Project Id")
    project_protocol_id = models.CharField(max_length=40, verbose_name="Project/Protocol Id")
    sponsor_id = models.ForeignKey(Sponsor, on_delete=models.RESTRICT,
                                   verbose_name="Sponsor")
    qc_status = models.CharField(max_length=20, verbose_name="QC Status")
    qced_dt = models.DateTimeField(null=True, blank=True, verbose_name=_('QCed Date Time'))
    qced_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="ProjQCedBy",
        verbose_name="QCed By", null=True, blank=True
    )
    qc_reason = models.CharField(max_length=2000, blank=True, null=True, verbose_name="QC Reason")
    instructions = models.CharField(max_length=2000, blank=True, null=True, verbose_name="Project Instructions")
    modification_notes = models.TextField(
        max_length=2000,
        blank=True,
        null=True,
        verbose_name="Modification Notes"
    )
    client_project_protocol_id = models.CharField(max_length=200, blank=True, null=True,
                                                  verbose_name="Client Project/Protocol ID")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_dt = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created Date Time'), null=True)
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT,
                                   verbose_name="Created By", null=True)
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=True)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="ProjModifiedBy",
        verbose_name="Modified By", null=True
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return str(self.project_protocol_id)

    def natural_key(self):
        return str(self.bioproject_id)

    def save(self, *args, **kwargs):
        if not self.pk:
            model_name = self.__class__.__name__
            prefix = "BPR"
            module = importlib.import_module("util.util")
            UtilClass = getattr(module, "UtilClass")
            seq_no = UtilClass.get_next_sequence(prefix, model_name, self.created_by.id)
            self.bioproject_id = f"{prefix}-{seq_no:05}"

        super().save(*args, **kwargs)


class ProjectVisitMap(models.Model):
    project_visit_map_id = models.AutoField(primary_key=True, verbose_name="Project Visit Map Id")
    bioproject_id = models.ForeignKey(BioProject, on_delete=models.RESTRICT,
                                      verbose_name="Bio Project")
    visit_id = models.CharField(max_length=20, verbose_name="Visit ID")
    client_visit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name="Client Visit ID")
    visit_instruction = models.CharField(max_length=200, blank=True, null=True, verbose_name="Visit Instruction")
    created_dt = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Created Date Time'))
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                   verbose_name='Created By',
                                   related_name="project_visitmap_created_by")
    mod_dt = models.DateTimeField(
        auto_now=True, null=True, blank=True,
        verbose_name=_('Modified Date Time'))
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT, null=True, blank=True,
        related_name="project_visitmap_modified_by",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Visit Details")
        verbose_name_plural = _("Visit Details")
        constraints = [
            models.UniqueConstraint(
                fields=['bioproject_id', 'visit_id'],
                name='unique_project_visit',
                violation_error_message="This visit is already associated with this project"
            )
        ]

    def __str__(self):
        return str(self.project_visit_map_id)

    def natural_key(self):
        return str(self.project_visit_map_id)


class ProjectTestMap(models.Model):
    project_test_map_id = models.AutoField(primary_key=True, verbose_name="Project Test Map Id")
    bioproject_id = models.ForeignKey(BioProject, on_delete=models.RESTRICT, verbose_name="Bio Project")
    test_id = models.ForeignKey('tests.Test', on_delete=models.RESTRICT, verbose_name="Test")

    created_dt = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Created Date Time'))
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                   verbose_name='Created By',
                                   related_name="project_testmap_created_by")
    mod_dt = models.DateTimeField(
        auto_now=True, null=True, blank=True,
        verbose_name=_('Modified Date Time'))
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT, null=True, blank=True,
        related_name="project_testmap_modified_by",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Test")
        verbose_name_plural = _("Tests")
        constraints = [
            models.UniqueConstraint(
                fields=['bioproject_id', 'test_id'],
                name='unique_project_test_id',
                violation_error_message="This test is already associated with this project"
            )
        ]

    def __str__(self):
        return str(self.project_test_map_id)

    def natural_key(self):
        return str(self.project_test_map_id)


class ProjectEmailMap(models.Model):
    project_email_map_id = models.AutoField(primary_key=True, verbose_name="Project Email Map Id")
    bioproject_id = models.ForeignKey(BioProject, on_delete=models.RESTRICT, verbose_name="Bio Project")
    email_id = models.CharField(max_length=2000, blank=True, null=True, verbose_name="Email Id")
    email_category = models.CharField(max_length=40, blank=True, null=True, verbose_name="Email Category")
    created_dt = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, verbose_name=_('Created Date Time'))
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                   verbose_name='Created By',
                                   related_name="project_emailmap_created_by")
    mod_dt = models.DateTimeField(
        auto_now=True, null=True, blank=True,
        verbose_name=_('Modified Date Time'))
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT, null=True, blank=True,
        related_name="project_emailmap_modified_by",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Email")
        verbose_name_plural = _("Email")

    def __str__(self):
        return str(self.project_email_map_id)

    def natural_key(self):
        return str(self.project_email_map_id)


class BioSite(models.Model):
    biosite_id = models.AutoField(primary_key=True, verbose_name="BioSite ID")
    sponsor_id = models.ForeignKey(Sponsor, on_delete=models.RESTRICT,
                                   verbose_name="Sponsor", related_name="Sponsor")
    bioproject_id = models.ForeignKey(BioProject, on_delete=models.RESTRICT,
                                      verbose_name="BioProject", related_name="BioProject")
    site_number = models.CharField(max_length=40, verbose_name="Site Number")

    created_dt = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Created Date Time'))
    created_by = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                   verbose_name="BioSCreated By")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'))
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT, null=True, blank=True,
        related_name="BioSiteModifiedBy",
        verbose_name="Modified By"
    )
    address = models.TextField(
        max_length=2000,
        blank=True,
        null=True,
        verbose_name="Address"
    )

    street = models.CharField(max_length=100, blank=True, null=True, verbose_name="Street")
    city = models.CharField(max_length=80, blank=True, null=True, verbose_name="City")
    state = models.CharField(max_length=80, blank=True, null=True, verbose_name="State")
    postalcode = models.CharField(max_length=50, blank=True, null=True, verbose_name="Postal Code")
    country = models.CharField(max_length=80, verbose_name="Investigator Site Country")
    investigator_name = models.CharField(max_length=200, verbose_name="Investigator Name")
    phone_number = models.CharField(max_length=20,
                                    validators=[
                                        RegexValidator(
                                            regex=r'^\+?1?\s?-?\(?\d{3}\)?\s?-?\d{3}\s?-?\d{4}$',
                                            message="Enter a valid US phone number (e.g., +1 123-456-7890, (123) 456-7890, or 1234567890)."
                                        )
                                    ],
                                    blank=True, null=True, verbose_name="Phone Number")
    fax_number = models.CharField(max_length=20,
                                  validators=[
                                      RegexValidator(
                                          regex=r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$',
                                          message="Enter a valid fax number in the format (123) 456-7890 or 123-456-7890."
                                      )
                                  ],
                                  blank=True, null=True, verbose_name="Fax Number")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Investigator Site")
        verbose_name_plural = _("Investigator Site")

    def __str__(self):
        return str(self.investigator_name)


class EmailConfig(models.Model):
    emailconfig_id = models.AutoField(primary_key=True, verbose_name="Email Config ID")

    email_category = models.CharField(max_length=40, blank=False, null=False, unique=True,
                                      verbose_name="Email Category")

    email_to = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        verbose_name="Email To",
        help_text="Multiple email IDs separated by semicolons"
    )

    email_cc = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Email CC",
        help_text="Multiple email IDs separated by semicolons"
    )

    subject = models.CharField(max_length=255, blank=False, null=False, verbose_name="Email Subject")

    body = models.TextField(blank=False, null=False, verbose_name="Email Body")

    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Date Time'))
    created_by = models.ForeignKey(
        security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
        verbose_name="Created By", related_name="emailconfigCreatedBy"
    )
    mod_dt = models.DateTimeField(auto_now=True, verbose_name=_('Modified Date Time'))
    mod_by = models.ForeignKey(
        User, on_delete=models.RESTRICT, null=True, blank=True,
        related_name="emailconfigModifiedBy", verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    def __str__(self):
        return f"{self.email_category or 'Email Config'} - {self.emailconfig_id}"


class QCPendingBioProject(BioProject):
    """
    Proxy model for BioProject to display only QC Pending entries in Admin.
    """

    class Meta:
        proxy = True
        verbose_name = "QC Pending Project"
        verbose_name_plural = "QC Pending Projects"


class BodySiteTestMap(models.Model):
    bodysite_test_map_id = models.AutoField(primary_key=True, verbose_name="Bodysite Test Id")
    body_site = models.ForeignKey(BodySite, on_delete=models.RESTRICT, verbose_name="Body Site")
    test_id = models.ForeignKey("tests.Test", on_delete=models.RESTRICT, null=True, verbose_name="Test Id")
    is_default = models.BooleanField(default=False, verbose_name="Is Default")
    created_dt = models.DateTimeField(auto_now_add=True, verbose_name=_("Created DateTime"), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By", related_name="testbodysite_created_by")
    mod_dt = models.DateTimeField(auto_now=True, verbose_name=_("Modified DateTime"), null=True, blank=True)
    mod_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                               verbose_name="Modified By", related_name="testbodysite_mod_by")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Bodysite Test Map"
        verbose_name_plural = 'Associated Tests'
        unique_together = ('body_site', 'test_id')

    def __str__(self):
        return str(self.bodysite_test_map_id)


class AccessionPrefix(models.Model):
    accession_prefix = models.CharField(
        max_length=10,
        unique=True,
        blank=False,
        null=False,
        verbose_name="Accession Prefix"
    )
    magazine = models.CharField(max_length=10, null=True, blank=True)

    history = AuditlogHistoryField()

    def __str__(self):
        return self.accession_prefix

    class Meta:
        verbose_name = "Accession Prefix"
        verbose_name_plural = "Accession Prefixes"
        ordering = ['accession_prefix']


class ProjectFieldsMap(models.Model):
    project = models.ForeignKey(
        BioProject,
        on_delete=models.CASCADE,
        verbose_name="Project"
    )
    field_name = models.CharField(
        max_length=100,
        verbose_name="Field Name"
    )
    model_field_name = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="Model Field Name"
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name="Is Visible"
    )

    CATEGORY_CHOICES = [
        ('ACCESSION', 'Accession'),
        ('SAMPLE', 'Sample'),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True
    )
    created_dt = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created DateTime"),
        null=True, blank=True
    )
    created_by = models.ForeignKey(
        security.models.User, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Created By",
        related_name="projectfieldsmap_created_by"
    )
    mod_dt = models.DateTimeField(
        auto_now=True, verbose_name=_("Modified DateTime"),
        null=True, blank=True
    )
    mod_by = models.ForeignKey(
        security.models.User, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Modified By",
        related_name="projectfieldsmap_mod_by"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Demographic"
        verbose_name_plural = "Demographics"
        unique_together = ('project', 'field_name')

    def __str__(self):
        return f"{self.project.project_protocol_id}: {self.field_name} ({'Visible' if self.is_visible else 'Hidden'})"


class DemographicFields(models.Model):
    demographicfieldsid = models.AutoField(primary_key=True)
    field_name = models.CharField(
        max_length=100,
        verbose_name="Field Name"
    )
    model_field_name = models.CharField(
        max_length=100,
        verbose_name="Model Field Name"
    )

    CATEGORY_CHOICES = [
        ('ACCESSION', 'Accession'),
        ('SAMPLE', 'Sample'),

    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Demographic Field"
        verbose_name_plural = "Demographic Fields"

    def __str__(self):
        return f"{self.field_name}"


class ProjectPhysicianMap(models.Model):
    project_physician_map_id = models.AutoField(
        primary_key=True, verbose_name="Project Physician Map Id"
    )

    bioproject_id = models.ForeignKey(
        'masterdata.BioProject',
        on_delete=models.RESTRICT,
        verbose_name="Bio Project"
    )

    physician_id = models.ForeignKey(
        'masterdata.Physician',
        on_delete=models.RESTRICT,
        verbose_name="Physician"
    )

    created_dt = models.DateTimeField(
        auto_now_add=True, null=True, blank=True,
        verbose_name=_("Created Date Time")
    )

    created_by = models.ForeignKey(
        security.models.User,
        on_delete=models.RESTRICT,
        null=True, blank=True,
        verbose_name="Created By",
        related_name="project_physicianmap_created_by"
    )

    mod_dt = models.DateTimeField(
        auto_now=True, null=True, blank=True,
        verbose_name=_("Modified Date Time")
    )

    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=True, blank=True,
        related_name="project_physicianmap_modified_by",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Project Physician Map")
        verbose_name_plural = _("Project Physician Maps")
        constraints = [
            models.UniqueConstraint(
                fields=['bioproject_id', 'physician_id'],
                name='unique_project_physician',
                violation_error_message="This physician is already associated with this project"
            )
        ]

    def __str__(self):
        return f"{self.bioproject_id} - {self.physician_id}"


auditlog.register(Client)
auditlog.register(Patient)
auditlog.register(Subject)
auditlog.register(Physician)
auditlog.register(PatientInsuranceInfo)
auditlog.register(ClientDoctorInfo)
auditlog.register(AccessionType)
auditlog.register(BodySite)
auditlog.register(BodySubSiteMap)
auditlog.register(ReportImgPropInfo)
auditlog.register(AttachmentConfiguration)
auditlog.register(Sponsor)
auditlog.register(BioProject)
auditlog.register(ProjectVisitMap)
auditlog.register(ProjectTestMap)
auditlog.register(ProjectEmailMap)
auditlog.register(BioSite)
auditlog.register(EmailConfig)
auditlog.register(QCPendingBioProject)
auditlog.register(BodySiteTestMap)
auditlog.register(AccessionPrefix)
auditlog.register(ProjectFieldsMap)
auditlog.register(DemographicFields)
auditlog.register(ProjectPhysicianMap)
