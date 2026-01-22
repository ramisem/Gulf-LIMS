from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Matches:
    #   /ws/agent/<agent_id>/
    #   /anything/ws/agent/<agent_id>/
    re_path(
        r"^(?:.*/)?ws/agent/(?P<agent_id>[^/]+)/?$",
        consumers.AgentConsumer.as_asgi()
    ),

    # Matches:
    #   /ws/notify/<client_id>/
    #   /anything/ws/notify/<client_id>/
    re_path(
        r"^(?:.*/)?ws/notify/(?P<client_id>[^/]+)/?$",
        consumers.NotifyConsumer.as_asgi()
    ),
]
