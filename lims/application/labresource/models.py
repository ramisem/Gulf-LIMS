from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _

import security


class InstrumentType(models.Model):
    instrument_type_id = models.AutoField(primary_key=True, verbose_name="Instrument Type Id")
    instrument_type = models.CharField(unique=True, max_length=40, blank=False, null=False,
                                       verbose_name="Instrument Type")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Instrument Type"
        verbose_name_plural = 'Instrument Types'

    def __str__(self):
        return str(self.instrument_type)


class InstrumentModel(models.Model):
    instrument_model_id = models.AutoField(primary_key=True, verbose_name="Instrument Model Id")
    instrument_model = models.CharField(max_length=40, blank=False, null=False,
                                        verbose_name="Instrument Model")
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.RESTRICT, null=True,
                                        verbose_name="Instrument Type")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Instrument Model"
        verbose_name_plural = 'Instrument Models'
        unique_together = ('instrument_model', 'instrument_type')

    def __str__(self):
        return str(self.instrument_model)


auditlog.register(InstrumentType)
auditlog.register(InstrumentModel)
