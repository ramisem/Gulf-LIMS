import json

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from masterdata.models import AccessionType, BodySite, ReportImgPropInfo, BodySubSiteMap, AttachmentConfiguration, \
    Client, Physician, Patient, PatientInsuranceInfo, Sponsor, BodySiteTestMap
from security.models import User
from tests.models import Test


class ClientResource(resources.ModelResource):
    """
    Resource for the Client model.
    No created_by field exported/imported as per request.
    No inlines are exported/imported for Client.
    """

    # Removed: created_by = fields.Field(...)

    class Meta:
        model = Client
        import_id_fields = ('name',)
        fields = (
            'name',
            'active_flag',
            # 'created_dt' is auto_now_add, so don't include for import
            # Removed: 'created_by',
            'address1',
            'address2',
            'city',
            'state',
            'postalcode',
            'country',
            'telephone',
            'fax_number',
            'primaryemail',
        )
        export_order = (
            'name', 'active_flag', 'address1', 'address2',
            'city', 'state', 'postalcode', 'country', 'telephone',
            'fax_number', 'primaryemail'
        )


class PatientResource(resources.ModelResource):
    """
    Resource for the Patient model.
    No created_by field exported/imported as per request.
    Includes 'patient_insurance_info' as a JSON field for related PatientInsuranceInfo objects.
    """
    # Removed: created_by = fields.Field(...)

    # Field to handle the PatientInsuranceInfo inline data as JSON
    patient_insurance_info = fields.Field(column_name='patient_insurance_info')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient_insurance_info_map = {}  # To store JSON string during import

    class Meta:
        model = Patient
        import_id_fields = ('mrn', 'birth_dt')
        fields = (
            'first_name',
            'last_name',
            'middle_initial',
            'active_flag',
            # 'created_dt' is auto_now_add
            # Removed: 'created_by',
            'birth_dt',
            'gender',
            'mrn',
            'ssn',
            'street_address',
            'apt',
            'city',
            'zipcode',
            'state',
            'phone_number',
            'fax_number',
            'email',
            'marital_status',
            'smoking_status',
            'race',
            'patient_insurance_info',  # Include the custom field for inline data
        )
        export_order = (
            'first_name', 'last_name', 'middle_initial', 'active_flag',
            'birth_dt', 'gender', 'mrn', 'ssn', 'street_address', 'apt',
            'city', 'zipcode', 'state', 'phone_number', 'fax_number',
            'email', 'marital_status', 'smoking_status', 'race', 'patient_insurance_info'
        )

    def dehydrate_patient_insurance_info(self, obj):
        """
        Exports related PatientInsuranceInfo objects as a JSON array of dictionaries.
        """
        insurance_data = []
        for pi_info in obj.patientinsuranceinfo_set.order_by('pk'):
            insurance_data.append({
                "insurance": pi_info.insurance,
                "group": pi_info.group,
                "policy": pi_info.policy,
            })
        return json.dumps(insurance_data)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store the 'patient_insurance_info' JSON string for later processing,
        then remove it from the row to prevent direct import errors.
        """
        patient_key = f"{row.get('mrn')}_{row.get('birth_dt')}"

        patient_insurance_info_json = row.get('patient_insurance_info', None)
        if patient_insurance_info_json is not None:
            self.patient_insurance_info_map[patient_key] = patient_insurance_info_json
            del row['patient_insurance_info']

        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        """
        After Patient objects are imported/updated, process the related PatientInsuranceInfo data.
        """
        imported_data = dataset.dict
        for row_index, row_data in enumerate(imported_data):
            patient_key = f"{row_data.get('mrn')}_{row_data.get('birth_dt')}"

            try:
                patient_instance = Patient.objects.get(
                    mrn=row_data.get('mrn'),
                    birth_dt=row_data.get('birth_dt')
                )
            except Patient.DoesNotExist:
                print(
                    f"Warning: Patient with MRN '{row_data.get('mrn')}' and Birth Date '{row_data.get('birth_dt')}' not found after import. Skipping PatientInsuranceInfo processing.")
                continue
            except Exception as e:
                print(
                    f"An unexpected error occurred while fetching Patient '{patient_key}': {e}. Skipping PatientInsuranceInfo processing.")
                continue

            insurance_info_json = self.patient_insurance_info_map.get(patient_key)

            if insurance_info_json:
                try:
                    insurance_data_list = json.loads(insurance_info_json)

                    for info_dict in insurance_data_list:
                        insurance_name = info_dict.get("insurance")
                        group = info_dict.get("group")
                        policy = info_dict.get("policy")

                        if not all([insurance_name, group, policy]):
                            print(
                                f"Skipping PatientInsuranceInfo for Patient '{patient_key}' due to missing required data. Data: {info_dict}")
                            continue

                        existing_info = PatientInsuranceInfo.objects.filter(
                            patient=patient_instance,
                            insurance=insurance_name,
                            group=group,
                            policy=policy
                        ).first()

                        try:
                            if existing_info:
                                existing_info.save()
                            else:
                                PatientInsuranceInfo.objects.create(
                                    patient=patient_instance,
                                    insurance=insurance_name,
                                    group=group,
                                    policy=policy,
                                )
                        except Exception as pi_e:
                            print(
                                f"Error saving PatientInsuranceInfo for Patient '{patient_key}' and data {info_dict}: {pi_e}")

                except json.JSONDecodeError as e:
                    print(f"Error parsing patient_insurance_info JSON for Patient '{patient_key}': {e}")
                except Exception as e:
                    print(
                        f"An unexpected error occurred processing PatientInsuranceInfo for Patient '{patient_key}': {e}")

        return super().after_import(dataset, result, **kwargs)


class PhysicianResource(resources.ModelResource):
    """
    Resource for the Physician model.
    No created_by field exported/imported as per request.
    Handles 'user_id' as a ForeignKey to User.
    No inlines are exported/imported for Physician.
    """
    # Removed: created_by = fields.Field(...)

    user_id = fields.Field(
        column_name='user_id_username',
        attribute='user_id',
        widget=ForeignKeyWidget(User, 'username')
    )

    class Meta:
        model = Physician
        import_id_fields = ('first_name', 'last_name', 'category')
        fields = (
            'first_name',
            'last_name',
            'external',
            'active_flag',
            'category',
            # 'created_dt' is auto_now_add
            # Removed: 'created_by',
            'phone_number',
            'fax_number',
            'email',
            'physician_type',
            'user_id',
            'title',
            'env_type',
        )
        export_order = (
            'first_name', 'last_name', 'external', 'active_flag', 'category',
            'phone_number', 'fax_number', 'email', 'physician_type',
            'user_id', 'title', 'env_type'
        )

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


class AttachmentConfigurationResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attachment_config_map = {}

    class Meta:
        model = AttachmentConfiguration
        id_field = 'attachment_config_id'
        import_id_fields = ('model_name',)
        fields = (
            'model_name',
            'path',
        )


class BodySiteResource(resources.ModelResource):
    sub_sites = fields.Field(column_name='sub_sites')
    associated_tests = fields.Field(column_name='associated_tests')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # temp storage for import
        self.body_site_sub_sites_value_map = {}
        self.body_site_associated_tests_value_map = {}

    class Meta:
        model = BodySite
        import_id_fields = ('body_site',)
        fields = (
            'body_site',
            'base_image',
            'image_render_category',
            'sub_sites',
            'associated_tests'
        )

    def dehydrate_sub_sites(self, obj):
        """
        Exports the related BodySubSiteMap objects as a JSON array of dictionaries.
        """
        sub_sites_data = []
        for m in obj.bodysubsitemap_set.order_by('pk'):
            sub_sites_data.append({
                "sub_site": m.sub_site,
                "x_axis": m.x_axis,
                "y_axis": m.y_axis,
            })
        return json.dumps(sub_sites_data)

    def dehydrate_associated_tests(self, obj):
        """
        Exports the related BodySubSiteMap objects as a JSON array of dictionaries.
        """
        associated_tests_data = []
        for m in obj.bodysitetestmap_set.order_by('pk'):
            associated_tests_data.append({
                "test": m.test_id.test_name,  # OR test_code — whichever you use
                "is_default": m.is_default,
            })
        return json.dumps(associated_tests_data)

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        """
        Store the 'sub_sites' JSON string for later processing in after_import,
        then remove it from the row to prevent direct import errors.
        """
        sub_sites_json = row.get('sub_sites')
        if sub_sites_json is not None:
            key = row['body_site']
            self.body_site_sub_sites_value_map[key] = sub_sites_json
            del row['sub_sites']
        associated_tests_json = row.get('associated_tests')
        if associated_tests_json is not None:
            key = row['body_site']
            self.body_site_associated_tests_value_map[key] = associated_tests_json
            del row['associated_tests']
        return super().import_row(row, instance_loader, **kwargs)

    def after_import(self, dataset, result, **kwargs):
        """
        After BodySite objects are imported/updated, process the related BodySubSiteMap data.
        This method will create new BodySubSiteMap objects or update existing ones.
        """
        imported_data = dataset.dict
        for row in imported_data:
            body_site_name = row['body_site']
            try:
                body_site_detail = BodySite.objects.get(body_site=body_site_name)
            except BodySite.DoesNotExist:
                print(
                    f"Warning: BodySite '{body_site_name}' not found after import. Skipping BodySubSiteMap processing. (This often happens with new imports)")
                continue
            except Exception as e:
                print(
                    f"An unexpected error occurred while fetching BodySite '{body_site_name}': {e}. Skipping BodySubSiteMap processing.")
                continue

            sub_sites_json = self.body_site_sub_sites_value_map.get(body_site_name)

            if sub_sites_json:
                try:
                    sub_sites_data_list = json.loads(sub_sites_json)

                    for prop_dict in sub_sites_data_list:
                        sub_site_name = prop_dict.get("sub_site")
                        x_axis = prop_dict.get("x_axis")
                        y_axis = prop_dict.get("y_axis")

                        if sub_site_name is None:
                            print(
                                f"Skipping BodySubSiteMap for '{body_site_name}' due to missing 'sub_site'. Data: {prop_dict}")
                            continue

                        existing_property = BodySubSiteMap.objects.filter(
                            body_site=body_site_detail,  # Use the object directly
                            sub_site=sub_site_name,
                        ).first()

                        try:
                            if existing_property:
                                existing_property.sub_site = sub_site_name  # Ensure it's updated even if it's the same
                                existing_property.x_axis = x_axis if x_axis is not None else None
                                existing_property.y_axis = y_axis if y_axis is not None else None
                                existing_property.save()
                            else:
                                BodySubSiteMap.objects.create(
                                    body_site=body_site_detail,  # Use the object directly
                                    sub_site=sub_site_name,
                                    x_axis=x_axis if x_axis is not None else None,
                                    y_axis=y_axis if y_axis is not None else None,
                                )
                        except Exception as sub_site_e:
                            print(
                                f"Error saving BodySubSiteMap for BodySite '{body_site_name}' and sub_site '{sub_site_name}': {sub_site_e}")

                except json.JSONDecodeError as e:
                    print(f"Error parsing sub_sites JSON for BodySite '{body_site_name}': {e}")
                except Exception as e:
                    print(
                        f"An unexpected error occurred processing BodySubSiteMap for BodySite '{body_site_name}': {e}")

            tests_json = self.body_site_associated_tests_value_map.get(body_site_name)

            if tests_json:
                try:
                    tests_list = json.loads(tests_json)

                    for tdict in tests_list:
                        test_name = tdict.get("test")
                        is_default = tdict.get("is_default", False)

                        if not test_name:
                            print(f"Missing test name for BodySite '{body_site_name}'. Data: {tdict}")
                            continue

                        # Fetch Test object
                        try:
                            test_obj = Test.objects.get(test_name=test_name)
                        except Test.DoesNotExist:
                            print(f"Test '{test_name}' does not exist. Skipping.")
                            continue

                        # Check existing
                        obj = BodySiteTestMap.objects.filter(
                            body_site=body_site_detail,
                            test_id=test_obj
                        ).first()

                        if obj:
                            obj.is_default = is_default
                            obj.save()
                        else:
                            BodySiteTestMap.objects.create(
                                body_site=body_site_detail,
                                test_id=test_obj,
                                is_default=is_default
                            )

                except Exception as e:
                    print(f"Error processing associated tests for BodySite '{body_site_name}': {e}")

        return super().after_import(dataset, result, **kwargs)


class ReportImgPropInfoResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accession_type_map = {}

    class Meta:
        model = ReportImgPropInfo
        import_id_fields = ('category',)
        fields = (
            "category",
            "shape",
            "color",
        )

class SponsorResource(resources.ModelResource):

    class Meta:
        model = Sponsor
        import_id_fields = ('sponsor_name','sponsor_number')
        fields = (
            'sponsor_name',
            'sponsor_number',
        )
