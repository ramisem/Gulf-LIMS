from django.apps import AppConfig


class ResourceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'labresource'
    default_site = "controllerapp.views.Controller"
    verbose_name = 'Lab-Resource'
