import logging
import os

from django.apps import AppConfig
from django.apps import apps
from django.conf import settings

from logutil.log import log


class LogUtilConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logutil'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true' or not settings.DEBUG:
            log.info("Starting customlogger initialization")
            from logutil.customlogger import custom_wrap_project_apps
            # Ensure models loaded
            self._preload_all_models()
            # Let custom_wrap import submodules and wrap them
            custom_wrap_project_apps()
            log.info("Customlogger initialization complete")

    def _preload_all_models(self):
        """Ensure all models are imported before wrapping attempts."""
        log.debug("Preloading all application models")

        for app_config in apps.get_app_configs():
            try:
                __import__(f"{app_config.name}.models")
                log.debug(f"Successfully preloaded models for {app_config.name}")
            except ImportError as e:
                if "No module named" not in str(e):
                    log.warning(f"Error preloading models for {app_config.name}: {e}")
            except Exception as e:
                log.error(f"Unexpected error preloading {app_config.name}.models: {e}")

    def _register_app_loggers(self):
        """Register loggers for all project apps."""
        app_folder_name = getattr(settings, "APPLICATION_NAME", "")
        if not app_folder_name:
            log.warning("APPLICATION_NAME not set in settings")
            return

        exclude_prefixes = getattr(settings, "CUSTOMLOGGER_EXCLUDE_MODULES", [])

        for app_name in settings.INSTALLED_APPS:
            # Skip excluded apps
            if any(app_name.startswith(excl.rstrip('.')) for excl in exclude_prefixes):
                log.debug(f"Skipping excluded app: {app_name}")
                continue

            try:
                app_logger = logging.getLogger(app_name)
                app_logger.info(f"Registered logger for app: {app_name}")
            except Exception as e:
                log.error(f"Failed to register logger for {app_name}: {e}")
