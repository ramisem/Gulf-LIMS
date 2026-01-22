from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from controllerapp.views import controller
from import_export.admin import ImportExportActionModelAdmin
from security.forms import CustomUserCreationForm, UserPrinterInfoForm, DepartmentPrinterInlineForm
from security.models import User, JobType, Department, Site, SiteTimezone, DepartmentPrinter, UserPrinterInfo
from security.resources import SiteTimezoneResource, SiteResource, DepartmentResource, JobTypeResource


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_active',)
    actions = ['activate_users', 'deactivate_users']
    ordering = ('username', 'email', 'first_name', 'last_name', 'is_active')

    add_form = CustomUserCreationForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'jobtypes')}),
    )

    filter_horizontal = (
        "jobtypes",
    )

    def save_model(self, request, obj, form, change):
        # Set is_staff to True by default when adding a new user
        obj.is_staff = True
        super().save_model(request, obj, form, change)

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_users.short_description = "Deactivate selected users"


class SiteTimezoneAdmin(ImportExportActionModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)
    resource_classes = [SiteTimezoneResource]
    change_form_template = 'admin/change_form.html'


class SiteAdmin(ImportExportActionModelAdmin):
    list_display = ("name", "timezone", "abbreviation")
    search_fields = ("name", "timezone__name")
    ordering = ("name", "timezone", "abbreviation")
    resource_classes = [SiteResource]
    change_form_template = 'admin/change_form.html'


class DepartmentAdmin(ImportExportActionModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    resource_classes = [DepartmentResource]
    change_form_template = 'admin/change_form.html'


class DepartmentPrinterInline(admin.TabularInline):
    model = DepartmentPrinter
    fields = (
        "printer_id",
        "printer_path",
    )
    extra = 0
    readonly_fields = ['printer_path']
    form = DepartmentPrinterInlineForm

    class Media:
        js = ("js/security/department_printer.js", 'js/util/util.js',)


class JobTypeAdmin(ImportExportActionModelAdmin):
    list_display = ("name", "departmentid", "site_independent")
    search_fields = ("name", "departmentid__name", "site_independent",)
    ordering = ("name", "departmentid")
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ("name", "departmentid", "site_independent", "permissions"),
        }),
    )

    fieldsets = (
        (
            None,
            {'fields': ("name", "departmentid", "site_independent", "permissions")}),
    )
    filter_horizontal = ("permissions",)
    inlines = [DepartmentPrinterInline]
    resource_classes = [JobTypeResource]
    change_form_template = 'admin/change_form.html'

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "permissions":
            qs = kwargs.get("queryset", db_field.remote_field.model.objects)
            kwargs["queryset"] = qs.select_related("content_type")
        return super().formfield_for_manytomany(db_field, request=request, **kwargs)

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                if (not obj.departmentid and not obj.site_independent) or (obj.departmentid and obj.site_independent):
                    raise ValueError(
                        'Jobtype has to be either independent of site or should have the department id associated with it.')
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return


class UserPrinterInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "userid",
                    "jobtype_id",
                    "printer_category",
                    "is_default",
                    "printer_id",
                ),
            },
        ),
    )
    list_display = (
        "userid",
                    "jobtype_id",
                    "printer_category",
                    "is_default",
                    "printer_id",
    )
    form = UserPrinterInfoForm
    change_form_template = 'admin/change_form.html'
    ordering = ['userid', 'jobtype_id', 'printer_category']

    def save_model(self, request, obj, form, change):
        try:
            if request.user.is_authenticated:
                username = request.user.username
                user_map_obj = User.objects.get(username=username)
                obj.created_by = user_map_obj
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Error saving model: {e}")
            return

    actions = ['set_as_default_printer']

    # Restrict Add, Edit, and Delete to only superusers
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return True

    def get_queryset(self, request):
        """Superusers see all records; regular users see only their own."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(userid=request.user)

    def set_as_default_printer(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "You can only select one record at a time.", level=messages.ERROR)
            return

        obj = queryset.first()
        if not request.user.is_superuser and obj.userid != request.user:
            self.message_user(request, "You can only set the default printer for yourself.", level=messages.ERROR)
            return

        obj.is_default = True
        obj.save()

        self.message_user(request, "Successfully set as the default printer.", level=messages.SUCCESS)

    class Media:
        js = (
            'js/security/user_printer_info.js', 'js/util/util.js',
        )


controller.register(SiteTimezone, SiteTimezoneAdmin)
controller.register(Site, SiteAdmin)
controller.register(Department, DepartmentAdmin)
controller.register(User, CustomUserAdmin)
controller.register(JobType, JobTypeAdmin)
controller.register(UserPrinterInfo, UserPrinterInfoAdmin)
