from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security'
    default_site = "controllerapp.views.Controller"
    verbose_name = 'Security'
