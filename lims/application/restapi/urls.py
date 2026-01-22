from django.urls import path

from .views import EventRuleCreate, CustomPeriodicTaskUpdateAPIView, EventRuleUpdate

app_name = 'restapi'


class URLS:
    urlpatterns = [
        path('event_rules/', EventRuleCreate.as_view(), name='create-event-rule'),
        path('event_rule/<str:name>/', EventRuleUpdate.as_view(), name='update-event-rule'),
        path('task/<str:name>/', CustomPeriodicTaskUpdateAPIView.as_view(), name='update-task'),
    ]

    def __dir__(self):
        return self.urlpatterns
