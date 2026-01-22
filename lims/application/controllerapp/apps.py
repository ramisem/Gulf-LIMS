from django.apps import AppConfig
import threading
import os
from logutil.log import log

class ControllerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'controllerapp'

    _listener_started = False
    _listener_lock = threading.Lock()

    def ready(self):

        from django.conf import settings

        # Starting the listener

        with self._listener_lock:
            if not ControllerAppConfig._listener_started:
                try:
                    from hl7.listener import HL7Listener

                    listener_host = getattr(settings, 'APPLICATION_ROOT_URL', '0.0.0.0')
                    listener_port = getattr(settings, 'HL7_LISTENER_PORT', 6660)

                    log.info(f"Preparing to start hl7 listener at {listener_host}:{listener_port}")

                    listener = HL7Listener(listener_host, listener_port)
                    thread = threading.Thread(target=listener.start, daemon=True)
                    thread.start()

                    log.info(f"HL7 Listener thread started at {listener_host}:{listener_port}")

                    ControllerAppConfig._listener_started = True
                except Exception as e:
                    log.error(f"Error starting HL7 Listener: {e}")
