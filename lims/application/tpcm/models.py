from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _
import security
from accessioning.models import Accession

from security.models import Department, User, Site


# Create your models here.
class TechnicalProfessionalComponentMap(models.Model):
    technical_professional_component_map_id = models.AutoField(primary_key=True)

    accession_id = models.ForeignKey(Accession, on_delete=models.RESTRICT, null=False, blank=False,
                                     verbose_name="Accession ID")

    compontent_site_id = models.ForeignKey(Site, on_delete=models.RESTRICT, null=False, blank=False,
                                           verbose_name="Component Site ID")

    class ComponentType(models.TextChoices):
        TC = 'TC', 'Technical Component'
        TCA = 'TCA', 'Technical Component with Assistance'
        PC = 'PC', 'Professional Component'

    component_type = models.CharField(
        max_length=3,
        choices=ComponentType.choices,
        null=False,
        blank=False,
        verbose_name='Component Type'
    )
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="TPCMCreated By", related_name="tpcmcreated_by")
    mod_dt = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modified Date Time'), null=False, blank=False)
    mod_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="TPCMModifiedBy",
        verbose_name="Modified By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("TechnicalProfessionalComponentMap")
        verbose_name_plural = _("TechnicalProfessionalComponentMaps")
        unique_together = (
            'technical_professional_component_map_id',
            'accession_id',
            'compontent_site_id',
            'component_type'

        )

    def __str__(self):
        return str(self.technical_professional_component_map_id)

    def natural_key(self):
        return str(self.technical_professional_component_map_id)


auditlog.register(TechnicalProfessionalComponentMap)
