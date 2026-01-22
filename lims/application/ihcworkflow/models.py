from django.db import models
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from sample.models import Sample


class IhcWorkflow(Sample):
    stain_startdt = models.DateTimeField(verbose_name=_('Stain Start DateTime'), null=True, blank=True)
    stain_enddt = models.DateTimeField(verbose_name=_('Stain End DateTime'), null=True, blank=True)
    image_startdt = models.DateTimeField(verbose_name=_('Image Start DateTime'), null=True, blank=True)
    image_enddt = models.DateTimeField(verbose_name=_('Image'
                                                      'End DateTime'), null=True, blank=True)
    image_qcstatus = models.CharField(max_length=20, null=True, blank=True, verbose_name="Image QC Status")
    image_qcdate = models.DateTimeField(verbose_name=_('Image QC DateTime'), null=True, blank=True)
    is_recordvisible = models.BooleanField(null=True, verbose_name="Is visible")
    staining_status = models.CharField(max_length=50, null=True, blank=True, verbose_name="Staining Status")
    staining_technique = models.CharField(max_length=50, null=True, blank=True, verbose_name="Staining Technique")

    class Meta:
        verbose_name = _("IHC Sample")
        verbose_name_plural = _("IHC Samples")

    def __str__(self):
        return str(self.sample_id)

    def natural_key(self):
        return self.sample_id


auditlog.register(IhcWorkflow)
