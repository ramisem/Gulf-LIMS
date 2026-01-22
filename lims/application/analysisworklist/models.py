from auditlog.registry import auditlog
from accessioning.models import Accession
from analysis.models import Attachment


class AccessionReportsWrapper(Accession):
    class Meta:
        proxy = True
        verbose_name = "Pending Case"
        verbose_name_plural = "Pending Cases"


class AccessionHistoricalReportsWrapper(Accession):
    class Meta:
        proxy = True
        verbose_name = "Historical Case"
        verbose_name_plural = "Historical Cases"


class AttachmentMergeReport(Attachment):
    class Meta:
        proxy = True
        verbose_name = "Signed Report"
        verbose_name_plural = "Signed Reports"


auditlog.register(AccessionReportsWrapper)
auditlog.register(AccessionHistoricalReportsWrapper)
auditlog.register(AttachmentMergeReport)
