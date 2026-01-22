from django.db import models
from django.utils.translation import gettext_lazy as _
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from sample.models import Sample


class CytoWorkflow(Sample):
    stain_date = models.DateTimeField(verbose_name=_('Stain DateTime'), null=True, blank=True)

    class Meta:
        verbose_name = _("Cyto Sample")
        verbose_name_plural = _("Cyto Samples")

    def __str__(self):
        return str(self.sample_id)

    def natural_key(self):
        return self.sample_id


auditlog.register(CytoWorkflow)
