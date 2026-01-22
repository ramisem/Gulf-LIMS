import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from configuration.models import ReferenceType
from process.models import SampleType, ConsumableType, ContainerType
from labresource.models import InstrumentType
from tests.models import Test, Units, Analyte, ICDCode, CPTCode, TestAnalyte, TestCPTCodeMap, TestAttribute, \
    TestWorkflowStep, TestWFSTPInstrumentMap, TestWFSTPConsumableMap, TestWorkflowStepActionMap, WorkflowStepConfigField
from workflows.models import Workflow, WorkflowStep

logger = logging.getLogger(__name__)


class TestResource(resources.ModelResource):
    analytes = fields.Field(column_name='analytes')
    cpt_codes = fields.Field(column_name='cpt_codes')
    test_attributes = fields.Field(column_name='test_attributes')
    test_workflow_steps = fields.Field(column_name='test_workflow_steps')
    test_wf_stp_instrument_maps = fields.Field(column_name='test_wf_stp_instrument_maps')
    test_wf_stp_consumable_maps = fields.Field(column_name='test_wf_stp_consumable_maps')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_analyte_values_map = {}
        self.test_cptcode_values_map = {}
        self.test_test_attribute_values_map = {}
        self.test_test_workflow_step_values_map = {}
        self.test_test_wf_stp_instrument_map_values_map = {}
        self.test_test_wf_stp_consumable_map_values_map = {}

    class Meta:
        model = Test
        import_id_fields = ('test_name', 'version')
        fields = (
            'test_name',
            'version',
            'description',
            'active_flag',
            'smear_process',
            'analytes',
            'cpt_codes',
            'test_workflow_steps',
            'test_attributes',
            'test_wf_stp_instrument_maps',
            'test_wf_stp_consumable_maps',
        )

    def dehydrate_analytes(self, obj):
        analytes_data = []
        analytes_objects = obj.testanalyte_set.order_by('pk')
        for a in analytes_objects:
            analytes_data.append({
                "analyte": a.analyte_id.analyte if a.analyte_id else None,
                "input_mode": a.input_mode,
                "data_type": a.data_type,
                "dropdown_reference_type": a.dropdown_reference_type.name if a.dropdown_reference_type else None,
                "dropdown_sql": a.dropdown_sql,
                "decimal_precision": a.decimal_precision,
                "operator1": a.operator1,
                "value1": a.value1,
                "condition": a.condition,
                "operator2": a.operator2,
                "value2": a.value2,
                "value_text": a.value_text,
                "unit": a.unit.unit_name if a.unit else None,
                "is_reportable": a.is_reportable,
            })
        return json.dumps(analytes_data)

    def dehydrate_cpt_codes(self, obj):
        cpt_codes_data = []
        cpt_codes_object = obj.testcptcodemap_set.order_by('pk')
        for c in cpt_codes_object:
            cpt_codes_data.append({
                "cpt_code": c.cpt_code_id.cpt_code if c.cpt_code_id else None
            })
        return json.dumps(cpt_codes_data)

    def dehydrate_test_attributes(self, obj):
        test_attributes_data = []
        test_attibutes_object = obj.testattribute_set.order_by('pk')
        for c in test_attibutes_object:
            test_workflow_step_str = None
            if c.test_workflow_step_id:
                tws = c.test_workflow_step_id
                workflow_name = tws.workflow_id.workflow_name if tws.workflow_id else 'None'
                sample_type_name = tws.sample_type_id.sample_type if tws.sample_type_id else 'None'
                container_type_name = tws.container_type.container_type if tws.container_type else 'None'
                workflow_step_name = tws.workflow_step_id.step_id if tws.workflow_step_id else 'None'
                test_workflow_step_str = f"{workflow_name} - {sample_type_name} - {container_type_name} - {workflow_step_name}"

            test_attributes_data.append({
                "test_workflow_step": test_workflow_step_str,
                "test_attribute": c.test_attribute,
                "value": c.value,
            })
        return json.dumps(test_attributes_data)

    def dehydrate_test_workflow_steps(self, obj):
        test_workflow_steps_data = []
        test_workflow_steps_object = obj.testworkflowstep_set.order_by('pk')
        for c in test_workflow_steps_object:
            test_workflow_steps_data.append({
                "workflow": c.workflow_id.workflow_name if c.workflow_id else None,
                "sample_type": c.sample_type_id.sample_type if c.sample_type_id else None,
                "container_type": c.container_type.container_type if c.container_type else None,
                "step": c.workflow_step_id.step_id if c.workflow_step_id else None,
                "backward_movement": c.backward_movement,
            })
        return json.dumps(test_workflow_steps_data)

    def dehydrate_test_wf_stp_instrument_maps(self, obj):
        test_wf_stp_instrument_maps_data = []
        test_wf_stp_instrument_maps_object = obj.testwfstpinstrumentmap_set.order_by('pk')
        for c in test_wf_stp_instrument_maps_object:
            test_wf_stp_instrument_maps_data.append({
                "workflow": c.workflow_id.workflow_name if c.workflow_id else None,
                "step": c.workflow_step_id.step_id if c.workflow_step_id else None,
                "sample_type": c.sample_type_id.sample_type if c.sample_type_id else None,
                "container_type": c.container_type.container_type if c.container_type else None,
                "instrument": c.instrument_type_id.instrument_type if c.instrument_type_id else None,
            })
        return json.dumps(test_wf_stp_instrument_maps_data)

    def dehydrate_test_wf_stp_consumable_maps(self, obj):
        test_wf_stp_consumable_maps_data = []
        test_wf_stp_consumable_maps_object = obj.testwfstpconsumablemap_set.order_by('pk')
        for c in test_wf_stp_consumable_maps_object:
            test_wf_stp_consumable_maps_data.append({
                "workflow": c.workflow_id.workflow_name if c.workflow_id else None,
                "step": c.workflow_step_id.step_id if c.workflow_step_id else None,
                "sample_type": c.sample_type_id.sample_type if c.sample_type_id else None,
                "container_type": c.container_type.container_type if c.container_type else None,
                "consumable": c.consumable_type_id.consumable_type if c.consumable_type_id else None,
            })
        return json.dumps(test_wf_stp_consumable_maps_data)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        def handle_field_for_import(field_name, map_dict):
            field_value = row.get(field_name, None)
            if field_value:
                map_dict[row['test_name'] + "_ver" + row['version']] = field_value
            if field_name in row: # Defensive check before deleting
                del row[field_name]

        handle_field_for_import('analytes', self.test_analyte_values_map)
        handle_field_for_import('cpt_codes', self.test_cptcode_values_map)
        handle_field_for_import('test_attributes', self.test_test_attribute_values_map)
        handle_field_for_import('test_workflow_steps', self.test_test_workflow_step_values_map)
        handle_field_for_import('test_wf_stp_instrument_maps', self.test_test_wf_stp_instrument_map_values_map)
        handle_field_for_import('test_wf_stp_consumable_maps', self.test_test_wf_stp_consumable_map_values_map)

        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        imported_data = dataset.dict

        def get_test_instance(row_data):
            test_name = row_data['test_name']
            version = row_data['version']
            try:
                return Test.objects.get(test_name=test_name, version=version)
            except Test.DoesNotExist:
                print(f"Warning: Test '{test_name}' version '{version}' not found after import. Skipping related data processing.")
                return None
            except Exception as e:
                print(f"An unexpected error occurred while fetching Test '{test_name}' version '{version}': {e}. Skipping related data processing.")
                return None

        def process_related_data(test_instance, json_map, handler_func, map_key_suffix):
            map_key = test_instance.test_name + "_ver" + str(test_instance.version)
            json_string = json_map.get(map_key)
            if json_string:
                try:
                    data_list = json.loads(json_string)
                    for item_data in data_list:
                        handler_func(test_instance, item_data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for {map_key_suffix} for Test '{test_instance.test_name}' version '{test_instance.version}': {e}")
                except Exception as e:
                    print(f"An unexpected error occurred processing {map_key_suffix} for Test '{test_instance.test_name}' version '{test_instance.version}': {e}")

        def handle_cpt_codes_mapping(test_instance, item_data):
            cpt_code_name = item_data.get("cpt_code")
            if not cpt_code_name:
                print(f"Skipping CPTCodeMap for Test '{test_instance.test_name}' due to missing 'cpt_code'. Data: {item_data}")
                return

            try:
                cpt_code_obj = CPTCode.objects.get(cpt_code=cpt_code_name)
            except CPTCode.DoesNotExist:
                print(f"Warning: CPTCode '{cpt_code_name}' referenced in Test '{test_instance.test_name}' does not exist. Skipping this TestCPTCodeMap entry.")
                return

            existing_property = TestCPTCodeMap.objects.filter(
                test_id=test_instance,
                cpt_code_id=cpt_code_obj
            ).first()

            try:
                if existing_property:
                    existing_property.cpt_code_id = cpt_code_obj
                    existing_property.save()
                else:
                    TestCPTCodeMap.objects.create(
                        test_id=test_instance,
                        cpt_code_id=cpt_code_obj,
                    )
            except Exception as e:
                print(f"Error saving TestCPTCodeMap for Test '{test_instance.test_name}' and CPTCode '{cpt_code_name}': {e}")

        def handle_analytes_mapping(test_instance, item_data):
            analyte_name = item_data.get("analyte")
            if not analyte_name:
                print(f"Skipping TestAnalyte for Test '{test_instance.test_name}' due to missing 'analyte'. Data: {item_data}")
                return

            try:
                analyte_obj = Analyte.objects.get(analyte=analyte_name)
            except Analyte.DoesNotExist:
                print(f"Warning: Analyte '{analyte_name}' referenced in Test '{test_instance.test_name}' does not exist. Skipping this TestAnalyte entry.")
                return

            dropdown_reference_type_name = item_data.get("dropdown_reference_type")
            dropdown_reference_type_obj = None
            if dropdown_reference_type_name:
                try:
                    dropdown_reference_type_obj = ReferenceType.objects.get(name=dropdown_reference_type_name)
                except ReferenceType.DoesNotExist:
                    print(f"Warning: ReferenceType '{dropdown_reference_type_name}' for Analyte '{analyte_name}' does not exist.")

            unit_name = item_data.get("unit")
            unit_obj = None
            if unit_name:
                try:
                    unit_obj = Units.objects.get(unit_name=unit_name)
                except Units.DoesNotExist:
                    print(f"Warning: Unit '{unit_name}' for Analyte '{analyte_name}' does not exist.")

            existing_property = TestAnalyte.objects.filter(
                test_id=test_instance,
                analyte_id=analyte_obj
            ).first()

            input_mode = item_data.get("input_mode")
            data_type = item_data.get("data_type")
            dropdown_sql = item_data.get("dropdown_sql")
            decimal_precision = item_data.get("decimal_precision")
            operator1 = item_data.get("operator1")
            value1 = item_data.get("value1")
            condition = item_data.get("condition")
            operator2 = item_data.get("operator2")
            value2 = item_data.get("value2")
            value_text = item_data.get("value_text")
            is_reportable = item_data.get("is_reportable", False) # Default to False if not present

            try:
                if existing_property:
                    existing_property.analyte_id = analyte_obj
                    existing_property.input_mode = input_mode
                    existing_property.data_type = data_type
                    existing_property.dropdown_reference_type = dropdown_reference_type_obj
                    existing_property.dropdown_sql = dropdown_sql
                    existing_property.decimal_precision = decimal_precision
                    existing_property.operator1 = operator1
                    existing_property.value1 = value1
                    existing_property.condition = condition
                    existing_property.operator2 = operator2
                    existing_property.value2 = value2
                    existing_property.value_text = value_text
                    existing_property.unit = unit_obj
                    existing_property.is_reportable = is_reportable
                    existing_property.save()
                else:
                    TestAnalyte.objects.create(
                        test_id=test_instance,
                        analyte_id=analyte_obj,
                        input_mode=input_mode,
                        data_type=data_type,
                        dropdown_reference_type=dropdown_reference_type_obj,
                        dropdown_sql=dropdown_sql,
                        decimal_precision=decimal_precision,
                        operator1=operator1,
                        value1=value1,
                        condition=condition,
                        operator2=operator2,
                        value2=value2,
                        value_text=value_text,
                        unit=unit_obj,
                        is_reportable=is_reportable
                    )
            except Exception as e:
                print(f"Error saving TestAnalyte for Test '{test_instance.test_name}' and Analyte '{analyte_name}': {e}")

        def handle_test_workflow_steps_mapping(test_instance, item_data):
            workflow_name = item_data.get("workflow")
            sample_type_name = item_data.get("sample_type")
            container_type_name = item_data.get("container_type")
            workflow_step_name = item_data.get("step")

            if not all([workflow_name, sample_type_name, container_type_name, workflow_step_name]):
                print(f"Skipping TestWorkflowStep for Test '{test_instance.test_name}' due to missing required data. Data: {item_data}")
                return

            try:
                workflow_obj = Workflow.objects.get(workflow_name=workflow_name)
                sample_type_obj = SampleType.objects.get(sample_type=sample_type_name)
                container_type_obj = ContainerType.objects.get(container_type=container_type_name)
                workflow_step_obj = WorkflowStep.objects.get(step_id=workflow_step_name, workflow_id=workflow_obj) # Ensure workflow_id is used for lookup
            except (Workflow.DoesNotExist, SampleType.DoesNotExist, ContainerType.DoesNotExist, WorkflowStep.DoesNotExist) as e:
                print(f"Warning: Related object for TestWorkflowStep in Test '{test_instance.test_name}' does not exist: {e}. Data: {item_data}. Skipping entry.")
                return

            backward_movement = item_data.get("backward_movement") # Boolean value

            existing_property = TestWorkflowStep.objects.filter(
                test_id=test_instance,
                workflow_id=workflow_obj,
                workflow_step_id=workflow_step_obj,
                sample_type_id=sample_type_obj,
                container_type=container_type_obj
            ).first()

            try:
                if existing_property:
                    existing_property.workflow_id = workflow_obj
                    existing_property.workflow_step_id = workflow_step_obj
                    existing_property.sample_type_id = sample_type_obj
                    existing_property.container_type = container_type_obj
                    existing_property.backward_movement = backward_movement
                    existing_property.save()
                else:
                    TestWorkflowStep.objects.create(
                        test_id=test_instance,
                        workflow_id=workflow_obj,
                        workflow_step_id=workflow_step_obj,
                        sample_type_id=sample_type_obj,
                        container_type=container_type_obj,
                        backward_movement=backward_movement
                    )
            except Exception as e:
                print(f"Error saving TestWorkflowStep for Test '{test_instance.test_name}' and data {item_data}: {e}")

        def handle_test_attributes_mapping(test_instance, item_data):
            test_attribute_name = item_data.get("test_attribute")
            value = item_data.get("value")
            test_workflow_step_str = item_data.get("test_workflow_step") # This is the string "workflow - sample_type - container_type - step"

            if not all([test_attribute_name, test_workflow_step_str]):
                print(f"Skipping TestAttribute for Test '{test_instance.test_name}' due to missing 'test_attribute' or 'test_workflow_step'. Data: {item_data}")
                return

            test_workflow_step_obj = get_test_workflow_step_id_from_string(test_workflow_step_str, test_instance)
            if not test_workflow_step_obj:
                print(f"Warning: TestWorkflowStep '{test_workflow_step_str}' for Test '{test_instance.test_name}' not found. Skipping TestAttribute entry.")
                return

            existing_property = TestAttribute.objects.filter(
                test_id=test_instance,
                test_workflow_step_id=test_workflow_step_obj,
                test_attribute=test_attribute_name
            ).first()

            try:
                if existing_property:
                    existing_property.test_attribute = test_attribute_name
                    existing_property.value = value
                    existing_property.save()
                else:
                    TestAttribute.objects.create(
                        test_id=test_instance,
                        test_workflow_step_id=test_workflow_step_obj,
                        test_attribute=test_attribute_name,
                        value=value,
                    )
            except Exception as e:
                print(f"Error saving TestAttribute for Test '{test_instance.test_name}' and data {item_data}: {e}")

        def handle_test_wf_stp_instrument_maps_mapping(test_instance, item_data):
            workflow_name = item_data.get("workflow")
            workflow_step_name = item_data.get("step")
            sample_type_name = item_data.get("sample_type")
            container_type_name = item_data.get("container_type")
            instrument_type_name = item_data.get("instrument")

            if not all([workflow_name, workflow_step_name, sample_type_name, container_type_name, instrument_type_name]):
                print(f"Skipping TestWFSTPInstrumentMap for Test '{test_instance.test_name}' due to missing required data. Data: {item_data}")
                return

            try:
                workflow_obj = Workflow.objects.get(workflow_name=workflow_name)
                workflow_step_obj = WorkflowStep.objects.get(step_id=workflow_step_name, workflow_id=workflow_obj)
                sample_type_obj = SampleType.objects.get(sample_type=sample_type_name)
                container_type_obj = ContainerType.objects.get(container_type=container_type_name)
                instrument_type_obj = InstrumentType.objects.get(instrument_type=instrument_type_name)
            except (Workflow.DoesNotExist, WorkflowStep.DoesNotExist, SampleType.DoesNotExist, ContainerType.DoesNotExist, InstrumentType.DoesNotExist) as e:
                print(f"Warning: Related object for TestWFSTPInstrumentMap in Test '{test_instance.test_name}' does not exist: {e}. Data: {item_data}. Skipping entry.")
                return

            existing_property = TestWFSTPInstrumentMap.objects.filter(
                test_id=test_instance,
                workflow_id=workflow_obj,
                workflow_step_id=workflow_step_obj,
                sample_type_id=sample_type_obj,
                container_type=container_type_obj,
                instrument_type_id=instrument_type_obj
            ).first()

            try:
                if existing_property:
                    existing_property.workflow_id = workflow_obj
                    existing_property.workflow_step_id = workflow_step_obj
                    existing_property.sample_type_id = sample_type_obj
                    existing_property.instrument_type_id = instrument_type_obj
                    existing_property.container_type = container_type_obj
                    existing_property.save()
                else:
                    TestWFSTPInstrumentMap.objects.create(
                        test_id=test_instance,
                        workflow_id=workflow_obj,
                        workflow_step_id=workflow_step_obj,
                        sample_type_id=sample_type_obj,
                        container_type=container_type_obj,
                        instrument_type_id=instrument_type_obj,
                    )
            except Exception as e:
                print(f"Error saving TestWFSTPInstrumentMap for Test '{test_instance.test_name}' and data {item_data}: {e}")

        def handle_test_wf_stp_consumable_maps_mapping(test_instance, item_data):
            workflow_name = item_data.get("workflow")
            workflow_step_name = item_data.get("step")
            sample_type_name = item_data.get("sample_type")
            container_type_name = item_data.get("container_type")
            consumable_type_name = item_data.get("consumable")

            if not all([workflow_name, workflow_step_name, sample_type_name, container_type_name, consumable_type_name]):
                print(f"Skipping TestWFSTPConsumableMap for Test '{test_instance.test_name}' due to missing required data. Data: {item_data}")
                return

            try:
                workflow_obj = Workflow.objects.get(workflow_name=workflow_name)
                workflow_step_obj = WorkflowStep.objects.get(step_id=workflow_step_name, workflow_id=workflow_obj)
                sample_type_obj = SampleType.objects.get(sample_type=sample_type_name)
                container_type_obj = ContainerType.objects.get(container_type=container_type_name)
                consumable_type_obj = ConsumableType.objects.get(consumable_type=consumable_type_name)
            except (Workflow.DoesNotExist, WorkflowStep.DoesNotExist, SampleType.DoesNotExist, ContainerType.DoesNotExist, ConsumableType.DoesNotExist) as e:
                print(f"Warning: Related object for TestWFSTPConsumableMap in Test '{test_instance.test_name}' does not exist: {e}. Data: {item_data}. Skipping entry.")
                return

            existing_property = TestWFSTPConsumableMap.objects.filter(
                test_id=test_instance,
                workflow_id=workflow_obj,
                workflow_step_id=workflow_step_obj,
                sample_type_id=sample_type_obj,
                container_type=container_type_obj,
                consumable_type_id=consumable_type_obj
            ).first()

            try:
                if existing_property:
                    existing_property.workflow_id = workflow_obj
                    existing_property.workflow_step_id = workflow_step_obj
                    existing_property.sample_type_id = sample_type_obj
                    existing_property.container_type = container_type_obj
                    existing_property.consumable_type_id = consumable_type_obj
                    existing_property.save()
                else:
                    TestWFSTPConsumableMap.objects.create(
                        test_id=test_instance,
                        workflow_id=workflow_obj,
                        workflow_step_id=workflow_step_obj,
                        sample_type_id=sample_type_obj,
                        container_type=container_type_obj,
                        consumable_type_id=consumable_type_obj,
                    )
            except Exception as e:
                print(f"Error saving TestWFSTPConsumableMap for Test '{test_instance.test_name}' and data {item_data}: {e}")

        for row in imported_data:
            test_instance = get_test_instance(row)
            if test_instance:
                process_related_data(test_instance, self.test_test_workflow_step_values_map, handle_test_workflow_steps_mapping, 'test_workflow_steps')
                process_related_data(test_instance, self.test_cptcode_values_map, handle_cpt_codes_mapping, 'cpt_codes')
                process_related_data(test_instance, self.test_analyte_values_map, handle_analytes_mapping, 'analytes')
                process_related_data(test_instance, self.test_test_attribute_values_map, handle_test_attributes_mapping, 'test_attributes')
                process_related_data(test_instance, self.test_test_wf_stp_instrument_map_values_map, handle_test_wf_stp_instrument_maps_mapping, 'test_wf_stp_instrument_maps')
                process_related_data(test_instance, self.test_test_wf_stp_consumable_map_values_map, handle_test_wf_stp_consumable_maps_mapping, 'test_wf_stp_consumable_maps')

        return super().after_import(dataset, result, **kwargs)


def get_test_workflow_step_id_from_string(step_string, test_id):
    """
    Helper function to retrieve TestWorkflowStep instance from its string representation.
    This function is used by TestAttribute mapping.
    """
    print("get_test_workflow_step_id_from_string   ", step_string)
    parts = step_string.split(" - ")
    if len(parts) != 4:
        print(f"Error: Invalid step string format: {step_string}")
        return None

    workflow_name, sample_type_name, container_type_name, workflow_step_name = parts

    workflow = Workflow.objects.filter(workflow_name=workflow_name).first()
    sample_type = SampleType.objects.filter(sample_type=sample_type_name).first()
    container_type = ContainerType.objects.filter(container_type=container_type_name).first()
    workflow_step = WorkflowStep.objects.filter(step_id=workflow_step_name, workflow_id=workflow).first()

    if workflow and sample_type and container_type and workflow_step:
        twfs = TestWorkflowStep.objects.filter(
            test_id=test_id,
            workflow_id=workflow,
            sample_type_id=sample_type,
            container_type=container_type,
            workflow_step_id=workflow_step
        ).first()
        print("TestWorkflowStep : ", twfs)
        return twfs
    else:
        try:
            missing_parts = []
            if not workflow: missing_parts.append(f"Workflow '{workflow_name}'")
            if not sample_type: missing_parts.append(f"SampleType '{sample_type_name}'")
            if not container_type: missing_parts.append(f"ContainerType '{container_type_name}'")
            if not workflow_step: missing_parts.append(f"WorkflowStep '{workflow_step_name}' for Workflow '{workflow_name}'")
            print(f"Warning: Could not find all components for TestWorkflowStep string '{step_string}'. Missing: {', '.join(missing_parts)}")
        except Exception as e:
            logger.error(f"Error identifying missing parts. Returning no error")

    return None


class UnitsResource(resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.units_map = {}

    class Meta:
        model = Units
        import_id_fields = ('unit',)
        fields = (
            'unit',
            'description',
        )


class AnalyteResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analyte_map = {}

    # Map the foreign key field using ForeignKeyWidget
    unit = fields.Field(
        column_name='unit',  # CSV column name
        attribute='unit_id',  # The field name in Unit Model
        widget=ForeignKeyWidget(Units, 'unit')  # Map using the ForeignModel's `name` field
    )

    class Meta:
        model = Analyte
        import_id_fields = ('analyte',)
        fields = (
            'analyte',
            'description',
            'unit',
        )


class ICDCodeResource(resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icd_code_map = {}

    class Meta:
        model = ICDCode
        import_id_fields = ('icd_code',)
        fields = (
            'icd_code',
            'description',
        )


class CPTCodeResource(resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icd_code_map = {}

    class Meta:
        model = CPTCode
        import_id_fields = ('cpt_code',)
        fields = (
            'cpt_code',
            'description',
        )


class TestWorkflowStepResource(resources.ModelResource):
    # CSV columns used for both import and export.
    test_name = fields.Field(column_name='test_name')
    version = fields.Field(column_name='version')
    sample_type = fields.Field(column_name='sample_type')
    container_type = fields.Field(column_name='container_type')
    workflow = fields.Field(column_name='workflow')
    step = fields.Field(column_name='step')

    # Extra detail fields.
    workflow_step_config_fields = fields.Field(column_name='workflow_step_config_fields')
    test_workflow_actions = fields.Field(column_name='test_workflow_actions')

    class Meta:
        model = TestWorkflowStep
        # Use the unique combination for lookups.
        import_id_fields = ('test_name', 'version', 'sample_type', 'container_type', 'workflow', 'step')
        fields = (
            'test_name',
            'version',
            'sample_type',
            'container_type',
            'workflow',
            'step',
            'workflow_step_config_fields',
            'test_workflow_actions',
        )

    # --- Export (Dehydrate) Methods ---
    def dehydrate_test_name(self, obj):
        return obj.test_id.test_name if obj.test_id else None

    def dehydrate_version(self, obj):
        return obj.test_id.version if obj.test_id else None

    def dehydrate_sample_type(self, obj):
        return obj.sample_type_id.sample_type if obj.sample_type_id else None

    def dehydrate_container_type(self, obj):
        return obj.container_type.container_type if obj.container_type else None

    def dehydrate_workflow(self, obj):
        return obj.workflow_id.workflow_name if obj.workflow_id else None

    def dehydrate_step(self, obj):
        return obj.workflow_step_id.step_id if obj.workflow_step_id else None

    def dehydrate_workflow_step_config_fields(self, obj):
        """
        Exports WorkflowStepConfigField objects as a JSON array of dictionaries.
        """
        config_fields_data = []
        config_fields = obj.workflowstepconfigfield_set.all()
        for cf in config_fields:
            config_fields_data.append({
                "model": cf.model,
                "field": cf.field_id,
            })
        return json.dumps(config_fields_data)

    def dehydrate_test_workflow_actions(self, obj):
        """
        Exports TestWorkflowStepActionMap objects as a JSON array of dictionaries.
        """
        actions_data = []
        actions = obj.testworkflowstepactionmap_set.all()
        for a in actions:
            actions_data.append({
                "action": a.action,
                "action_method": a.action_method,
                "sequence": a.sequence,
            })
        return json.dumps(actions_data)

    # --- Import Methods ---
    def get_instance(self, instance_loader, row):
        """
        Lookup a TestWorkflowStep using the unique combination:
         - Test: by test_name and version.
         - Workflow: by workflow_name.
         - WorkflowStep: by step_id (filtered by Workflow).
         - SampleType and ContainerType: by their unique names.
        """
        try:
            test = Test.objects.get(
                test_name=row.get('test_name'),
                version=row.get('version')
            )
            workflow = Workflow.objects.get(workflow_name=row.get('workflow'))
            workflow_step = WorkflowStep.objects.get(
                step_id=row.get('step'),
                workflow_id=workflow
            )
            sample_type = SampleType.objects.get(sample_type=row.get('sample_type'))
            container_type = ContainerType.objects.get(container_type=row.get('container_type'))
            instance = TestWorkflowStep.objects.get(
                test_id=test,
                workflow_id=workflow,
                workflow_step_id=workflow_step,
                sample_type_id=sample_type,
                container_type=container_type
            )
            return instance
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error in get_instance for row {row}: {e}")
            return None

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store extra values (workflow_step_config_fields and test_workflow_actions)
        temporarily using a composite key, then remove them from the row.
        The values stored will now be JSON strings.
        """
        key_parts = [
            row.get('test_name'),
            "ver" + str(row.get('version')), # Ensure version is string for key
            row.get('sample_type'),
            row.get('container_type'),
            row.get('workflow'),
            row.get('step')
        ]
        key = "_".join([str(p) for p in key_parts if p is not None]) # Ensure all parts are strings and handle None

        if not hasattr(self, 'workflow_config_map'):
            self.workflow_config_map = {}
        if not hasattr(self, 'workflow_action_map'):
            self.workflow_action_map = {}

        if row.get('workflow_step_config_fields') is not None:
            self.workflow_config_map[key] = row.get('workflow_step_config_fields')
            del row['workflow_step_config_fields']
        if row.get('test_workflow_actions') is not None:
            self.workflow_action_map[key] = row.get('test_workflow_actions')
            del row['test_workflow_actions']

        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        """
        After import, for each row use the composite key to fetch the proper
        TestWorkflowStep and then create/update its detail records.
        Now parses JSON strings for related data.
        """
        imported_data = dataset.dict
        for row in imported_data:
            key_parts = [
                row.get('test_name'),
                "ver" + str(row.get('version')),
                row.get('sample_type'),
                row.get('container_type'),
                row.get('workflow'),
                row.get('step')
            ]
            key = "_".join([str(p) for p in key_parts if p is not None])

            try:
                test = Test.objects.get(
                    test_name=row.get('test_name'),
                    version=row.get('version')
                )
                workflow = Workflow.objects.get(workflow_name=row.get('workflow'))
                workflow_step = WorkflowStep.objects.get(
                    step_id=row.get('step'),
                    workflow_id=workflow
                )
                sample_type = SampleType.objects.get(sample_type=row.get('sample_type'))
                container_type = ContainerType.objects.get(container_type=row.get('container_type'))

                tws = TestWorkflowStep.objects.get(
                    test_id=test,
                    workflow_id=workflow,
                    workflow_step_id=workflow_step,
                    sample_type_id=sample_type,
                    container_type=container_type
                )
            except Exception as e:
                logger.error(f"Error finding TestWorkflowStep for row {row}: {e}")
                continue

            config_fields_json = self.workflow_config_map.get(key)
            if config_fields_json:
                try:
                    config_fields_data = json.loads(config_fields_json)
                    for field_data in config_fields_data:
                        model_name = field_data.get("model")
                        field_id = field_data.get("field")

                        if not all([model_name, field_id]):
                            logger.warning(f"Skipping WorkflowStepConfigField for TestWorkflowStep '{key}' due to missing 'model' or 'field_id'. Data: {field_data}")
                            continue

                        qs = tws.workflowstepconfigfield_set.filter(
                            model=model_name,
                            field_id=field_id
                        )
                        if qs.exists():
                            pass
                        else:
                            try:
                                WorkflowStepConfigField.objects.create(
                                    test_workflow_step_id=tws,
                                    model=model_name,
                                    field_id=field_id
                                )
                            except Exception as create_e:
                                logger.error(f"Error creating WorkflowStepConfigField for TestWorkflowStep '{key}' with data {field_data}: {create_e}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing WorkflowStepConfigField JSON for TestWorkflowStep '{key}': {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred processing WorkflowStepConfigField for TestWorkflowStep '{key}': {e}")


            actions_json = self.workflow_action_map.get(key)
            if actions_json:
                try:
                    actions_data = json.loads(actions_json)
                    for action_data in actions_data:
                        action_name = action_data.get("action")
                        action_method = action_data.get("action_method")
                        sequence = action_data.get("sequence")

                        if not all([action_name, action_method, sequence is not None]):
                             logger.warning(f"Skipping TestWorkflowStepActionMap for TestWorkflowStep '{key}' due to missing 'action', 'action_method', or 'sequence'. Data: {action_data}")
                             continue

                        try:
                            seq = int(sequence)
                        except ValueError:
                            logger.warning(f"Invalid sequence value '{sequence}' for TestWorkflowStepActionMap in TestWorkflowStep '{key}'. Defaulting to 0.")
                            seq = 0

                        existing = tws.testworkflowstepactionmap_set.filter(
                            action=action_name,
                            action_method=action_method
                        ).first()
                        if existing:
                            if existing.sequence != seq:
                                existing.sequence = seq
                                try:
                                    existing.save()
                                except Exception as update_e:
                                    logger.error(f"Error updating TestWorkflowStepActionMap for TestWorkflowStep '{key}' with data {action_data}: {update_e}")
                        else:
                            try:
                                TestWorkflowStepActionMap.objects.create(
                                    testwflwstepmap_id=tws,
                                    action=action_name,
                                    action_method=action_method,
                                    sequence=seq
                                )
                            except Exception as create_e:
                                logger.error(f"Error creating TestWorkflowStepActionMap for TestWorkflowStep '{key}' with data {action_data}: {create_e}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing TestWorkflowStepActionMap JSON for TestWorkflowStep '{key}': {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred processing TestWorkflowStepActionMap for TestWorkflowStep '{key}': {e}")

        return super().after_import(dataset, result, **kwargs)