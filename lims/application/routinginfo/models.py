from django.db import models

from analysis.models import ReportOption
from security.models import Department, User
from sample.models import Sample
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.utils.translation import gettext_lazy as _


class RoutingInfo(models.Model):
    routing_info_id = models.AutoField(primary_key=True, verbose_name="Routing Info Id")
    sample_id = models.ForeignKey(Sample, on_delete=models.RESTRICT, null=True, blank=True,
                                  verbose_name="Sample Id")
    report_option_id = models.ForeignKey(ReportOption, on_delete=models.RESTRICT, null=True, blank=True,
                                         verbose_name="Report Option Id")
    from_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="From Step")
    to_step = models.CharField(max_length=40, null=True, blank=True, verbose_name="To Step")
    from_department = models.ForeignKey(Department, on_delete=models.RESTRICT, null=True, blank=True,
                                        related_name="FromDept",
                                        verbose_name="From Department")
    to_department = models.ForeignKey(Department, on_delete=models.RESTRICT, null=True, blank=True,
                                      related_name="ToDept",
                                      verbose_name="To Department")
    from_user = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True, related_name="FromUser",
                                  verbose_name="From User")
    to_user = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True, related_name="ToUser",
                                verbose_name="To User")
    from_storage = models.CharField(max_length=40, null=True, blank=True, verbose_name="From Storage")
    to_storage = models.CharField(max_length=40, null=True, blank=True,
                                  verbose_name="To Storage")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=False, blank=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        null=False,
        blank=False,
        related_name="RoutingCreatedBy",
        verbose_name="Created By"
    )

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Routing Info")
        verbose_name_plural = _("Routing Info")

    def __str__(self):
        return str(self.routing_info_id)


auditlog.register(RoutingInfo)
