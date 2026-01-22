from accessioning.models import Accession, BioPharmaAccession
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from django.db import models
import security
from auditlog.models import AuditlogHistoryField


class AccessionTemplate(Accession):
    class Meta:
        proxy = True
        verbose_name = _("Accession Template")
        verbose_name_plural = _("Accession Templates")

    def __str__(self):
        return str(self.accession_id)

    def natural_key(self):
        return self.accession_id


class BioPharmaAccessionTemplate(BioPharmaAccession):
    class Meta:
        proxy = True
        verbose_name = _("Pharma Accession Template")
        verbose_name_plural = _("Pharma Accession Templates")


class PathologyTemplate(models.Model):
    pathology_temp_id = models.AutoField(primary_key=True, verbose_name="Pathology Template Id")
    dx_code = models.CharField(verbose_name="Diagnosis Code", max_length=80, blank=False, null=False, unique=True)
    diagnosis = models.TextField(verbose_name="Diagnosis", null=True, blank=True)
    microscopic_desc = models.TextField(verbose_name="Microscopic Desc", null=True, blank=True)
    category = models.CharField(verbose_name="Category", null=True, blank=True, max_length=80)

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Pathology Template")
        verbose_name_plural = _("Pathology Templates")

    def __str__(self):
        return self.dx_code

    def natural_key(self):
        return self.dx_code


class GrossCodeTemplate(models.Model):
    gross_code_temp_id = models.AutoField(primary_key=True, verbose_name="GrossCode Template Id")
    gross_code = models.CharField(verbose_name="Gross Code", max_length=80, blank=False, null=False, unique=True)
    gross_description = models.TextField(verbose_name="Gross Description", null=True, blank=True)

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("GrossCode Template")
        verbose_name_plural = _("GrossCode Templates")

    def __str__(self):
        return self.gross_code

    def natural_key(self):
        return self.gross_code

class Macros(models.Model):
    macros_id = models.AutoField(primary_key=True, verbose_name="Macros Id")
    macros_name = models.CharField(
        verbose_name="Macros Name",
        max_length=40,
        unique=True,
        blank=False,
        null=False
    )
    actual_content = models.TextField(
        verbose_name="Actual Content",
        null=True,
        blank=True
    )  # CLOB equivalent
    macros_type = models.CharField(
        verbose_name="Macros Type",
        max_length=20,
        null=True,
        blank=True
    )

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'),
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        security.models.User,
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        verbose_name="Created By"
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Macros")
        verbose_name_plural = _("Macros")

    def __str__(self):
        return self.macros_name

    def natural_key(self):
        return self.macros_name



auditlog.register(AccessionTemplate)
auditlog.register(PathologyTemplate)
auditlog.register(GrossCodeTemplate)
auditlog.register(Macros)

