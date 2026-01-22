import json

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from process.models import SampleType, ContainerType, SampleTypeContainerType, ConsumableType
from workflows.models import Workflow


class SampleTypeResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample_type_map = {}

    class Meta:
        model = SampleType
        import_id_fields = ('sample_type',)
        fields = (
            'sample_type',
            'description',
        )


class ContainerTypeResource(resources.ModelResource):
    sample_types = fields.Field(column_name='sample_types')
    workflow_name = fields.Field(
        column_name='workflow_name',  # Column in Excel
        attribute='workflow_id',
        widget=ForeignKeyWidget(Workflow, 'workflow_name')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container_type_sample_type_values_map = {}

    class Meta:
        model = ContainerType
        import_id_fields = ('container_type',)
        fields = (
            'container_type',
            'description',
            'child_sample_creation',
            'gen_block_or_cassette_seq',
            'gen_slide_seq',
            'is_liquid',
            'workflow_name',
            'sample_types',
        )

    def dehydrate_sample_types(self, obj):
        """
        Exports the related SampleTypeContainerType objects as a JSON array of dictionaries.
        """
        sample_types_data_list = []
        sample_type_container_types = obj.sampletypecontainertype_set.order_by('pk')

        for sample_type_ct in sample_type_container_types:
            sample_types_data_list.append({
                "sample_type": sample_type_ct.sample_type_id.sample_type,
            })
        return json.dumps(sample_types_data_list)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store the 'sample_types' JSON string for later processing in after_import,
        then remove it from the row to prevent direct import errors.
        """
        sample_types_json = row.get('sample_types', None)
        if sample_types_json:
            self.container_type_sample_type_values_map[row['container_type']] = sample_types_json
        if 'sample_types' in row:  # Defensive check
            del row['sample_types']
        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        """
        After ContainerType objects are imported/updated, process the related SampleTypeContainerType data.
        This method will create new SampleTypeContainerType objects or update existing ones.
        """
        imported_data = dataset.dict
        for row in imported_data:
            container_type_name = row['container_type']
            try:
                container_type_detail = ContainerType.objects.get(container_type=container_type_name)
            except ContainerType.DoesNotExist:
                print(
                    f"Warning: ContainerType '{container_type_name}' not found after import. Skipping SampleTypeContainerType processing. (This often happens with new imports)")
                continue
            except Exception as e:
                print(
                    f"An unexpected error occurred while fetching ContainerType '{container_type_name}': {e}. Skipping SampleTypeContainerType processing.")
                continue

            sample_types_json = self.container_type_sample_type_values_map.get(container_type_name)

            if sample_types_json:
                try:
                    sample_type_sets = json.loads(sample_types_json)

                    for prop_dict in sample_type_sets:
                        sample_type_name = prop_dict.get("sample_type")

                        if sample_type_name is None:
                            print(
                                f"Skipping SampleTypeContainerType for '{container_type_name}' due to missing 'sample_type' name. Data: {prop_dict}")
                            continue

                        try:
                            sample_type_obj = SampleType.objects.get(sample_type=sample_type_name)
                        except SampleType.DoesNotExist:
                            print(
                                f"Warning: SampleType '{sample_type_name}' referenced in ContainerType '{container_type_name}' does not exist. Skipping this SampleTypeContainerType entry.")
                            continue

                        existing_property = SampleTypeContainerType.objects.filter(
                            container_type_id=container_type_detail,
                            sample_type_id=sample_type_obj,
                        ).first()

                        try:
                            if existing_property:
                                existing_property.sample_type_id = sample_type_obj
                                existing_property.save()
                            else:
                                SampleTypeContainerType.objects.create(
                                    container_type_id=container_type_detail,
                                    sample_type_id=sample_type_obj,
                                )
                        except Exception as stct_e:
                            print(
                                f"Error saving SampleTypeContainerType for ContainerType '{container_type_name}' and SampleType '{sample_type_name}': {stct_e}")

                except json.JSONDecodeError as e:
                    print(f"Error parsing sample_types JSON for ContainerType '{container_type_name}': {e}")
                except Exception as e:
                    print(
                        f"An unexpected error occurred processing SampleTypeContainerType for ContainerType '{container_type_name}': {e}")

        return super().after_import(dataset, result, **kwargs)


class ConsumableTypeResource(resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = ConsumableType
        import_id_fields = ('consumable_type',)
        fields = (
            'consumable_type',
            'description',
        )
