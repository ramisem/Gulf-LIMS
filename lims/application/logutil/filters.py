import logging
import random
import threading


class DeveloperContextFilter(logging.Filter):
    """
    Adds contextual developer info to log records and supports log sampling.
    Controlled by settings:
      CUSTOMLOGGER_ENABLED (bool) – enable/disable entirely
      CUSTOMLOGGER_SAMPLE_RATE (float 0–1) – probability of logging
    """

    _local = threading.local()

    def __init__(self, name=""):
        super().__init__(name)
        from django.conf import settings
        self.enabled = getattr(settings, "CUSTOMLOGGER_ENABLED", False)
        self.sample_rate = getattr(settings, "CUSTOMLOGGER_SAMPLE_RATE", 1.0)

    def filter(self, record):
        if not self.enabled:
            return True  # Pass through without extra fields

        if self.sample_rate < 1.0 and random.random() > self.sample_rate:
            return False  # Drop this log

        # Attach contextual info if available
        record.dev_module = getattr(self._local, "module", None)
        record.dev_func = getattr(self._local, "func", None)
        record.dev_class = getattr(self._local, "cls", None)
        return True

    @classmethod
    def set_context(cls, module=None, func=None, cls_name=None):
        cls._local.module = module
        cls._local.func = func
        cls._local.cls = cls_name

    @classmethod
    def clear_context(cls):
        cls._local.module = None
        cls._local.func = None
        cls._local.cls = None
