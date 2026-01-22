from auditlog.admin import LogEntryAdmin
from auditlog.filters import ResourceTypeFilter
from auditlog.models import LogEntry
from django.contrib import admin
from rangefilter.filters import DateRangeFilter

from audit.mixins import ArchivedAuditLogMixin
from audit.models import ArchivedAuditLog
from controllerapp.views import controller


class CustomDateRangeFilter(DateRangeFilter):
    template = 'admin/audit/custom_date_range_filter.html'


class CustomLogEntryAdmin(LogEntryAdmin):
    search_fields = []
    list_filter = ['object_id', ResourceTypeFilter, 'action', ('timestamp', CustomDateRangeFilter)]
    change_form_template = 'admin/audit/audit_change_form.html'
    change_list_template = 'admin/audit/audit_change_list.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_as_new'] = False
        extra_context['show_save_and_add_another'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_delete_link'] = False
        extra_context['original'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class ArchivedAuditLogAdmin(admin.ModelAdmin, ArchivedAuditLogMixin):
    search_fields = []
    list_display = ["created", "resource_url", "action", "msg_short", "user_url"]
    list_filter = ['object_id', ResourceTypeFilter, 'action', ('timestamp', CustomDateRangeFilter)]
    change_form_template = 'admin/audit/audit_change_form.html'
    change_list_template = 'admin/audit/audit_change_list.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_as_new'] = False
        extra_context['show_save_and_add_another'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_delete_link'] = False
        extra_context['original'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    readonly_fields = ["created", "resource_url", "action", "user_url", "msg"]
    fieldsets = [
        (None, {"fields": ["created", "user_url", "resource_url"]}),
        ("Changes", {"fields": ["action", "msg"]}),
    ]

    def has_add_permission(self, request):
        # As audit admin doesn't allow log creation from admin
        return False


controller.register(LogEntry, CustomLogEntryAdmin)
controller.register(ArchivedAuditLog, ArchivedAuditLogAdmin)
