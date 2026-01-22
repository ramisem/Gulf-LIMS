from django.apps import apps
from django.db.models import Case, When, Value, IntegerField, F

from workflows.models import Workflow
from .models import Sample, ChildSample
from django.core.exceptions import ValidationError
from util.util import UtilClass
from datetime import datetime
from process.models import SampleType, ContainerType
from security.models import User, Department, JobType
from accessioning.models import Accession
from tests.models import Test, TestWorkflowStep
from sample.models import SampleTestMap


class SampleUtilClass:
    # This is for creating samples
    @staticmethod
    def create_sample(accession_id, sample_type_id, container_type_id, count, test_id, request, part_no,
                      is_child_sample_creation, is_generate_parent_seq, selected_block_or_cassette_seq, workflow_id=None):
        print(
            f" accession_id: {accession_id}, sample_type_id: {sample_type_id}, container_type_id: {container_type_id}, count: {count}, test_id: {test_id}")
        if accession_id is not None and sample_type_id is not None and container_type_id is not None and count is not None and request is not None:
            print("All required parameters are present")
            if request.user.is_authenticated:
                print("User is authenticated")
                accession_id_instance = Accession.objects.get(accession_id=accession_id)
                print(f"Accession ID found: {accession_id_instance}")
                sample_type_instance = SampleType.objects.get(sample_type_id=sample_type_id)
                print(f"SampleType found: {sample_type_instance}")
                if sample_type_instance is None:
                    raise ValidationError("Sample Type is blank")

                container_type_instance = ContainerType.objects.get(container_type_id=container_type_id)

                if container_type_instance is None:
                    raise ValidationError("Container Type is blank")

                # test validation
                if test_id:
                    test_list = test_id.split('|')
                    child_sample_creation = container_type_instance.child_sample_creation
                    if len(test_list) > 1 and child_sample_creation is False:
                        raise ValidationError("Multiple tests cannot be assigned to this Container Type")
                workflow_instance = None
                if workflow_id:
                    try:
                        workflow_instance = Workflow.objects.get(pk=workflow_id)
                        print(f"Workflow found: {workflow_instance}")
                    except Workflow.DoesNotExist:
                        # This prevents creating samples if an invalid workflow is passed
                        raise ValidationError(f"Invalid Workflow ID provided: {workflow_id}")

                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                current_jobtype = request.session.get('currentjobtype', '')
                if current_jobtype is not None:
                    department_id = JobType.objects.filter(name=current_jobtype).values_list('departmentid',
                                                                                             flat=True).first()
                    department_instance = None
                    if department_id is not None:
                        department_instance = Department.objects.get(id=department_id)
                    if user_map_obj is not None:
                        list_sample = []
                        if "Y" == is_generate_parent_seq and accession_id_instance.accession_category != 'Clinical':
                            if container_type_instance.gen_slide_seq:
                                block_or_cassette_seq_prefix = accession_id + "-" + part_no
                                selected_block_or_cassette_seq = UtilClass.get_next_sequence(
                                    block_or_cassette_seq_prefix,
                                    "Sample",
                                    user_map_obj.id)
                        for i in range(int(count)):
                            sample_instance = Sample()
                            current_date = datetime.now()
                            prefix = f"S-{current_date.strftime('%m%d%Y')}"
                            seq_no = UtilClass.get_next_sequence(prefix, "Sample", user_map_obj.id)
                            sample_instance.sample_id = f"{prefix}-{seq_no:05}"
                            sample_instance.part_no = part_no
                            if ("true" == is_child_sample_creation
                                    and accession_id_instance.accession_category != 'Clinical'):
                                if container_type_instance.gen_block_or_cassette_seq:
                                    block_or_cassette_seq_prefix = accession_id + "-" + part_no
                                    block_cassette_seq = UtilClass.get_next_sequence(block_or_cassette_seq_prefix,
                                                                                     "Sample", user_map_obj.id)
                                    sample_instance.block_or_cassette_seq = str(block_cassette_seq)
                            else:
                                if container_type_instance.gen_slide_seq and accession_id_instance.accession_category != 'Clinical':
                                    sample_instance.block_or_cassette_seq = selected_block_or_cassette_seq
                                    slide_seq_prefix = accession_id + "-" + part_no + "-" + str(
                                        selected_block_or_cassette_seq)
                                    slide_seq = UtilClass.get_next_sequence(slide_seq_prefix, "Sample",
                                                                            user_map_obj.id)
                                    sample_instance.slide_seq = str(slide_seq)
                            sample_instance.sample_type = sample_type_instance
                            sample_instance.container_type = container_type_instance
                            if department_instance:
                                sample_instance.custodial_department = department_instance
                            sample_instance.custodial_user = user_map_obj
                            sample_instance.current_step = "Accessioning"
                            sample_instance.accession_id = accession_id_instance
                            sample_instance.avail_at = current_date
                            sample_instance.accession_generated = False
                            sample_instance.receive_dt = accession_id_instance.receive_dt
                            sample_instance.receive_dt_timezone = accession_id_instance.receive_dt_timezone
                            sample_instance.collection_dt = accession_id_instance.collection_dt
                            sample_instance.collection_dt_timezone = accession_id_instance.collection_dt_timezone
                            sample_instance.created_by = user_map_obj
                            sample_instance.mod_by = user_map_obj
                            sample_instance.sample_status = "Initial"
                            if workflow_instance:
                                sample_instance.workflow_id = workflow_instance
                            list_sample.append(sample_instance)
                        if list_sample is not None:
                            Sample.objects.bulk_create(list_sample)
                            UtilClass.createRoutingInfoForSample(list_sample)
                        accession_type_instance = accession_id_instance.accession_type
                        SampleUtilClass.associateTest(test_id, sample_type_id, container_type_id, list_sample,
                                                      accession_type_instance)

    # This is to associate tests to samples
    @staticmethod
    def associateTest(test_id, sample_type_id, container_type_id, list_sample, accession_type_instance):
        if test_id  and list_sample  and sample_type_id  and container_type_id  and accession_type_instance :
            test_list = test_id.split('|')
            if test_list is not None:
                if len(test_list) > 0:
                    container_type_instance = ContainerType.objects.get(container_type_id=container_type_id)
                    if container_type_instance is None:
                        raise ValidationError("Container Type is Blank")
                    sample_type_instance = SampleType.objects.get(sample_type_id=sample_type_id)
                    if sample_type_instance is None:
                        raise ValidationError("Sample Type is blank")
                    child_sample_creation = container_type_instance.child_sample_creation
                    if len(test_list) > 1 and child_sample_creation is False:
                        raise ValidationError("Multiple tests cannot be assigned to this Container Type")

                    test_list_objects = Test.objects.filter(test_id__in=test_list)
                    list_sampletestmap = []
                    for sample in list_sample:
                        for test in test_list_objects:
                            sampletestmap_instance = SampleTestMap()
                            sampletestmap_instance.sample_id = sample
                            sampletestmap_instance.test_id = test
                            sampletestmap_instance.test_status = "Initial"
                            test_workflowstep_instance = TestWorkflowStep.objects.select_related(
                                'workflow_id'
                            ).filter(test_id=test,
                                     sample_type_id=sample_type_instance,
                                     container_type=container_type_instance,
                                     workflow_id__accession_type=accession_type_instance).first()
                            if test_workflowstep_instance is not None:
                                sampletestmap_instance.workflow_id = test_workflowstep_instance.workflow_id
                            list_sampletestmap.append(sampletestmap_instance)

                    if list_sampletestmap is not None:
                        SampleTestMap.objects.bulk_create(list_sampletestmap)

    # This is for creating child samples
    @staticmethod
    def create_child_sample(list_sample_info, user_id, copy_down_cols=None):
        if list_sample_info is not None and user_id is not None:
            list_sample_types = []
            list_container_types = []
            list_tests = []
            list_accession_types = []
            dict_sample_test_info = {}
            child_sample_list = []
            list_records_to_save_in_child_sample = []
            for sample_info in list_sample_info:
                try:
                    parent_sample_id = sample_info['parent_sample_id']
                    parent_sample_instance = Sample.objects.get(sample_id=parent_sample_id)
                    sample_type_instance = sample_info['sample_type']
                    if sample_type_instance is None:
                        raise ValidationError("Sample Type is blank")
                    list_sample_types.append(sample_type_instance)
                    container_type_instance = sample_info['container_type']
                    if container_type_instance is None:
                        raise ValidationError("Container Type is Blank")
                    list_container_types.append(container_type_instance)
                    copies = sample_info['copies']
                    test_id = sample_info['test_id']
                    previous_step = sample_info['previous_step']
                    current_step = sample_info['current_step']
                    next_step = sample_info['next_step']
                    pending_action = sample_info['pending_action']
                    sample_status = sample_info['sample_status']
                    smearing_process = sample_info.get('smearing_process')
                    list_tests.append(test_id)
                    accession_type_instance = parent_sample_instance.accession_id.accession_type
                    list_accession_types.append(accession_type_instance)
                    if parent_sample_instance is not None:
                        for i in range(int(copies)):
                            sample_instance = Sample()
                            current_date = datetime.now()
                            prefix = f"S-{current_date.strftime('%m%d%Y')}"
                            seq_no = UtilClass.get_next_sequence(prefix, "Sample", user_id.id)
                            sample_instance.sample_id = f"{prefix}-{seq_no:05}"
                            sample_instance.accession_id = parent_sample_instance.accession_id
                            sample_instance.sample_type = sample_type_instance
                            sample_instance.container_type = container_type_instance
                            if smearing_process is not None:
                                sample_instance.smearing_process = smearing_process
                            sample_instance.custodial_department = parent_sample_instance.custodial_department
                            sample_instance.custodial_user = parent_sample_instance.custodial_user
                            sample_instance.custodial_storage_id = parent_sample_instance.custodial_storage_id
                            sample_instance.previous_step = previous_step
                            sample_instance.current_step = current_step
                            sample_instance.next_step = next_step
                            sample_instance.pending_action = pending_action
                            sample_instance.sample_status = sample_status
                            sample_instance.avail_at = current_date
                            sample_instance.body_site = parent_sample_instance.body_site
                            sample_instance.sub_site = parent_sample_instance.sub_site
                            sample_instance.collection_method = parent_sample_instance.collection_method
                            sample_instance.receive_dt = parent_sample_instance.receive_dt
                            sample_instance.receive_dt_timezone = parent_sample_instance.receive_dt_timezone
                            sample_instance.collection_dt = parent_sample_instance.collection_dt
                            sample_instance.collection_dt_timezone = parent_sample_instance.collection_dt_timezone
                            if parent_sample_instance.accession_sample is not None:
                                sample_instance.accession_sample = parent_sample_instance.accession_sample
                            else:
                                sample_instance.accession_sample = parent_sample_instance
                            sample_instance.created_by = user_id
                            sample_instance.mod_by = user_id
                            sample_instance.part_no = parent_sample_instance.part_no
                            if 'Clinical' != parent_sample_instance.accession_id.accession_category:
                                if container_type_instance.gen_slide_seq:
                                    sample_instance.block_or_cassette_seq = parent_sample_instance.block_or_cassette_seq
                                    slide_seq_prefix = parent_sample_instance.accession_id.accession_id + "-" + parent_sample_instance.part_no + "-" + str(
                                        parent_sample_instance.block_or_cassette_seq)
                                    slide_seq = UtilClass.get_next_sequence(slide_seq_prefix, "Sample",
                                                                            user_id.id)
                                    sample_instance.slide_seq = str(slide_seq)
                                elif container_type_instance.gen_block_or_cassette_seq:
                                    block_or_cassette_seq_prefix = parent_sample_instance.accession_id.accession_id + "-" + parent_sample_instance.part_no
                                    block_cassette_seq = UtilClass.get_next_sequence(block_or_cassette_seq_prefix,
                                                                                     "Sample", user_id.id)
                                    sample_instance.block_or_cassette_seq = str(block_cassette_seq)
                            child_sample_list.append(sample_instance)

                            dict_sample_test_info[sample_instance] = test_id
                            instance_child_sample_model = ChildSample()
                            instance_child_sample_model.destination_sample = sample_instance
                            instance_child_sample_model.source_sample = parent_sample_instance
                            list_records_to_save_in_child_sample.append(instance_child_sample_model)
                            if copy_down_cols is not None:
                                copy_down_cols_sets = copy_down_cols.split("|")
                                if copy_down_cols_sets is not None:
                                    for items in copy_down_cols_sets:
                                        items_set = items.split(":")
                                        if items_set is not None:
                                            app_model_name = items_set[0]
                                            column_name_set = items_set[1]
                                            col_name_list = column_name_set.split(",")
                                            if app_model_name is not None:
                                                try:
                                                    app_name = app_model_name.split("-")[0]
                                                    model_name = app_model_name.split("-")[1]
                                                    ModelClass = apps.get_model(app_name, model_name)
                                                    if ModelClass:
                                                        parent_model_instance = ModelClass.objects.get(
                                                            sample_id=parent_sample_id)
                                                        if parent_model_instance is not None and col_name_list is not None:
                                                            model_instance = ModelClass()
                                                            for col_name in col_name_list:
                                                                col_val = getattr(parent_model_instance,
                                                                                  col_name,
                                                                                  "")
                                                                if col_val is not None:
                                                                    setattr(model_instance, col_name, col_val)
                                                            setattr(model_instance, "sample_id", sample_instance)
                                                            model_instance.save()
                                                except Exception as e:
                                                    raise ValidationError(
                                                        f"Parent Sample Record not found for this Model : {model_name.__class__.__name__}")
                except Sample.DoesNotExist:
                    raise ValidationError(f"Following parent_sample_ids does not exists: {parent_sample_id}")

            if child_sample_list is not None and len(child_sample_list) > 0:
                Sample.objects.bulk_create(child_sample_list)
                UtilClass.createRoutingInfoForSample(child_sample_list)
            if list_records_to_save_in_child_sample is not None and len(list_records_to_save_in_child_sample) > 0:
                ChildSample.objects.bulk_create(list_records_to_save_in_child_sample)
            SampleUtilClass.associateTestWithCreatedChildSamples(list_sample_types, list_container_types,
                                                                 list_tests, dict_sample_test_info,
                                                                 list_accession_types)
            return child_sample_list

    # This is for associating Tests to child samples
    @staticmethod
    def associateTestWithCreatedChildSamples(list_sample_types, list_container_types, list_tests, dict_sample_test_info,
                                             list_accession_types):
        if list_sample_types and list_container_types and list_tests and dict_sample_test_info and list_accession_types:
            all_tests = ','.join(list_tests)
            list_all_tests = all_tests.split(',')
            if len(list_all_tests) > 0:
                test_list_objects = Test.objects.filter(test_id__in=list_all_tests)

                Sample = apps.get_model('sample', 'Sample')
                sample_ids = [s.sample_id for s in dict_sample_test_info.keys()]
                samples_with_workflow = Sample.objects.filter(sample_id__in=sample_ids).annotate(
                    effective_workflow_id=Case(
                        When(accession_sample_id__isnull=True, then=F('workflow_id')),
                        When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                        default=Value(None),
                        output_field=IntegerField()
                    )
                )
                workflow_map = dict(samples_with_workflow.values_list('sample_id', 'effective_workflow_id'))

                list_test_workflowsteps = TestWorkflowStep.objects.select_related(
                    'workflow_id'
                ).filter(test_id__in=test_list_objects,
                         sample_type_id__in=list_sample_types,
                         container_type__in=list_container_types,
                         workflow_id__accession_type__in=list_accession_types,
                         workflow_step_id__workflow_type='WetLab')
            list_sample_test_instance = []
            for sample, tests in dict_sample_test_info.items():
                child_sample_creation = sample.container_type.child_sample_creation
                test_list = tests.split(",")
                if len(test_list) > 1 and child_sample_creation is False:
                    raise ValidationError("Multiple tests cannot be assigned to this Container Type")
                effective_workflow_id = workflow_map.get(sample.sample_id)
                for test in test_list:
                    test_instance = test_list_objects.filter(test_id=test).first()

                    sample_test_map_instance = SampleTestMap()
                    sample_test_map_instance.sample_id = sample
                    sample_test_map_instance.test_id = test_instance
                    sample_test_map_instance.test_status = "Pending"
                    if not effective_workflow_id:
                        test_workflowstep_instance = list_test_workflowsteps.filter(test_id=test_instance,
                                                                                    sample_type_id=sample.sample_type,
                                                                                    container_type=sample.container_type,
                                                                                    workflow_id__accession_type=sample.accession_id.accession_type).first()

                        sample_test_map_instance.workflow_id = test_workflowstep_instance.workflow_id

                    list_sample_test_instance.append(sample_test_map_instance)
            SampleTestMap.objects.bulk_create(list_sample_test_instance)

    @staticmethod
    def create_samples_from_existing_list_of_samples(list_template_samples, request, obj):
        if request and list_template_samples and obj:
            list_samples_to_be_created = []
            list_sample_test_map = []
            user_map_obj = request.user
            qs_sample_test_info = SampleTestMap.objects.filter(sample_id__in=list_template_samples)
            for sample in list_template_samples:
                sample_instance = Sample()
                current_date = datetime.now()
                prefix = f"S-{current_date.strftime('%m%d%Y')}"
                seq_no = UtilClass.get_next_sequence(prefix, "Sample", user_map_obj.id)
                sample_instance.sample_id = f"{prefix}-{seq_no:05}"
                if sample.part_no:
                    sample_instance.part_no = sample.part_no
                if sample.slide_seq:
                    sample_instance.block_or_cassette_seq = sample.block_or_cassette_seq
                    slide_seq_prefix = obj.accession_id + "-" + sample_instance.part_no + "-" + str(
                        sample_instance.block_or_cassette_seq)
                    slide_seq = UtilClass.get_next_sequence(slide_seq_prefix, "Sample",
                                                            user_map_obj.id)
                    sample_instance.slide_seq = str(slide_seq)
                else:
                    if sample.block_or_cassette_seq:
                        block_or_cassette_seq_prefix = obj.accession_id + "-" + sample_instance.part_no
                        block_cassette_seq = UtilClass.get_next_sequence(block_or_cassette_seq_prefix,
                                                                         "Sample", user_map_obj.id)
                        sample_instance.block_or_cassette_seq = str(block_cassette_seq)

                if sample.sample_type:
                    sample_instance.sample_type = sample.sample_type
                if sample.container_type:
                    sample_instance.container_type = sample.container_type

                current_jobtype = request.session.get('currentjobtype', '')
                if current_jobtype:
                    department_id = JobType.objects.filter(name=current_jobtype).values_list('departmentid',
                                                                                             flat=True).first()
                    if department_id:
                        department_instance = Department.objects.get(id=department_id)
                        if department_instance is not None:
                            sample_instance.custodial_department = department_instance
                if user_map_obj:
                    sample_instance.custodial_user = user_map_obj
                sample_instance.current_step = "Accessioning"
                sample_instance.avail_at = datetime.now()
                sample_instance.accession_generated = False
                sample_instance.accession_id = obj
                sample_instance.created_by = user_map_obj
                sample_instance.mod_by = user_map_obj
                sample_instance.sample_status = "Initial"
                if sample.previous_step:
                    sample_instance.previous_step = sample.previous_step
                if sample.current_step:
                    sample_instance.current_step = sample.current_step
                if sample.next_step:
                    sample_instance.next_step = sample.next_step
                if sample.accession_sample:
                    sample_instance.accession_sample = sample.accession_sample
                if sample.accession_generated:
                    sample_instance.accession_generated = sample.accession_generated
                if sample.pending_action:
                    sample_instance.pending_action = sample.pending_action
                if sample.body_site:
                    sample_instance.body_site = sample.body_site
                if sample.sub_site:
                    sample_instance.sub_site = sample.sub_site
                if sample.collection_method:
                    sample_instance.collection_method = sample.collection_method
                if sample.workflow_id:
                    sample_instance.workflow_id = sample.workflow_id
                if sample.size:
                    sample_instance.size = sample.size
                if sample.pieces:
                    sample_instance.pieces = sample.pieces
                if sample.num_of_blocks:
                    sample_instance.num_of_blocks = sample.num_of_blocks
                if sample.num_of_slides:
                    sample_instance.num_of_slides = sample.num_of_slides
                if sample.num_of_manualsmear_slides:
                    sample_instance.num_of_manualsmear_slides = sample.num_of_manualsmear_slides
                if sample.num_of_thinprep_slides:
                    sample_instance.num_of_thinprep_slides = sample.num_of_thinprep_slides
                if sample.grossing_comments:
                    sample_instance.grossing_comments = sample.grossing_comments
                if sample.gross_code:
                    sample_instance.gross_code = sample.gross_code
                if sample.gross_description:
                    sample_instance.gross_description = sample.gross_description
                if sample.descriptive:
                    sample_instance.descriptive = sample.descriptive
                if sample.isvisible:
                    sample_instance.isvisible = sample.isvisible
                if sample.smearing_process:
                    sample_instance.isvisible = sample.smearing_process
                if sample.label_count:
                    sample_instance.label_count = sample.label_count

                list_samples_to_be_created.append(sample_instance)
                if qs_sample_test_info:
                    filter_qs_sample_test_info = qs_sample_test_info.filter(sample_id=sample)
                    for sample_test_instance in filter_qs_sample_test_info:
                        new_sample_test_instance = SampleTestMap()
                        new_sample_test_instance.sample_id = sample_instance
                        new_sample_test_instance.test_id = sample_test_instance.test_id
                        new_sample_test_instance.test_status = "Initial"
                        new_sample_test_instance.workflow_id = sample_test_instance.workflow_id
                        list_sample_test_map.append(new_sample_test_instance)
            if list_samples_to_be_created:
                Sample.objects.bulk_create(list_samples_to_be_created)
                UtilClass.createRoutingInfoForSample(list_samples_to_be_created)

            if list_sample_test_map:
                SampleTestMap.objects.bulk_create(list_sample_test_map)