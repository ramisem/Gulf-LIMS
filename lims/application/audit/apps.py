from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    default_site = "controllerapp.views.Controller"
    verbose_name = 'Transaction Log'
