from import_export import resources, fields
import json

from configuration.models import ReferenceType, RefValues


class ReferenceTypeResource(resources.ModelResource):
    ref_values = fields.Field(column_name='ref_values')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reference_type_name_values_map = {}

    class Meta:
        model = ReferenceType
        import_id_fields = ('name',)
        fields = (
            'name',
            'description',
            'is_system_level',
            'ref_values',
        )

    def dehydrate_is_system_level(self, obj):
        return "Yes" if obj.is_system_level else "No"

    def dehydrate_ref_values(self, obj):
        reference_type = ReferenceType.objects.get(name=obj.name)
        ref_values_data = []

        if reference_type:
            ref_values_objects = reference_type.refvalues_set.order_by('pk')

            for ref_value in ref_values_objects:
                ref_values_data.append({
                    "value": ref_value.value,
                    "display_value": ref_value.display_value
                })

        return json.dumps(ref_values_data)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        row["is_system_level"] = True if row["is_system_level"] == "Yes" else False

        ref_values_json = row.get('ref_values', None)
        if ref_values_json:
            self.reference_type_name_values_map[row['name']] = ref_values_json
        del row['ref_values']

        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        imported_data = dataset.dict
        for row in imported_data:
            try:
                reference_type_detail = ReferenceType.objects.get(name=row['name'])
            except ReferenceType.DoesNotExist:
                print(f"Warning: ReferenceType '{row['name']}' not found after import. Skipping RefValues processing.")
                continue

            ref_values_json = self.reference_type_name_values_map.get(row['name'])

            if ref_values_json:
                try:
                    ref_value_sets = json.loads(ref_values_json)

                    for prop_dict in ref_value_sets:
                        value = prop_dict.get("value")
                        display_value = prop_dict.get("display_value")

                        if value is None:
                            print(f"Skipping RefValue for '{row['name']}' due to missing 'value'. Data: {prop_dict}")
                            continue

                        existing_property = RefValues.objects.filter(
                            reftype_id=reference_type_detail,
                            value=value
                        ).first()

                        if existing_property:
                            existing_property.display_value = display_value
                            existing_property.save()
                        else:
                            RefValues.objects.create(
                                reftype_id=reference_type_detail,
                                value=value,
                                display_value=display_value,
                            )
                except json.JSONDecodeError as e:
                    print(f"Error parsing ref_values JSON for ReferenceType '{row['name']}': {e}")
                except Exception as e:
                    print(f"An unexpected error occurred processing RefValues for ReferenceType '{row['name']}': {e}")

        return super().after_import(dataset, result, **kwargs)
