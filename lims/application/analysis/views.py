import json
import os
import re
from django.contrib import messages
from datetime import datetime
from urllib.parse import urlencode

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from analysis.models import ReportOption, MergeReporting, MergeReportingDtl
from analysis.models import ReportOptionDtl
from controllerapp.views import controller
from logutil.log import log
from tests.models import Analyte, TestAnalyte
from util.actions import GenericAction
from util.util import UtilClass
from django.http import HttpResponse



@csrf_exempt
@require_POST
def report_option_dtl_autosave(request, report_option_id):
    """
    AJAX autosave for ReportOptionDtl:
      - POST keys: reportoptiondtlid, analyte_id (PK or name), analyte_value
      - On model validation error → 400 + {"status":"error","errors":{field:[msgs]}}
      - On success → 200 + {"status":"success"}
    """
    if not request.user.is_authenticated:
        log.error(f"User is not authenticated!")
        return JsonResponse({'status': 'forbidden'}, status=403)

    dtl_id = request.POST.get("reportoptiondtlid")
    raw_analyte = request.POST.get("analyte_id", "").strip()
    analyte_value = request.POST.get("analyte_value", "").strip()
    log.info(f"reportoptiondtlid ---> {dtl_id}")
    log.info(f"analyte_id ---> {raw_analyte}")
    log.info(f"analyte_value ---> {analyte_value}")
    try:
        if raw_analyte.isdigit():
            analyte_obj = Analyte.objects.get(pk=int(raw_analyte))
        else:
            analyte_obj = Analyte.objects.get(analyte=raw_analyte)
    except Analyte.DoesNotExist:
        log.error(f"Analyte '{raw_analyte}' not found")
        return JsonResponse({
            "status": "error",
            "message": f"Analyte '{raw_analyte}' not found"
        }, status=404)

    if not dtl_id:
        log.error(f"Missing reportoptiondtlid")
        return JsonResponse({
            "status": "error",
            "message": "Missing reportoptiondtlid"
        }, status=400)

    try:
        dtl = ReportOptionDtl.objects.get(
            pk=dtl_id,
            report_option_id=report_option_id,
            analyte_id=analyte_obj
        )
    except ReportOptionDtl.DoesNotExist:
        log.error(f"Detail row not found")
        return JsonResponse({
            "status": "error",
            "message": "Detail row not found"
        }, status=404)

    dtl.analyte_value = analyte_value
    try:
        dtl.save()
        log.info(f"Report Option Detail ID analyte record saved successfully ---> {dtl_id}")
        return JsonResponse({"status": "success"})

    except ValidationError as ve:
        test_obj = dtl.report_option_id.test_id
        if not test_obj:
            log.error(f"Test ID not configured for this Report Option")
            return JsonResponse({
                "status": "error",
                "message": "Test ID not configured for this Report Option"
            }, status=400)

        rule = TestAnalyte.objects.get(
            test_id=test_obj,
            analyte_id=dtl.analyte_id
        )

        # Get the error message
        error_msg = ve.message_dict.get('analyte_value', [""])[0]

        # Determine the 'expected' based on which error it was
        if "must be an integer" in error_msg.lower():
            expected = "Value should be an Integer."
        elif "must be a decimal" in error_msg.lower():
            expected = "Value should be a Decimal number."
        elif "configured rule" in error_msg.lower():
            # Build expected string based on rule logic
            if rule.value_text:
                allowed_values = [v.strip() for v in rule.value_text.split(';') if v.strip()]
                if len(allowed_values) == 1:
                    expected = f"Value must be '{allowed_values[0]}'"
                else:
                    formatted = "', '".join(allowed_values)
                    expected = f"Value must be one of the below- <br>['{formatted}']"
            elif not rule.condition:
                expected = f"Value should be {rule.operator1} {rule.value1}"
            else:
                expected = (
                    f"Value should be {rule.operator1} {rule.value1} "
                    f"{rule.condition.upper()} {rule.operator2} {rule.value2}"
                )
        else:
            expected = "Invalid value."

        log.error(
            f"Validation error: {ve.message_dict} | Expected: {expected} | Current: {analyte_value}"
        )
        return JsonResponse({
            "status": "error",
            "errors": ve.message_dict,
            "expected": expected,
            "current": analyte_value
        }, status=400)

    except Exception as e:
        log.error(f"Error Message : {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


def open_pdf_after_action(request):
    pdf_url = request.session.pop("pdf_report_url", None)
    log.info(f"pdf_report_url ---> {pdf_url}")
    return JsonResponse({"pdf_url": pdf_url})


def get_amendment_types(request):
    log.info(f"Getting the configuration refvalues and referencetype")
    RefValues = apps.get_model('configuration', 'RefValues')
    ReferenceType = apps.get_model('configuration', 'ReferenceType')

    try:
        amendment_reftype = ReferenceType.objects.get(name="AmendmentType")
        amendment_types = RefValues.objects.filter(reftype_id_id=amendment_reftype.reference_type_id).values('value',
                                                                                                             'display_value')
        return JsonResponse({"amendment_types": list(amendment_types)})
    except ReferenceType.DoesNotExist:
        log.error(f"Amendment Types does not exist")
        return JsonResponse({"amendment_types": []})


@csrf_exempt
def amend_report_action(request):
    log.info(f"request.method ---> {request.method}")
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_ids = data.get("selected_ids", [])
            amendment_type = data.get("amendment_type", "")
            log.info(f"Selected Reportoption Ids ---> {selected_ids}")
            log.info(f"Selected amendment_type ---> {amendment_type}")

            # Get the model dynamically if not directly imported
            HistoricalReportOption = apps.get_model('analysis', 'HistoricalReportOption')

            # Update field (you can adjust this logic as needed)
            updated = HistoricalReportOption.objects.filter(id__in=selected_ids).update(
                pending_action=amendment_type
            )

            log.info(f"Successfully updated ---> {selected_ids}")
            return JsonResponse({"status": "success", "updated": updated})
        except Exception as e:
            log.error(f"Error Message : {str(e)}")
            return JsonResponse({"status": "error", "error": str(e)})

    log.error(f"Error Message : Invalid method")
    return JsonResponse({"status": "error", "error": "Invalid method"})


def preview_report_view(request):
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    report_option_id = request.GET.get("reportoption_id")
    log.info(f"Preview report for ID ---> {report_option_id}")

    if not report_option_id:
        log.error(f"Reportoption Id is invalid ---> {report_option_id}")
        return

    input_path = os.path.join(settings.BASE_DIR, 'static', 'reports', 'TestReport.jasper')

    # Create a timestamped output filename with report_option_id
    now = datetime.now()
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    output_filename = f"{report_option_id}_{timestamp_str}.pdf"
    output_path = os.path.join(settings.BASE_DIR, settings.REPORT_PREVIEW_OUTPUT_PATH, output_filename)

    # Call generate_report with correct args
    pdf_rel_path = UtilClass.generate_report(
        input_file=input_path,
        output_file=output_path,
        filetype='pdf',
        use_db=False,
        is_preview=True
    )

    log.info(f"PDF relative path returned from generate_report ---> {pdf_rel_path}")
    pdf_url = UtilClass.get_s3_url(pdf_rel_path)
    log.info(f"PDF S3 URL path for report ---> {pdf_url}")
    request.current_app = "controllerapp"
    context = controller.each_context(request)
    context.update({
        "pdf_url": pdf_url,
        "opts": ReportOption._meta,
        "has_permission": request.user.is_authenticated,
    })

    return render(request, "admin/analysis/reportoption/preview_report.html", context)


# This is to generate preview report for merge report
def merge_preview_report_view(request):
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    merge_reporting_id = request.GET.get("merge_reporting_id")
    log.info(f"Preview report for ID ---> {merge_reporting_id}")

    if not merge_reporting_id:
        log.error(f"Merge Reportoption Id is invalid ---> {merge_reporting_id}")
        return

    # Fetching the accession object and accession_category.
    try:
        merge_reporting = MergeReporting.objects.get(pk=merge_reporting_id)
        accession = merge_reporting.accession_id
        accession_category = accession.accession_category
    except (MergeReporting.DoesNotExist, AttributeError) as e:
        log.error(f"Could not retrieve accession or accession_category: {e}")
        return

    # Deciding the report template based on accession_category.
    if accession_category == "Pharma":
        jrxml_file = 'PharmaGulfFinalReport.jasper'
    else:
        jrxml_file = 'GulfFinalReport.jasper'

    input_path = os.path.join(settings.BASE_DIR, 'static', 'reports', jrxml_file)

    # Create a timestamped output filename with report_option_id
    now = datetime.now()
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    output_filename = f"{merge_reporting_id}_{timestamp_str}.pdf"
    output_path = os.path.join(settings.BASE_DIR, settings.REPORT_PREVIEW_OUTPUT_PATH, output_filename)

    # Call generate_report with correct args
    pdf_rel_path = UtilClass.generate_report(
        input_file=input_path,
        output_file=output_path,
        merge_reporting_id=merge_reporting_id,
        filetype='pdf',
        use_db=True,
        is_preview=True
    )
    log.info(f"PDF relative path returned from generate_report ---> {pdf_rel_path}")
    pdf_url = UtilClass.get_s3_url(pdf_rel_path)
    log.info(f"PDF S3 URL path for report ---> {pdf_url}")
    request.current_app = "controllerapp"
    context = controller.each_context(request)
    context.update({
        "pdf_url": pdf_url,
        "opts": MergeReporting._meta,
        "has_permission": request.user.is_authenticated,
    })

    return render(request, "admin/analysis/mergereporting/merge_preview_report.html", context)


def merge_preview_report_view_for_amendment(request):
    """
    This is to generate preview report during amendment
    """
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    merge_reporting_id = request.GET.get("merge_reporting_id")
    log.info(f"Preview Amendment report for ID ---> {merge_reporting_id}")

    if not merge_reporting_id:
        log.error(f"Merge Reportoption Id is invalid ---> {merge_reporting_id}")
        return

    # Fetching the accession object and accession_category.
    try:
        merge_reporting = MergeReporting.objects.get(pk=merge_reporting_id)
        accession = merge_reporting.accession_id
        accession_category = accession.accession_category
    except (MergeReporting.DoesNotExist, AttributeError) as e:
        log.error(f"Could not retrieve accession or accession_category: {e}")
        return

    # Deciding the report template based on accession_category.
    if accession_category == "Pharma":
        jrxml_file = 'PharmaGulfFinalReport.jasper'
    else:
        jrxml_file = 'GulfFinalReport.jasper'

    input_path = os.path.join(settings.BASE_DIR, 'static', 'reports', jrxml_file)

    # Create a timestamped output filename with report_option_id
    now = datetime.now()
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    output_filename = f"{merge_reporting_id}_{timestamp_str}.pdf"
    output_path = os.path.join(settings.BASE_DIR, settings.REPORT_PREVIEW_OUTPUT_PATH, output_filename)

    # Call generate_report with correct args
    pdf_rel_path = UtilClass.generate_report(
        input_file=input_path,
        output_file=output_path,
        merge_reporting_id=merge_reporting_id,
        filetype='pdf',
        use_db=True,
        is_preview=True
    )
    log.info(f"PDF relative path returned from generate_report ---> {pdf_rel_path}")
    pdf_url = UtilClass.get_s3_url(pdf_rel_path)
    log.info(f"PDF S3 URL path for report ---> {pdf_url}")
    request.current_app = "controllerapp"
    context = controller.each_context(request)
    context.update({
        "pdf_url": pdf_url,
        "opts": MergeReporting._meta,
        "has_permission": request.user.is_authenticated,
    })

    return render(request, "admin/analysis/mergereporting/merge_preview_report_for_amendment.html", context)


# This is for Report Signout
def report_signout_view(request):
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    reportoption_id = request.GET.get("reportoption_id")
    is_signout_complete = request.GET.get("is_signout_complete")
    log.info(f"Report signout for ID ---> {reportoption_id}")
    log.info(f"Is signout complete? ---> {is_signout_complete}")

    if "Y" == is_signout_complete and reportoption_id:
        return redirect(f"/gulfcoastpathologists/analysis/historicalreportoption/{reportoption_id}/change/")
    report_option = ReportOption.objects.get(report_option_id=reportoption_id)
    pdf_url = GenericAction().report_signout_method(request, reportoption_id)
    log.info(f"PDF URL path for report ---> {pdf_url}")
    request.current_app = "controllerapp"
    context = controller.each_context(request)
    context.update({
        "pdf_url": pdf_url,
        "opts": ReportOption._meta,
        "has_permission": request.user.is_authenticated,
        "report_option_pk": report_option.pk,
    })

    return render(request, "admin/analysis/reportoption/final_report.html", context)


def merge_report_signout_view(request):
    # This is for Merge Report Signout
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    merge_reporting_id = request.GET.get("merge_reporting_id")
    is_signout_complete = request.GET.get("is_signout_complete")
    log.info(f"Report signout for ID ---> {merge_reporting_id}")
    log.info(f"Is signout complete? ---> {is_signout_complete}")

    if "Y" == is_signout_complete and merge_reporting_id:
        return redirect(f"/gulfcoastpathologists/analysisworklist/accessionhistoricalreportswrapper/")

    try:
        merge_report = MergeReporting.objects.get(merge_reporting_id=merge_reporting_id)
        pdf_url = GenericAction().merge_report_signout_method(request, merge_reporting_id)
        log.info(f"PDF URL path for report ---> {pdf_url}")
        request.current_app = "controllerapp"
        context = controller.each_context(request)
        context.update({
            "pdf_url": pdf_url,
            "opts": MergeReporting._meta,
            "has_permission": request.user.is_authenticated,
            "report_option_pk": merge_report.pk,
        })
        return render(request, "admin/analysis/mergereporting/merge_final_report.html", context)
    except Exception as e:
        log.error(f"An error occurred: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        referrer = request.META.get('HTTP_REFERER', '/gulfcoastpathologists/analysisworklist/')
        return redirect(referrer)


# this is for merge report signout view for amendment
@csrf_exempt
def merge_report_signout_view_for_amendment(request):
    # 1. Check login
    if not request.user.is_authenticated:
        params = urlencode({'next': request.get_full_path()})
        return redirect(f"/gulfcoastpathologists/login/?{params}")

    # 2. GET parameters
    merge_reporting_id = request.GET.get("merge_reporting_id")
    amendment_type_selected = request.GET.get("amendment_type")
    is_signout_complete = request.GET.get("is_signout_complete")

    # 3. POST parameter
    amendment_comments = request.POST.get("amendment_comments")

    # KEEP EXACTLY AS YOUR ORIGINAL LOGIC
    if "Y" == is_signout_complete and merge_reporting_id:
        return redirect(f"/gulfcoastpathologists/analysisworklist/accessionhistoricalreportswrapper/")

    # Also preserved EXACTLY
    merge_report = MergeReporting.objects.get(merge_reporting_id=merge_reporting_id)

    # ---- SAVE Amendment Type + Comments ----
    fields_to_update = []

    if amendment_type_selected:
        merge_report.amendment_type = amendment_type_selected
        fields_to_update.append("amendment_type")

    if amendment_comments:
        merge_report.amendment_comments = amendment_comments
        fields_to_update.append("amendment_comments")

    if fields_to_update:
        merge_report.save(update_fields=fields_to_update)

    # ---- Continue to existing logic ----
    pdf_url = GenericAction().merge_report_signout_method(
        request, merge_reporting_id
    )

    request.current_app = "controllerapp"
    context = controller.each_context(request)
    context.update({
        "pdf_url": pdf_url,
        "opts": MergeReporting._meta,
        "has_permission": request.user.is_authenticated,
        "report_option_pk": merge_report.pk,
    })

    return render(
        request,
        "admin/analysis/mergereporting/merge_final_report.html",
        context
    )

@csrf_exempt
@require_POST
def merge_reporting_dtl_autosave(request, merge_reporting_id):
    """
    AJAX autosave for MergeReportingDtl:
      - POST keys: merge_reporting_dtl_id, analyte_id (PK or name), analyte_value
      - On model validation error → 400 + {"status":"error","errors":{field:[msgs]}}
      - On success → 200 + {"status":"success"}
    """
    if not request.user.is_authenticated:
        log.error(f"User is not authenticated!")
        return JsonResponse({'status': 'forbidden'}, status=403)

    dtl_id = request.POST.get("merge_reporting_dtl_id")
    raw_analyte = request.POST.get("analyte_id", "").strip()
    analyte_value = request.POST.get("analyte_value", "").strip()
    log.info(f"merge_reporting_dtl_id ---> {dtl_id}")
    log.info(f"analyte_id ---> {raw_analyte}")
    log.info(f"analyte_value ---> {analyte_value}")

    try:
        if raw_analyte.isdigit():
            analyte_obj = Analyte.objects.get(pk=int(raw_analyte))
        else:
            analyte_obj = Analyte.objects.get(analyte=raw_analyte)
    except Analyte.DoesNotExist:
        log.error(f"Analyte '{raw_analyte}' not found")
        return JsonResponse({
            "status": "error",
            "message": f"Analyte '{raw_analyte}' not found"
        }, status=404)

    if not dtl_id:
        log.error(f"Missing merge_reporting_dtl_id")
        return JsonResponse({
            "status": "error",
            "message": "Missing merge_reporting_dtl_id"
        }, status=400)

    try:
        dtl = MergeReportingDtl.objects.get(
            pk=dtl_id,
            merge_reporting_id=merge_reporting_id,
            analyte_id=analyte_obj
        )
    except MergeReportingDtl.DoesNotExist:
        log.error(f"Detail row not found")
        return JsonResponse({
            "status": "error",
            "message": "Detail row not found"
        }, status=404)

    dtl.analyte_value = analyte_value
    try:
        dtl.save()
        log.info(f"Merge Report Option Detail ID analyte record saved successfully ---> {dtl_id}")
        return JsonResponse({"status": "success"})

    except ValidationError as ve:
        test_obj = dtl.report_option_id.test_id
        if not test_obj:
            log.error(f"Test ID not configured for this Merge Report Option")
            return JsonResponse({
                "status": "error",
                "message": "Test ID not configured for this Merge Report Option"
            }, status=400)

        rule = TestAnalyte.objects.get(
            test_id=test_obj,
            analyte_id=dtl.analyte_id
        )

        # Get the error message
        error_msg = ve.message_dict.get('analyte_value', [""])[0]

        # Determine the 'expected' based on which error it was
        if "must be an integer" in error_msg.lower():
            expected = "Value should be an Integer."
        elif "must be a decimal" in error_msg.lower():
            expected = "Value should be a Decimal number."
        elif "configured rule" in error_msg.lower():
            # Build expected string based on rule logic
            if rule.value_text:
                allowed_values = [v.strip() for v in rule.value_text.split(';') if v.strip()]
                if len(allowed_values) == 1:
                    expected = f"Value must be '{allowed_values[0]}'"
                else:
                    formatted = "', '".join(allowed_values)
                    expected = f"Value must be one of the below- <br>['{formatted}']"
            elif not rule.condition:
                expected = f"Value should be {rule.operator1} {rule.value1}"
            else:
                expected = (
                    f"Value should be {rule.operator1} {rule.value1} "
                    f"{rule.condition.upper()} {rule.operator2} {rule.value2}"
                )
        else:
            expected = "Invalid value."

        log.error(
            f"Validation error: {ve.message_dict} | Expected: {expected} | Current: {analyte_value}"
        )
        return JsonResponse({
            "status": "error",
            "errors": ve.message_dict,
            "expected": expected,
            "current": analyte_value
        }, status=400)

    except Exception as e:
        log.error(f"Error Message : {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@require_POST
def fetch_analyte_value(request):
    ta_id = request.POST.get('ta_id')
    report_option_id = request.POST.get('reportoption_id')
    log.info(f"Test Analyte ID ---> {ta_id}")
    log.info(f"report_option_id ---> {report_option_id}")

    # Extract all analyte values sent from frontend
    analyte_values = {
        k: v for k, v in request.POST.items() if k.startswith('analyte_id__')
    }

    log.info("analyte_values:", analyte_values)

    try:
        ta = TestAnalyte.objects.get(pk=ta_id)
    except TestAnalyte.DoesNotExist:
        log.error(f"TestAnalyte does not exist.")
        return JsonResponse({'value': ''})

    raw_sql = ta.dropdown_sql or ''
    if not raw_sql:
        return JsonResponse({'value': ''})

    log.info("raw_sql:", raw_sql)
    params = {}

    resolved_sql = resolve_dynamic_placeholders(raw_sql, analyte_values, params)
    log.info("resolved_sql:", resolved_sql)
    log.info("params:", params)
    rows = UtilClass.resolve_sql(resolved_sql, params)
    log.info("rows:", rows)
    return JsonResponse({'value': rows[0][0] if rows else ''})


def resolve_dynamic_placeholders(raw_sql, analyte_values, params):
    pattern = re.compile(r"'?:(?P<key>\w+)\|(?P<lookup>[^']+)'?")

    def _replacer(match):
        key = match.group('key')  # e.g. 'analyte_id'
        lookup = match.group('lookup')  # e.g. 'Mitotic Count (%)'

        # Normalize lookup into safe key used in frontend
        safe = re.sub(r'[^0-9A-Za-z]+', '_', lookup).strip('_')  # e.g. Mitotic_Count
        normalized_key = f"{key}__{safe}"  # final param name

        # Try exact match first
        val = analyte_values.get(normalized_key)

        # Try with trailing underscore if present in POST
        if val is None and f"{normalized_key}_" in analyte_values:
            val = analyte_values[f"{normalized_key}_"]

        # If still None, set as empty
        if val is None:
            val = ''

        params[normalized_key] = val
        return f":{normalized_key}"

    return pattern.sub(_replacer, raw_sql)

def get_macros(request):
    """
    Returns Amendment Type Comments depending upon the Amendment Type
    """
    amendment_type = request.GET.get("amendmenttype")
    if not amendment_type:
        return JsonResponse({"macros": []})

    Macros = apps.get_model('template', 'Macros')

    try:
        macros_type = None
        if amendment_type == "Amended":
            macros_type = "Amendment Comments"
        elif  amendment_type == "Corrected":
            macros_type = "Corrected Comments"
        elif amendment_type == "Addend":
            macros_type = "Addend Comments"
        else:
            pass

        macros = Macros.objects.filter(macros_type=macros_type).values("macros_id","macros_name")

        return JsonResponse({"macros": list(macros)})
    except Exception as e:
        log.error(f"Error while fetching Macros")
        return JsonResponse({"macros": []})

def get_macro_content(request):
    """
    Return the Macro Content based on the Macro Name
    """
    macro_id = request.GET.get("macro")
    if not macro_id:
        return JsonResponse({'success': False, 'content': None})

    Macros = apps.get_model('template', 'Macros')

    if Macros:
        try:
            macro = Macros.objects.get(macros_id=macro_id)
            return JsonResponse({'success': True, 'content': macro.actual_content})
        except Macros.DoesNotExist:
            return JsonResponse({'success': False, 'content': None})