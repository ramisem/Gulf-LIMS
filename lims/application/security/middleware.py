import pytz
from django.utils import timezone

from controllerapp import settings


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.session.get('currenttimezone', getattr(settings, 'SERVER_TIME_ZONE', 'UTC'))
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()

        response = self.get_response(request)
        return response
