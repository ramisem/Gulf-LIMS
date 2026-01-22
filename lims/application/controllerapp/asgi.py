"""
ASGI config for controllerapp project.
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "controllerapp.settings")

# Initialize Django before importing routing
django.setup()

import scanner.routing   # safe to import now

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(scanner.routing.websocket_urlpatterns)
    ),
})
