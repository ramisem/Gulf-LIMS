from __future__ import absolute_import, unicode_literals

import logging
import os
from logging.handlers import RotatingFileHandler

from celery import Celery
from celery.signals import after_setup_logger
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controllerapp.settings')

app = Celery(getattr(settings, 'CELERY_APP_NAME'))
app.config_from_object('django.conf:settings', namespace=getattr(settings, 'CELERY_NAMESPACE'))

app.autodiscover_tasks()


def setup_logging(**kwargs):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    info_file_handler = RotatingFileHandler(getattr(settings, 'CELERY_LOG_FILE_FOR_INFO'),
                                            maxBytes=getattr(settings, 'CELERY_LOG_MAX_BYTES', 1024 * 1024 * 300),
                                            backupCount=getattr(settings, 'CELERY_LOG_BACKUP_COUNT', 10))
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(formatter)

    error_file_handler = RotatingFileHandler(getattr(settings, 'CELERY_LOG_FILE_FOR_ERROR'),
                                             maxBytes=getattr(settings, 'CELERY_LOG_MAX_BYTES', 1024 * 1024 * 300),
                                             backupCount=getattr(settings, 'CELERY_LOG_BACKUP_COUNT', 10))
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    logger = logging.getLogger('celery')
    logger.addHandler(info_file_handler)
    logger.addHandler(error_file_handler)


after_setup_logger.connect(setup_logging)
