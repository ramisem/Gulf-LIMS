from _decimal import InvalidOperation, Decimal
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

import security
from configuration.models import ReferenceType
from controllerapp import settings
from labresource.models import InstrumentType
from process.models import SampleType, ConsumableType, ContainerType
from util.util import UtilClass
from workflows.models import Workflow, WorkflowStep


# Create your models here.


class Test(models.Model):
    test_id = models.AutoField(primary_key=True, verbose_name="Test Id")
    test_name = models.CharField(max_length=40, blank=False, null=False, verbose_name="Test Name")
    version = models.IntegerField(blank=False, null=False, verbose_name="Version")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    smear_process = models.CharField(max_length=200, blank=True, null=True, verbose_name="Smear Process")
    active_flag = models.CharField(max_length=10, blank=True, null=True, verbose_name="Active Flag")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Test")
        verbose_name_plural = _("Tests")
        constraints = [
            models.UniqueConstraint(fields=['test_name', 'version'], name='unique_test_name_version')
        ]

    def __str__(self):
        return self.test_name

    def natural_key(self):
        return self.test_name

    def save(self, *args, **kwargs):
        required_reftype = getattr(settings, 'APPLICATION_YES_NO_OPTION_REFERENCE', '')
        valid_choices = [choice[0] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        valid_display_choices = [choice[1] for choice in UtilClass.get_refvalues_for_field(required_reftype)]
        if not self.active_flag or self.active_flag not in valid_choices:
            raise ValueError(f"Entered value for Active flag is invalid. Valid options are {valid_display_choices}.")
        super().save(*args, **kwargs)


class Units(models.Model):
    unit_id = models.AutoField(primary_key=True, verbose_name="Unit Id")
    unit = models.CharField(unique=True, max_length=40, verbose_name="Unit")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")

    def __str__(self):
        return self.unit

    def natural_key(self):
        return self.unit


class Analyte(models.Model):
    analyte_id = models.AutoField(primary_key=True, verbose_name="Analyte Id")
    analyte = models.CharField(unique=True, max_length=40, verbose_name="Analyte")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")

    unit_id = models.ForeignKey(Units, null=True, blank=True, on_delete=models.RESTRICT,
                                verbose_name="Unit")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("analyte")
        verbose_name_plural = _("analytes")
        constraints = [
            models.UniqueConstraint(fields=['analyte_id', 'analyte'], name='unique_analyte_id_analyte')
        ]

    def __str__(self):
        return self.analyte

    def natural_key(self):
        return self.analyte


class ICDCode(models.Model):
    icd_code_id = models.AutoField(primary_key=True, verbose_name="ICD Code Id")
    icd_code = models.CharField(unique=True, max_length=40, verbose_name="ICD Code")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("ICD Codes")
        verbose_name_plural = _("ICD Codes")

    def __str__(self):
        return self.icd_code

    def natural_key(self):
        return self.icd_code


class CPTCode(models.Model):
    cpt_code_id = models.AutoField(primary_key=True, verbose_name="CPT Code Id")
    cpt_code = models.CharField(unique=True, max_length=40, verbose_name="CPT Code")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Description")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("CPT Codes")
        verbose_name_plural = _("CPT Codes")

    def __str__(self):
        return self.cpt_code

    def natural_key(self):
        return self.cpt_code




class TestAnalyte(models.Model):
    OPERATOR_CHOICES = [
        ('==', '='),
        ('<', '<'),
        ('<=', '<='),
        ('>', '>'),
        ('>=', '>='), ]

    CONDITION_CHOICES = [
        ('and', 'AND'),
        ('or', 'OR'), ]

    test_analyte_id = models.AutoField(primary_key=True, verbose_name="Test Analyte Id")
    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test")
    analyte_id = models.ForeignKey(Analyte, on_delete=models.RESTRICT, null=True, verbose_name="Analyte")
    # UI Rendering related fields
    input_mode = models.CharField(max_length=80, null=True, blank=True, verbose_name="Input Mode")
    data_type = models.CharField(max_length=80, null=True, blank=True, verbose_name="Data Type")
    dropdown_reference_type = models.ForeignKey(ReferenceType, on_delete=models.SET_NULL, null=True, blank=True,
                                                verbose_name="Dropdown Reftype")
    dropdown_sql = models.TextField(null=True, blank=True, verbose_name="Dropdown Sql")

    # Specification related fields
    decimal_precision = models.IntegerField(null=True, blank=True, verbose_name="Decimal Precision")
    operator1 = models.CharField(null=True, blank=True, max_length=40, choices=OPERATOR_CHOICES,
                                 verbose_name="Operator-1")
    value1 = models.DecimalField(null=True, blank=True, max_digits=10, decimal_places=2, verbose_name="Value-1", )
    condition = models.CharField(null=True, blank=True, max_length=40, choices=CONDITION_CHOICES,
                                 verbose_name="Condition")
    operator2 = models.CharField(null=True, blank=True, max_length=40, choices=OPERATOR_CHOICES,
                                 verbose_name="Operator-2")
    value2 = models.DecimalField(null=True, blank=True, max_digits=10, decimal_places=2, verbose_name="Value-2", )
    value_text = models.TextField(null=True, blank=True, max_length=80,
                                  verbose_name="Text Value",
                                  help_text="Enter the string value to use for comparison. For multiple allowed values, separate each with a semicolon (;). Example: 'Positive;Negative;Inconclusive'.")
    unit = models.ForeignKey(Units, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="Unit")

    is_reportable = models.BooleanField(default=True, verbose_name="Is Reportable?")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Test Analyte"
        verbose_name_plural = 'Analytes'
        unique_together = ('test_id', 'analyte_id')

    def __str__(self):
        return str(self.test_analyte_id)

    def evaluate_condition1(self, input_value):
        return eval(f"{input_value} {self.operator1} {self.value1}")

    def evaluate_condition2(self, input_value):
        return eval(f"{input_value} {self.operator2} {self.value2}")

    def validate_value_type(self, value):
        if not self.data_type:
            return True, None

        plain_value = strip_tags(str(value)).strip()

        if self.data_type.lower() == 'integer':
            try:
                # Must not allow decimals here
                if '.' in plain_value:
                    return False, f"Value must be an integer for analyte '{self.analyte_id}'."
                int(plain_value)
                return True, None
            except (ValueError, TypeError):
                return False, f"Value must be an integer for analyte '{self.analyte_id}'."

        if self.data_type.lower() == 'decimal':
            try:
                # This will allow values like "10" and "10.25"
                Decimal(plain_value)
                return True, None
            except (InvalidOperation, ValueError, TypeError):
                return False, f"Value must be a decimal number for analyte '{self.analyte_id}'."

        return True, None  # Allow other types silently

    def validate_analyte_value(self, value):
        # Strip HTML if value_text is being validated
        if self.value_text:
            plain_value = strip_tags(str(value)).strip()
            allowed_values = [v.strip() for v in self.value_text.split(';') if v.strip()]
            return plain_value in allowed_values

        if self.operator1 and self.value1 is not None:
            if not self.condition:
                return self.evaluate_condition1(value)
            if self.operator2 and self.value2 is not None:
                if self.condition == 'or':
                    return self.evaluate_condition1(value) or self.evaluate_condition2(value)
                else:  # 'and'
                    return self.evaluate_condition1(value) and self.evaluate_condition2(value)
        return True  # fallback if no rule defined


class TestCPTCodeMap(models.Model):
    test_cptcode_map_id = models.AutoField(primary_key=True, verbose_name="Test CPTCode Id")

    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test Id")
    cpt_code_id = models.ForeignKey(CPTCode, on_delete=models.RESTRICT, null=True, verbose_name="CPTCode Id")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Test CPT Code Map"
        verbose_name_plural = 'CPT Codes'
        unique_together = ('test_id', 'cpt_code_id')

    def __str__(self):
        return str(self.test_cptcode_map_id)


class TestWorkflowStep(models.Model):
    test_workflow_step_id = models.AutoField(primary_key=True, verbose_name="Test Workflow Step Id")

    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test")
    workflow_id = models.ForeignKey(Workflow, on_delete=models.RESTRICT, null=True, verbose_name="Workflow")
    workflow_step_id = models.ForeignKey(WorkflowStep, on_delete=models.RESTRICT, null=True, verbose_name="Step")
    sample_type_id = models.ForeignKey(SampleType, on_delete=models.RESTRICT, null=True, verbose_name="Sample Type")
    container_type = models.ForeignKey(ContainerType, on_delete=models.RESTRICT, null=True,
                                       verbose_name="Container Type")

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
        verbose_name=_('Created DateTime'), null=True, blank=True,
        help_text=_('In UTC'))

    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Test Workflow Step"
        verbose_name_plural = 'Test Workflow Steps'
        unique_together = ('test_id', 'workflow_id', 'workflow_step_id', 'sample_type_id', 'container_type')

    @property
    def step_no(self):
        if self.workflow_step_id:
            return self.workflow_step_id.step_no
        return ""

    @property
    def workflow_type(self):
        if self.workflow_step_id:
            return self.workflow_step_id.workflow_type
        return ""

    @property
    def version(self):
        if self.test_id:
            return self.test_id.version
        return ""

    def __str__(self):
        # return str(self.test_workflow_step_id)
        return f"{self.workflow_id} - {self.sample_type_id} - {self.container_type} - {self.workflow_step_id}"


class TestAttribute(models.Model):
    test_attribute_id = models.AutoField(primary_key=True, verbose_name="Test Attribute Id")
    test_attribute = models.CharField(max_length=80, verbose_name="Test Attribute")
    value = models.CharField(max_length=200, blank=True, null=True, verbose_name="Value")
    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test")
    test_workflow_step_id = models.ForeignKey(TestWorkflowStep, on_delete=models.RESTRICT, null=True,
                                              verbose_name="Test Workflow Step")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)

    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.RESTRICT,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Test Attribute")
        verbose_name_plural = _("Test Attributes")
        unique_together = ('test_id', 'test_workflow_step_id', 'test_attribute')

    def __str__(self):
        return self.test_attribute

    def natural_key(self):
        return self.test_attribute


class TestWFSTPInstrumentMap(models.Model):
    test_wf_stp_instrument_map_id = models.AutoField(primary_key=True,
                                                     verbose_name="Test Workflow Step Instrument Map Id")

    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test")
    workflow_id = models.ForeignKey(Workflow, on_delete=models.RESTRICT, null=True, verbose_name="Workflow")
    workflow_step_id = models.ForeignKey(WorkflowStep, on_delete=models.RESTRICT, null=True, verbose_name="Step")
    sample_type_id = models.ForeignKey(SampleType, on_delete=models.RESTRICT, null=True, verbose_name="Sample Type")
    container_type = models.ForeignKey(ContainerType, on_delete=models.RESTRICT, null=True,
                                       verbose_name="Container Type")
    instrument_type_id = models.ForeignKey(InstrumentType, on_delete=models.RESTRICT, null=True,
                                           verbose_name="Instrument Type")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Test Workflow Step Instrument"
        verbose_name_plural = 'Test Workflow Step Instruments'
        unique_together = ('test_id', 'workflow_id', 'workflow_step_id', 'sample_type_id', 'instrument_type_id')

    def __str__(self):
        return str(self.test_wf_stp_instrument_map_id)

    @property
    def step_no(self):
        if self.workflow_step_id:
            return self.workflow_step_id.step_no
        return ""

    @property
    def workflow_type(self):
        if self.workflow_step_id:
            return self.workflow_step_id.workflow_type
        return ""


class TestWFSTPConsumableMap(models.Model):
    test_wf_stp_consumable_map_id = models.AutoField(primary_key=True,
                                                     verbose_name="Test Workflow Step Consumable Map Id")

    test_id = models.ForeignKey(Test, on_delete=models.RESTRICT, null=True, verbose_name="Test")
    workflow_id = models.ForeignKey(Workflow, on_delete=models.RESTRICT, null=True, verbose_name="Workflow")
    workflow_step_id = models.ForeignKey(WorkflowStep, on_delete=models.RESTRICT, null=True, verbose_name="Step")
    sample_type_id = models.ForeignKey(SampleType, on_delete=models.RESTRICT, null=True, verbose_name="Sample Type")
    container_type = models.ForeignKey(ContainerType, on_delete=models.RESTRICT, null=True,
                                       verbose_name="Container Type")
    consumable_type_id = models.ForeignKey(ConsumableType, on_delete=models.RESTRICT, null=True,
                                           verbose_name="Consumable Type")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Test Workflow Step Consumable"
        verbose_name_plural = 'Test Workflow Step Consumables'
        unique_together = ('test_id', 'workflow_id', 'workflow_step_id', 'sample_type_id', 'consumable_type_id')

    def __str__(self):
        return str(self.test_wf_stp_consumable_map_id)

    @property
    def step_no(self):
        if self.workflow_step_id:
            return self.workflow_step_id.step_no
        return ""

    @property
    def workflow_type(self):
        if self.workflow_step_id:
            return self.workflow_step_id.workflow_type
        return ""


class WorkflowStepConfigField(models.Model):
    ws_config_field_id = models.AutoField(primary_key=True, verbose_name="Workflow Step Config Field Id")
    model = models.CharField(max_length=80, blank=True, null=True, verbose_name="Model")
    field_id = models.CharField(max_length=40, blank=False, null=False, verbose_name="Model Column ID")
    test_workflow_step_id = models.ForeignKey(TestWorkflowStep, on_delete=models.RESTRICT, null=True,
                                              verbose_name="Test Workflow Step")
    workflow_step_id = models.ForeignKey(WorkflowStep, null=True, blank=True,
                                         on_delete=models.RESTRICT,
                                         verbose_name="Workflow Step Id")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True,
        help_text=_('In UTC'))

    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By")

    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Workflow Step Config Field"
        verbose_name_plural = "Workflow Step Config Fields"
        unique_together = ('test_workflow_step_id', 'model', 'field_id')

    def __str__(self):
        return str(self.ws_config_field_id)

    def natural_key(self):
        return str(self.ws_config_field_id)


class TestWorkflowStepActionMap(models.Model):
    testwflwstepmap_id = models.ForeignKey(TestWorkflowStep, max_length=40, null=True, blank=True,
                                           on_delete=models.SET_NULL,
                                           verbose_name="Model Id")
    action = models.CharField(max_length=200, null=True, blank=True, verbose_name="Action")
    action_method = models.CharField(max_length=200, null=True, blank=True, verbose_name="Action Method")
    sequence = models.IntegerField(verbose_name="Sequence No")
    workflow_step_id = models.ForeignKey(WorkflowStep, max_length=40, null=True, blank=True,
                                           on_delete=models.SET_NULL,
                                           verbose_name="Workflow Step Id")
    created_dt = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created DateTime'), null=True, blank=True)
    created_by = models.ForeignKey(security.models.User, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Created By")
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("Test Workflow Action")
        verbose_name_plural = _("Test Workflow Actions")
        unique_together = ('testwflwstepmap_id', 'action', 'action_method')

    def __str__(self):
        return str(self.id)


auditlog.register(Test)
auditlog.register(Units)
auditlog.register(Analyte)
auditlog.register(ICDCode)
auditlog.register(CPTCode)
auditlog.register(TestAnalyte)
auditlog.register(TestCPTCodeMap)
auditlog.register(TestAttribute)
auditlog.register(TestWorkflowStep)
auditlog.register(TestWFSTPInstrumentMap)
auditlog.register(TestWFSTPConsumableMap)
auditlog.register(TestWorkflowStepActionMap)
