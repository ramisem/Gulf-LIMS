from django.urls import path

from configuration.ajax import ajax

app_name = 'configuration'

class URLS:
    urlpatterns = [
        path("ajax/get_staining_techniques/", ajax.get_staining_techniques, name="get_staining_techniques"),
    ]