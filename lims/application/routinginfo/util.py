import os
from datetime import datetime
from django.db import transaction
from django.db.models import Value, IntegerField, F, When, Case
from sample.models import SampleTestMap
from security.models import Department
from django.apps import apps
from django.contrib import messages
from pyreportjasper import PyReportJasper
from django.conf import settings


class UtilClass:
    @staticmethod
    def process_workflow_steps_wetlab(self, request, sample_ids, accession_flag):
        success_samples = []
        try:
            Sample = apps.get_model('sample', 'Sample')
            SampleTestMap = apps.get_model('sample', 'SampleTestMap')

            has_pending_action = Sample.objects.filter(
                sample_id__in=sample_ids
            ).exclude(pending_action__isnull=True).exclude(pending_action="").exists()

            if has_pending_action:
                messages.error(request, "One or more selected samples have a pending action to perform before routing.")
                return

            with transaction.atomic():
                sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
                sample_type_ids = sample_maps.values_list('sample_type_id', flat=True).distinct()
                container_type_ids = sample_maps.values_list('container_type_id', flat=True).distinct()

                sample_test_maps = SampleTestMap.objects.filter(sample_id_id__in=sample_ids)
                test_ids = sample_test_maps.values_list('test_id_id', flat=True).distinct()
                workflow_ids_from_tests = sample_test_maps.values_list('workflow_id_id', flat=True).distinct()

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

                queryset = TestWorkflowStep.objects.select_related(
                    'workflow_step_id'
                ).filter(
                    sample_type_id__in=sample_type_ids,
                    container_type_id__in=container_type_ids,
                    test_id__in=test_ids,
                    workflow_id__in=workflow_ids_from_tests,
                    workflow_step_id__workflow_id__in=workflow_ids_from_tests,
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

                for sample_map in sample_maps:
                    try:
                        sample = sample_map
                        workflow_id = workflow_map.get(sample.sample_id)

                        if workflow_id:
                            # Use WorkflowStep for samples with workflow_id
                            relevant_row = workflow_steps.filter(
                                workflow_id=workflow_id
                            )
                        else:
                            # Use TestWorkflowStep for samples without workflow_id
                            sample_test_map = sample_test_maps.filter(sample_id_id=sample.sample_id).first()
                            if not sample_test_map:
                                continue
                            relevant_row = queryset.filter(
                                sample_type_id=sample_map.sample_type_id,
                                container_type_id=sample_map.container_type_id,
                                test_id=sample_test_map.test_id_id,
                                workflow_id=sample_test_map.workflow_id_id
                            )

                        if relevant_row:
                            current_step, next_step = UtilClass.get_current_and_next_step(filtered_steps=relevant_row,
                                                                                          sample=sample,
                                                                                          request=request,
                                                                                          accession_flag=accession_flag,
                                                                                          workflow_map=workflow_map)
                            if current_step:
                                success_samples.append({
                                    "sample_id": sample.sample_id,
                                    "current_step": current_step['workflow_step_id__step_id'] if current_step else 'N/A'
                                })
                            else:
                                messages.error(request,
                                               "Sample(s) failed to route or no next step found")
                                transaction.set_rollback(True)
                                return
                        else:
                            continue
                    except Exception as e:
                        messages.error(request,
                                       e)
                        transaction.set_rollback(True)
                        return

            if len(success_samples) > 0:
                return success_samples

        except Exception as e:
            messages.error(request, e)
            transaction.set_rollback(True)
            return

    @staticmethod
    def process_workflow_steps_drylab(self, request, queryset, report_option_id, accession_flag):
        success_samples = []
        error_messages = []
        if not report_option_id:
            messages.error(request, "No Report Option selected")
            return
        try:
            list_report_options = list(queryset)
            if not list_report_options:
                messages.error(request, "No Report Option selected")
                return
            ReportOption = apps.get_model('analysis', 'ReportOption')
            Sample = apps.get_model('sample', 'Sample')
            SampleTestMap = apps.get_model('sample', 'SampleTestMap')

            has_pending_action = ReportOption.objects.filter(
                report_option_id__in=report_option_id
            ).exclude(pending_action__isnull=True).exclude(pending_action="").exists()

            if has_pending_action:
                messages.error(request,
                               "One or more selected report options have a pending action to perform before routing.")
                return
            with transaction.atomic():
                sample_ids = queryset.values_list('root_sample_id', flat=True)
                sample_maps = Sample.objects.filter(sample_id__in=sample_ids)
                sample_type_ids = sample_maps.values_list('sample_type_id', flat=True).distinct()
                container_type_ids = sample_maps.values_list('container_type_id', flat=True).distinct()
                test_ids = queryset.values_list('test_id_id', flat=True).distinct()
                sample_test_maps = SampleTestMap.objects.filter(sample_id_id__in=sample_ids, test_id_id__in=test_ids)
                workflow_ids = sample_test_maps.values_list('workflow_id_id', flat=True).distinct()

                report_options_with_workflow = ReportOption.objects.filter(
                    report_option_id__in=report_option_id
                ).annotate(
                    effective_workflow_id=Case(
                        When(workflow_id__isnull=False, then=F('workflow_id')),
                        default=Value(None),
                        output_field=IntegerField(),
                    )
                )

                workflow_map = dict(
                    report_options_with_workflow.values_list('report_option_id', 'effective_workflow_id')
                )

                workflow_ids_from_report_options = report_options_with_workflow.values_list(
                    'effective_workflow_id', flat=True
                ).distinct()
                TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
                WorkflowStep = apps.get_model('workflows', 'WorkflowStep')

                workflow_steps = WorkflowStep.objects.filter(
                    workflow_id__in=workflow_ids_from_report_options,
                    workflow_type='DryLab',
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
                queryset = TestWorkflowStep.objects.select_related(
                    'workflow_step_id'
                ).filter(
                    sample_type_id__in=sample_type_ids,
                    container_type_id__in=container_type_ids,
                    test_id__in=test_ids,
                    workflow_id__in=workflow_ids,
                    workflow_step_id__workflow_id__in=workflow_ids,
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

                for report_option in list_report_options:
                    try:
                        workflow_id = workflow_map.get(report_option.report_option_id)

                        if workflow_id:
                            # Use WorkflowStep for samples with workflow_id
                            relevant_row = workflow_steps.filter(
                                workflow_id=workflow_id
                            )
                        else:
                            # Use TestWorkflowStep for samples without workflow_id
                            sample_test_map = sample_test_maps.filter(sample_id_id=report_option.root_sample_id,
                                                                      test_id_id=report_option.test_id).first()
                            if not sample_test_map:
                                continue
                            relevant_row = queryset.filter(
                                sample_type_id=report_option.root_sample_id.sample_type_id,
                                container_type_id=report_option.root_sample_id.container_type_id,
                                test_id=sample_test_map.test_id_id,
                                workflow_id=sample_test_map.workflow_id_id
                            )

                        if relevant_row:
                            current_step, next_step = UtilClass.get_current_and_next_step_by_report_option(
                                filtered_steps=relevant_row,
                                report_option=report_option,
                                request=request,
                                accession_flag=accession_flag,
                                workflow_map=workflow_map)
                            success_samples.append({
                                "report_option_id": report_option.report_option_id,
                                "current_step": current_step['workflow_step_id__step_id'] if current_step else 'N/A'
                            })
                        else:
                            continue
                    except Exception as e:
                        error_messages.append(
                            f"Error updating Sample {report_option.report_option_id}: {str(e)}"
                        )
                if error_messages:
                    messages.error(request, "; ".join(error_messages))
                    return
            if len(success_samples) > 0:
                return success_samples

        except Exception as e:
            messages.error(request, e)
            return

    def get_current_and_next_step(filtered_steps, sample, request, accession_flag, workflow_map):
        previous_step = None

        # Sort steps based on step number
        sorted_steps = filtered_steps.order_by('workflow_step_id__step_no')
        # Determine current and next steps
        if sample.current_step:
            # Find the index of the current step
            current_step_index = next(
                (i for i, step in enumerate(sorted_steps) if step['workflow_step_id__step_id'] == sample.current_step),
                None
            )

            if current_step_index is None:
                return None, None

            # Check if current step is the last one
            if current_step_index == len(sorted_steps) - 1:
                return None, None

            # Move to the next step
            previous_step = sample.current_step
            current_step = sorted_steps[current_step_index + 1]
            next_step = sorted_steps[current_step_index + 2] if current_step_index + 2 < len(sorted_steps) else None

        else:
            # First-time assignment
            current_step = sorted_steps[0] if sorted_steps else None
            next_step = sorted_steps[1] if len(sorted_steps) > 1 else None
        # Update sample with current and next steps
        TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')

        workflow_id = workflow_map.get(sample.sample_id)
        if workflow_id:
            # Sample has workflow_id → use workflow_step_id column
            qs = TestWorkflowStepActionMap.objects.filter(
                workflow_step_id=current_step['workflow_step_id__workflow_step_id']
            ).order_by('sequence').first()
        else:
            qs = TestWorkflowStepActionMap.objects.filter(
                testwflwstepmap_id=current_step['test_workflow_step_id']).order_by('sequence').first()
        if qs:
            sample.pending_action = qs.action
        else:
            sample.pending_action = None
        sample.previous_step = previous_step
        sample.current_step = current_step['workflow_step_id__step_id'] if current_step else None
        sample.next_step = next_step['workflow_step_id__step_id'] if next_step else None
        if current_step:
            dept = request.session.get('currentjobtype', '').split('-')[0] + '-' + current_step[
                'workflow_step_id__department']
            sample.custodial_department_id = Department.objects.filter(name=dept).values_list('id', flat=True).first()
        sample.custodial_user_id = request.user.id
        sample.avail_at = datetime.now()
        if accession_flag == 'Y':
            sample.accession_generated = True
            sample.sample_status = 'In-progress'
            # Default population of num_of_blocks and num_of_slides for samples being routed to Grossing
            if current_step['workflow_step_id__step_id'] == 'Grossing':
                if sample.container_type and sample.container_type.is_liquid == 'Y':
                    # Logic for liquid container types
                    sample.num_of_blocks = 1
                    test_maps = SampleTestMap.objects.filter(sample_id=sample.sample_id).exclude(
                        test_status='Cancelled')
                    sample.num_of_manualsmear_slides = test_maps.exclude(test_id__smear_process='Thin Prep').count()
                    sample.num_of_thinprep_slides = test_maps.filter(test_id__smear_process='Thin Prep').count()
                elif sample.container_type and sample.container_type.is_liquid != 'Y':
                    sample.num_of_blocks = 1
                    test_maps = SampleTestMap.objects.filter(sample_id=sample.sample_id).exclude(
                        test_status='Cancelled')
                    sample.num_of_slides = test_maps.count()
        if qs and qs.action == 'MoveToStorage':
            sample.previous_step = current_step['workflow_step_id__step_id'] if current_step else None
            sample.current_step = 'Storage'
            sample.next_step = None
        sample.save()
        return current_step, next_step

    # This is to route the report options
    @staticmethod
    def get_current_and_next_step_by_report_option(filtered_steps, report_option, request, accession_flag, workflow_map):
        previous_step = None

        # Sort steps based on step number
        sorted_steps = filtered_steps.order_by('workflow_step_id__step_no')
        # Determine current and next steps
        if report_option.current_step:
            # Find the index of the current step
            current_step_index = next(
                (i for i, step in enumerate(sorted_steps) if
                 step['workflow_step_id__step_id'] == report_option.current_step),
                None
            )

            if current_step_index is None:
                return None, None

            # Check if current step is the last one
            if current_step_index == len(sorted_steps) - 1:
                return None, None

            # Move to the next step
            previous_step = report_option.current_step
            current_step = sorted_steps[current_step_index + 1]
            next_step = sorted_steps[current_step_index + 2] if current_step_index + 2 < len(sorted_steps) else None

        else:
            # First-time assignment
            current_step = sorted_steps[0] if sorted_steps else None
            next_step = sorted_steps[1] if len(sorted_steps) > 1 else None
        # Update sample with current and next steps
        TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
        workflow_id = workflow_map.get(report_option.report_option_id)
        if workflow_id:
            # Sample has workflow_id → use workflow_step_id column
            qs = TestWorkflowStepActionMap.objects.filter(
                workflow_step_id=current_step['workflow_step_id__workflow_step_id']
            ).order_by('sequence').first()
        else:
            qs = TestWorkflowStepActionMap.objects.filter(
                testwflwstepmap_id=current_step['test_workflow_step_id']).order_by('sequence').first()
        if qs:
            report_option.pending_action = qs.action
        else:
            report_option.pending_action = None
        report_option.previous_step = previous_step
        report_option.current_step = current_step['workflow_step_id__step_id'] if current_step else None
        report_option.next_step = next_step['workflow_step_id__step_id'] if next_step else None
        if current_step:
            dept = request.session.get('currentjobtype', '').split('-')[0] + '-' + current_step[
                'workflow_step_id__department']
            report_option.custodial_department_id = Department.objects.filter(name=dept).values_list('id',
                                                                                                     flat=True).first()
        report_option.custodial_user_id = request.user.id
        report_option.avail_at = datetime.now()
        report_option.save()
        return current_step, next_step

    @staticmethod
    def validate_next_step_exists(filtered_steps, sample, workflow_map):
        """
        Check if a next step exists WITHOUT modifying the sample.
        Returns True if routing is possible, False otherwise.
        """
        try:
            # Sort steps based on step number
            sorted_steps = list(filtered_steps.order_by('workflow_step_id__step_no'))

            if not sorted_steps:
                return False

            # Determine if there's a next step available
            if sample.current_step:
                # Find the index of the current step
                current_step_index = next(
                    (i for i, step in enumerate(sorted_steps)
                     if step['workflow_step_id__step_id'] == sample.current_step),
                    None
                )

                if current_step_index is None:
                    return False

                # Check if current step is the last one
                if current_step_index >= len(sorted_steps) - 1:
                    return False

                # There's a next step available
                return True
            else:
                # First-time assignment - at least one step exists
                return len(sorted_steps) > 0

        except Exception as e:
            return False
