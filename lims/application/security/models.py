from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.apps import apps
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteTimezone(models.Model):
    name = models.CharField(_("name"), max_length=150, unique=True)
    description = models.CharField(_("description"), max_length=150, null=True, blank=True)
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _("site timezone")
        verbose_name_plural = _("site timezones")

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name


class Site(models.Model):
    name = models.CharField(_("name"), max_length=150, unique=True)
    history = AuditlogHistoryField()
    timezone = models.ForeignKey(SiteTimezone, on_delete=models.RESTRICT, null=True, verbose_name="Timezone")
    abbreviation = models.CharField(max_length=20, null=True, verbose_name="Abbreviation")

    class Meta:
        verbose_name = _("site")
        verbose_name_plural = _("sites")

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name


class Department(models.Model):
    name = models.CharField(_("name"), max_length=150, unique=True)
    history = AuditlogHistoryField()
    siteid = models.ForeignKey(Site, on_delete=models.RESTRICT, null=True, verbose_name="Site")
    lab_name = models.CharField(max_length=40, null=True, blank=True, verbose_name="Lab Name")

    class Meta:
        verbose_name = _("department")
        verbose_name_plural = _("departments")

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name


class JobType(Group):
    history = AuditlogHistoryField()
    departmentid = models.ForeignKey(Department, on_delete=models.RESTRICT, null=True, blank=True,
                                     verbose_name="Department")
    site_independent = models.BooleanField(default=False, verbose_name='Is Site Independent')

    class Meta:
        verbose_name = "Job Type"
        verbose_name_plural = 'Job Types'

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(unique=True)
    jobtypes = models.ManyToManyField(
        JobType,
        verbose_name=_("jobtypes"),
        blank=True,
        help_text=_(
            "The job types this user belongs to. A user will get all permissions "
            "granted to each of their job types."
        ),
        related_name="users",
        related_query_name="jobtype",
    )
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = "Registered User"
        verbose_name_plural = 'Registered Users'

    def __str__(self):
        return self.username


class DepartmentPrinter(models.Model):
    department_printer_id = models.AutoField(primary_key=True, verbose_name="Department Printer ID")
    printer_id = models.ForeignKey('reporting.Printer',
                                   null=False,
                                   blank=False,
                                   on_delete=models.RESTRICT,
                                   verbose_name="Printer")
    jobtype_id = models.ForeignKey(JobType, null=False, blank=False, on_delete=models.RESTRICT, verbose_name="Jobtype")

    @property
    def printer_path(self):
        if self.printer_id:
            return self.printer_id.printer_path
        return ""

    class Meta:
        verbose_name = "Department Printer"
        verbose_name_plural = "Department Printers"
        unique_together = ('printer_id', 'jobtype_id')

        def __str__(self):
            return str(self.printer_id) + "-" + str(self.jobtype_id)


class UserPrinterInfo(models.Model):
    user_printer_info_id = models.AutoField(primary_key=True, verbose_name="User Printer Info ID")
    userid = models.ForeignKey(User, null=False, blank=False, verbose_name="User ID", on_delete=models.RESTRICT)
    jobtype_id = models.ForeignKey(JobType, null=False, blank=False, on_delete=models.RESTRICT, verbose_name="Jobtype")
    printer_category = models.CharField(null=False, blank=False, verbose_name="Print Operation Category")
    is_default = models.BooleanField(default=False, verbose_name='Is Default Printer')
    printer_id = models.ForeignKey('reporting.Printer',
                                   null=False,
                                   blank=False,
                                   on_delete=models.RESTRICT,
                                   verbose_name="Printer")

    class Meta:
        verbose_name = "User Printer Info"
        verbose_name_plural = "User Printer Info"

    def save(self, *args, **kwargs):
        # If setting is_default=True, ensure no other instance has it for the same combination
        if self.is_default:
            UserPrinterInfo.objects.filter(
                userid=self.userid,
                jobtype_id=self.jobtype_id,
                printer_category=self.printer_category,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.printer_category) + "-" + str(self.jobtype_id) + "-" + str(self.userid)


auditlog.register(SiteTimezone)
auditlog.register(Site)
auditlog.register(Department)
auditlog.register(User)
auditlog.register(JobType)
auditlog.register(DepartmentPrinter)
auditlog.register(UserPrinterInfo)
