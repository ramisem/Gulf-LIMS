from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from masterdata.models import Client, Patient, Physician, PatientInsuranceInfo, Sponsor, BioProject, BioSite, ProjectVisitMap
from security.models import User, Department
import security


class Accession(models.Model):
    accession_id = models.CharField(primary_key=True, max_length=40, verbose_name="Case Number")
    active_flag = models.CharField(max_length=10, blank=False, null=True, verbose_name="Active Flag", default="Y")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created Date Time'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name="Created By")
    accession_lab = models.CharField(max_length=50, blank=True, null=True, verbose_name="Accession Lab")
    status = models.CharField(max_length=40, blank=True, null=True, verbose_name="Status")
    complete_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Completed Date Time'), null=True, blank=True)
    client_id = models.ForeignKey(Client, on_delete=models.RESTRICT, null=True, verbose_name="Client")
    patient_id = models.ForeignKey(Patient, on_delete=models.RESTRICT, null=True, verbose_name="Patient")
    insurance_id = models.ForeignKey(PatientInsuranceInfo, on_delete=models.PROTECT, null=True, blank=True,
                                     verbose_name="Insurance")
    created_by_dept = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT,
                                        verbose_name="Created By Dept")
    accession_failedby = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                           verbose_name="Accession Failed By", related_name="acc_failed_by")
    qc_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('QC Date Time'), null=True, blank=True)
    env_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Env Type", default="Clinical")
    accessionqc_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.PROTECT,
                                       verbose_name="Accession QC By", related_name="acc_qc_by")
    doctor = models.ForeignKey(Physician, null=True, blank=True, on_delete=models.PROTECT,
                               verbose_name="Referring Doctor")
    reporting_doctor = models.ForeignKey(Physician, null=True, blank=True, on_delete=models.PROTECT,
                                         verbose_name="Reporting Doctor / Pathologist", related_name="reporting_doctor")
    diagnosis = models.CharField(max_length=50, blank=True, null=True, verbose_name="Diagnosis")
    accession_type = models.ForeignKey("masterdata.AccessionType", max_length=40, blank=False, null=True,
                                       verbose_name="Accession Type", on_delete=models.RESTRICT
                                       )
    accession_category = models.CharField(max_length=40, blank=False, null=True, verbose_name="Accession Category")
    accession_template = models.CharField(max_length=40, blank=False, null=True, verbose_name="Accession Template")
    accession_prefix = models.CharField(max_length=10, blank=True, null=True, verbose_name="Accession Prefix")
    payment_type = models.CharField(max_length=40, blank=False, null=True, verbose_name="Payment Type")
    is_external = models.BooleanField(default=False, verbose_name="External")
    is_internal = models.BooleanField(default=False, verbose_name="Internal")
    is_technical_reporting = models.BooleanField(default=False, verbose_name="Technical Reporting")
    is_auto_gen_pk = models.BooleanField(default=True, verbose_name="Auto Key Generation")
    receive_dt = models.CharField(max_length=200, blank=True, null=True,
                                  verbose_name="Receive Date")
    receive_dt_timezone = models.CharField(max_length=100, null=True, blank=True, verbose_name="Receive Date Timezone")
    collection_dt = models.CharField(max_length=200, blank=True, null=True,
                                     verbose_name="Collection Date")
    collection_dt_timezone = models.CharField(max_length=100, null=True, blank=True,
                                              verbose_name="Collection Date Timezone")
    label_count = models.IntegerField(verbose_name="Label Events", default=0)
    is_template = models.BooleanField(default=False, blank=True, verbose_name="Is Template")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Accessioning")
        verbose_name_plural = _("Accessioning")

    def __str__(self):
        return self.accession_id

    def natural_key(self):
        return self.accession_id

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)


class BioPharmaAccession(Accession):
    """
    An extension of the Accession model for BioPharma specific projects,
    inheriting all its fields and logic.
    """
    project = models.ForeignKey(
        BioProject,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name=_("Project"),
        related_name="biopharma_accessions"
    )
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name=_("Sponsor"),
        related_name="biopharma_accessions"
    )
    investigator = models.ForeignKey(
        BioSite,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name=_("Investigator"),
        related_name="biopharma_accessions"
    )
    visit = models.ForeignKey(
        ProjectVisitMap,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name=_("Visit"),
        related_name="biopharma_accessions"
    )

    class Meta:
        verbose_name = _("Pharma Accession")
        verbose_name_plural = _("Pharma Accessions")

    def __str__(self):
        return f"{self.accession_id} (Pharma)"


class AccessionICDCodeMap(models.Model):
    accession_icd_code_map_id = models.AutoField(primary_key=True, verbose_name="Accession ICD Code Map ID")
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=False, verbose_name="Accession ID")
    icd_code_id = models.ForeignKey("tests.ICDCode", on_delete=models.RESTRICT, null=False, verbose_name="ICD Code")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=True,
        blank=False,
        related_name="ICDCodeCreatedBy",
        verbose_name="Created By"
    )
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=True,
        blank=False,
        related_name="ICDCodeModifiedBy",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("ICD Code")
        verbose_name_plural = _("ICD Code")
        constraints = [
            models.UniqueConstraint(fields=['accession_id', 'icd_code_id'], name='unique_accession_id_icd_code_id')
        ]

    def __str__(self):
        return str(self.accession_icd_code_map_id)

    def natural_key(self):
        return self.accession_icd_code_map_id


auditlog.register(Accession)
auditlog.register(AccessionICDCodeMap)
