import logging

from django.core.exceptions import ObjectDoesNotExist
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from reporting.models import LabelMethod

logger = logging.getLogger(__name__)


class LabelMethodResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_method_map = {}

    class Meta:
        model = LabelMethod
        import_id_fields = ('label_method_name', 'label_method_version_id',)
        fields = (
            'label_method_name',
            'label_method_version_id',
            'label_method_desc',
            's3bucket',
            'export_location',
            'designer_format',
            'label_query',
            'delimiter',
            'file_format',
            'show_header',
            'show_fields',
            'is_bio_pharma_label',
        )