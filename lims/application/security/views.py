from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, TemplateView

from controllerapp import settings
from security.forms import JobTypeChangeForm
from security.models import JobType, Site


class JobTypeContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"title": self.title, "subtitle": None, **(self.extra_context or {})}
        )
        return context


class JobTypeChangeView(JobTypeContextMixin, FormView):
    form_class = JobTypeChangeForm
    success_url = reverse_lazy("controllerapp:jobtype_change_done")
    template_name = "registration/jobtype_change_form.html"
    title = _("JobType change")

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"title": self.title, "subtitle": None, **(self.extra_context or {})}
        )
        return context

    def form_valid(self, form):
        form.save()
        selectedjobtype = form.cleaned_data.get("selectedjobtype")
        selectedsite = form.cleaned_data.get("selectedsite")
        if 'currentdepartmentid' in self.request.session:
            del self.request.session['currentdepartmentid']
        if 'currentjobtype' in self.request.session:
            del self.request.session['currentjobtype']
        if 'currentsite' in self.request.session:
            del self.request.session['currentsite']
        if 'currenttimezone' in self.request.session:
            del self.request.session['currenttimezone']
        self.request.session['currentjobtype'] = selectedjobtype
        jobtype = JobType.objects.filter(name=selectedjobtype).first()
        if jobtype.departmentid:
            self.request.session['currentdepartmentid'] = jobtype.departmentid.name
        site = Site.objects.get(name=selectedsite)
        timezone = site.timezone.name if site.timezone else getattr(settings, 'SERVER_TIME_ZONE', 'UTC')
        self.request.session['currentsite'] = site.name
        self.request.session['currenttimezone'] = timezone
        return super().form_valid(form)


class JobTypeChangeDoneView(JobTypeContextMixin, TemplateView):
    template_name = "registration/jobtype_change_done.html"
    title = _("JobType change successful")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"title": self.title, "subtitle": None, **(self.extra_context or {})}
        )
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
