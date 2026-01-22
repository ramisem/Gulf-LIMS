from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.translation import gettext as _

from routinginfo.util import UtilClass
from ihcworkflow.models import IhcWorkflow
from ihcworkflow.forms import IhcSampleBulkEditForm
from security.views import JobTypeContextMixin
from logutil.log import log


class IhcSampleBulkEditView(JobTypeContextMixin, View):
    form_class = IhcSampleBulkEditForm
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
        context['workflow'] = self.request.GET.get('workflow', 'ihc')
        # Pass the Sample model's _meta as opts so the admin template can access app_label, etc.
        context.setdefault("opts", IhcWorkflow._meta)
        return context

    def get_queryset(self, ids):
        return IhcWorkflow.objects.filter(sample_id__in=ids)

    def get(self, request):
        ids = request.GET.get('ids', '')
        log.info(f"Sample ids --> {ids}")
        if not ids:
            messages.error(request, "No samples selected for bulk editing.")
            return redirect("controllerapp:ihcworkflow_ihcworkflow_changelist")
        ids = ids.split(',')
        queryset = self.get_queryset(ids)
        SampleFormSet = modelformset_factory(IhcWorkflow, form=IhcSampleBulkEditForm, extra=0)
        formset = SampleFormSet(queryset=queryset, auto_id='id_%s')
        context = self.get_context_data(formset=formset)
        return render(request, self.template_name, context)

    def post(self, request):
        ids = request.GET.get('ids', '')
        log.info(f"Sample ids --> {ids}")
        ids = ids.split(',') if ids else []
        queryset = self.get_queryset(ids)
        SampleFormSet = modelformset_factory(IhcWorkflow, form=IhcSampleBulkEditForm, extra=0)
        formset = SampleFormSet(request.POST, queryset=queryset, auto_id='id_%s')
        if formset.is_valid():
            formset.save()

            q = request.GET.get('q', '')

            # If "Save and continue editing" was clicked, redirect to same page
            if "_continue" in request.POST:
                messages.success(request,
                                 "The selected sample(s) was changed successfully. You may edit it again below.")
                return redirect(request.get_full_path())

            # otherwise go back to the changelist, re‑applying q=
            base = reverse("controllerapp:ihcworkflow_ihcworkflow_changelist")
            messages.success(request, "The selected sample(s) was changed successfully.")
            if q:
                return redirect(f"{base}?q={q}")
            return redirect(base)

        return render(request, self.template_name, self.get_context_data(formset=formset))


class SampleRouteView(View):
    def get(self, request):
        # Determine the source of the routing action
        origin = request.GET.get("origin", "bulk")  # defaults to bulk if not specified
        log.info(f"origin --> {origin}")
        # For a single sample edit, the button passes active_id and all_ids.
        active_id = request.GET.get('active_id')
        log.info(f"Active sample id --> {active_id}")
        # For bulk editing, we may simply have ids.
        all_ids = request.GET.get('all_ids') or request.GET.get('ids', '')
        log.info(f"All sample ids --> {all_ids}")

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
                return redirect(reverse("controllerapp:ihc_sample_bulk_edit") + f"?ids={all_ids}")

        # Execute the routing logic
        queryset = IhcWorkflow.objects.filter(sample_id__in=sample_ids)
        success_samples = UtilClass.process_workflow_steps_wetlab(self, request, sample_ids, 'N')
        if success_samples:
            messages.success(request, f"Routing executed for sample(s): {', '.join(sample_ids)}")

        # Redirect based on the origin of the request
        if origin == "change":
            # For the change form page, redirect back to the sample’s admin change page.
            sample = queryset.first()
            if sample:
                # Assuming your admin URL name is 'admin:sample_sample_change'
                return redirect(reverse("admin:ihcworkflow_ihcworkflow_change", args=[sample.pk]))
            else:
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            # Default: return to the bulk edit page
            return redirect(reverse("controllerapp:ihc_sample_bulk_edit") + f"?ids={all_ids}")
