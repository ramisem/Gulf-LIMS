from functools import update_wrapper

from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.utils.translation import gettext as _

from configuration.models import RefValues
from controllerapp import settings
from controllerapp.forms import AdminJobTypeChangeForm
from sample.views import SampleBulkEditView
from ihcworkflow.views import IhcSampleBulkEditView
from security.forms import UserGroupAuthenticationForm
from security.views import JobTypeChangeView, JobTypeChangeDoneView


class Controller(AdminSite):

    def get_urls(self):

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)

            wrapper.admin_site = self
            return update_wrapper(wrapper, view)

        super_urls = super().get_urls()
        urls = [
            path('jobtype_change/', wrap(self.jobtype_change, cacheable=True), name="jobtype_change"),
            path('jobtype_change/done/', wrap(self.jobtype_change_done, cacheable=True), name="jobtype_change_done"),
            path('bulk-edit-samples/', wrap(self.sample_bulk_edit, cacheable=True), name="sample_bulk_edit"),
            path('bulk-edit-ihc-samples/', wrap(self.ihc_sample_bulk_edit, cacheable=True),
                 name="ihc_sample_bulk_edit"),
        ]
        urls += super_urls
        return urls

    def login(self, request, extra_context=None):
        """
        Display the login form for the given HttpRequest.
        """
        if request.method == "GET" and self.has_permission(request):
            # Already logged-in, redirect to admin index
            index_path = reverse("admin:index", current_app=self.name)
            return HttpResponseRedirect(index_path)

        # Since this module gets imported in the application's root package,
        # it cannot import models from other applications at the module level,
        # and django.contrib.admin.forms eventually imports User.

        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
        }
        if (
                REDIRECT_FIELD_NAME not in request.GET
                and REDIRECT_FIELD_NAME not in request.POST
        ):
            context[REDIRECT_FIELD_NAME] = reverse("admin:index", current_app=self.name)
        context.update(extra_context or {})

        defaults = {
            "extra_context": context,
            "authentication_form": self.login_form or UserGroupAuthenticationForm,
            "template_name": self.login_template or "admin/auth/login.html",
        }
        request.current_app = self.name
        return LoginView.as_view(**defaults)(request)

    def each_context(self, request):
        script_name = request.META["SCRIPT_NAME"]
        site_url = (
            script_name if self.site_url == "/" and script_name else self.site_url
        )
        required_reftype = getattr(settings, 'APPLICATION_MODULE_IMAGES_REFERENCE', '')
        module_images = RefValues.objects.filter(reftype_id__name=required_reftype).values_list('value',
                                                                                                'display_value')
        module_images_dict = {value: display_value for value, display_value in module_images}
        return {
            "site_title": self.site_title,
            "site_header": self.site_header,
            "site_url": site_url,
            "has_permission": self.has_permission(request),
            "available_apps": self.get_app_list(request),
            "is_popup": False,
            "is_nav_sidebar_enabled": self.enable_nav_sidebar,
            'build_number': settings.BUILD_NUMBER,
            'module_images': module_images_dict,
        }

    def jobtype_change(self, request, extra_context=None):
        url = reverse("controllerapp:jobtype_change_done", current_app=self.name)
        defaults = {
            "form_class": AdminJobTypeChangeForm,
            "success_url": url,
            "extra_context": {**self.each_context(request), **(extra_context or {})},
        }
        request.current_app = self.name
        return JobTypeChangeView.as_view(**defaults)(request)

    def jobtype_change_done(self, request, extra_context=None):
        defaults = {
            "extra_context": {**self.each_context(request), **(extra_context or {})},
        }
        request.current_app = self.name
        return JobTypeChangeDoneView.as_view(**defaults)(request)

    def sample_bulk_edit(self, request, extra_context=None):
        defaults = {
            "extra_context": {**self.each_context(request), **(extra_context or {})},
        }
        request.current_app = self.name
        return SampleBulkEditView.as_view(**defaults)(request)

    def ihc_sample_bulk_edit(self, request, extra_context=None):
        defaults = {
            "extra_context": {**self.each_context(request), **(extra_context or {})},
        }
        request.current_app = self.name
        return IhcSampleBulkEditView.as_view(**defaults)(request)


controller = Controller(name="controllerapp")
