import importlib

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.apps import apps
import security
from accessioning.models import Accession
from masterdata.models import Client, Physician
from sample.models import Sample
from security.models import Department, User
from tests.models import Test, Analyte, TestAnalyte
from workflows.models import Workflow
from template.models import Macros


class ReportOption(models.Model):
    report_option_id = models.CharField(primary_key=True, max_length=40, verbose_name="Report Option ID")
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=False, blank=False,
                                     verbose_name="Case Number")
    root_sample_id = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=False, blank=False,
                                       verbose_name="Root Sample ID")
    version_id = models.IntegerField()
    amendment_type = models.CharField(max_length=40, null=True, blank=True, verbose_name="Amendment Type")
    assign_pathologist = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                           verbose_name="Assigned Pathologist", related_name="assign_pathologist")
    reporting_status = models.CharField(max_length=40, blank=False, null=False, verbose_name="Reporting Status")
    test_id = models.ForeignKey(Test, max_length=60, null=True, blank=True, on_delete=models.RESTRICT,
                                verbose_name="Test ID")
    custodial_department = models.ForeignKey(Department, on_delete=models.RESTRICT, null=True, blank=True,
                                             verbose_name="Custodial Department")
    previous_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="Previous Step")
    current_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="Current Step")
    next_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="Next Step")
    avail_at = models.DateTimeField(verbose_name=_('Avail DateTime'), null=True, blank=True)
    pending_action = models.CharField(max_length=200, null=True, blank=True, verbose_name="Pending Action")
    methodology = models.CharField(max_length=200, null=True, blank=True, verbose_name="Methodology")
    workflow_id = models.ForeignKey(Workflow, null=True, blank=True, on_delete=models.RESTRICT,
                                    verbose_name="Workflow Id")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By", related_name="created_by")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="ROModifiedBy",
        verbose_name="Modified By"
    )
    last_signed_dt = models.DateTimeField(
        verbose_name=_('Last Signed DateTime'), null=True, blank=True)
    last_signed_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                       verbose_name="Last Signed By", related_name="last_signed_by")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        unique_together = (
            'report_option_id',
            'accession_id',
            'root_sample_id',
            'version_id',
            'methodology',
        )

    def __str__(self):
        return str(self.report_option_id)

    def natural_key(self):
        return str(self.report_option_id)

    def save(self, *args, **kwargs):
        ReportOption = apps.get_model('analysis', 'ReportOption')

        module = importlib.import_module("util.util")
        UtilClass = getattr(module, "UtilClass")

        is_update = self.pk is not None
        old_instance = None
        if is_update:
            old_instance = ReportOption.objects.filter(pk=self.pk).first()

        super().save(*args, **kwargs)

        if is_update:
            UtilClass.createRoutingInfoForReportOption(
                self,
                old_reportoption={self.report_option_id: old_instance},
                single=True
            )
        else:
            UtilClass.createRoutingInfoForReportOption(self, single=True)


class ReportOptionDtl(models.Model):
    report_option_dtl_id = models.CharField(primary_key=True, max_length=40, verbose_name="Report Option Detail ID")
    report_option_id = models.ForeignKey(ReportOption, on_delete=models.RESTRICT, null=False, blank=False,
                                         verbose_name="Report Option ID")
    version_id = models.IntegerField()
    analyte_id = models.ForeignKey(Analyte, on_delete=models.RESTRICT, null=False, blank=False,
                                   verbose_name="Analyte")
    analyte_value = models.TextField(null=True, blank=True, verbose_name="Analyte Value")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(security.models.User, null=False, blank=False, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="RODModifiedBy",
        verbose_name="Modified By"
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Report Detail")
        verbose_name_plural = _("Report Details")

    def __str__(self):
        return str(self.report_option_dtl_id)

    def natural_key(self):
        return str(self.report_option_dtl_id)

    def clean(self):
        super().clean()

        # grab the matching TestAnalyte rule
        try:
            rule = TestAnalyte.objects.get(
                test_id=self.report_option_id.test_id,
                analyte_id=self.analyte_id
            )
        except TestAnalyte.DoesNotExist:
            return  # no rule → always valid

        is_type_valid, type_msg = rule.validate_value_type(self.analyte_value)
        if not is_type_valid:
            raise ValidationError({'analyte_value': type_msg})

        if not rule.validate_analyte_value(self.analyte_value):
            raise ValidationError({
                'analyte_value': "Value does not meet the configured rule "
                                 f"for analyte {self.analyte_id}."
            })

    def save(self, *args, **kwargs):
        # force full_clean → calls clean() above
        self.full_clean()
        return super().save(*args, **kwargs)


class MergeReporting(models.Model):
    merge_reporting_id = models.CharField(primary_key=True, max_length=40, verbose_name="Merge Reporting ID")
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=False, blank=False,
                                     verbose_name="Case Number")
    amendment_type = models.CharField(max_length=40, null=True, blank=True, verbose_name="Amendment Type")

    amendment_comments = models.TextField(
        null=True,
        blank=True,
        verbose_name="Amendment Comments"
    )
    assign_pathologist = models.ForeignKey(security.models.User, on_delete=models.RESTRICT, null=True, blank=True,
                                           verbose_name="Assigned Pathologist", related_name="mr_assign_pathologist")
    reporting_status = models.CharField(max_length=40, blank=False, null=False, verbose_name="Reporting Status")
    methodology = models.CharField(max_length=200, null=True, blank=True, verbose_name="Methodology")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(security.models.User, null=False, blank=False, on_delete=models.RESTRICT,
                                   verbose_name="Created By", related_name="mr_created_by")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="mr_modified_by",
        verbose_name="Modified By"
    )
    last_signed_dt = models.DateTimeField(
        verbose_name=_('Last Signed DateTime'), null=True, blank=True)
    last_signed_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                       verbose_name="Last Signed By", related_name="mr_last_signed_by")
    history = AuditlogHistoryField()

    class Meta:
        app_label = 'analysis'
        verbose_name = _("Reporting")
        verbose_name_plural = _("Reporting")

    def __str__(self):
        return str(self.merge_reporting_id)

    def natural_key(self):
        return str(self.merge_reporting_id)


class MergeReportingDtl(models.Model):
    merge_reporting_dtl_id = models.CharField(primary_key=True, max_length=40, verbose_name="Merge Reporting Detail ID")
    merge_reporting_id = models.ForeignKey(MergeReporting, on_delete=models.RESTRICT, null=False, blank=False,
                                           verbose_name="Merge Reporting ID")
    report_option_id = models.ForeignKey(ReportOption, on_delete=models.RESTRICT, null=False, blank=False,
                                         verbose_name="Report Option ID")
    analyte_id = models.ForeignKey(Analyte, on_delete=models.RESTRICT, null=False, blank=False,
                                   verbose_name="Analyte")
    analyte_value = models.TextField(null=True, blank=True, verbose_name="Analyte Value")
    version_id = models.IntegerField()
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(security.models.User, null=False, blank=False, on_delete=models.RESTRICT,
                                   verbose_name="Created By", related_name="mrd_created_by")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="mrd_modified_by",
        verbose_name="Modified By"
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Merge Reporting Detail")
        verbose_name_plural = _("Merge Reporting Details")

    def __str__(self):
        return str(self.merge_reporting_dtl_id)

    def natural_key(self):
        return str(self.merge_reporting_dtl_id)

    def clean(self):
        super().clean()

        # grab the matching TestAnalyte rule
        try:
            rule = TestAnalyte.objects.get(
                test_id=self.report_option_id.test_id,
                analyte_id=self.analyte_id
            )
        except TestAnalyte.DoesNotExist:
            return  # no rule → always valid

        is_type_valid, type_msg = rule.validate_value_type(self.analyte_value)
        if not is_type_valid:
            raise ValidationError({'analyte_value': type_msg})

        if not rule.validate_analyte_value(self.analyte_value):
            raise ValidationError({
                'analyte_value': "Value does not meet the configured rule "
                                 f"for analyte {self.analyte_id}."
            })

    def save(self, *args, **kwargs):
        # force full_clean → calls clean() above
        self.full_clean()
        return super().save(*args, **kwargs)


class ReportSignOut(models.Model):
    report_sign_out_id = models.AutoField(primary_key=True, verbose_name="Report Sign Out ID")
    report_option_id = models.ForeignKey(ReportOption, on_delete=models.RESTRICT, null=False, blank=False,
                                         verbose_name="Report Option ID")
    merge_reporting_id = models.ForeignKey(MergeReporting, on_delete=models.RESTRICT, null=True, blank=True,
                                           verbose_name="Merge Reporting ID")
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=True, blank=True,
                                     verbose_name="Accession ID")
    root_sample_id = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=True, blank=True,
                                       verbose_name="Root Sample ID")
    version_id = models.IntegerField()
    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, blank=True, verbose_name="Test ID")
    analyte_id = models.ForeignKey(Analyte, on_delete=models.RESTRICT, null=False, blank=False,
                                   verbose_name="Analyte")
    analyte_value = models.TextField(null=True, blank=True, verbose_name="Analyte Value")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(security.models.User, null=False, blank=False, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="RSOModifiedBy",
        verbose_name="Modified By"
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Report Sign Out")
        verbose_name_plural = _("Report Sign Outs")

    def __str__(self):
        return str(self.report_sign_out_id)

    def natural_key(self):
        return str(self.report_sign_out_id)


class HistoricalReportOption(ReportOption):
    class Meta:
        proxy = True
        verbose_name = _("Historical Report")
        verbose_name_plural = _("Historical Reports")

    def __str__(self):
        return str(self.report_option_id)

    def natural_key(self):
        return self.report_option_id


class HistoricalMergeReporting(MergeReporting):
    class Meta:
        proxy = True
        verbose_name = _("Reporting")
        verbose_name_plural = _("Reporting")

    def __str__(self):
        return str(self.merge_reporting_id)

    def natural_key(self):
        return self.merge_reporting_id


class Attachment(models.Model):
    attachment_id = models.AutoField(primary_key=True, verbose_name="Attachment ID")
    report_option_id = models.ForeignKey(ReportOption, on_delete=models.RESTRICT, null=True, blank=True,
                                         verbose_name="Report Option ID")
    merge_reporting_id = models.ForeignKey(MergeReporting, on_delete=models.RESTRICT, null=True, blank=True,
                                           verbose_name="Merge Reporting ID")
    version_id = models.IntegerField(null=True, blank=True, verbose_name="Version Id")
    file_path = models.FileField(
        max_length=2000,
        null=False,
        blank=False,
        verbose_name="File Path"
    )
    attachment_type = models.CharField(max_length=100, verbose_name="Attachment Type", null=True, blank=True)
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=True, blank=True,
                                     verbose_name="Accession ID")
    client_id = models.ForeignKey(Client, on_delete=models.RESTRICT, null=True, blank=True,
                                  verbose_name="Client ID")
    physician_id = models.ForeignKey(Physician, on_delete=models.RESTRICT, null=True, blank=True,
                                     verbose_name="Physician ID")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(security.models.User, null=False, blank=False, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="AtchmntModifiedBy",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return str(self.attachment_id)

    def natural_key(self):
        return str(self.attachment_id)


auditlog.register(ReportOption)
auditlog.register(ReportOptionDtl)
auditlog.register(MergeReporting)
auditlog.register(MergeReportingDtl)
auditlog.register(ReportSignOut)
auditlog.register(HistoricalReportOption)
auditlog.register(HistoricalMergeReporting)
auditlog.register(Attachment)
