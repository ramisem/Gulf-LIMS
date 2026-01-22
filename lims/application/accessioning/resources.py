from import_export import resources, fields

from masterdata.models import AccessionType


class AccessionTypeResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accession_type_map = {}

    class Meta:
        model = AccessionType
        import_id_fields = ('accession_type',)
        fields = (
            'accession_type',
            'reporting_type',
        )