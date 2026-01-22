from django.core.exceptions import ValidationError
from import_export import resources, fields
import json

from masterdata.models import AccessionType
from tests.models import WorkflowStepConfigField, TestWorkflowStepActionMap
from workflows.models import Workflow, WorkflowStep, ModalityModelMap


class WorkflowResource(resources.ModelResource):
    step_dept_values = fields.Field(column_name='step_dept_values')
    step_config_values = fields.Field(column_name='step_config_values')
    step_action_values = fields.Field(column_name='step_action_values')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_step_dept_values_map = {}
        self.workflow_step_config_map = {}
        self.workflow_step_action_map = {}

    class Meta:
        model = Workflow
        import_id_fields = ('workflow_name',)
        fields = (
            'workflow_name',
            'description',
            'methodology',
            'step_dept_values',
            'step_config_values',
            'step_action_values',
        )

    def dehydrate_step_dept_values(self, obj):
        """
        Exports the related WorkflowStep objects as a JSON array of dictionaries.
        """
        steps_data = []
        workflow_steps = obj.workflowstep_set.order_by('pk')

        for step_dept in workflow_steps:
            steps_data.append({
                "step_id": step_dept.step_id,
                "step_no": step_dept.step_no,
                "department": step_dept.department,
                "workflow_type": step_dept.workflow_type,
            })
        return json.dumps(steps_data)

    def dehydrate_step_config_values(self, obj):
        data = []
        for step in obj.workflowstep_set.all():
            configs = WorkflowStepConfigField.objects.filter(workflow_step_id=step)
            for cfg in configs:
                data.append({
                    "step_id": step.step_id,
                    "step_no": step.step_no,
                    "model": cfg.model,
                    "field_id": cfg.field_id,
                })
        return json.dumps(data)

    def dehydrate_step_action_values(self, obj):
        data = []
        for step in obj.workflowstep_set.all():
            actions = TestWorkflowStepActionMap.objects.filter(workflow_step_id=step)
            for act in actions:
                data.append({
                    "step_id": step.step_id,
                    "step_no": step.step_no,
                    "action": act.action,
                    "action_method": act.action_method,
                    "sequence": act.sequence,
                })
        return json.dumps(data)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store the 'step_dept_values' JSON for later processing in after_import,
        then remove it from the row to prevent direct import errors.
        """
        if row.get('step_dept_values'):
            self.workflow_step_dept_values_map[row['workflow_name']] = row['step_dept_values']

        if row.get('step_config_values'):
            self.workflow_step_config_map[row['workflow_name']] = row['step_config_values']

        if row.get('step_action_values'):
            self.workflow_step_action_map[row['workflow_name']] = row['step_action_values']

        for k in ('step_dept_values', 'step_config_values', 'step_action_values'):
            row.pop(k, None)

        return super().import_row(row, instance_loader, **kwargs)

    def _get_workflow_step(self, workflow, step_id, step_no):
        return WorkflowStep.objects.filter(
            workflow_id=workflow,
            step_id=step_id,
            step_no=step_no
        ).first()

    def after_import(self, dataset, result, **kwargs):
        """
        After Workflow objects are imported/updated, process the related WorkflowStep data.
        This method will create new WorkflowStep objects or update existing ones.
        """
        imported_data = dataset.dict
        for row in imported_data:
            workflow_name = row['workflow_name']
            try:
                workflow_detail = Workflow.objects.get(workflow_name=workflow_name)
            except Workflow.DoesNotExist:
                print(f"Warning: Workflow '{workflow_name}' not found after import. Skipping WorkflowStep processing.")
                continue

            step_dept_values_json = self.workflow_step_dept_values_map.get(workflow_name)

            if step_dept_values_json:
                try:
                    step_dept_sets = json.loads(step_dept_values_json)

                    for prop_dict in step_dept_sets:
                        step_id = prop_dict.get("step_id")
                        step_no = prop_dict.get("step_no")
                        department = prop_dict.get("department")
                        workflow_type = prop_dict.get("workflow_type")

                        if step_id is None or step_no is None:
                            print(f"Skipping WorkflowStep for '{workflow_name}' due to missing 'step_id' or 'step_no'. Data: {prop_dict}")
                            continue

                        existing_step = WorkflowStep.objects.filter(
                            workflow_id=workflow_detail,
                            step_id=step_id,
                            step_no=step_no,
                        ).first()

                        if existing_step:
                            existing_step.department = department
                            existing_step.workflow_type = workflow_type
                            existing_step.save()
                        else:
                            WorkflowStep.objects.create(
                                workflow_id=workflow_detail,
                                step_id=step_id,
                                step_no=step_no,
                                department=department,
                                workflow_type=workflow_type,
                            )
                except json.JSONDecodeError as e:
                    print(f"Error parsing step_dept_values JSON for Workflow '{workflow_name}': {e}")
                except Exception as e:
                    print(f"An unexpected error occurred processing WorkflowStep for Workflow '{workflow_name}': {e}")

            config_json = self.workflow_step_config_map.get(workflow_name)
            if config_json:
                for cfg in json.loads(config_json):
                    step = self._get_workflow_step(
                        workflow_detail,
                        cfg.get("step_id"),
                        cfg.get("step_no")
                    )
                    if not step:
                        continue

                    WorkflowStepConfigField.objects.update_or_create(
                        workflow_step_id=step,
                        model=cfg.get("model"),
                        field_id=cfg.get("field_id"),
                        defaults={}
                    )

            action_json = self.workflow_step_action_map.get(workflow_name)
            if action_json:
                for act in json.loads(action_json):
                    step = self._get_workflow_step(
                        workflow_detail,
                        act.get("step_id"),
                        act.get("step_no")
                    )
                    if not step:
                        continue

                    TestWorkflowStepActionMap.objects.update_or_create(
                        workflow_step_id=step,
                        action=act.get("action"),
                        action_method=act.get("action_method"),
                        defaults={
                            "sequence": act.get("sequence")
                        }
                    )

        return super().after_import(dataset, result, **kwargs)


class ModalityModelMapResource(resources.ModelResource):
    modality = fields.Field(
        column_name='modality',
        attribute='modality'
    )
    model = fields.Field(
        column_name='model',
        attribute='model'
    )

    class Meta:
        model = ModalityModelMap
        import_id_fields = ('modality', 'model')
        fields = ('modality', 'model',)
        skip_unchanged = True

    def before_import_row(self, row, **kwargs):
        """
        Ensure that the incoming 'modality' actually exists as a Workflow.workflow_name.
        """
        mod = row.get('modality')
        if mod and not Workflow.objects.filter(workflow_name=mod).exists():
            raise ValidationError(
                f"Modality '{mod}' is not a valid Workflow name."
            )
        return super().before_import_row(row, **kwargs)