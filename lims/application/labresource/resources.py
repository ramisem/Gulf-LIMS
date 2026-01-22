from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from labresource.models import InstrumentType, InstrumentModel


class InstrumentTypeResource(resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = InstrumentType
        import_id_fields = ('instrument_type',)
        fields = (
            'instrument_type',
            'description',
        )


class InstrumentModelResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instrument_model_type_map = {}

    # Map the foreign key field using ForeignKeyWidget
    instrument_type = fields.Field(
        column_name='instrument_type',  # CSV column for foreign table name
        attribute='instrument_type',  # The field name in PrimaryModel
        widget=ForeignKeyWidget(InstrumentType, 'instrument_type')  # Map using the ForeignModel's `name` field
    )

    class Meta:
        model = InstrumentModel
        import_id_fields = ('instrument_model',)
        fields = (
            'instrument_model',
            'description',
            'instrument_type'
        )
