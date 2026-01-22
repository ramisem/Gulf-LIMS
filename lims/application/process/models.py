from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _

import security


class SampleType(models.Model):
    sample_type_id = models.AutoField(primary_key=True, verbose_name="Sample Type Id")
    sample_type = models.CharField(unique=True, max_length=40, verbose_name="Sample Type")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Sample Type")
        verbose_name_plural = _("Sample Types")
        unique_together = ('sample_type_id', 'sample_type')

    def __str__(self):
        return self.sample_type

    def natural_key(self):
        return self.sample_type


class ContainerType(models.Model):
    container_type_id = models.AutoField(primary_key=True, verbose_name="Container Type Id")
    container_type = models.CharField(unique=True, max_length=40, verbose_name="Container Type")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    child_sample_creation = models.BooleanField(default=False, verbose_name="Child Sample Creation")
    gen_slide_seq = models.BooleanField(default=False, verbose_name="Generate Slide Sequence")
    gen_block_or_cassette_seq = models.BooleanField(default=False,
                                                    verbose_name="Generate Block Or Cassette Sequence")
    workflow_id = models.ForeignKey('workflows.Workflow', on_delete=models.RESTRICT, null=True, blank=True, verbose_name="Default Workflow")
    LIQUID_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No'),
    ]

    # other fields...
    is_liquid = models.CharField(
        max_length=10,
        choices=LIQUID_CHOICES, null=True, blank=True, verbose_name="Is Liquid"
    )
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Container Type")
        verbose_name_plural = _("Container Types")
        unique_together = ('container_type_id', 'container_type')

    def __str__(self):
        return self.container_type

    def natural_key(self):
        return self.container_type


class SampleTypeContainerType(models.Model):
    sampletype_containertype_id = models.AutoField(primary_key=True, verbose_name="SampleType_ContainerType_Id")
    sample_type_id = models.ForeignKey(SampleType, on_delete=models.RESTRICT, null=True, verbose_name="Sample Type")
    container_type_id = models.ForeignKey(ContainerType, on_delete=models.RESTRICT, null=True,
                                          verbose_name="Container Type Id")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Sample Type Container Type Map"
        verbose_name_plural = 'Sample Type'
        unique_together = ('sample_type_id', 'container_type_id')

    def __str__(self):
        return str(self.sampletype_containertype_id)


class ConsumableType(models.Model):
    consumable_type_id = models.AutoField(primary_key=True, verbose_name="Consumable Type Id")
    consumable_type = models.CharField(unique=True, null=False, max_length=80, verbose_name="Consumable Type")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Consumable Type"
        verbose_name_plural = 'Consumable Types'

    def __str__(self):
        return str(self.consumable_type)


auditlog.register(SampleType)
auditlog.register(ContainerType)
auditlog.register(SampleTypeContainerType)
auditlog.register(ConsumableType)
