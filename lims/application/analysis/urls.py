from django.urls import path

from analysis import views

app_name = 'analysis'


class URLS:
    urlpatterns = [
        path('reportoption/<slug:report_option_id>/autosave/', views.report_option_dtl_autosave,
             name='report_option_autosave'),
        path('admin/open-pdf/', views.open_pdf_after_action, name='open-pdf-after-action'),
        path("get_amendment_types/", views.get_amendment_types, name="get_amendment_types"),
        path("amend-report-action/", views.amend_report_action, name="amend_report_action"),
        path("report_preview/", views.preview_report_view, name="preview_report"),
        path("report_signout/", views.report_signout_view, name="report_signout"),
        path("merge_report_signout/", views.merge_report_signout_view, name="merge_report_signout"),
        path("merge_report_signout_view_for_amendment/", views.merge_report_signout_view_for_amendment,
             name="merge_report_signout_view_for_amendment"),
        path('mergereporting/<slug:merge_reporting_id>/autosave/', views.merge_reporting_dtl_autosave,
             name='merge_reporting_dtl_autosave'),
        path('historicalmergereporting/<slug:merge_reporting_id>/autosave/', views.merge_reporting_dtl_autosave,
             name='merge_reporting_dtl_autosave'),
        path("merge_report_preview/", views.merge_preview_report_view, name="merge_preview_report"),
        path("merge_report_preview_for_amendment/", views.merge_preview_report_view_for_amendment,
             name="merge_preview_report_view_for_amendment"),
        path("fetch_analyte_value/", views.fetch_analyte_value, name="fetch_analyte_value"),
        path("get_macros/", views.get_macros, name="get_macros"),
        path("get_macro_content/", views.get_macro_content, name="get_macro_content"),

    ]
