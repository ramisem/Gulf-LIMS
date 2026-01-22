from auditlog.models import LogEntryManager, LogEntry
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class ArchivedAuditLog(models.Model):
    class Action:
        CREATE = 0
        UPDATE = 1
        DELETE = 2
        ACCESS = 3

        choices = (
            (CREATE, _("create")),
            (UPDATE, _("update")),
            (DELETE, _("delete")),
            (ACCESS, _("access")),
        )

    audit_sequence = models.IntegerField()
    content_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("content type"),
    )
    object_pk = models.CharField(
        db_index=True, max_length=255, verbose_name=_("object pk")
    )
    object_id = models.BigIntegerField(
        blank=True, db_index=True, null=True, verbose_name=_("object id")
    )
    action = models.PositiveSmallIntegerField(
        choices=Action.choices, verbose_name=_("action"), db_index=True
    )
    changes = models.TextField(blank=True, verbose_name=_("change message"))
    actor = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
        verbose_name=_("actor"),
    )
    remote_addr = models.GenericIPAddressField(
        blank=True, null=True, verbose_name=_("remote address")
    )
    timestamp = models.DateTimeField(
        db_index=True, auto_now_add=True, verbose_name=_("timestamp")
    )

    objects = LogEntryManager()

    class Meta:
        get_latest_by = "timestamp"
        ordering = ["-timestamp"]
        verbose_name = _("Archived data log entry")
        verbose_name_plural = _("Archived data log entries")


@receiver(post_save, sender=LogEntry, dispatch_uid='save_logentry_signal')
@receiver(pre_delete, sender=LogEntry, dispatch_uid='delete_logentry_signal')
def archive_audit_logs(sender, instance, **kwargs):
    if (kwargs.get('signal') in [pre_delete]) or (kwargs.get('created', False) and instance.action == 2):
        archived_log = ArchivedAuditLog()
        archived_log.action = instance.action
        archived_log.timestamp = instance.timestamp
        archived_log.object_id = instance.object_id
        archived_log.object_pk = instance.object_pk
        archived_log.actor_id = instance.actor_id
        archived_log.object_repr = instance.object_repr
        archived_log.remote_addr = instance.remote_addr
        archived_log.changes = instance.changes
        archived_log.content_type_id = instance.content_type_id
        archived_log.audit_sequence = instance.id
        archived_log.save()
