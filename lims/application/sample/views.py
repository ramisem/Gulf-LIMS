import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, Value, IntegerField, F, Q, Prefetch
from django.forms import modelformset_factory
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from ihcworkflow.models import IhcWorkflow
from logutil.log import log
from routinginfo.util import UtilClass
from sample.forms import SampleBulkEditForm
from sample.models import Sample, SampleTestMap
from security.views import JobTypeContextMixin
from util.actions import GenericAction


class SampleBulkEditView(JobTypeContextMixin, View):
    form_class = SampleBulkEditForm
    template_name = "admin/bulk_edit.html"
    title = _("Bulk Edit Samples")

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        return {"user": self.request.user}

    def get_context_data(self, **kwargs):
        context = {}
        context.update(kwargs)
        if hasattr(self, "extra_context") and self.extra_context:
            context.update(self.extra_context)
        context.setdefault("title", self.title)
        context.setdefault("subtitle", None)
        context['workflow'] = self.request.GET.get('workflow', 'enterprise')
        # Pass the Sample model's _meta as opts so the admin template can access app_label, etc.
        context.setdefault("opts", Sample._meta)
        return context

    def get_queryset(self, ids):
        return Sample.objects.filter(sample_id__in=ids)

    def get(self, request):
        ids = request.GET.get('ids', '')
        if not ids:
            messages.error(request, "No samples selected for bulk editing.")
            return redirect("controllerapp:sample_sample_changelist")
        ids = ids.split(',')
        queryset = self.get_queryset(ids)
        SampleFormSet = modelformset_factory(Sample, form=SampleBulkEditForm, extra=0)
        formset = SampleFormSet(queryset=queryset, auto_id='id_%s')
        context = self.get_context_data(formset=formset)
        return render(request, self.template_name, context)

    def post(self, request):
        ids = request.GET.get('ids', '')
        ids = ids.split(',') if ids else []
        queryset = self.get_queryset(ids)
        SampleFormSet = modelformset_factory(Sample, form=SampleBulkEditForm, extra=0)
        formset = SampleFormSet(request.POST, queryset=queryset, auto_id='id_%s')
        if formset.is_valid():
            formset.save()

            q = request.GET.get('q', '')

            # continue‑editing stays on the same URL (carries &q=… automatically)
            if "_continue" in request.POST:
                messages.success(request,
                                 "The selected sample(s) was changed successfully. You may edit it again below.")
                return redirect(request.get_full_path())

            # otherwise go back to the changelist, re‑applying q=
            base = reverse("controllerapp:sample_sample_changelist")
            messages.success(request, "The selected sample(s) was changed successfully.")
            if q:
                return redirect(f"{base}?q={q}")
            return redirect(base)

        return render(request, self.template_name, self.get_context_data(formset=formset))


class SampleRouteView(View):
    def get(self, request):
        # Determine the source of the routing action
        origin = request.GET.get("origin", "bulk")  # defaults to bulk if not specified

        # For a single sample edit, the button passes active_id and all_ids.
        active_id = request.GET.get('active_id')
        # For bulk editing, we may simply have ids.
        all_ids = request.GET.get('all_ids') or request.GET.get('ids', '')

        # Decide which sample(s) to process
        if active_id:
            sample_ids = [active_id]
        else:
            ids = request.GET.get('ids', '')
            sample_ids = ids.split(',') if ids else []

        if not sample_ids:
            messages.error(request, "No samples selected for routing.")
            if origin == "change":
                # Redirect back to the referring change form (or home if not available)
                return redirect(request.META.get('HTTP_REFERER', '/'))
            else:
                return redirect(reverse("controllerapp:sample_bulk_edit") + f"?ids={all_ids}")

        # Execute the routing logic
        queryset = Sample.objects.filter(sample_id__in=sample_ids)
        success_samples = UtilClass.process_workflow_steps_wetlab(self, request, sample_ids, 'N')
        if success_samples:
            messages.success(request, f"Routing executed for sample(s): {', '.join(sample_ids)}")

        # Redirect based on the origin of the request
        if origin == "change":
            # For the change form page, redirect back to the sample’s admin change page.
            sample = queryset.first()
            if sample:
                # Assuming your admin URL name is 'admin:sample_sample_change'
                return redirect(reverse("admin:sample_sample_change", args=[sample.pk]))
            else:
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            # Default: return to the bulk edit page
            return redirect(reverse("controllerapp:sample_bulk_edit") + f"?ids={all_ids}")


@require_POST
def admin_scan_validate(request):
    log.info(f"admin_scan_validate Start")
    """
    Validate single sample id quickly and return small set of fields to render.
    Expects JSON: { "id": "S123" }
    Response:
      { "valid": true, "sample": {
            "sample_id": "...",
            "part_no": "...",
            "tests": ["Test A", "Test B"],
            "current_step": "...",
            "next_step": "...",
            "pending_action": "...",
            "accession_id": "...",  
            "model_type": "sample" or "ihc" 
       } }
    Or:
      { "valid": false, "error": "Not found" }
    """
    if not request.user.is_staff:
        return HttpResponseForbidden("Forbidden")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    sid = (payload.get("id") or "").strip()
    if not sid:
        return JsonResponse({"valid": False, "error": "Missing sample id"})

    # Determine model type first
    model_type = "sample"  # default
    try:
        # Check if this sample exists in IhcWorkflow
        ihc_exists = IhcWorkflow.objects.filter(sample_id=sid).exists()
        if ihc_exists:
            model_type = "ihc"

        # Get the sample regardless (both models should have these fields)
        s = Sample.objects.select_related('accession_id').only(
            'sample_id', 'part_no', 'current_step', 'next_step', 'pending_action', 'accession_id'
        ).get(sample_id=sid)

    except ObjectDoesNotExist:
        log.error(f"Sample '{sid}' not found")
        return JsonResponse({"valid": False, "error": f"Sample '{sid}' not found"})

    # Retrieve associated tests (names). Use values_list to keep query lightweight.
    tests_qs = SampleTestMap.objects.filter(sample_id=s).select_related('test_id').values_list('test_id__test_name',
                                                                                               flat=True)
    tests_list = [str(t) for t in tests_qs if t]  # ensure strings, filter out None

    # Compose the response with safe string values
    sample_data = {
        "sample_id": s.sample_id,
        "part_no": s.part_no or "",
        "tests": tests_list,
        "current_step": s.current_step or "",
        "next_step": s.next_step or "",
        "pending_action": s.pending_action or "",
        "accession_id": str(s.accession_id) if s.accession_id else "",
        "model_type": model_type  # NEW: "sample" or "ihc"
    }

    log.info(f"admin_scan_validate sample_data : {sample_data}")
    return JsonResponse({"valid": True, "sample": sample_data})


@require_POST
def admin_scan_submit(request):
    log.info("admin_scan_submit Start")
    if not request.user.is_staff:
        return HttpResponseForbidden()

    # 1) Parse input
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    ids = data.get("ids")
    if not ids or not isinstance(ids, (list, str)):
        return HttpResponseBadRequest("Missing or invalid 'ids'")
    if isinstance(ids, str):
        ids = [s.strip() for s in ids.splitlines() if s.strip()]

    # 2) Inject form flags
    if not request.POST._mutable:
        request.POST._mutable = True
    for key in ("qc_status", "apply"):
        if key in data:
            request.POST[key] = data[key]

    # 3) Filter out blank pending_action samples upfront for routing
    pending_action_blanks = []
    valid_ids = []
    for sid in ids:
        try:
            sample = Sample.objects.get(sample_id=sid)
            if not sample.pending_action:
                pending_action_blanks.append(sid)
            else:
                valid_ids.append(sid)
        except Sample.DoesNotExist:
            continue

    # If all samples have blank pending_action, route immediately
    if len(pending_action_blanks) == len(ids):
        routing_results = []
        routed = UtilClass.process_workflow_steps_wetlab(None, request, pending_action_blanks, accession_flag="N") or []
        for r in routed:
            routing_results.append({
                "sample_id": r["sample_id"],
                "current_step": r.get("current_step"),
                "next_step": r.get("next_step"),
                "status": "routed"
            })
        return JsonResponse({
            "status": "ok",
            "action_results": [],
            "routing_results": routing_results,
            "not_found": [],
            "summary": {
                "total": len(ids),
                "automatic": 0,
                "form_groups": 0,
                "not_found": 0,
                "routed": len(routing_results),
            },
        })

    # 4) Build behaviors and validate mixed mode for samples with valid pending action
    behaviors, pending_actions = {}, set()
    for sid in valid_ids:
        try:
            sample = Sample.objects.get(sample_id=sid)
        except Sample.DoesNotExist:
            continue
        behavior = get_action_behavior(sample, request)
        behaviors[sid] = behavior
        if behavior["type"] == "form":
            pending_actions.add(sample.pending_action)

    if pending_actions:
        if len(pending_actions) > 1:
            return JsonResponse(
                {"status": "error", "message": "All form‐required samples must share one pending action."}, status=400)
        if any(behaviors[sid]["type"] == "automatic" for sid in valid_ids if sid in behaviors):
            return JsonResponse({"status": "error",
                                 "message": "Cannot mix Manual input pending action samples and automatic pending action excution samples."},
                                status=400)

    # 5) Group by (model, action, method)
    groups, automatic, not_found = {}, [], []
    for sid in valid_ids:
        try:
            sample = Sample.objects.get(sample_id=sid)
        except Sample.DoesNotExist:
            not_found.append(sid)
            continue
        behavior = behaviors.get(sid) or get_action_behavior(sample, request)
        if behavior["type"] == "automatic":
            automatic.append(sid)
            continue
        action = sample.pending_action
        method = behavior["action_method"]
        model_cls = next(iter(get_model_for_sample_ids([sid]).keys()))
        groups.setdefault((model_cls, action, method), []).append(sid)

    # 6) Single-form early return
    if len(groups) == 1 and not automatic:
        (model_cls, action, method), sids = next(iter(groups.items()))
        qs = model_cls.objects.filter(sample_id__in=sids)

        # Check if this is prepare_liquid_sample method
        if method == 'prepare_liquid_sample':
            # VALIDATION: Check if all samples have gross_description populated
            missing_gross_desc = qs.filter(
                Q(gross_description__isnull=True) | Q(gross_description="")
            ).count()

            if missing_gross_desc > 0:
                return JsonResponse({
                    "status": "error",
                    "message": "All selected samples must have Gross Description populated."
                }, status=400)

            # Render smearing selection form
            from django.urls import reverse

            # Build sample and test data for the template
            sample_data = []
            sample_test_data = []

            samples = Sample.objects.filter(pk__in=sids).order_by('pk')
            for sample in samples:
                sample_data.append({'sample': sample})

            # Get test mappings
            sample_tests = Sample.objects.filter(sample_id__in=sids).prefetch_related(
                Prefetch(
                    'sampletestmap_set',
                    queryset=SampleTestMap.objects.select_related('test_id')
                )
            ).order_by('sample_id')

            for sample in sample_tests:
                for testmap in sample.sampletestmap_set.all():
                    test = testmap.test_id
                    sample_test_data.append({
                        'sample': sample,
                        'testname': test.test_name,
                        'testid': test.test_id,
                        'default_smearing': test.smear_process,
                        'sample_test_map_id': testmap.sample_test_map_id
                    })

            html = render_to_string(
                "admin/sample/smearing_selection_prompt.html",
                {
                    "sample_data": sample_data,
                    "sample_test_data": sample_test_data,
                    "base_template": "admin/popup_base.html"
                },
                request=request
            )
            return JsonResponse({
                "status": "form_html",
                "html": html,
                # "post_url": reverse('admin:sample_sample_send_to_prepare_liquid_sample'),
                "post_url": request.path,
                "csrf_token": request.COOKIES.get("csrftoken"),
            })
        elif method == 'perform_imageqc_method':
            ga = GenericAction()
            form_type, form_obj = ga.generic_action_call(
                request, qs, desired_action=action, action_desc=method
            )
            if form_type == "render_form":
                html = render_to_string(
                    "admin/qc_status_form.html",
                    {"samples": qs, "form": form_obj},
                    request=request
                )
                return JsonResponse({
                    "status": "form_html",
                    "html": html,
                    "post_url": request.path,
                    "csrf_token": request.COOKIES.get("csrftoken"),
                })

    # 7) Process automatic samples
    action_results = []
    post_auto_pending_blank = []

    for sid in automatic:
        try:
            sample = Sample.objects.get(sample_id=sid)
            result = process_single_sample_automatically(sample, request)
            action_results.append(result)
            sample.refresh_from_db()
            if not sample.pending_action:
                post_auto_pending_blank.append(sample.sample_id)
        except Exception as e:
            action_results.append({"sample_id": sid, "status": "error", "message": str(e)})

    # 8) Route both blanks before and after auto-processing
    routing_candidates = set(post_auto_pending_blank) | set(pending_action_blanks)
    valid_ids, invalid_meta = filter_valid_routing(request, list(routing_candidates))

    routing_results = []
    if valid_ids:
        routed = UtilClass.process_workflow_steps_wetlab(
            None, request, valid_ids, accession_flag="N"
        ) or []
        for r in routed:
            routing_results.append({
                "sample_id": r["sample_id"],
                "current_step": r.get("current_step"),
                "next_step": r.get("next_step"),
                "status": "routed"
            })

    summary = {
        "total": len(ids),
        "automatic": len(automatic),
        "form_groups": 0,
        "not_found": len(not_found),
        "routed": len(routing_results),
        "routing_candidates": len(routing_candidates),
        "valid_routing_candidates": len(valid_ids),
        "invalid_routing_samples": len(invalid_meta)
    }

    return JsonResponse({
        "status": "ok",
        "action_results": action_results,
        "routing_results": routing_results,
        "not_found": not_found,
        "invalid_routing_samples": invalid_meta,
        "summary": summary,
    })


def get_action_behavior(sample, request):
    """
    Determine if a sample's pending action can be processed automatically
    or requires form input
    """
    from .models import Sample, SampleTestMap
    from tests.models import TestWorkflowStep, TestWorkflowStepActionMap
    from workflows.models import WorkflowStep

    try:
        # Build the same logic as the main function to get action_method
        qs = Sample.objects.filter(sample_id=sample.sample_id)

        # Get effective workflow (same logic as main function)
        eff_wf = (
            Sample.objects.filter(sample_id=sample.sample_id)
            .annotate(
                effective_workflow_id=Case(
                    When(accession_sample_id__isnull=True, then=F("workflow_id")),
                    When(accession_sample_id__isnull=False, then=F("accession_sample__workflow_id")),
                    default=Value(None),
                    output_field=IntegerField(),
                )
            )
            .values_list("effective_workflow_id", flat=True)
        )
        effective_wf_id = eff_wf[0] if eff_wf else None

        # Find test_workflow_step
        stm = SampleTestMap.objects.filter(sample_id=sample).first()
        tws = None
        cur = sample.current_step
        if stm:
            tws = TestWorkflowStep.objects.filter(
                test_id=stm.test_id,
                workflow_id=stm.workflow_id,
                workflow_step_id__step_id=cur,
            ).first()

        # Build fallback maps (same logic as main function)
        wf_dict = {
            step_id: wf_id
            for wf_id, step_id in WorkflowStep.objects.filter(
                workflow_id=effective_wf_id, workflow_type="WetLab", step_id=cur
            ).values_list("workflow_step_id", "step_id")
        }
        ts_dict = {
            step_id: tws_id
            for tws_id, step_id in TestWorkflowStep.objects.filter(
                sample_type_id=sample.sample_type_id,
                container_type_id=sample.container_type_id,
                test_id=stm.test_id if stm else None,
                workflow_id=stm.workflow_id if stm else None,
                workflow_step_id__workflow_type="WetLab",
                workflow_step_id__step_id=cur,
            ).values_list("test_workflow_step_id", "workflow_step_id__step_id")
        }

        # Choose key
        if cur in wf_dict:
            key = wf_dict[cur]
        elif cur in ts_dict:
            key = ts_dict[cur]
        elif tws:
            key = tws.test_workflow_step_id
        else:
            raise ValueError(f"No step match for {sample.sample_id}")

        # Get action method
        am = TestWorkflowStepActionMap.objects.filter(
            Q(testwflwstepmap_id=key) | Q(workflow_step_id_id=key),
            action=sample.pending_action
        ).values_list("action_method", flat=True)

        if not am:
            raise ValueError(f"No action_method for {sample.sample_id}")

        action_method = am[0]

        # Check if this action method requires form input
        if action_method == 'perform_imageqc_method':
            form_url = '/gulfcoastpathologists/ihcworkflow/ihcworkflow/'
            return {
                'type': 'form',
                'action_method': action_method,
                'form_class': 'QCStatusForm',  # Based on your code
                'form_url': form_url
            }
        elif action_method == 'prepare_liquid_sample':
            form_url = '/gulfcoastpathologists/sample/sample/smearing-selection-prompt/'
            return {
                'type': 'form',
                'action_method': action_method,
                'form_class': 'SmearingSelectionForm',
                'form_url': form_url
            }
        else:
            # These methods can be processed automatically
            return {
                'type': 'automatic',
                'action_method': action_method
            }

    except Exception as e:
        log.error(f"Error determining action behavior for {sample.sample_id}: {e}")
        return {'type': 'error', 'message': str(e)}


def process_single_sample_automatically(sample, request):
    from util.actions import GenericAction
    try:
        ga = GenericAction()
        res = ga.generic_action_call(
            request,
            Sample.objects.filter(sample_id=sample.sample_id),
            desired_action=sample.pending_action,
            action_desc=sample.pending_action
        )
        if len(res) == 3:
            flag, msg, err = res
        else:
            flag, msg = res;
            err = ""
        return {
            "sample_id": sample.sample_id,
            "action_method": sample.pending_action,
            "status": "success" if flag == "Y" else "failed",
            "message": msg,
        }
    except Exception as e:
        return {"sample_id": sample.sample_id, "status": "error", "message": str(e)}


def filter_valid_routing(request, sample_ids):
    """
    Returns (valid_ids, invalid_metadata)
    where invalid_metadata is a list of {"sample_id":…, "reason":…}.
    """
    Sample = apps.get_model('sample', 'Sample')
    SampleTestMap = apps.get_model('sample', 'SampleTestMap')
    TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
    WorkflowStep = apps.get_model('workflows', 'WorkflowStep')

    valid = []
    invalid = []
    try:
        # 1) Exclude samples with pending actions
        pending = set(
            Sample.objects.filter(sample_id__in=sample_ids)
            .exclude(pending_action__isnull=True)
            .exclude(pending_action="")
            .values_list('sample_id', flat=True)
        )
        for sid in pending:
            invalid.append({"sample_id": sid, "reason": "has_pending_action"})
        candidates = [sid for sid in sample_ids if sid not in pending]
        if not candidates:
            return [], invalid

        # 2) Gather sample and test mappings
        sample_maps = Sample.objects.filter(sample_id__in=candidates)
        sample_type_ids = sample_maps.values_list('sample_type_id', flat=True).distinct()
        container_type_ids = sample_maps.values_list('container_type_id', flat=True).distinct()
        test_maps = SampleTestMap.objects.filter(sample_id_id__in=candidates)
        test_ids = test_maps.values_list('test_id_id', flat=True).distinct()
        workflow_ids_tests = test_maps.values_list('workflow_id_id', flat=True).distinct()

        # 3) Annotate effective workflows
        samples_with_wf = (
            Sample.objects.filter(sample_id__in=candidates)
            .annotate(
                effective_workflow_id=Case(
                    When(accession_sample_id__isnull=True, then=F('workflow_id')),
                    When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                    default=Value(None),
                    output_field=IntegerField(),
                )
            )
        )
        wf_map = dict(samples_with_wf.values_list('sample_id', 'effective_workflow_id'))
        wf_ids_samples = samples_with_wf.values_list('effective_workflow_id', flat=True).distinct()

        # 4) Load workflow steps
        workflow_steps = (
            WorkflowStep.objects
            .filter(workflow_id__in=wf_ids_samples, workflow_type='WetLab')
            .annotate(
                test_workflow_step_id=Value(None, output_field=IntegerField()),
                sample_type_id=Value(None, output_field=IntegerField()),
                container_type_id=Value(None, output_field=IntegerField()),
                test_id=Value(None, output_field=IntegerField()),
                workflow_step_id__workflow_step_id=F('workflow_step_id'),
                workflow_step_id__workflow_id=F('workflow_id'),
                workflow_step_id__step_id=F('step_id'),
                workflow_step_id__step_no=F('step_no'),
                workflow_step_id__department=F('department'),
            )
            .values(
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
        )

        test_wf_steps = (
            TestWorkflowStep.objects.select_related('workflow_step_id')
            .filter(
                sample_type_id__in=sample_type_ids,
                container_type_id__in=container_type_ids,
                test_id__in=test_ids,
                workflow_id__in=workflow_ids_tests,
                workflow_step_id__workflow_id__in=workflow_ids_tests,
                workflow_step_id__workflow_type='WetLab',
            )
            .values(
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
        )

        # 5) Validate each sample WITHOUT modifying it
        for sm in sample_maps:
            sid = sm.sample_id
            wf_id = wf_map.get(sid)
            try:
                if wf_id:
                    rows = workflow_steps.filter(workflow_id=wf_id)
                else:
                    tm = test_maps.filter(sample_id_id=sid).first()
                    if not tm:
                        # Silently skip samples without test mapping
                        continue
                    rows = test_wf_steps.filter(
                        sample_type_id=sm.sample_type_id,
                        container_type_id=sm.container_type_id,
                        test_id=tm.test_id_id,
                        workflow_id=tm.workflow_id_id,
                    )

                if not rows.exists():
                    # Silently skip samples without workflow steps
                    continue

                # CHANGED: Use validation-only method instead of get_current_and_next_step
                has_next_step = UtilClass.validate_next_step_exists(
                    filtered_steps=rows,
                    sample=sm,
                    workflow_map=wf_map
                )

                if has_next_step:
                    valid.append(sid)
                # else: silently skip - no next step available

            except Exception as e:
                log.error(f"Validation error for sample {sid}: {e}")
                # Silently skip samples with validation errors
                continue

    except Exception as e:
        log.error(f"Routing validation failed: {e}")
        return [], []

    return valid, invalid


def get_model_for_sample_ids(sample_ids):
    """
    Return mapping of model class -> list of sample_ids.
    """
    ihc_ids = set(
        IhcWorkflow.objects.filter(sample_id__in=sample_ids)
        .values_list("sample_id", flat=True)
    )
    base_ids = set(sample_ids) - ihc_ids
    model_map = {}
    if ihc_ids:
        model_map[IhcWorkflow] = list(ihc_ids)
    if base_ids:
        model_map[Sample] = list(base_ids)
    return model_map
