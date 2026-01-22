from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.contrib.auth.models import Group, Permission

from .models import SiteTimezone, Site, Department, JobType


class SiteTimezoneResource(resources.ModelResource):
    """
    Resource for the SiteTimezone model.
    Exports/imports 'name' and 'description'.
    """
    class Meta:
        model = SiteTimezone
        import_id_fields = ('name',)
        fields = (
            'name',
            'description',
        )


class SiteResource(resources.ModelResource):
    """
    Resource for the Site model.
    Handles 'timezone' as a ForeignKey to SiteTimezone using its 'name' (natural key).
    """

    timezone = fields.Field(
        column_name='timezone',
        attribute='timezone',
        widget=ForeignKeyWidget(SiteTimezone, 'name')
    )

    class Meta:
        model = Site
        import_id_fields = ('name',)
        fields = (
            'name',
            'abbreviation',
            'timezone',
        )


class DepartmentResource(resources.ModelResource):
    """
    Resource for the Department model.
    Handles 'siteid' as a ForeignKey to Site using its 'name' (natural key).
    """
    # Define a field for the 'siteid' ForeignKey.
    # Using 'site' as the column name for clarity in the export/import file.
    siteid = fields.Field(
        column_name='site',
        attribute='siteid',
        widget=ForeignKeyWidget(Site, 'name') # Use 'name' as the lookup field for Site
    )

    class Meta:
        model = Department
        import_id_fields = ('name',)
        fields = (
            'name',
            'lab_name',
            'siteid',
        )


class JobTypeResource(resources.ModelResource):
    departmentid = fields.Field(
        column_name='department',
        attribute='departmentid',
        widget=ForeignKeyWidget(Department, 'name')
    )
    permissions = fields.Field(column_name='permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jobtype_permissions_map = {}

    class Meta:
        model = JobType
        import_id_fields = ('name',)
        fields = (
            'name',
            'site_independent',
            'departmentid',
            'permissions',
        )

    def dehydrate_permissions(self, obj):
        """
        Exports permissions as a comma-separated string of permission codenames.
        Example: "add_user,change_user,delete_user"
        """
        return ",".join([p.codename for p in obj.permissions.all()])

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store permissions data temporarily, then remove from row for parent import.
        """
        permissions_str = row.get('permissions', None)
        if permissions_str is not None:
            self.jobtype_permissions_map[row['name']] = permissions_str
            del row['permissions']
        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        """
        After JobType (Group) objects are imported/updated, assign their permissions.
        """
        imported_data = dataset.dict
        for row_index, row_data in enumerate(imported_data):
            jobtype_name = row_data['name']

            try:
                jobtype_instance = JobType.objects.get(name=jobtype_name)
            except JobType.DoesNotExist:
                print(f"Warning: JobType '{jobtype_name}' not found after import. Skipping permission assignment.")
                continue
            except Exception as e:
                print(
                    f"An unexpected error occurred while fetching JobType '{jobtype_name}': {e}. Skipping permission assignment.")
                continue

            permissions_str = self.jobtype_permissions_map.get(jobtype_name)

            if permissions_str:
                permission_codenames = [s.strip() for s in permissions_str.split(',') if s.strip()]
                permissions_to_add = []
                for codename in permission_codenames:
                    try:
                        perm = Permission.objects.get(codename=codename)
                        permissions_to_add.append(perm)
                    except Permission.DoesNotExist:
                        print(
                            f"Warning: Permission with codename '{codename}' not found for JobType '{jobtype_name}'. Skipping this permission.")
                    except Exception as e:
                        print(f"Error fetching permission '{codename}' for JobType '{jobtype_name}': {e}")
                if permissions_to_add:
                    try:
                        jobtype_instance.permissions.set(permissions_to_add)
                    except Exception as e:
                        print(f"Error assigning permissions to JobType '{jobtype_name}': {e}")

        return super().after_import(dataset, result, **kwargs)
