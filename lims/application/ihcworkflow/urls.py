from django.urls import path
from ihcworkflow.views import SampleRouteView

app_name = 'ihcworkflow'


class URLS:
    urlpatterns = [
        path('route_samples/', SampleRouteView.as_view(), name='sample_route'),
    ]
