from django.apps import AppConfig


class SampleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sample'
    verbose_name = 'Enterprise'
    default_site = "controllerapp.views.Controller"
