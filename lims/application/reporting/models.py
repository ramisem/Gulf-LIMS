from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _

import security
from process.models import ContainerType


class LabelMethod(models.Model):
    label_method_id = models.AutoField(primary_key=True, verbose_name="Label Method Id")
    label_method_name = models.CharField(max_length=40, verbose_name="Label Method Name")
    label_method_version_id = models.IntegerField(verbose_name="Label Method Version Id")
    label_method_desc = models.CharField(max_length=80, verbose_name="Label Method Desc")
    s3bucket = models.BooleanField(verbose_name="S3 Bucket?", default=False,
                                   help_text="Enable this to store label files in S3 Bucket. "
                                             "Mention the bucket path in <b>Export Location</b> field below")
    export_location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Export Location")
    designer_format = models.CharField(max_length=200, verbose_name="Designer Format")
    is_bio_pharma_label = models.BooleanField(
        default=False,
        verbose_name="Is Pharma Label?"
    )
    label_query = models.TextField(verbose_name="Label Query")
    delimiter = models.CharField(max_length=20, blank=True, null=True, verbose_name="Delimiter")
    file_format = models.CharField(max_length=20, blank=True, null=True, verbose_name="Label File Format")
    show_header = models.BooleanField(verbose_name="Show Header in Label File", default=False,
                                      help_text="Enable this for File Based BarTender Printing")
    show_fields = models.BooleanField(verbose_name="Show Field Names in Label File", default=False,
                                      help_text="Enable this for File Based BarTender Printing")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        unique_together = ('label_method_name', 'label_method_version_id')
        verbose_name = "Label Method"
        verbose_name_plural = "Label Methods"

    def __str__(self):
        return str(self.label_method_name) + '-' + str(self.label_method_version_id)


class ContainerTypeLabelMethodMap(models.Model):
    container_type = models.ForeignKey(
        ContainerType,
        on_delete=models.RESTRICT,
        verbose_name="Container Type",
        related_name="label_methods"
    )
    label_method = models.ForeignKey(
        LabelMethod,
        on_delete=models.RESTRICT,
        verbose_name="Label Method",
        help_text="Select a label method name and version"
    )
    is_default = models.BooleanField(default=False, verbose_name="Default")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Container Type - Label Method Mapping"
        verbose_name_plural = "Container Type - Label Method Mappings"
        unique_together = ('container_type', 'label_method')

    def save(self, *args, **kwargs):
        # If setting is_default=True, ensure no other instance has it for the same combination
        if self.is_default:
            ContainerTypeLabelMethodMap.objects.filter(
                container_type=self.container_type,
                label_method=self.label_method,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.container_type} - {self.label_method}"


class ContainerTypePharmaLabelMethodMap(models.Model):
    """
    A separate mapping table for BioPharma-specific label methods.
    """
    container_type = models.ForeignKey(
        ContainerType,
        on_delete=models.RESTRICT,
        verbose_name="Container Type",
        related_name="pharma_label_methods" # Use a new related_name
    )
    label_method = models.ForeignKey(
        LabelMethod,
        on_delete=models.RESTRICT,
        verbose_name="BioPharma Label Method",
        help_text="Select a BioPharma label method name and version"
    )
    is_default = models.BooleanField(default=False, verbose_name="Default")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Container Type - Pharma Label Method Mapping"
        verbose_name_plural = "Container Type - Pharma Label Method Mappings"
        unique_together = ('container_type', 'label_method')

    def save(self, *args, **kwargs):
        # If setting is_default=True, ensure no other instance has it for the same combination
        if self.is_default:
            ContainerTypePharmaLabelMethodMap.objects.filter(
                container_type=self.container_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.container_type} - {self.label_method}"


class Printer(models.Model):
    printer_id = models.CharField(max_length=40, verbose_name="Printer ID", primary_key=True)
    printer_name = models.CharField(max_length=80, verbose_name="Printer Name")
    printer_path = models.CharField(max_length=120, verbose_name="Printer Path")
    communication_type = models.CharField(max_length=20, null=True, blank=True, verbose_name="Communication Type")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")

    class Meta:
        verbose_name = "Printer"
        verbose_name_plural = "Printers"

    def __str__(self):
        return self.printer_name


auditlog.register(LabelMethod)
auditlog.register(Printer)
