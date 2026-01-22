import importlib

from django.db import models, transaction
import security, tests
from django.utils.translation import gettext_lazy as _
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from controllerapp import settings
from util.util import UtilClass
from datetime import datetime
from django.apps import apps
import workflows
from process.models import SampleType, ContainerType
from security.models import Department, User
from accessioning.models import Accession
from django.db import connection

from workflows.models import Workflow


class Sample(models.Model):
    sample_id = models.CharField(primary_key=True, max_length=40,
                                 verbose_name="Sample Id")
    part_no = models.CharField(max_length=20, null=True, blank=True, verbose_name="Part No")
    sample_type = models.ForeignKey(SampleType, on_delete=models.RESTRICT, null=True, verbose_name="Sample Type")
    container_type = models.ForeignKey(ContainerType, on_delete=models.RESTRICT, null=True,
                                       verbose_name="Container")
    custodial_department = models.ForeignKey(Department, on_delete=models.RESTRICT, null=True, blank=True,
                                             verbose_name="Custodial Department")
    custodial_user = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True,
                                       related_name="CustodialUser",
                                       verbose_name="Custodial User")
    custodial_storage_id = models.CharField(max_length=40, null=True, blank=True, verbose_name="Custodial Storage")
    previous_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="Previous Step")
    current_step = models.CharField(max_length=40, null=False, blank=False, verbose_name="Current Step")
    next_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="Next Step")
    avail_at = models.DateTimeField(verbose_name=_('Avail DateTime'), null=True, blank=True)
    accession_sample = models.ForeignKey('self', on_delete=models.RESTRICT, null=True, blank=True,
                                         verbose_name="Accession Sample", related_name="accessionsample")
    accession_generated = models.BooleanField(default=False, verbose_name="Accession Generated")
    pending_action = models.CharField(max_length=200, null=True, blank=True, verbose_name="Pending Action")
    body_site = models.CharField(max_length=80, null=True, blank=True, verbose_name="Body Site")
    sub_site = models.CharField(max_length=80, null=True, blank=True, verbose_name="Sub Site")
    collection_method = models.CharField(max_length=80, null=True, blank=True, verbose_name="Collection Method")
    workflow_id = models.ForeignKey(Workflow, null=True, blank=True, on_delete=models.RESTRICT,
                                       verbose_name="Workflow Id")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="CreatedBy",
        verbose_name="Created By"
    )
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="ModifiedBy",
        verbose_name="Modified By"
    )
    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=True, blank=True,
                                     verbose_name="Case Number",
                                     related_name="AccessionID")
    receive_dt = models.CharField(max_length=200, blank=True, null=True,
                                  verbose_name="Receive Date")
    receive_dt_timezone = models.CharField(max_length=100, null=True, blank=True)
    collection_dt = models.CharField(max_length=200, blank=True, null=True,
                                     verbose_name="Collection Date")
    collection_dt_timezone = models.CharField(max_length=100, null=True, blank=True)
    slide_seq = models.CharField(max_length=20, null=True, blank=True, verbose_name="Slide #")
    block_or_cassette_seq = models.CharField(max_length=20, null=True, blank=True, verbose_name="Block/Cassette #")
    sample_status = models.CharField(max_length=20, null=True, blank=True, verbose_name="Sample Status")

    size = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Size")
    pieces = models.IntegerField(verbose_name="Pieces", blank=True, null=True)
    num_of_blocks = models.IntegerField(verbose_name="Number of Blocks", null=True, blank=True)
    num_of_slides = models.IntegerField(verbose_name="Number of Slides", null=True, blank=True)
    num_of_manualsmear_slides = models.IntegerField(verbose_name="Number of Manual Smear Slides", null=True, blank=True)
    num_of_thinprep_slides = models.IntegerField(verbose_name="Number of Thin Smear Slides", null=True, blank=True)
    grossing_comments = models.TextField(verbose_name="Grossing Comments", blank=True, null=True)
    gross_code = models.CharField(verbose_name="Gross Code", max_length=150, null=True, blank=True)
    gross_description = models.TextField(verbose_name="Gross Description", null=True, blank=True)
    descriptive = models.CharField(verbose_name="Descriptive", max_length=150, null=True, blank=True)
    isvisible = models.BooleanField(null=True, verbose_name="Is visible")
    smearing_process = models.CharField(max_length=20, null=True, blank=True, verbose_name="Smearing Process")
    label_count = models.IntegerField(verbose_name="Label Events", default=0)

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Sample")
        verbose_name_plural = _("Samples")

    def __str__(self):
        return str(self.sample_id)

    def natural_key(self):
        return self.sample_id

    def save(self, *args, **kwargs):
        is_macro_creation = kwargs.pop('is_macro_creation', False)
        Sample = apps.get_model('sample', 'Sample')

        module = importlib.import_module("util.util")
        UtilClass = getattr(module, "UtilClass")

        is_update = self.pk is not None
        old_instance = None
        if is_update:
            old_instance = Sample.objects.filter(pk=self.pk).first()

        if is_macro_creation:  # Generate SAM-Macros ID only for SampleMacro creation
            if not self.sample_id:  # Only generate if it's a new record
                seq_no = UtilClass.get_next_sequence('SAM-Macros', 'Sample', self.created_by_id)
                self.sample_id = f"SAM-Macros-{seq_no:05}"
        else:  # Original logic for other Sample creations
            if not self.sample_id:
                model_name = self.__class__.__name__
                current_date = datetime.now()
                prefix = f"S-{current_date.strftime('%m%d%Y')}"
                seq_no = UtilClass.get_next_sequence(prefix, model_name, self.created_by.id)
                self.sample_id = f"{prefix}-{seq_no:05}"

        with transaction.atomic():
            def validate_field(field_value, setting_name, field_name):
                # Only perform validation if a value is provided
                if field_value:
                    required_reftype = getattr(settings, setting_name, None)
                    if required_reftype is None:
                        raise ValueError(f"Setting {setting_name} is not defined.")

                    ref_values = UtilClass.get_refvalues_for_field(required_reftype)
                    if not ref_values:
                        raise ValueError(f"No reference values found for {setting_name}.")

                    valid_choices = {choice[0] for choice in ref_values}
                    if field_value and field_value not in valid_choices:
                        valid_display_choices = [choice[1] for choice in ref_values]
                        raise ValueError(
                            f"Entered value for {field_name} is invalid. Valid options are {valid_display_choices}.")

            # validate_field(self.gross_code, 'APPLICATION_GROSS_CODE_REFERENCE', 'Gross Code')
            validate_field(self.descriptive, 'APPLICATION_DESCRIPTIVE_REFERENCE', 'Descriptive')
            super().save(*args, **kwargs)

        if is_update:
            UtilClass.createRoutingInfoForSample(
                self,
                old_samples={self.sample_id: old_instance},
                single=True
            )
        else:
            UtilClass.createRoutingInfoForSample(self, single=True)

    def delete(self, *args, **kwargs):
        RoutingInfo = apps.get_model('routinginfo', 'RoutingInfo')
        with transaction.atomic():
            with connection.cursor() as cursor:
                try:
                    if SampleTestMap.objects.filter(sample_id=self).exists():
                        SampleTestMap.objects.filter(sample_id=self).delete()
                    if RoutingInfo.objects.filter(sample_id=self).exists():
                        RoutingInfo.objects.filter(sample_id=self).delete()
                    sql = """
                       DELETE FROM sample_sample
                       WHERE sample_id = %s
                       """
                    cursor.execute(sql, [self.sample_id])
                except Exception as e:
                    raise ValueError(f"Error occurred during deletion: {str(e)}")


class ChildSample(models.Model):
    child_sample_id = models.AutoField(primary_key=True, verbose_name="Child Sample ID")
    destination_sample = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=False,
                                           verbose_name="Child Sample ID", related_name="destinationsample")
    source_sample = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=False, verbose_name="Parent Sample ID",
                                      related_name="sourcesample")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("ChildSample")
        verbose_name_plural = _("ChildSamples")

    def __str__(self):
        return str(self.child_sample_id)

    def natural_key(self):
        return self.child_sample_id


class SampleTestMap(models.Model):
    sample_test_map_id = models.AutoField(primary_key=True, verbose_name="Sample Test Map ID")
    sample_id = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=False, verbose_name="Sample ID")
    test_status = models.CharField(max_length=50, null=False, blank=False, verbose_name="Test Status")
    test_id = models.ForeignKey(tests.models.Test, max_length=60, null=True, blank=True, on_delete=models.RESTRICT,
                                verbose_name="Test ID")
    workflow_id = models.ForeignKey(workflows.models.Workflow, max_length=60, null=True, blank=True,
                                    on_delete=models.RESTRICT,
                                    verbose_name="Workflow ID")
    microtomy_completed = models.BooleanField(null=True, verbose_name="Is Microtomy Completed")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("SampleTestMap")
        verbose_name_plural = _("SampleTestMap")

    def __str__(self):
        return str(self.sample_test_map_id)

    def natural_key(self):
        return self.sample_test_map_id


class HistoricalSample(Sample):
    class Meta:
        proxy = True
        verbose_name = _("Historical Sample")
        verbose_name_plural = _("Historical Samples")

    def __str__(self):
        return str(self.sample_id)

    def natural_key(self):
        return self.sample_id


class StoredSample(Sample):
    class Meta:
        proxy = True
        verbose_name = _("Stored Sample")
        verbose_name_plural = _("Stored Samples")

    def __str__(self):
        return str(self.sample_id)

    def natural_key(self):
        return self.sample_id


auditlog.register(Sample)
auditlog.register(SampleTestMap)
auditlog.register(ChildSample)
auditlog.register(HistoricalSample)
auditlog.register(StoredSample)
