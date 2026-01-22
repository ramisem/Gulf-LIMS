from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _

import security


class ReferenceType(models.Model):
    reference_type_id = models.AutoField(primary_key=True, verbose_name="Reference_Type_Id")
    name = models.CharField(unique=True, max_length=40, verbose_name="Name")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    is_system_level = models.BooleanField(default=False, verbose_name="System Level")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Reference Type"
        verbose_name_plural = 'Reference Type'

    def __str__(self):
        return str(self.name)


class RefValues(models.Model):
    ref_value_id = models.AutoField(primary_key=True, verbose_name="Ref_Value_id")
    value = models.CharField(max_length=80, verbose_name="Value")
    display_value = models.CharField(max_length=200, verbose_name="Display Value")
    reftype_id = models.ForeignKey(ReferenceType, on_delete=models.RESTRICT, null=True, verbose_name="Reference Type")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "RefValues"
        verbose_name_plural = 'RefValues'
        unique_together = ('reftype_id', 'value')

    def __str__(self):
        return self.display_value


auditlog.register(ReferenceType)
auditlog.register(RefValues)
