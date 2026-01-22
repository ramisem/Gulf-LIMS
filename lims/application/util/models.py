from django.db import models
import security
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.utils.translation import gettext_lazy as _


class SequenceGen(models.Model):
    model_id = models.CharField(max_length=40, verbose_name="Model Id")
    prefix_id = models.CharField(max_length=100, verbose_name="Prefix Id")
    seq_no = models.IntegerField(verbose_name="Sequence No")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Sequence Gen")
        verbose_name_plural = _("Sequence Gen")
        unique_together = ('model_id', 'prefix_id')

    def __str__(self):
        return str(self.id)


auditlog.register(SequenceGen)
