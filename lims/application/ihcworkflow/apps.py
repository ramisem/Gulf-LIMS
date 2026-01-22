from django.apps import AppConfig


class IhcworkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ihcworkflow'
    verbose_name = 'IHC Workflow'
    default_site = "controllerapp.views.Controller"
