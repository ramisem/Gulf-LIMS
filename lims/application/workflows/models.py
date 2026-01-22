from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _

import security
from masterdata.models import AccessionType
from controllerapp import settings
from util.util import UtilClass


class Workflow(models.Model):
    workflow_id = models.AutoField(primary_key=True, verbose_name="Workflow")
    workflow_name = models.CharField(max_length=40, blank=False, null=False, verbose_name="Workflow Name")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    methodology = models.CharField(max_length=200, blank=True, null=True, verbose_name="Methodology")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    accession_type = models.ForeignKey(AccessionType, null=True, blank=True, on_delete=models.RESTRICT,
                                       verbose_name="AccessionType")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Workflow"
        verbose_name_plural = 'Workflow'
        unique_together = ('workflow_name', 'methodology')

    def __str__(self):
        return str(self.workflow_name)


class WorkflowStep(models.Model):
    workflow_step_id = models.AutoField(primary_key=True, verbose_name="Workflow Step Id")
    workflow_id = models.ForeignKey(Workflow, on_delete=models.RESTRICT, null=True, verbose_name="Workflow")
    step_id = models.CharField(max_length=200, blank=False, null=False, verbose_name="Step")
    step_no = models.IntegerField(blank=False, null=False, verbose_name="Step Number")
    department = models.CharField(max_length=80, blank=False, null=False, verbose_name="Department")

    WORKFLOW_TYPE_CHOICES = [
        ('WetLab', 'Wet Lab'),
        ('DryLab', 'Dry lab'),
    ]
    workflow_type = models.CharField(max_length=40, choices=WORKFLOW_TYPE_CHOICES, blank=True, null=True,
                                     verbose_name="Workflow Type")

    BACKWARD_MOVEMENT_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No'),
    ]

    backward_movement = models.CharField(
        max_length=10,
        choices=BACKWARD_MOVEMENT_CHOICES,
        blank=True,
        null=True,
        verbose_name="Backward Movement"
    )

    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Workflow Step"
        verbose_name_plural = 'Workflow Steps'
        unique_together = ('workflow_id', 'step_id', 'step_no', 'department')

    def __str__(self):
        return str(self.step_id)

    def natural_key(self):
        return self.workflow_step_id

    def save(self, *args, **kwargs):
        required_reftype = getattr(settings, 'APPLICATION_DEPARTMENT_NAME_REFERENCE', '')
        valid_choices = [choice[0] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        valid_display_choices = [choice[1] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        if not self.department or self.department not in valid_choices:
            raise ValueError(
                f"Entered value {self.department} for Department is invalid. Valid options are {valid_display_choices}.")
        super().save(*args, **kwargs)


class ModalityModelMap(models.Model):
    modality_model_map_id = models.AutoField(primary_key=True, verbose_name="Modality Model Map ID")
    modality = models.CharField(max_length=40, verbose_name="Modality")
    model = models.CharField(max_length=40, verbose_name="Model")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Modality Model Map"
        verbose_name_plural = 'Modality Model Maps'
        unique_together = ('modality', 'model')

    def __str__(self):
        return str(self.modality_model_map_id)

    def save(self, *args, **kwargs):
        if not Workflow.objects.filter(workflow_name=self.modality).exists():
            raise ValueError(f"Invalid modality '{self.modality}'. Must be an existing Workflow name.")

        required_reftype = getattr(settings, 'APPLICATION_MODEL_REFERENCE', '')
        valid_choices = [choice[0] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        valid_display_choices = [choice[1] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        if not self.model or self.model not in valid_choices:
            raise ValueError(f"Entered value for modality is invalid. Valid options are {valid_display_choices}.")
        super().save(*args, **kwargs)


auditlog.register(Workflow)
auditlog.register(WorkflowStep)
auditlog.register(ModalityModelMap)
