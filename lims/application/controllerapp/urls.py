"""
URL configuration for controllerapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, include
from django.contrib import admin

import accessioning.urls
import analysis.urls
import ihcworkflow.urls
import configuration.urls
import masterdata.urls
import sample.urls
import security.urls
import tests.urls
from controllerapp.views import controller
from security.ajax.ajax import load_job_types_by_site
from scanner.views import upload_scan, start_scan

urlpatterns = [
    path('gulfcoastpathologists/', controller.urls),
    path('', lambda request: redirect('gulfcoastpathologists/'), name='gulfcoastpathologists'),
    path('ajax/load-job-types/', load_job_types_by_site, name='ajax_load_job_types'),
    path('tests/', include((tests.urls.URLS, 'tests'), namespace='tests')),
    path('accessioning/', include((accessioning.urls.URLS, 'accessioning'), namespace='accessioning')),
    path('security/', include((security.urls.URLS, 'security'), namespace='security')),
    path('masterdata/', include((masterdata.urls.URLS, 'masterdata'), namespace='masterdata')),
    path('sample/', include((sample.urls.URLS, 'sample'), namespace='sample')),
    path('ihcworkflow/', include((ihcworkflow.urls.URLS, 'ihcworkflow'), namespace='ihcworkflow')),
    path('configuration/', include((configuration.urls.URLS, 'configuration'), namespace='configuration')),
    path('summernote/', include('django_summernote.urls')),
    path('editor/', include('django_summernote.urls')),
    path('analysis/', include((analysis.urls.URLS, 'analysis'), namespace='analysis')),
    path('admin/', admin.site.urls),
    # --------------------------------------------
    #  SCANNER API ENDPOINTS (NEW REQUIRED ROUTES)
    # --------------------------------------------
    path('api/scan-upload', upload_scan, name='scan_upload'),
    path('api/start-scan', start_scan, name='start_scan'),
    # --------------------------------------------
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)
