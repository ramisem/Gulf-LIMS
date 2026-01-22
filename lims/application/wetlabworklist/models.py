from auditlog.registry import auditlog

from accessioning.models import Accession


class AccessionSampleWrapper(Accession):
    class Meta:
        proxy = True
        verbose_name = "Enterprise Worklist"
        verbose_name_plural = "Enterprise Worklist"


class AccessionIHCWrapper(Accession):
    class Meta:
        proxy = True
        verbose_name = "IHC Worklist"
        verbose_name_plural = "IHC Worklist"


auditlog.register(AccessionSampleWrapper)
auditlog.register(AccessionIHCWrapper)
