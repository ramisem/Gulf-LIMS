import importlib
import inspect
import threading
from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models import Q, When, Value, Case, IntegerField, F
from django_auto_logout.utils import now

import util.util
from accessioning.models import Accession, BioPharmaAccession
from analysis.models import ReportOptionDtl, ReportSignOut, Attachment, ReportOption, MergeReporting, MergeReportingDtl
from controllerapp.settings import *
from ihcworkflow.forms import QCStatusForm
from ihcworkflow.models import IhcWorkflow
from masterdata.models import ProjectEmailMap, EmailConfig
from process.models import ContainerType, SampleType
from sample.models import SampleTestMap, Sample
from sample.util import SampleUtilClass
from security.models import User
from util.util import generate_automatic_sample_labels, UtilClass
from workflows.models import Workflow, ModalityModelMap
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from hl7.sender import send_single_hl7
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

MODEL_APP_MAP = {model.__name__: model._meta.app_label for model in apps.get_models()}


def get_app_name_from_model(model_name):
    return MODEL_APP_MAP.get(model_name)


class GenericAction:
    def generic_action_call(self, request, queryset, desired_action, action_desc, prep_type_dict=None):
        invalid_samples = queryset.exclude(pending_action=desired_action)
        sample_ids = queryset.values_list('sample_id', flat=True)
        if invalid_samples.exists():
            sample_names = ", ".join(str(sample) for sample in invalid_samples)
            messages.error(request, f"The following samples are not pending for '{action_desc}'\n: {sample_names}")
            return '', ''
        else:
            Sample = apps.get_model('sample', 'Sample')
            SampleTestMap = apps.get_model('sample', 'SampleTestMap')
            sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
            sample_type_ids = sample_maps.values_list('sample_type_id', flat=True).distinct()
            container_type_ids = sample_maps.values_list('container_type_id', flat=True).distinct()
            current_step_ids = sample_maps.values_list('current_step', flat=True).distinct()

            sample_test_maps = SampleTestMap.objects.filter(sample_id_id__in=sample_ids)
            test_ids = sample_test_maps.values_list('test_id_id', flat=True).distinct()
            workflow_ids = sample_test_maps.values_list('workflow_id_id', flat=True).distinct()

            samples_with_workflow = Sample.objects.filter(sample_id__in=sample_ids).annotate(
                effective_workflow_id=Case(
                    When(accession_sample_id__isnull=True, then=F('workflow_id')),
                    When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                    default=Value(None),
                    output_field=IntegerField()
                )
            )

            workflow_map = dict(
                samples_with_workflow.values_list('sample_id', 'effective_workflow_id')
            )

            # Get distinct workflow_ids for WorkflowStep query
            workflow_ids_from_samples = samples_with_workflow.values_list('effective_workflow_id',
                                                                          flat=True).distinct()

            TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
            WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
            workflow_steps = WorkflowStep.objects.filter(
                workflow_id__in=workflow_ids_from_samples,
                workflow_type='WetLab',
                step_id__in=current_step_ids,
            ).annotate(
                test_workflow_step_id=Value(None, output_field=IntegerField()),
                sample_type_id=Value(None, output_field=IntegerField()),
                container_type_id=Value(None, output_field=IntegerField()),
                test_id=Value(None, output_field=IntegerField()),
                workflow_step_id__workflow_step_id=F('workflow_step_id'),
                workflow_step_id__workflow_id=F('workflow_id'),
                workflow_step_id__step_id=F('step_id'),
                workflow_step_id__step_no=F('step_no'),
                workflow_step_id__department=F('department'),
            ).values(
                'test_workflow_step_id',
                'sample_type_id',
                'container_type_id',
                'test_id',
                'workflow_id',
                'workflow_step_id__workflow_step_id',
                'workflow_step_id__workflow_id',
                'workflow_step_id__step_id',
                'workflow_step_id__step_no',
                'workflow_step_id__department',
            )

            testqueryset = TestWorkflowStep.objects.select_related(
                'workflow_step_id'
            ).filter(
                sample_type_id__in=sample_type_ids,
                container_type_id__in=container_type_ids,
                test_id__in=test_ids,
                workflow_id__in=workflow_ids,
                workflow_step_id__workflow_id__in=workflow_ids,
                workflow_step_id__step_id__in=current_step_ids,
                workflow_step_id__workflow_type='WetLab',
            ).values(
                'test_workflow_step_id',
                'sample_type_id',
                'container_type_id',
                'test_id',
                'workflow_id',
                'workflow_step_id__workflow_step_id',
                'workflow_step_id__workflow_id',
                'workflow_step_id__step_id',
                'workflow_step_id__step_no',
                'workflow_step_id__department',
            )
            workflow_step_dict_direct = {
                (entry['workflow_id'], entry['workflow_step_id__step_id']): entry['workflow_step_id__workflow_step_id']
                for entry in workflow_steps
            }
            workflow_step_dict = {
                (entry['sample_type_id'], entry['container_type_id'], entry['test_id'], entry['workflow_id'],
                 entry['workflow_step_id__step_id']): entry['test_workflow_step_id']
                for entry in testqueryset
            }

            sample_test_map_dict = {}
            for sample_map in sample_maps:
                try:
                    sample = sample_map
                    sample_test_map = sample_test_maps.filter(sample_id_id=sample.sample_id).first()
                    if not sample_test_map:
                        continue
                    effective_workflow_id = workflow_map.get(sample_map.sample_id)
                    key_direct = (effective_workflow_id, sample_map.current_step)
                    key_test = (
                        sample_map.sample_type_id,
                        sample_map.container_type_id,
                        sample_test_map.test_id_id,
                        sample_test_map.workflow_id_id,
                        sample_map.current_step,
                    )

                    if effective_workflow_id and workflow_step_dict_direct.get(key_direct):
                        # Sample-level workflow takes precedence
                        sample_test_map_dict[sample_map] = workflow_step_dict_direct[key_direct]
                    elif workflow_step_dict.get(key_test):
                        sample_test_map_dict[sample_map] = workflow_step_dict[key_test]

                except Exception as e:
                    print(e)
            testworkflowstepmap_ids = list(sample_test_map_dict.values())
            TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')

            action_maps = TestWorkflowStepActionMap.objects.filter(
                Q(testwflwstepmap_id__in=testworkflowstepmap_ids) |
                Q(workflow_step_id_id__in=testworkflowstepmap_ids),
                action=desired_action
            ).values('testwflwstepmap_id', 'workflow_step_id_id', 'sequence', 'action_method')

            action_map_dict = {}
            for entry in action_maps:
                key = entry['workflow_step_id_id'] if entry['workflow_step_id_id'] else entry['testwflwstepmap_id']
                action_map_dict[key] = (entry['sequence'], entry['action_method'])

            unique_methods = set(action[1] for action in action_map_dict.values() if action[1])
            if len(unique_methods) == 0:
                messages.error(request, "Error: No Action methods found for the selected samples.")
                return '', ''
            if len(unique_methods) != 1:
                messages.error(request, "Error: Different action methods found for selected samples.")
                return '', ''
            action_method = unique_methods.pop()
            method = getattr(self, action_method, None)
            if callable(method):
                args = inspect.signature(method).parameters
                if 'prep_type_dict' in args:
                    apply_pending_action, custom_msg, is_error = method(request, queryset, sample_maps, prep_type_dict)
                else:
                    apply_pending_action, custom_msg, is_error = method(request, queryset, sample_maps)
            else:
                messages.error(request, f"'{action_method}' is not a callable method.")
                return '', ''
            if is_error == 'Y':
                messages.error(request, custom_msg)
                return '', ''

            form_type = ''
            if '##' in apply_pending_action:
                apply_pending_action, form_type = apply_pending_action.split('##', 1)

            if form_type == 'render_form':
                return form_type, custom_msg

            if apply_pending_action == 'Y':

                next_actions = TestWorkflowStepActionMap.objects.filter(
                    Q(testwflwstepmap_id__in=testworkflowstepmap_ids) |
                    Q(workflow_step_id_id__in=testworkflowstepmap_ids),
                    sequence__in=[seq + 1 for seq, _ in action_map_dict.values()]
                ).values('testwflwstepmap_id', 'workflow_step_id_id', 'action')

                next_action_dict = {
                    entry['workflow_step_id_id'] if entry['workflow_step_id_id'] else entry['testwflwstepmap_id']:
                        entry['action']
                    for entry in next_actions
                }

                update_data = []
                sample_obj_dict = {sample.sample_id: sample for sample in sample_maps}
                for sample in sample_maps:
                    testwflwstepmap_id = sample_test_map_dict.get(sample)
                    if testwflwstepmap_id:
                        next_action = next_action_dict.get(testwflwstepmap_id, None)
                        sample_obj = sample_obj_dict.get(sample.sample_id)
                        if sample_obj:
                            sample_obj.pending_action = next_action
                            if next_action == 'MoveToStorage':
                                sample_obj.previous_step = sample_obj.current_step
                                sample_obj.current_step = 'Storage'
                                sample_obj.next_step = None
                            elif "complete_imaging_method" == action_method:
                                sample_obj.previous_step = sample_obj.current_step
                                sample_obj.current_step = 'Historical'
                            update_data.append(sample_obj)
                if update_data:
                    old_samples = Sample.objects.in_bulk([s.sample_id for s in update_data])
                    Sample.objects.bulk_update(update_data,
                                               ['pending_action', 'previous_step', 'current_step', 'next_step'])
                    UtilClass.createRoutingInfoForSample(update_data, old_samples)
            if custom_msg:
                messages.success(request, mark_safe(custom_msg + ' ' + f"{action_desc} action completed successfully."))
            else:
                messages.success(request, mark_safe(f"{action_desc} action completed successfullly."))
            if form_type == 'render_submit':
                return form_type, custom_msg

    def generic_action_call_for_report_option_routing(self, request, queryset, desired_action, action_desc,
                                                      sub_action=None):

        # This is the generic action for all report option routing related functionalities

        invalid_report_options = queryset.exclude(pending_action=desired_action)
        report_option_ids = queryset.values_list('report_option_id', flat=True)
        if invalid_report_options.exists():
            report_options = ", ".join(str(report_options) for report_options in report_option_ids)
            raise Exception(f"Selected Test(s) are not pending for '{action_desc}'\n: {report_options}")
        else:
            ReportOption = apps.get_model('analysis', 'ReportOption')
            Sample = apps.get_model('sample', 'Sample')
            report_option_obj_list = ReportOption.objects.filter(report_option_id__in=report_option_ids)
            if not report_option_obj_list:
                raise Exception("No Report Option IDs found")

            root_sample_id_list = report_option_obj_list.values_list('root_sample_id', flat=True).distinct()
            sample_maps = Sample.objects.filter(sample_id__in=root_sample_id_list)
            sample_type_ids = sample_maps.values_list('sample_type_id', flat=True).distinct()
            container_type_ids = sample_maps.values_list('container_type_id', flat=True).distinct()
            current_step_ids = report_option_obj_list.values_list('current_step', flat=True).distinct()
            test_ids = report_option_obj_list.values_list('test_id_id', flat=True).distinct()
            sample_test_maps = SampleTestMap.objects.filter(sample_id_id__in=sample_maps, test_id_id__in=test_ids)
            workflow_ids = sample_test_maps.values_list('workflow_id_id', flat=True).distinct()

            samples_with_workflow = Sample.objects.filter(sample_id__in=root_sample_id_list).annotate(
                effective_workflow_id=Case(
                    When(accession_sample_id__isnull=True, then=F('workflow_id')),
                    When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                    default=Value(None),
                    output_field=IntegerField()
                )
            )
            workflow_map = dict(
                samples_with_workflow.values_list('sample_id', 'effective_workflow_id')
            )

            # Get distinct workflow_ids for WorkflowStep query
            workflow_ids_from_samples = samples_with_workflow.values_list('effective_workflow_id',
                                                                          flat=True).distinct()

            TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
            WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
            workflow_steps = WorkflowStep.objects.filter(
                workflow_id__in=workflow_ids_from_samples,
                workflow_type='DryLab',
                step_id__in=current_step_ids,
            ).annotate(
                test_workflow_step_id=Value(None, output_field=IntegerField()),
                sample_type_id=Value(None, output_field=IntegerField()),
                container_type_id=Value(None, output_field=IntegerField()),
                test_id=Value(None, output_field=IntegerField()),
                workflow_step_id__workflow_step_id=F('workflow_step_id'),
                workflow_step_id__workflow_id=F('workflow_id'),
                workflow_step_id__step_id=F('step_id'),
                workflow_step_id__step_no=F('step_no'),
                workflow_step_id__department=F('department'),
            ).values(
                'test_workflow_step_id',
                'sample_type_id',
                'container_type_id',
                'test_id',
                'workflow_id',
                'workflow_step_id__workflow_step_id',
                'workflow_step_id__workflow_id',
                'workflow_step_id__step_id',
                'workflow_step_id__step_no',
                'workflow_step_id__department',
            )
            testqueryset = TestWorkflowStep.objects.select_related(
                'workflow_step_id'
            ).filter(
                sample_type_id__in=sample_type_ids,
                container_type_id__in=container_type_ids,
                test_id__in=test_ids,
                workflow_id__in=workflow_ids,
                workflow_step_id__workflow_id__in=workflow_ids,
                workflow_step_id__step_id__in=current_step_ids,
                workflow_step_id__workflow_type='DryLab',
            ).values(
                'test_workflow_step_id',
                'sample_type_id',
                'container_type_id',
                'test_id',
                'workflow_id',
                'workflow_step_id__workflow_step_id',
                'workflow_step_id__workflow_id',
                'workflow_step_id__step_id',
                'workflow_step_id__step_no',
                'workflow_step_id__department',
            )
            workflow_step_dict_direct = {
                (entry['workflow_id'], entry['workflow_step_id__step_id']): entry['workflow_step_id__workflow_step_id']
                for entry in workflow_steps
            }
            workflow_step_dict = {
                (entry['sample_type_id'], entry['container_type_id'], entry['test_id'], entry['workflow_id'],
                 entry['workflow_step_id__step_id']): entry['test_workflow_step_id']
                for entry in testqueryset
            }
            report_option_dict = {}
            for report_option in report_option_obj_list:
                try:
                    sample = report_option.root_sample_id
                    sample_test_map = sample_test_maps.filter(sample_id_id=sample.sample_id,
                                                              test_id_id=report_option.test_id.test_id).first()
                    if not sample_test_map and not report_option.workflow_id:
                        continue
                    effective_workflow_id = workflow_map.get(sample.sample_id)
                    if report_option.workflow_id:
                        key_direct = (effective_workflow_id, report_option.current_step)
                    else:
                        key_test = (
                            sample.sample_type_id,
                            sample.container_type_id,
                            sample_test_map.test_id_id,
                            sample_test_map.workflow_id_id,
                            report_option.current_step,
                        )
                    if effective_workflow_id and workflow_step_dict_direct.get(key_direct):
                        # Sample-level workflow takes precedence
                        report_option_dict[report_option] = workflow_step_dict_direct[key_direct]
                    elif workflow_step_dict.get(key_test):
                        report_option_dict[report_option] = workflow_step_dict[key_test]



                except Exception as e:
                    print(e)
            testworkflowstepmap_ids = list(report_option_dict.values())
            TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')

            action_maps = TestWorkflowStepActionMap.objects.filter(
                Q(testwflwstepmap_id__in=testworkflowstepmap_ids) |
                Q(workflow_step_id_id__in=testworkflowstepmap_ids),
                action=desired_action
            ).values('testwflwstepmap_id', 'workflow_step_id_id', 'sequence', 'action_method')

            action_map_dict = {}
            for entry in action_maps:
                key = entry['workflow_step_id_id'] if entry['workflow_step_id_id'] else entry['testwflwstepmap_id']
                action_map_dict[key] = (entry['sequence'], entry['action_method'])

            unique_methods = set(action[1] for action in action_map_dict.values() if action[1])
            if len(unique_methods) == 0:
                raise Exception("No Action methods found for the selected report option(s)")

            if len(unique_methods) != 1:
                raise Exception("Different action methods found for selected report option(s)")

            action_method = unique_methods.pop()
            method = getattr(self, action_method, None)
            if callable(method):
                args = inspect.signature(method).parameters
                if 'sub_action' in args:
                    apply_pending_action, custom_msg, is_error, redirect_to_url = method(request, queryset,
                                                                                         report_option_obj_list,
                                                                                         sub_action)
                else:
                    apply_pending_action, custom_msg, is_error, redirect_to_url = method(request, queryset)
            else:
                raise Exception(f"'{action_method}' is not a callable method")

            if is_error == 'Y':
                raise Exception(custom_msg)

            form_type = ''
            if '##' in apply_pending_action:
                apply_pending_action, form_type = apply_pending_action.split('##', 1)

            if form_type == 'render_form':
                return form_type, custom_msg

            if apply_pending_action == 'Y':
                next_actions = TestWorkflowStepActionMap.objects.filter(
                    Q(testwflwstepmap_id__in=testworkflowstepmap_ids) |
                    Q(workflow_step_id_id__in=testworkflowstepmap_ids),
                    sequence__in=[seq + 1 for seq, _ in action_map_dict.values()]
                ).values('testwflwstepmap_id', 'workflow_step_id_id', 'action')

                next_action_dict = {
                    entry['workflow_step_id_id'] if entry['workflow_step_id_id'] else entry['testwflwstepmap_id']:
                        entry['action']
                    for entry in next_actions
                }
                update_data = []
                for report_option in report_option_obj_list:
                    testwflwstepmap_id = report_option_dict.get(report_option)
                    if testwflwstepmap_id:
                        next_action = next_action_dict.get(testwflwstepmap_id, None)
                        update_data.append((report_option.report_option_id, next_action))
                if update_data:
                    bulk_update_queryset = [
                        ReportOption(report_option_id=report_option_id, pending_action=next_action)
                        for report_option_id, next_action in update_data
                    ]
                    ReportOption.objects.bulk_update(bulk_update_queryset, ['pending_action'])
            if custom_msg:
                messages.success(request, custom_msg + ' ' + f"{action_desc} action completed successfully.")
            else:
                messages.success(request, f"{action_desc} action completed successfullly.")

            if redirect_to_url:
                return redirect_to_url

            if form_type == 'render_submit':
                return form_type, custom_msg

    def perform_microtomy_method(self, request, queryset, sample_maps):
        child_samples = []  # Store all child Sample objects
        list_sample_info_for_microtomy = []
        user_map_obj = User.objects.get(username=request.user.username)
        sampletestmap_ids_to_update = []
        container_type = ContainerType.objects.get(container_type=CONTAINER_TYPE_SLIDE_UNSTAINED)
        for parent_sample in sample_maps:
            sample_test_maps = SampleTestMap.objects.filter(sample_id=parent_sample).exclude(
                microtomy_completed=True).order_by("sample_id")

            if not sample_test_maps.exists():
                continue  # Skip if no test is mapped to the sample
            for test_map in sample_test_maps:
                test_id = str(test_map.test_id.test_id)
                list_sample_info_for_microtomy.append(
                    {'parent_sample_id': parent_sample, 'sample_type': parent_sample.sample_type,
                     'container_type': container_type, 'copies': '1',
                     'test_id': test_id, 'previous_step': 'Microtomy',
                     'current_step': 'Staining', 'next_step': 'Imaging',
                     'pending_action': 'SendToStaining', 'sample_status': 'In-progress'})
                sampletestmap_ids_to_update.append(test_map.sample_test_map_id)

        with transaction.atomic():
            child_samples = SampleUtilClass.create_child_sample(list_sample_info_for_microtomy, user_map_obj)
            if child_samples:
                t1 = threading.Thread(target=generate_automatic_sample_labels,
                                      args=(request, [sample.pk for sample in child_samples]))
                t1.start()
            SampleTestMap.objects.filter(sample_test_map_id__in=sampletestmap_ids_to_update).update(
                microtomy_completed=True)
        self.complete_microtomy_method(request, queryset, child_samples)
        return 'Y', 'Child sample(s) routed to Staining.', 'N'

    def move_tostorage_method(self, request, queryset, sample_maps):
        messages.success('Move to Storage is successful')

    def complete_microtomy_method(self, request, queryset, child_samples):
        sample_maps = Sample.objects.filter(pk__in=[obj.pk for obj in child_samples])
        if sample_maps.exists():
            samples_with_workflow = sample_maps.annotate(
                effective_workflow_id=Case(
                    When(accession_sample_id__isnull=True, then=F('workflow_id')),
                    When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                    default=Value(None),
                    output_field=IntegerField()
                )
            )
            workflow_map_sample = dict(samples_with_workflow.values_list('sample_id', 'effective_workflow_id'))

            # Get workflow names for direct workflow_ids
            workflow_ids_direct = list(filter(None, workflow_map_sample.values()))
            workflow_map_direct = {
                w.workflow_id: w.workflow_name
                for w in Workflow.objects.filter(workflow_id__in=workflow_ids_direct)
            }

            # Inline logic to get workflow_map_testmap (from SampleTestMap)
            workflow_ids_testmap = SampleTestMap.objects.filter(
                sample_id__in=sample_maps.values_list('sample_id', flat=True)
            ).values_list('workflow_id_id', flat=True).distinct()

            # Step 2: Build the mapping of ID → name
            workflow_map_testmap = {
                w.workflow_id: w.workflow_name
                for w in Workflow.objects.filter(workflow_id__in=workflow_ids_testmap)
            }

            workflow_names = list(workflow_map_direct.values()) + list(workflow_map_testmap.values())

            # Get workflow-specific modality table mapping
            modality_map = {
                m.modality: m.model
                for m in ModalityModelMap.objects.filter(modality__in=workflow_names)
            }

            bulk_insert_map = {}
            successfully_inserted_samples = set()
            for sample in sample_maps:
                effective_workflow_id = workflow_map_sample.get(sample.sample_id)
                if effective_workflow_id:
                    workflow_name = workflow_map_direct.get(effective_workflow_id)
                else:
                    workflow_id = SampleTestMap.objects.filter(
                        sample_id=sample.sample_id
                    ).values_list("workflow_id_id", flat=True).first()
                    workflow_name = workflow_map_testmap.get(workflow_id)

                if workflow_name:
                    model = modality_map.get(workflow_name)
                    if model:
                        app_name = get_app_name_from_model(model)

                        if (app_name, model) not in bulk_insert_map:
                            bulk_insert_map[(app_name, model)] = []

                        bulk_insert_map[(app_name, model)].append(sample.sample_id)

            with connection.cursor() as cursor:
                for (app_name, model), sample_ids in bulk_insert_map.items():
                    table_name = f"{app_name}_{model}"
                    query = f"INSERT INTO {table_name} (sample_ptr_id) VALUES (%s) ON CONFLICT DO NOTHING;"
                    values = [(sample_id,) for sample_id in sample_ids]  # Convert to tuple list
                    cursor.executemany(query, values)  # Bulk insert
                    successfully_inserted_samples.update(sample_ids)

            if successfully_inserted_samples:
                Sample.objects.filter(sample_id__in=successfully_inserted_samples).update(isvisible=False)

    def send_to_staining_method(self, request, queryset, sample_maps):

        # Send HL7 messages for each sample

        executor = ThreadPoolExecutor(max_workers=settings.HL7_THREADPOOL_MAX_WORKERS_SENDER)
        if sample_maps:
            qs_tests = SampleTestMap.objects.filter(sample_id__in=list(sample_maps))
            for sample in sample_maps:
                slide_id = f"{sample.accession_id.accession_id}-{sample.part_no}-{sample.block_or_cassette_seq}-{sample.slide_seq}"
                accession_id = sample.accession_id.accession_id
                if qs_tests:
                    sample_test = qs_tests.filter(sample_id=sample.sample_id).first()
                    if sample_test:
                        test_name = sample_test.test_id.test_name
                        executor.submit(send_single_hl7, slide_id, accession_id, test_name)

            executor.shutdown(wait=False)
        return 'N', '', 'N'

    def start_staining_method(self, request, queryset, sample_maps):
        with transaction.atomic():
            qs_ihcworkflow = IhcWorkflow.objects.filter(sample_id__in=[sample.sample_id for sample in sample_maps])
            if qs_ihcworkflow:
                qs_ihcworkflow.update(stain_startdt=now(), pending_action="CompleteStaining",
                                      staining_status="In Progress")
        return 'Y', '', 'N'

    def complete_staining_method(self, request, queryset, sample_maps):
        with transaction.atomic():
            IhcWorkflow.objects.filter(sample_id__in=[sample.sample_id for sample in sample_maps]).update(
                stain_enddt=now(), pending_action=None, staining_status="Complete")
        return 'Y', '', 'N'

    def start_imaging_method(self, request, queryset, sample_maps):
        with transaction.atomic():
            IhcWorkflow.objects.filter(sample_id__in=[sample.sample_id for sample in sample_maps]).update(
                image_startdt=now())
        return 'Y', '', 'N'

    def complete_imaging_method(self, request, queryset, sample_maps):
        with transaction.atomic():
            IhcWorkflow.objects.filter(sample_id__in=[sample.sample_id for sample in sample_maps]).update(
                image_enddt=now())
            util_instance = util.util.UtilClass
            util_instance.completewetlab(self, request, queryset)
        return 'Y', '', 'N'

    def perform_imageqc_method(self, request, queryset, sample_maps):
        if 'apply' in request.POST:
            form = QCStatusForm(request.POST)
            if form.is_valid():
                qc_status = form.cleaned_data['qc_status']
                if qc_status == 'Pass':
                    queryset.update(image_qcstatus=qc_status, image_qcdate=now())
                    return 'Y##render_submit', '', ''
                elif qc_status == 'Fail':
                    queryset.update(image_startdt=None, pending_action='StartImaging')
                    return 'N##render_submit', '', ''
        else:
            form = QCStatusForm()
            return 'N##render_form', form, ''

    def create_cassette_method(self, request, queryset, sample_maps):
        # Creates cassettes for the given queryset of parent samples.
        SampleTestMap = apps.get_model('sample', 'SampleTestMap')
        ContainerType = apps.get_model('process', 'ContainerType')
        container_type = ContainerType.objects.get(container_type='Cassette')
        user = request.user if request.user.is_authenticated else None
        user_map_obj = User.objects.get(username=request.user.username)

        if not user or not user.is_authenticated:
            return "N", "User not authenticated, cannot generate cassette sequence.", "Y"

        errors = {}
        success_count = 0
        all_child_samples_to_create = []

        try:
            with transaction.atomic():  # Transaction starts here
                for parent_sample in queryset:
                    num_blocks = parent_sample.num_of_blocks
                    num_slides = parent_sample.num_of_slides
                    gross_desc = parent_sample.gross_description
                    sample_id = parent_sample.sample_id

                    if num_blocks is None or num_blocks <= 0:
                        errors[sample_id] = "Invalid number of blocks."
                        continue

                    if num_slides is None or num_slides <= 0:
                        errors[sample_id] = "Invalid number of slides."
                        continue

                    parent_test_maps = SampleTestMap.objects.filter(sample_id=parent_sample).exclude(
                        test_status='Cancelled')
                    num_test_maps = parent_test_maps.count()

                    if num_slides != num_test_maps:
                        errors[
                            sample_id] = "Slide# and test count mismatch found. Number of tests associated with a selected sample(s) should match with the Slide# provided for that sample."
                        continue

                    if gross_desc is None or gross_desc == '':
                        errors[sample_id] = "Gross description is not provided."
                        continue

                    child_samples_to_create = []

                    for _ in range(num_blocks):
                        test_id = ''
                        for stm in parent_test_maps:
                            test_id = test_id + "," + str(stm.test_id_id)
                        if test_id:
                            test_id = test_id[1:]
                        child_samples_to_create.append(
                            {'parent_sample_id': parent_sample, 'sample_type': parent_sample.sample_type,
                             'container_type': container_type, 'copies': '1',
                             'test_id': test_id, 'previous_step': 'Grossing',
                             'current_step': 'Processing', 'next_step': 'Embedding',
                             'sample_status': 'In-progress', 'pending_action': ''})
                        success_count += 1
                    all_child_samples_to_create.extend(child_samples_to_create)
                if not errors:
                    child_samples = SampleUtilClass.create_child_sample(all_child_samples_to_create, user_map_obj)
                    if child_samples:
                        generate_automatic_sample_labels(request, [sample.pk for sample in child_samples])

        except Exception as e:
            error_message = f"An error occurred: {e}"
            if errors:
                error_message += "<br>Validation Errors:<br>" + "<br>".join(
                    [f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(error_message), "Y"

        if errors:
            error_messages = "<br>".join([f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(f"Error occurred:<br>{error_messages}"), "Y"

        if success_count > 0 and not errors:
            return "Y", f"{success_count} Cassette(s) created successfully.", "N"
        return "N", "No Cassette(s) could be created", "Y"

    def complete_embedding_method(self, request, queryset, sample_maps):

        container_type = ContainerType.objects.get(container_type=CONTAINER_TYPE_PARAFFIN_TISSUE_BLOCK)
        sample_type = SampleType.objects.get(sample_type=SAMPLE_TYPE_TISSUE)
        try:
            with transaction.atomic():
                for sample in queryset:
                    sample.container_type = container_type
                    sample.sample_type = sample_type
                    sample.pending_action = "PerformMicrotomy"
                    sample.current_step = "Microtomy"
                    sample.previous_step = "Embedding"
                    sample.next_step = None
                    sample.save()

        except Exception as e:
            return 'N', f"Failed to perform Embedding completion. {e}", 'Y'

        return 'N', 'Samples(s) moved to Microtomy.', 'N'

    def _create_cell_blocks(self, request, queryset, entries):

        sample_ids = [e["sample_id"] for e in entries]
        cell_block_queryset = Sample.objects.filter(pk__in=sample_ids).order_by('sample_id')
        container_type = ContainerType.objects.get(container_type=CONTAINER_TYPE_CELL_BLOCK)
        sample_type = SampleType.objects.get(sample_type=SAMPLE_TYPE_CELL_BUTTON)
        user_map_obj = User.objects.get(username=request.user.username)  # Get once
        if not request.user.is_authenticated:
            return "N", "User not authenticated, cannot Create Cell Block.", "Y"

        errors = {}
        success_count = 0
        all_child_samples_to_create = []
        try:
            with transaction.atomic():
                for parent_sample in cell_block_queryset:
                    num_blocks = parent_sample.num_of_blocks
                    sample_id = parent_sample.sample_id

                    if num_blocks is None or num_blocks <= 0:
                        errors[sample_id] = "Invalid number of blocks."
                        continue

                    parent_test_maps = SampleTestMap.objects.filter(sample_id=parent_sample).exclude(
                        test_status='Cancelled')

                    child_samples_to_create = []

                    for _ in range(num_blocks):
                        test_id = ''
                        for stm in parent_test_maps:
                            test_id = test_id + "," + str(stm.test_id_id)
                        if test_id:
                            test_id = test_id[1:]
                        child_samples_to_create.append(
                            {'parent_sample_id': parent_sample, 'sample_type': sample_type,
                             'container_type': container_type, 'copies': '1',
                             'test_id': test_id, 'previous_step': 'Grossing',
                             'current_step': 'Microtomy', 'next_step': '',
                             'sample_status': 'In-progress', 'pending_action': 'PerformMicrotomy'})
                        success_count += 1
                    all_child_samples_to_create.extend(child_samples_to_create)
                if not errors:
                    child_samples = SampleUtilClass.create_child_sample(all_child_samples_to_create, user_map_obj)
                    if child_samples:
                        t1 = threading.Thread(target=generate_automatic_sample_labels,
                                              args=(request, [sample.pk for sample in child_samples]))
                        t1.start()
        except Exception as e:
            error_message = f"An error occurred: {e}"
            if errors:
                error_message += "<br>Validation Errors:<br>" + "<br>".join(
                    [f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(error_message), "Y"
        if errors:
            error_messages = "<br>".join(
                [f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(f"Error occurred:<br>{error_messages}"), "Y"

        if success_count > 0 and not errors:
            return "Y", mark_safe(f"{success_count} Cell Block(s) created successfully."), "N"
        return "N", "No Cell Block(s) could be created", "Y"

    def _prepare_smear_samples(self, request, queryset, entries, prep_type):

        sample_ids = [e["sample_id"] for e in entries]
        sample_test_map_ids = [e["sample_test_map_id"] for e in entries]
        list_sample_info_for_staining = []
        user_map_obj = User.objects.get(username=request.user.username)
        errors = {}
        container_type = ContainerType.objects.get(container_type=CONTAINER_TYPE_SLIDE_UNSTAINED)
        smearing_queryset = SampleTestMap.objects.select_related("sample_id").filter(
            sample_id__in=sample_ids,
            pk__in=sample_test_map_ids
        )
        try:
            with transaction.atomic():
                for sample_test_map in smearing_queryset:
                    parent_sample = Sample.objects.filter(sample_id=sample_test_map.sample_id).first()
                    sample_id = parent_sample.sample_id
                    test_id = str(sample_test_map.test_id_id)
                    list_sample_info_for_staining.append(
                        {'parent_sample_id': parent_sample, 'sample_type': parent_sample.sample_type,
                         'container_type': container_type, 'copies': '1',
                         'test_id': test_id, 'previous_step': 'Grossing',
                         'current_step': 'Staining', 'next_step': 'Imaging',
                         'pending_action': 'SendToStaining', 'sample_status': 'In-progress',
                         'smearing_process': prep_type})
                if not errors:
                    child_samples = SampleUtilClass.create_child_sample(list_sample_info_for_staining,
                                                                        user_map_obj)
                    if child_samples:
                        t1 = threading.Thread(target=generate_automatic_sample_labels,
                                              args=(request, [sample.pk for sample in child_samples]))
                        t1.start()
                    self.complete_microtomy_method(request, smearing_queryset,
                                                   child_samples)
                    parent_ids = [str(sample_info['parent_sample_id']) for sample_info in
                                  list_sample_info_for_staining]
                    parent_ids_str = ", ".join(parent_ids)
                    return 'Y', mark_safe(
                        f'Child sample(s) routed to Staining for parent sample(s): {parent_ids_str}.'), 'N'
        except Exception as e:
            error_message = f"An error occurred: {e}"
            if errors:
                error_message += "<br>Validation Errors:<br>" + "<br>".join(
                    [f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(error_message), "Y"
        if errors:
            error_messages = "<br>".join(
                [f"Sample ID: {sample_id} - {error}" for sample_id, error in errors.items()])
            return "N", mark_safe(f"Error occurred:<br>{error_messages}"), "Y"

    def prepare_liquid_sample(self, request, queryset, sample_maps, prep_type_dict):
        if not prep_type_dict:
            return "N", "No Prepare Liquid Sample Type is Selected.", "Y"

        grouped = defaultdict(list)
        # ... (your existing grouping logic) ...
        for entry in prep_type_dict:
            sample_id = entry.get("sample_id")
            prep_type = entry.get("prep_type")
            accession_id = entry.get("accession_id")
            part_no = entry.get("part_no")
            container_type = entry.get("container_type")
            sample_type = entry.get("sample_type")
            test_id = entry.get("test_id")
            sample_test_map_id = entry.get("sample_test_map_id")

            grouped[prep_type].append({
                "sample_id": sample_id,
                "container_type": container_type,
                "accession_id": accession_id,
                "sample_type": sample_type,
                "part_no": part_no,
                "test_id": test_id,
                "sample_test_map_id": sample_test_map_id
            })

        all_results = []
        for prep_type, entries in grouped.items():
            if prep_type == 'Cell Block':
                status, msg, is_error = self._create_cell_blocks(request, queryset, entries)  # Pass relevant args
                all_results.append((status, msg, is_error))
            elif prep_type == 'Manual' or prep_type == 'Thin Prep':
                status, msg, is_error = self._prepare_smear_samples(request, queryset, entries, prep_type)
                all_results.append((status, msg, is_error))

        # Now, consolidate all_results into a single return value for prepare_liquid_sample
        final_status = 'Y'
        final_message_parts = []
        final_is_error = 'N'

        for status, msg, is_error in all_results:
            if status == 'N' or is_error == 'Y':
                final_status = 'N'
                final_is_error = 'Y'
            final_message_parts.append(msg)

        return final_status, "<br>".join(final_message_parts), final_is_error

    def merge_report_signout_method(self, request, merge_reporting_id):
        # This is for Merge Report Signout
        if not merge_reporting_id:
            raise Exception("Merge Reporting Id is blank")

        with transaction.atomic():
            try:
                list_reportion_option = MergeReportingDtl.objects.filter(
                    merge_reporting_id=merge_reporting_id).order_by('report_option_id').values_list('report_option_id',
                                                                                                    flat=True).distinct()
                qs_report_option = ReportOption.objects.filter(report_option_id__in=list_reportion_option)
                qs_report_option.update(reporting_status="Completed", pending_action=None)
                list_root_sample_id = qs_report_option.order_by('root_sample_id').values_list('root_sample_id',
                                                                                              flat=True).distinct()
                list_test_id = qs_report_option.order_by('test_id').values_list('test_id', flat=True).distinct()
                accession_id = qs_report_option.order_by('accession_id').values_list('accession_id',
                                                                                     flat=True).distinct().first()
                if list_root_sample_id and list_test_id:
                    qs_sample_test_map = SampleTestMap.objects.filter(
                        sample_id__in=list_root_sample_id,
                        test_id__in=list_test_id
                    ).exclude(test_status="Completed")

                    if qs_sample_test_map.exists():
                        qs_sample_test_map.update(test_status="Completed")

                if accession_id:
                    accession_instance = Accession.objects.filter(accession_id=accession_id).first()
                    if accession_instance:
                        incomplete_reports_exist = ReportOption.objects.filter(
                            accession_id=accession_id
                        ).exclude(reporting_status="Completed").exists()

                        if not incomplete_reports_exist:
                            if accession_instance.status != "Completed":
                                accession_instance.status = "Completed"
                                accession_instance.save(update_fields=["status"])

                merge_report = MergeReporting.objects.get(merge_reporting_id=merge_reporting_id)
                merge_report.reporting_status = "Completed"
                merge_report.last_signed_dt = datetime.now()
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                merge_report.last_signed_by = user_map_obj
                merge_report.save(update_fields=["reporting_status", "last_signed_dt", "last_signed_by"])

                max_version = MergeReportingDtl.objects.filter(
                    merge_reporting_id=merge_report
                ).aggregate(max_version=models.Max("version_id"))["max_version"]

                if max_version is None:
                    return

                dtl_rows = MergeReportingDtl.objects.filter(
                    merge_reporting_id=merge_report,
                    version_id=max_version
                )
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                module = importlib.import_module("util.util")
                GenericUtilClass = getattr(module, "UtilClass")

                if dtl_rows.exists():
                    reporting_version_id = GenericUtilClass.get_next_sequence(merge_reporting_id,
                                                                              "ReportSignOut", user_map_obj.id)
                    signout_entries = []
                    for dtl in dtl_rows:
                        report_signout_instance = ReportSignOut()
                        report_signout_instance.merge_reporting_id = merge_report
                        report_signout_instance.report_option_id = dtl.report_option_id
                        report_signout_instance.version_id = reporting_version_id
                        report_signout_instance.analyte_id = dtl.analyte_id
                        report_signout_instance.analyte_value = dtl.analyte_value
                        report_signout_instance.created_by = user_map_obj
                        report_signout_instance.mod_by = user_map_obj
                        signout_entries.append(report_signout_instance)

                    if not signout_entries:
                        raise Exception("No Records to create in Report Signout Table")

                    ReportSignOut.objects.bulk_create(signout_entries)

                    # ----------- BEGIN DYNAMIC JASPER REPORT SELECTION ------------
                    accession = merge_report.accession_id  # adjust field name if different
                    accession_category = getattr(accession, 'accession_category', None)

                    if accession_category == "Pharma":
                        jrxml_file = "PharmaGulfFinalReport.jasper"
                    else:
                        jrxml_file = "GulfFinalReport.jasper"

                    input_path = os.path.join(settings.BASE_DIR, 'static', 'reports', jrxml_file)
                    # ----------- END DYNAMIC JASPER REPORT SELECTION --------------

                    if not os.path.exists(input_path):
                        raise Exception("The specified Jasper file does not exist.")

                    # Define output path
                    now = datetime.now()
                    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
                    output_filename = f"{merge_reporting_id}_{reporting_version_id}"
                    output_path = os.path.join(settings.BASE_DIR, settings.REPORT_FINAL_OUTPUT_PATH, output_filename)

                    # Generate report
                    pdf_path_rel = GenericUtilClass.generate_report(input_file=input_path, output_file=output_path,
                                                                    filetype='pdf',
                                                                    merge_reporting_id=merge_reporting_id,
                                                                    use_db=True, is_preview=False)

                    # Prepare download/view URL
                    pdf_url = GenericUtilClass.get_s3_url(pdf_path_rel)

                    # Save the generated report to the Attachment model
                    Attachment.objects.create(
                        merge_reporting_id=merge_report,
                        version_id=reporting_version_id,
                        file_path=pdf_path_rel,
                        created_by=user_map_obj,
                        mod_by=user_map_obj
                    )

                    self.populate_profesional_component(request, merge_reporting_id)

                    thread = threading.Thread(target=self.send_mail, args=(accession_id, pdf_url))
                    thread.start()

                    return pdf_url
            except Exception as e:
                raise Exception(f"Error generating report: {e}")

    def send_mail(self, accession_id, pdf_url):
        """
        Send Mail after Report Signout
        """
        if not accession_id:
            raise Exception("Accession Id not found")

        if not pdf_url:
            raise Exception("Report not found")

        accession_instance = BioPharmaAccession.objects.get(accession_id=accession_id)
        if not accession_instance:
            raise Exception("No record exists for the Accession Id ")

        email_config = EmailConfig.objects.get(email_category__iexact="ReportEmail")
        if not email_config:
            raise Exception("No Email Configuration exists.")

        project = getattr(accession_instance, "project", None)
        if not project:
            raise Exception("No Project is associated with this Accession")

        recipient_list = []
        project_emails = ProjectEmailMap.objects.filter(
            bioproject_id=project, email_category__iexact="ReportEmail"
        ).values_list("email_id", flat=True)

        if project_emails:
            for email_str in project_emails:
                for e in email_str.replace(",", ";").split(";"):
                    e = e.strip()
                    if e:
                        recipient_list.append(e)

        # Combine recipients from EmailConfig and ProjectEmailMap
        if email_config.email_to:
            recipient_list.extend(
                [e.strip() for e in email_config.email_to.replace(",", ";").split(";") if e.strip()]
            )
        recipient_list = list(set(recipient_list))  # Remove duplicates

        sponsor = project.sponsor_id
        sponsor_name = ""
        if sponsor:
            sponsor_name = sponsor.sponsor_name

        email_subject = email_config.subject
        if email_subject:
            email_subject = email_subject.replace("[accessionid]", accession_instance.pk)
        else:
            raise Exception("Subject is missing in Email Configuration")

        email_body = email_config.body
        if email_body:
            if sponsor_name:
                email_body = email_body.replace("[sponsorname]", sponsor_name)
            else:
                raise Exception("Sponsor Name not found")

        # Step 7️⃣: Prepare mail_data
        mail_data = {
            "from_email": getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            "to_email": ";".join(recipient_list),
            "cc_email": email_config.email_cc or "",
            "subject": email_subject,
            "body": email_body,
            "attachments": [
                pdf_url
            ],
        }

        # Step 8️⃣: Send email
        module = importlib.import_module("util.util")
        GenericUtilClass = getattr(module, "UtilClass")
        GenericUtilClass.send_mail_for_pharma_implementation(mail_data)

    def populate_profesional_component(self, request, merge_reporting_id):
        # This is for Populating Professional Component
        if merge_reporting_id:
            module = importlib.import_module("tpcm.technicalprofessionalcomponentutil")
            TechnicalProfessionalComponentUtilClass = getattr(module, "TechnicalProfessionalComponentUtilClass")
            TechnicalProfessionalComponentUtilClass.populate_pc(request, merge_reporting_id)
        else:
            raise Exception("Merge ReportOption ID is blank")

    def generate_report_method(self, request, queryset):
        # This is to create merge report option id
        try:
            with transaction.atomic():
                module = importlib.import_module("util.util")
                GenericUtilClass = getattr(module, "UtilClass")
                username = request.user.username
                user_map_obj = User.objects.get(username=username)

                accession_id = queryset.values_list('accession_id', flat=True).first()
                selected_methodology = queryset.values_list('methodology', flat=True).first()
                queryset_report_option = queryset.filter(methodology=selected_methodology) \
                    .order_by('report_option_id') \
                    .values_list('report_option_id', flat=True).distinct()

                # Avoiding duplicate MergeReporting
                merge_reporting_instance = MergeReporting.objects.filter(
                    accession_id=accession_id,
                    methodology=selected_methodology
                ).first()
                if merge_reporting_instance and not merge_reporting_instance.reporting_status == "Completed":
                    existing_report_option_ids = list(MergeReportingDtl.objects.filter(
                        merge_reporting_id=merge_reporting_instance,
                        report_option_id__in=queryset_report_option
                    ).values_list('report_option_id', flat=True).distinct())

                    missing_report_option_ids = list(set(queryset_report_option) - set(existing_report_option_ids))

                    if missing_report_option_ids:
                        queryset.filter(report_option_id__in=missing_report_option_ids).update(
                            assign_pathologist=user_map_obj)
                        existing_version_id = MergeReportingDtl.objects.filter(
                            merge_reporting_id=merge_reporting_instance
                        ).values_list('version_id', flat=True).first()

                        missing_details = ReportOptionDtl.objects.filter(report_option_id__in=missing_report_option_ids)

                        list_merge_reporting_dtl = []

                        for report_option_id in missing_report_option_ids:
                            current_details = missing_details.filter(report_option_id=report_option_id)
                            for detail in current_details:
                                dtl_seq_no = GenericUtilClass.get_next_sequence("MRD", "MergeReportingDtl",
                                                                                user_map_obj.id)
                                merge_reporting_dtl_id = f"MRD-{dtl_seq_no:08}"
                                merge_reporting_dtl_instance = MergeReportingDtl()
                                merge_reporting_dtl_instance.merge_reporting_dtl_id = merge_reporting_dtl_id
                                merge_reporting_dtl_instance.version_id = existing_version_id
                                merge_reporting_dtl_instance.merge_reporting_id = merge_reporting_instance
                                merge_reporting_dtl_instance.report_option_id = detail.report_option_id
                                merge_reporting_dtl_instance.analyte_id = detail.analyte_id
                                merge_reporting_dtl_instance.analyte_value = detail.analyte_value
                                merge_reporting_dtl_instance.created_by = user_map_obj
                                merge_reporting_dtl_instance.mod_by = user_map_obj
                                list_merge_reporting_dtl.append(merge_reporting_dtl_instance)

                        if list_merge_reporting_dtl:
                            MergeReportingDtl.objects.bulk_create(list_merge_reporting_dtl)

                    dynamic_part_for_redirecting = (
                        f"/gulfcoastpathologists/"
                        f"{merge_reporting_instance._meta.app_label}/"
                        f"{merge_reporting_instance._meta.model_name}/"
                        f"{merge_reporting_instance.pk}/change/"
                    )
                    return 'N', '', 'N', dynamic_part_for_redirecting

                elif merge_reporting_instance and merge_reporting_instance.reporting_status == "Completed":
                    err_msg = "Merge Reporting Id for selected case and methodology is already Completed"
                    return 'N', err_msg, 'Y', ''

                # Filtering ReportOption IDs only for the selected methodology
                queryset_report_option = queryset.filter(methodology=selected_methodology) \
                    .order_by('report_option_id') \
                    .values_list('report_option_id', flat=True).distinct()

                # Assigning pathologist to these filtered report options
                queryset.filter(methodology=selected_methodology).update(assign_pathologist=user_map_obj)

                merge_reporting_instance = MergeReporting()
                seq_no = GenericUtilClass.get_next_sequence("MR", " MergeReporting", user_map_obj.id)
                merge_reporting_instance.merge_reporting_id = f"MR-{seq_no:08}"
                merge_reporting_instance.accession_id_id = accession_id
                merge_reporting_instance.methodology = selected_methodology
                merge_reporting_instance.created_by = user_map_obj
                merge_reporting_instance.mod_by = user_map_obj
                merge_reporting_instance.reporting_status = "In-progress"
                merge_reporting_instance.assign_pathologist = user_map_obj
                merge_reporting_instance.save()

                queryset_report_option_details = ReportOptionDtl.objects.filter(
                    report_option_id__in=queryset_report_option)

                list_merge_reporting_dtl = []
                merge_reporting_dtl_version_prefix = f"{merge_reporting_instance.merge_reporting_id}"
                merge_reporting_dtl_version_id = GenericUtilClass.get_next_sequence(
                    merge_reporting_dtl_version_prefix, "MergeReportingDtl", user_map_obj.id)

                for report_option_id in queryset_report_option:
                    current_details = queryset_report_option_details.filter(report_option_id=report_option_id)
                    for detail in current_details:
                        dtl_seq_no = GenericUtilClass.get_next_sequence("MRD", "MergeReportingDtl", user_map_obj.id)
                        merge_reporting_dtl_id = f"MRD-{dtl_seq_no:08}"
                        merge_reporting_dtl_instance = MergeReportingDtl()
                        merge_reporting_dtl_instance.merge_reporting_dtl_id = merge_reporting_dtl_id
                        merge_reporting_dtl_instance.version_id = merge_reporting_dtl_version_id
                        merge_reporting_dtl_instance.merge_reporting_id = merge_reporting_instance
                        merge_reporting_dtl_instance.report_option_id = detail.report_option_id
                        merge_reporting_dtl_instance.analyte_id = detail.analyte_id
                        merge_reporting_dtl_instance.analyte_value = detail.analyte_value
                        merge_reporting_dtl_instance.created_by = user_map_obj
                        merge_reporting_dtl_instance.mod_by = user_map_obj
                        list_merge_reporting_dtl.append(merge_reporting_dtl_instance)

                if list_merge_reporting_dtl:
                    MergeReportingDtl.objects.bulk_create(list_merge_reporting_dtl)

                dynamic_part_for_redirecting = (
                    f"/gulfcoastpathologists/"
                    f"{merge_reporting_instance._meta.app_label}/"
                    f"{merge_reporting_instance._meta.model_name}/"
                    f"{merge_reporting_instance.pk}/change/"
                )
                return 'N', '', 'N', dynamic_part_for_redirecting

        except Exception as e:
            err_msg = str(e)
            return 'N', err_msg, 'Y', ''
