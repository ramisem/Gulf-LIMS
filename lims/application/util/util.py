import datetime
import importlib
import io
import json
import logging
import mimetypes
import os
import re
import threading
from collections import defaultdict

import boto3
import requests
from botocore.exceptions import ClientError
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import OuterRef, Subquery, Value, When, IntegerField, Case, F
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse
from pyreportjasper import PyReportJasper

from configuration.models import ReferenceType, RefValues
from controllerapp.settings import DEFAULT_REPORT_LOGO_PATH, REPORT_IMAGE_OUTPUT_PATH, ATTACHMENT_TYPE_LOGO, \
    ATTACHMENT_TYPE_SIGNATURE, REPORT_DIR_INPUT_FOLDER_PATH, TEST_ID_GULF
from masterdata.models import AttachmentConfiguration, Client, Physician
from process.models import ContainerType
from reporting.models import LabelMethod, Printer, ContainerTypeLabelMethodMap, ContainerTypePharmaLabelMethodMap
from security.models import UserPrinterInfo, JobType, User, Department, DepartmentPrinter
from util.models import SequenceGen
from django.core.mail import EmailMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_printer_by_category(request, printer_category):
    current_jobtype = request.session.get('currentjobtype', '')
    current_user = request.user.id

    try:
        jobtype_id = JobType.objects.filter(name=current_jobtype).values_list('id', flat=True).first()
        default_printer_info = UserPrinterInfo.objects.filter(userid=current_user, jobtype_id=jobtype_id,
                                                              is_default=True,
                                                              printer_category=printer_category)

        if not default_printer_info.exists():
            return None, f"No default printer configured for the User: {request.user.username} and JobType: {current_jobtype} and Printer Category: {printer_category}"

        printer_id = default_printer_info.first().printer_id
        printer_info = Printer.objects.filter(printer_name=printer_id).first()
        return printer_info, "Printer Info Fetched"
    except Exception as pe:
        messages.error(request, "Failed to Fetch Default Printer Info. " + str(pe))


def get_lab_name_by_jobtype_department(request):
    current_jobtype = request.session.get('currentjobtype', '')

    try:
        departmentid_id = JobType.objects.filter(name=current_jobtype).values_list('departmentid_id', flat=True).first()
        department_info = Department.objects.filter(id=departmentid_id)
        if not department_info.exists():
            return ""
        department_lab_name = department_info.first().lab_name
        if not department_lab_name:
            department_lab_name = department_info.first().name
        return department_lab_name
    except Exception as ge:
        messages.error(request, "Failed to Print Label. Failed to Fetch Lab Name from Department. " + str(ge))


def get_user_printer_selection_data(request, printer_category):
    current_jobtype_name = request.session.get('currentjobtype', '')
    current_user_id = request.user.id
    current_user_obj = request.user  # Get the User object directly

    default_printer_id = None
    default_communication_type = None
    all_printers_for_selection = []  # This list will hold all options for the dropdown

    try:
        jobtype_obj = JobType.objects.filter(name=current_jobtype_name).first()
        if not jobtype_obj:
            messages.error(request, f"Job Type '{current_jobtype_name}' not found. Cannot load printer options.")
            return {
                'default_printer_id': None,
                'default_communication_type': None,
                'printers': []
            }

        default_user_printer_info = UserPrinterInfo.objects.filter(
            userid=current_user_obj,  # Pass the User object
            jobtype_id=jobtype_obj,
            is_default=True,
            printer_category=printer_category
        ).select_related('printer_id').first()

        if default_user_printer_info:
            default_printer_id = default_user_printer_info.printer_id.printer_id
            default_communication_type = default_user_printer_info.printer_id.communication_type

        applicable_department_printers = DepartmentPrinter.objects.filter(
            jobtype_id=jobtype_obj
        ).select_related('printer_id').order_by('printer_id__printer_name')

        seen_printer_ids = set()

        for dept_printer_info in applicable_department_printers:
            printer = dept_printer_info.printer_id
            if printer.printer_id not in seen_printer_ids:
                all_printers_for_selection.append({
                    'printer_id': printer.printer_id,
                    'printer_name': printer.printer_name,
                    'printer_path': printer.printer_path,
                    'communication_type': printer.communication_type,
                })
                seen_printer_ids.add(printer.printer_id)

        if not all_printers_for_selection and default_printer_id:
            default_printer_obj = Printer.objects.filter(printer_id=default_printer_id).first()
            if default_printer_obj and default_printer_obj.printer_id not in seen_printer_ids:
                all_printers_for_selection.append({
                    'printer_id': default_printer_obj.printer_id,
                    'printer_name': default_printer_obj.printer_name,
                    'printer_path': default_printer_obj.printer_path,
                    'communication_type': default_printer_obj.communication_type,
                })
                seen_printer_ids.add(default_printer_obj.printer_id)

    except Exception as e:
        messages.error(request, f"An unexpected error occurred while preparing printer selection data: {e}")
        return {
            'default_printer_id': None,
            'default_communication_type': None,
            'printers': []
        }

    return {
        'default_printer_id': default_printer_id,
        'default_communication_type': default_communication_type,
        'printers': all_printers_for_selection,
    }


def generate_automatic_sample_labels(request, samples_ids, printer_category=None):
    from sample.models import Sample
    samples = Sample.objects.filter(pk__in=samples_ids).select_related('container_type', 'accession_id')

    if not samples:
        logging.info(request, "No samples found for the provided IDs.")
        return

    if printer_category is None:
        samples_by_current_step = defaultdict(list)
        for sample in samples:
            if sample.current_step:
                samples_by_current_step[sample.current_step].append(sample)
            else:
                logging.info(request, f"Sample {sample.pk} has no current_step defined. Skipping label generation.")

        if not samples_by_current_step:
            logging.info(request, "No samples with a valid current_step for label generation.")
            return

        for step_category, samples_in_step in samples_by_current_step.items():
            print(
                f"--- Processing samples for Printer Category (current_step): {step_category} ---")

            printer_info, message_text = get_printer_by_category(request, step_category)
            if printer_info is None:
                logging.info(request, f"Skipping printing for '{step_category}': {message_text}")
                continue
            else:
                printer, communication_type = printer_info.printer_path, printer_info.communication_type

                if not printer:
                    logging.info(request, f"No printer path defined for category '{step_category}'. Skipping.")
                    continue
                if not communication_type:
                    logging.info(request,
                                 f"Please select a Communication Type for the Printer: {printer_info.printer_name} (Category: {step_category}). Skipping.")
                    continue

                container_type_ids = [s.container_type_id for s in samples_in_step if s.container_type_id]
                if not container_type_ids:
                    logging.info(request, f"No container types found for samples in '{step_category}'. Skipping.")
                    continue

                clinical_label_maps = ContainerTypeLabelMethodMap.objects.filter(
                    container_type__in=set(container_type_ids),
                    is_default=True
                ).select_related('label_method')
                clinical_map_dict = {
                    ctlm.container_type_id: ctlm.label_method
                    for ctlm in clinical_label_maps
                }

                pharma_label_maps = ContainerTypePharmaLabelMethodMap.objects.filter(
                    container_type__in=set(container_type_ids),
                    is_default=True
                ).select_related('label_method')
                pharma_map_dict = {
                    ctlm.container_type_id: ctlm.label_method
                    for ctlm in pharma_label_maps
                }

                grouped_samples_by_label_method = defaultdict(list)

                for sample in samples_in_step:
                    label_method = None
                    if sample.accession_id and sample.accession_id.accession_category == 'Pharma':
                        label_method = pharma_map_dict.get(sample.container_type_id)
                    else:
                        label_method = clinical_map_dict.get(sample.container_type_id)

                    if label_method:
                        grouped_samples_by_label_method[label_method.pk].append({
                            "sample_id": sample.pk,
                        })
                    else:
                        logging.info(request,
                                     f"Warning: ContainerType {sample.container_type.container_type} (ID: {sample.container_type.pk}) has no default label method for current_step '{step_category}'.")
                        continue

                obj = GenerateLabel()

                for label_method_id, entries in grouped_samples_by_label_method.items():
                    sample_ids_to_print = [e["sample_id"] for e in entries]
                    print(
                        f"  Printing {len(sample_ids_to_print)} labels for label_method_id {label_method_id} under category {step_category}")
                    result = obj.print_label(
                        request,
                        sample_ids_to_print,
                        model_pk=sample_ids_to_print,
                        model_app_id="sample/Sample",
                        label_method_id=label_method_id,
                        communication_type=communication_type,
                        printer=printer,
                        count=1
                    )
    else:
        printer_info, message_text = get_printer_by_category(request, printer_category)
        if printer_info is None:
            logging.info(request, message_text)
            return
        else:
            printer, communication_type = printer_info.printer_path, printer_info.communication_type

            if not printer:
                return
            if not communication_type:
                logging.info(request, "Please select a Communication Type for the Printer :",
                             printer_info.printer_name)
                return

            container_type_ids = samples.values_list('container_type__pk', flat=True).distinct()

            clinical_label_maps = ContainerTypeLabelMethodMap.objects.filter(
                container_type__in=container_type_ids,
                is_default=True
            ).select_related('label_method')
            clinical_map_dict = {
                ctlm.container_type_id: ctlm.label_method
                for ctlm in clinical_label_maps
            }

            pharma_label_maps = ContainerTypePharmaLabelMethodMap.objects.filter(
                container_type__in=container_type_ids,
                is_default=True
            ).select_related('label_method')
            pharma_map_dict = {
                ctlm.container_type_id: ctlm.label_method
                for ctlm in pharma_label_maps
            }

            grouped_samples_by_label_method = defaultdict(list)

            for sample in samples:
                label_method = None
                if sample.accession_id and sample.accession_id.accession_category == 'Pharma':
                    label_method = pharma_map_dict.get(sample.container_type_id)
                else:
                    label_method = clinical_map_dict.get(sample.container_type_id)

                if label_method:
                    grouped_samples_by_label_method[label_method.pk].append({
                        "sample_id": sample.pk,
                    })
                else:
                    print(
                        f"Warning: ContainerType {sample.container_type.container_type} (ID: {sample.container_type.pk}) has no default label method.")
                    continue

            obj = GenerateLabel()

            for label_method_id, entries in grouped_samples_by_label_method.items():
                sample_ids = [e["sample_id"] for e in entries]
                result = obj.print_label(
                    request,
                    sample_ids,
                    model_pk=sample_ids, model_app_id="sample/Sample",
                    label_method_id=label_method_id,
                    communication_type=communication_type, printer=printer,
                    count=1
                )


class GenerateLabel:

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

    def print_label(self, request, *query_args, model_pk=None, model_app_id=None, label_method_id=None,
                    label_method_name=None, label_method_version=None,
                    communication_type=None, printer=None, count=1):
        if not printer:
            return {'status': 'error', 'message': "Failed to fetch printer for the current user."}
        if not communication_type:
            return {'status': 'error', 'message': "Please select a communication type on the printer."}
        if not label_method_id:
            if not (label_method_name and label_method_version):
                return {'status': 'error',
                        'message': "You must provide either label_method_id or both label_method_name & "
                                   "label_method_version"}

        if label_method_id:
            label_result = LabelMethod.objects.filter(
                label_method_id=label_method_id).values('designer_format',
                                                        's3bucket',
                                                        'export_location',
                                                        'label_method_name',
                                                        'label_query',
                                                        'label_method_version_id',
                                                        'delimiter',
                                                        'file_format',
                                                        'show_header',
                                                        'show_fields')
        else:
            label_result = LabelMethod.objects.filter(
                label_method_name=label_method_name,
                label_method_version_id=label_method_version).values('designer_format',
                                                                     's3bucket',
                                                                     'export_location',
                                                                     'label_method_name',
                                                                     'label_query',
                                                                     'label_method_version_id',
                                                                     'delimiter',
                                                                     'file_format',
                                                                     'show_header',
                                                                     'show_fields')

        if not label_result.exists():
            return {'status': 'error', 'message': "No matching Label Method(s) found"}

        label_result_first = label_result.first()
        export_location = label_result_first['export_location']
        designer_format = label_result_first['designer_format']
        s3_bucket = label_result_first['s3bucket']
        label_query = label_result_first['label_query']
        label_query = label_query.replace("'%s'", "%s")
        delimiter = label_result_first['delimiter']
        file_format = label_result_first['file_format']
        show_header = label_result_first['show_header']
        show_fields = label_result_first['show_fields']
        if delimiter == "" or delimiter == "default":
            delimiter = "\t"
        if file_format == "":
            file_format = ".dd"
        if "[department_labname]" in label_query:
            department_labname = get_lab_name_by_jobtype_department(request)
            label_query = label_query.replace("[department_labname]", department_labname)

        try:
            result_query, expanded_parameters = self.construct_query(label_query, query_args)
            with connection.cursor() as cursor:
                try:
                    cursor.execute(result_query,
                                   expanded_parameters)
                except Exception as ee:
                    return {'status': 'error', 'message': f"Database query failed: {ee}"}

                label_query_data = cursor.fetchall()
                label_query_columns = [desc[0] for desc in cursor.description]
                if label_query_data:
                    now = datetime.datetime.now()
                    filename = f"{request.user.username}_" + now.strftime("%Y_%m_%d_%H_%M_%f") + "." + file_format

                    user_id = request.user.id  # Assuming request.user exists and has an ID

                    if not isinstance(model_pk, (list, tuple)):
                        pks_to_process = [model_pk]
                    else:
                        pks_to_process = model_pk

                    def _update_label_count_and_sequence():
                        if model_app_id and pks_to_process:
                            try:
                                app_name, model_name = model_app_id.split('/', 1)
                                Model = apps.get_model(app_label=app_name, model_name=model_name)

                                for pk_value in pks_to_process:
                                    if pk_value is not None:
                                        next_sequence_value = UtilClass.get_next_sequence(pk_value, model_name, user_id)
                                        with transaction.atomic():
                                            instance = Model.objects.select_for_update().get(pk=pk_value)
                                            instance.label_count = next_sequence_value
                                            instance.save()
                                            logging.info(
                                                f"Updated label_count for {model_name} with PK {pk_value} to {next_sequence_value}")
                                return {'status': 'success'}
                            except Exception as seq_err:
                                logging.error(
                                    f"Failed to update sequence or label_count for model {model_name}, pk {pks_to_process}: {seq_err}")
                                return {'status': 'warning',
                                        'message': f"Failed to Update Label Event. Labels may have bee Generated. Error: {seq_err}"}
                        return {
                            'status': 'success'}

                    if communication_type == "File Driven":
                        if export_location:
                            if s3_bucket:
                                errors = ""
                                try:
                                    self.generate_label_s3(label_query_data, label_query_columns,
                                                           export_location + printer + '/',
                                                           filename,
                                                           designer_format, printer, delimiter, show_header,
                                                           show_fields,
                                                           count)
                                    s3_generation_success = True
                                except Exception as s3_err:
                                    errors = s3_err
                                    s3_generation_success = False

                                if s3_generation_success:
                                    update_status = _update_label_count_and_sequence()
                                    if update_status['status'] == 'success':
                                        return {'status': 'success',
                                                'message': "Label File Generated to S3 Bucket Successfully"}
                                    else:
                                        return {'status': 'warning', 'message': update_status['message']}
                                else:
                                    return {'status': 'error', 'message': f"Failed to generate label to S3. {errors}"}
                            else:
                                errors = ""
                                try:
                                    self.generate_label(label_query_data, label_query_columns,
                                                        export_location + filename, designer_format,
                                                        printer, delimiter, show_header, show_fields, count)
                                    local_generation_success = True
                                except Exception as local_err:
                                    errors = local_err
                                    local_generation_success = False

                                if local_generation_success:
                                    update_status = _update_label_count_and_sequence()
                                    if update_status['status'] == 'success':
                                        return {'status': 'success', 'message': "Label File Generated Successfully"}
                                    else:
                                        return {'status': 'warning', 'message': update_status['message']}
                                else:
                                    return {'status': 'error',
                                            'message': f"Failed to generate label to local repository. {errors}"}
                        else:
                            return {'status': 'error',
                                    'message': "Printer Communication Type is set to File Driven but Export Location "
                                               "is not set on Label Method."}
                    else:
                        logging.info("Calling API Driven")
                        api_driven_result = self.generate_label_api_driven(request, label_query_data,
                                                                           label_query_columns, designer_format,
                                                                           printer, count, *query_args)

                        if api_driven_result and api_driven_result.get('status') == 'success':
                            update_status = _update_label_count_and_sequence()
                            if update_status['status'] == 'success':
                                return api_driven_result
                            else:
                                return {'status': 'warning', 'message': update_status['message']}
                        else:
                            return api_driven_result
                else:
                    return {'status': 'error', 'message': "No data returned from the query"}
        except Exception as e:
            logging.exception("An unexpected error occurred during label printing process.")  # Log full traceback
            return {'status': 'error', 'message': f"Failed to Generate Label: {e}"}

    def generate_label(self, label_query_data, label_query_columns, file_path, btw_path, printer, delimiter,
                       show_header, show_fields, count):
        try:
            print("generate_label called")
            with open(file_path, "w", encoding="utf-8") as file:
                if show_header:
                    label_head = f'%BTW% /F="{btw_path}" /P /PRN="{printer}" {settings.LABEL_HEADER}'
                    file.write(label_head + "\n")
                if show_fields:
                    file.write(delimiter.join(label_query_columns) + "\n")

                for row in label_query_data:
                    row_values = [str(value) for value in row]
                    row_data = delimiter.join(row_values) + "\n"
                    for i in range(count):
                        file.write(row_data)
            return True
        except Exception as e:
            logging.error(f"Error in generate_label: {e}")
            raise

    def generate_label_s3(self, label_query_data, label_query_columns, export_location, filename, btw_path, printer,
                          delimiter, show_header, show_fields, count):
        try:
            print("generate_label_s3 called")
            output = io.StringIO()
            if show_header:
                label_head = f'%BTW% /F="{btw_path}" /P /PRN="{printer}" {settings.LABEL_HEADER}'
                output.write(label_head + "\n")
            if show_fields:
                output.write(delimiter.join(label_query_columns) + "\n")

            for row in label_query_data:
                row_values = [str(value) for value in row]
                row_data = delimiter.join(row_values) + "\n"
                for _ in range(count):
                    output.write(row_data)

            output.seek(0)  # Reset buffer position

            if "/" in export_location:
                bucket_name, key_prefix = export_location.split("/", 1)
                key_prefix = key_prefix.rstrip('/')
                s3_key = f"{key_prefix}/{filename}" if key_prefix else filename
            else:
                bucket_name = export_location
                s3_key = filename

            # S3 upload parameters
            # Set "ContentType": "application/octet-stream" to store the file as .dd file instead of .txt
            s3_params = {
                "Bucket": bucket_name,
                "Key": s3_key,
                "Body": output.getvalue(),
                "ContentType": "text/plain"
            }

            if hasattr(settings, "AWS_S3_KMS_KEY_ARN") and settings.AWS_S3_KMS_KEY_ARN:
                print("AWS KMS KEY FOUND")
                s3_params.update({
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": settings.AWS_S3_KMS_KEY_ARN
                })

            self.s3_client.put_object(**s3_params)

            print(f"Uploaded {filename} to S3: s3://{bucket_name}/{s3_key}")
            return True
        except Exception as e:
            logging.error(f"Error in generate_label_s3: {e}")
            raise

    def generate_label_api_driven(self, request, label_query_data, label_query_columns, designer_format, printer, count,
                                  *query_args):
        try:
            if not label_query_data:
                return {'status': 'error', 'message': "No data returned from the query for API Driven printing."}
            print_portal_web_root = settings.PRINT_PORTAL_WEB_ROOT
            successful_prints = 0
            failed_prints = 0
            error_details = []

            for row in label_query_data:
                label_data = dict(zip(label_query_columns, row))
                named_data_sources = {col: str(label_data[col]) for col in label_query_columns}

                result = self.print_bartender_document(
                    bartender_url=settings.BT_PRINT_PORTAL_URI,
                    absolute_path=print_portal_web_root + designer_format,
                    printer_name=printer,
                    copies=count,
                    named_data_sources=named_data_sources
                )

                if result['success']:
                    successful_prints += 1
                    # messages.success(request, result['message'])
                    if 'file_path' in result:
                        print(f"File path: {result['file_path']}")
                else:
                    failed_prints += 1
                    error_details.append(
                        f"Failed to print for data: {label_data}. Error: {result.get('message', 'Unknown error')}")
                    if 'error' in result:
                        error_details.append(f"  Details: {result['error']}")
                    if 'status_code' in result:
                        error_details.append(f"  Status Code: {result['status_code']}")

            if successful_prints > 0 and failed_prints == 0:
                return {'status': 'success', 'message': f"Successfully printed {successful_prints} label(s) via API."}
            elif successful_prints > 0 and failed_prints > 0:
                return {'status': 'warning',
                        'message': f"Printed {successful_prints} label(s) successfully, but {failed_prints} failed. Details: {' '.join(error_details)}"}
            else:
                return {'status': 'error',
                        'message': f"Failed to print any labels via API. Details: {' '.join(error_details)}"}
        except Exception as e:
            logging.error(f"An unexpected error occurred during API driven printing: {e}")
            return {'status': 'error', 'message': f"An unexpected error occurred during API driven printing: {e}"}

    def print_bartender_document(self, bartender_url, absolute_path, printer_name, copies, named_data_sources=None):
        """
        Prints a BarTender document using the Print Portal REST API.
        """
        try:
            # Construct the JSON payload
            print_data = {
                "AbsolutePath": absolute_path,
                "Printer": printer_name,
                "Copies": copies,
                "UsePrinterSettings": False
            }

            if named_data_sources:
                print_data["NamedDataSources"] = named_data_sources

            print_url = f"{bartender_url}print"
            headers = {'Content-Type': 'application/json'}

            logging.info(f"Sending print request to {print_url} with data: {print_data}")
            print_response = requests.post(print_url, headers=headers, json=print_data)

            if print_response.status_code == 200:
                if 'application/json' in print_response.headers.get('Content-Type', ''):
                    try:
                        response_json = print_response.json()
                        if response_json.get("filePath"):
                            return {
                                'success': True,
                                'message': 'Print job successful.',
                                'file_path': response_json.get('filePath')
                            }
                        elif response_json.get("messages"):
                            return {
                                'success': True,
                                'message': response_json.get('messages'),
                            }
                        else:
                            return {
                                'success': True,
                                'message': 'Print job submitted successfully.'
                            }
                    except json.JSONDecodeError as e:
                        logging.error(f"JSONDecodeError: {e}.  Response content: {print_response.text}")
                        return {
                            'success': False,
                            'message': 'Invalid JSON response received.',
                            'error': str(e),
                            'status_code': print_response.status_code,
                            'html_content': print_response.text  # Include the HTML for debugging
                        }
                else:
                    logging.warning(
                        f"Received non-JSON response. Content-Type: {print_response.headers.get('Content-Type', '')}, Content: {print_response.text}")
                    return {
                        'success': False,
                        'message': 'Received non-JSON response from Print Portal.',
                        'error': 'Content-Type is not application/json',
                        'status_code': print_response.status_code,
                        'html_content': print_response.text  # Include the HTML for debugging
                    }
            elif print_response.status_code == 400 and "printRequestID" in print_response.text:
                response_json = print_response.json()
                print_request_id = response_json.get("printRequestID")

                if not print_request_id:
                    return {
                        'success': False,
                        'message': 'Document requires data entry, but printRequestID not found in the initial response.',
                        'error': print_response.text,
                        'status_code': print_response.status_code
                    }
                print_data["printRequestID"] = print_request_id

                # Resend the request with the printRequestID and data entry controls
                logging.info(f"Resending print request with printRequestID: {print_request_id} and data: {print_data}")
                print_response = requests.post(print_url, headers=headers, json=print_data)
                logging.info(f"Resend print response status code: {print_response.status_code}")
                logging.info(f"Resend print response content: {print_response.content}")

                if print_response.status_code == 200:
                    response_json = print_response.json()
                    if response_json.get("filePath"):
                        return {
                            'success': True,
                            'message': 'Print job successful (with data entry).',
                            'file_path': response_json.get('filePath')
                        }
                    elif response_json.get("messages"):
                        return {
                            'success': True,
                            'message': response_json.get('messages'),
                        }
                    else:
                        return {
                            'success': True,
                            'message': 'Print job submitted successfully (with data entry).'
                        }
                else:
                    return {
                        'success': False,
                        'message': 'Print job failed (with data entry).',
                        'error': print_response.text,
                        'status_code': print_response.status_code
                    }

            else:
                return {
                    'success': False,
                    'message': 'Print job failed.',
                    'error': print_response.text,
                    'status_code': print_response.status_code
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': 'Network error.',
                'error': str(e)
            }

    def construct_query(self, label_query, query_args):
        expanded_parameters = []
        query_parts = label_query.split('(%s)')
        result_query = query_parts[0]  # Start with the first part
        for i, param in enumerate(query_args):
            if isinstance(param, (list, tuple)):
                placeholders = ','.join(['%s'] * len(param))
                result_query += f"({placeholders})" + query_parts[i + 1]
                expanded_parameters.extend(param)
            else:
                result_query += '%s' + query_parts[i + 1]
                expanded_parameters.append(param)
        return result_query, expanded_parameters


class UtilClass:

    @staticmethod
    def get_s3_client():
        return boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

    @staticmethod
    def get_refvalues_for_field(ref_name):
        try:
            ref_type = ReferenceType.objects.get(name=ref_name)
            choices = RefValues.objects.filter(reftype_id=ref_type).values_list("value", "display_value")
            return list(choices)
        except ReferenceType.DoesNotExist:
            return []

    @staticmethod
    def get_next_sequence(prefix, model_id, user_id):
        with transaction.atomic():
            sequence_gen, created = SequenceGen.objects.select_for_update().get_or_create(
                model_id=model_id,
                prefix_id=prefix,
                defaults={"seq_no": 0}
            )
            sequence_gen.created_by_id = user_id
            sequence_gen.seq_no += 1
            sequence_gen.save()
            return sequence_gen.seq_no

    @staticmethod
    def get_accession_types():
        AccessionType = apps.get_model('accessioning', 'AccessionType')
        accession_types = AccessionType.objects.all().values_list("accession_type_id", "accession_type").order_by(
            'accession_type')
        return list(accession_types)

    # This function is for WetLab completion
    def completewetlab(self, request, queryset):
        module = importlib.import_module("util.util")
        GenericUtilClass = getattr(module, "UtilClass")
        Test = apps.get_model('tests', 'Test')
        TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
        WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
        Workflow = apps.get_model('workflows', 'Workflow')
        gulftest_obj = Test.objects.filter(test_name=TEST_ID_GULF).first()
        gulftest_id = gulftest_obj.test_id if gulftest_obj else None
        username = request.user.username
        user_map_obj = User.objects.get(username=username)
        sample_test_info_for_report_option_creation = []
        sample_ids = list(queryset.values_list('sample_id', flat=True))
        Sample = apps.get_model('sample', 'Sample')
        Sample.objects.filter(sample_id__in=sample_ids).update(
            sample_status="Completed"
        )

        SampleTestMap = apps.get_model('sample', 'SampleTestMap')
        sample_test_info = SampleTestMap.objects.select_related('sample_id', 'workflow_id').filter(
            sample_id__in=sample_ids
        ).values(
            'sample_id__sample_id',
            'sample_id__accession_sample',
            'sample_id__accession_id',
            'test_id',
            'workflow_id',
            'workflow_id__methodology'
        )
        set_accession_samples = set()
        list_accession_samples = []
        is_acc_sample_same_as_sample = False
        for info in sample_test_info:
            if info['sample_id__accession_sample']:
                set_accession_samples.add(info['sample_id__accession_sample'])
            else:
                set_accession_samples.add(info['sample_id__sample_id'])
                is_acc_sample_same_as_sample = True

        list_accession_samples = list(set_accession_samples)
        Sample = apps.get_model('sample', 'Sample')
        accession_sample_info = Sample.objects.filter(sample_id__in=list_accession_samples)
        list_accession = []
        ReportOption = apps.get_model('analysis', 'ReportOption')
        if accession_sample_info is not None and len(accession_sample_info) > 0:
            dict_acc = {}
            list_sample_type_ids = []
            list_container_type_ids = []
            list_tests = []
            list_workflowids = []
            accession_ids = [sample.accession_id for sample in accession_sample_info]
            if accession_ids:

                # Populate TC & TCA

                module = importlib.import_module("tpcm.technicalprofessionalcomponentutil")
                TechnicalProfessionalComponentUtilClass = getattr(module, "TechnicalProfessionalComponentUtilClass")
                TechnicalProfessionalComponentUtilClass.populate_tc_tca(accession_ids, request, user_map_obj)

            for obj in accession_sample_info:
                accession_id = obj.accession_id
                if accession_id and accession_id.accession_type:
                    reporting_type = accession_id.accession_type.reporting_type
                else:
                    reporting_type = None

                if not reporting_type:
                    continue

                dict_acc[accession_id.accession_id] = accession_id
                list_accession.append(accession_id.accession_id)
                accession_sample = obj.sample_id
                sample_type_id = obj.sample_type_id
                list_sample_type_ids.append(sample_type_id)
                container_type_id = obj.container_type_id
                list_container_type_ids.append(container_type_id)
                if is_acc_sample_same_as_sample==False:
                    test_info = sample_test_info.filter(sample_id__accession_sample=accession_sample)
                else:
                    test_info = sample_test_info.filter(sample_id__sample_id=accession_sample)
                if not test_info:
                    return
                sample_obj = Sample.objects.filter(sample_id=accession_sample).first()
                effective_workflow_id = None
                if sample_obj and sample_obj.workflow_id:
                    effective_workflow_id = sample_obj.workflow_id.workflow_id
                elif sample_obj and sample_obj.accession_sample and sample_obj.accession_sample.workflow_id:
                    effective_workflow_id = sample_obj.accession_sample.workflow_id.workflow_id

                if effective_workflow_id:
                    workflow_obj = apps.get_model('workflows', 'Workflow').objects.filter(
                        workflow_id=effective_workflow_id
                    ).first()

                    record = {
                        "accession_id": accession_id.accession_id,
                        "accession_sample": accession_sample,
                        "sample_type": sample_type_id,
                        "container_type": container_type_id,
                        "test_id": gulftest_id,
                        "workflow_id": effective_workflow_id,
                        "methodology": workflow_obj.methodology if workflow_obj else None
                    }
                    if record not in sample_test_info_for_report_option_creation:
                        sample_test_info_for_report_option_creation.append(record)
                    list_workflowids.append(effective_workflow_id)
                else:
                    for test_instance in test_info:
                        test_id = test_instance['test_id']
                        eff_wf_id = test_instance['workflow_id']

                        workflow_obj = None
                        if eff_wf_id:
                            workflow_obj = apps.get_model('workflows', 'Workflow').objects.filter(
                                workflow_id=eff_wf_id
                            ).first()

                        record = {
                            "accession_id": accession_id.accession_id,
                            "accession_sample": accession_sample,
                            "sample_type": sample_type_id,
                            "container_type": container_type_id,
                            "test_id": test_id,
                            "workflow_id": eff_wf_id,
                            "methodology": workflow_obj.methodology if workflow_obj else None
                        }

                        if record not in sample_test_info_for_report_option_creation:
                            sample_test_info_for_report_option_creation.append(record)
                        list_tests.append(test_id)
                        list_workflowids.append(eff_wf_id)

            test_work_flow_steps_info = TestWorkflowStep.objects.select_related(
                'workflow_step_id'
            ).filter(sample_type_id__in=list_sample_type_ids,
                     container_type__in=list_container_type_ids,
                     test_id__in=list_tests, workflow_id__workflow_id__in=list_workflowids,
                     workflow_step_id__workflow_type='DryLab')
            workflow_steps_info = WorkflowStep.objects.filter(
                workflow_id__in=list_workflowids,
                workflow_type='DryLab'
            )
            if (test_work_flow_steps_info is None or len(test_work_flow_steps_info) == 0) and (
                    workflow_steps_info is None or len(workflow_steps_info) == 0):
                return
            report_option_info = ReportOption.objects.filter(accession_id__accession_id__in=list_accession)
            if report_option_info is None or len(report_option_info) == 0:
                list_report_option_instances = []
                for instances in sample_test_info_for_report_option_creation:
                    sample_type = instances['sample_type']
                    container_type = instances['container_type']
                    test_id = instances['test_id']
                    workflow_id = instances['workflow_id']
                    accession_id = instances['accession_id']
                    accession_instance = dict_acc[accession_id]
                    filter_work_flow_step_workflow = None
                    filter_test_work_flow_step = None
                    if Sample.objects.filter(sample_id=instances['accession_sample']).first().workflow_id:
                        # WorkflowStep logic
                        filter_work_flow_step_workflow = workflow_steps_info.filter(
                            workflow_id=workflow_id
                        )
                    else:
                        filter_test_work_flow_step = test_work_flow_steps_info.filter(sample_type_id=sample_type,
                                                                                      container_type=container_type,
                                                                                      test_id=test_id,
                                                                                      workflow_id__workflow_id=workflow_id)
                    if not filter_work_flow_step_workflow and not filter_test_work_flow_step:
                        continue

                    report_option_instance = ReportOption()
                    seq_no = GenericUtilClass.get_next_sequence("RO", "ReportOption", user_map_obj.id)
                    report_option_instance.report_option_id = f"RO-{seq_no:08}"
                    report_option_instance.accession_id = accession_instance
                    if accession_instance.reporting_doctor:
                        physician_instance = accession_instance.reporting_doctor
                        if physician_instance.user_id:
                            report_option_instance.assign_pathologist = physician_instance.user_id
                    report_option_instance.root_sample_id = Sample.objects.get(
                        sample_id=instances['accession_sample'])
                    report_option_version_prefix = accession_id + "-" + instances[
                        'accession_sample'] + "-" + str(instances['test_id'])
                    report_option_instance.version_id = UtilClass.get_next_sequence(report_option_version_prefix,
                                                                                    "ReportOption", user_map_obj.id)
                    report_option_instance.reporting_status = "In-progress"
                    req_test_instance = Test.objects.get(test_id=test_id)
                    report_option_instance.test_id = req_test_instance
                    report_option_instance.methodology = instances['methodology']

                    if filter_work_flow_step_workflow:
                        filter_work_flow_step_workflow = filter_work_flow_step_workflow.order_by(
                            'step_no').first()
                        report_option_instance.current_step = filter_work_flow_step_workflow.step_id
                        filter_work_flow_next_step_list = \
                            workflow_steps_info.filter(
                                workflow_id=workflow_id
                            ).order_by(
                                'step_no')
                        if filter_work_flow_next_step_list and len(filter_work_flow_next_step_list) > 1:
                            filter_work_flow_next_step = filter_work_flow_next_step_list[1]
                            report_option_instance.next_step = filter_work_flow_next_step.step_id
                        Department = apps.get_model('security', 'Department')
                        dept = request.session.get('currentjobtype', '').split('-')[
                                   0] + '-' + filter_work_flow_step_workflow.department
                        report_option_instance.custodial_department_id = Department.objects.filter(
                            name=dept).values_list('id',
                                                   flat=True).first()
                        workflow_instance = Workflow.objects.filter(workflow_id=workflow_id).first()
                        report_option_instance.workflow_id = workflow_instance
                        TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
                        qs = TestWorkflowStepActionMap.objects.filter(
                            workflow_step_id=filter_work_flow_step_workflow.workflow_step_id).order_by(
                            'sequence').first()
                        if qs is not None:
                            report_option_instance.pending_action = qs.action
                    elif filter_test_work_flow_step:
                        filter_test_work_flow_step = filter_test_work_flow_step.order_by(
                            'workflow_step_id__step_no').first()
                        report_option_instance.current_step = filter_test_work_flow_step.workflow_step_id.step_id
                        filter_test_work_flow_next_step_list = \
                            test_work_flow_steps_info.filter(sample_type_id=sample_type,
                                                             container_type=container_type,
                                                             test_id=test_id,
                                                             workflow_id__workflow_id=workflow_id).order_by(
                                'workflow_step_id__step_no')
                        if filter_test_work_flow_next_step_list and len(filter_test_work_flow_next_step_list) > 1:
                            filter_test_work_flow_next_step = filter_test_work_flow_next_step_list[1]
                            report_option_instance.next_step = filter_test_work_flow_next_step.workflow_step_id.step_id
                        Department = apps.get_model('security', 'Department')
                        dept = request.session.get('currentjobtype', '').split('-')[
                                   0] + '-' + filter_test_work_flow_step.workflow_step_id.department
                        report_option_instance.custodial_department_id = Department.objects.filter(
                            name=dept).values_list('id',
                                                   flat=True).first()
                        TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
                        qs = TestWorkflowStepActionMap.objects.filter(
                            testwflwstepmap_id=filter_test_work_flow_step.test_workflow_step_id).order_by(
                            'sequence').first()
                        if qs is not None:
                            report_option_instance.pending_action = qs.action
                    report_option_instance.created_by = user_map_obj
                    report_option_instance.mod_by = user_map_obj
                    report_option_instance.avail_at = datetime.datetime.now()
                    list_report_option_instances.append(report_option_instance)
                if list_report_option_instances:
                    ReportOption.objects.bulk_create(list_report_option_instances)
                    UtilClass.createRoutingInfoForReportOption(list_report_option_instances)
                    t1 = threading.Thread(target=UtilClass.createReportOptionDetails,
                                          args=(list_report_option_instances, user_map_obj))
                    t1.start()
            else:
                list_report_option_instances = []
                for instances in sample_test_info_for_report_option_creation:
                    accession_id = instances['accession_id']
                    accession_obj = dict_acc[accession_id]
                    accession_sample_obj = Sample.objects.get(sample_id=instances['accession_sample'])
                    Test = apps.get_model('tests', 'Test')
                    test_obj = Test.objects.get(test_id=instances['test_id'])
                    reqd_row = report_option_info.filter(accession_id=accession_obj,
                                                         root_sample_id=accession_sample_obj,
                                                         test_id=test_obj).exclude(
                        reporting_status='Completed')
                    if not reqd_row:
                        sample_type = instances['sample_type']
                        container_type = instances['container_type']
                        test_id = instances['test_id']
                        workflow_id = instances['workflow_id']
                        filter_work_flow_step_workflow = None
                        filter_test_work_flow_step = None
                        if Sample.objects.filter(sample_id=instances['accession_sample']).first().workflow_id:
                            # WorkflowStep logic
                            filter_work_flow_step_workflow = workflow_steps_info.filter(
                                workflow_id=workflow_id
                            )
                        else:
                            filter_test_work_flow_step = test_work_flow_steps_info.filter(sample_type_id=sample_type,
                                                                                          container_type=container_type,
                                                                                          test_id=test_id,
                                                                                          workflow_id__workflow_id=workflow_id)
                        if not filter_work_flow_step_workflow and not filter_test_work_flow_step:
                            continue
                        report_option_instance = ReportOption()
                        seq_no = GenericUtilClass.get_next_sequence("RO", "ReportOption", user_map_obj.id)
                        report_option_instance.report_option_id = f"RO-{seq_no:08}"
                        report_option_instance.accession_id = dict_acc[accession_id]
                        report_option_instance.root_sample_id = Sample.objects.get(
                            sample_id=instances['accession_sample'])
                        report_option_version_prefix = accession_id + "-" + instances[
                            'accession_sample'] + "-" + str(instances['test_id'])
                        report_option_instance.version_id = UtilClass.get_next_sequence(
                            report_option_version_prefix,
                            "ReportOption", user_map_obj.id)
                        report_option_instance.reporting_status = "In-progress"
                        req_test_instance = Test.objects.get(test_id=test_id)
                        report_option_instance.test_id = req_test_instance
                        report_option_instance.methodology = instances['methodology']

                        if filter_work_flow_step_workflow:
                            filter_work_flow_step_workflow = filter_work_flow_step_workflow.order_by(
                                'step_no').first()
                            report_option_instance.current_step = filter_work_flow_step_workflow.step_id
                            filter_work_flow_next_step_list = \
                                workflow_steps_info.filter(
                                    workflow_id=workflow_id
                                ).order_by(
                                    'step_no')
                            if filter_work_flow_next_step_list and len(filter_work_flow_next_step_list) > 1:
                                filter_work_flow_next_step = filter_work_flow_next_step_list[1]
                                report_option_instance.next_step = filter_work_flow_next_step.step_id
                            Department = apps.get_model('security', 'Department')
                            dept = request.session.get('currentjobtype', '').split('-')[
                                       0] + '-' + filter_work_flow_step_workflow.department
                            report_option_instance.custodial_department_id = Department.objects.filter(
                                name=dept).values_list('id',
                                                       flat=True).first()
                            workflow_instance = Workflow.objects.filter(workflow_id=workflow_id).first()
                            report_option_instance.workflow_id = workflow_instance
                            TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
                            qs = TestWorkflowStepActionMap.objects.filter(
                                workflow_step_id=filter_work_flow_step_workflow.workflow_step_id).order_by(
                                'sequence').first()
                            if qs is not None:
                                report_option_instance.pending_action = qs.action
                        elif filter_test_work_flow_step:
                            filter_test_work_flow_step = filter_test_work_flow_step.order_by(
                                'workflow_step_id__step_no').first()
                            report_option_instance.current_step = filter_test_work_flow_step.workflow_step_id.step_id
                            filter_test_work_flow_next_step_list = \
                                test_work_flow_steps_info.filter(sample_type_id=sample_type,
                                                                 container_type=container_type,
                                                                 test_id=test_id,
                                                                 workflow_id__workflow_id=workflow_id).order_by(
                                    'workflow_step_id__step_no')
                            if filter_test_work_flow_next_step_list and len(filter_test_work_flow_next_step_list) > 1:
                                filter_test_work_flow_next_step = filter_test_work_flow_next_step_list[1]
                                report_option_instance.next_step = filter_test_work_flow_next_step.workflow_step_id.step_id
                            Department = apps.get_model('security', 'Department')
                            dept = request.session.get('currentjobtype', '').split('-')[
                                       0] + '-' + filter_test_work_flow_step.workflow_step_id.department
                            report_option_instance.custodial_department_id = Department.objects.filter(
                                name=dept).values_list('id',
                                                       flat=True).first()
                            TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
                            qs = TestWorkflowStepActionMap.objects.filter(
                                testwflwstepmap_id=filter_test_work_flow_step.test_workflow_step_id).order_by(
                                'sequence').first()
                            if qs is not None:
                                report_option_instance.pending_action = qs.action
                        report_option_instance.created_by = user_map_obj
                        report_option_instance.mod_by = user_map_obj
                        report_option_instance.avail_at = datetime.datetime.now()
                        list_report_option_instances.append(report_option_instance)
                if list_report_option_instances:
                    ReportOption.objects.bulk_create(list_report_option_instances)
                    UtilClass.createRoutingInfoForReportOption(list_report_option_instances)
                    t1 = threading.Thread(target=UtilClass.createReportOptionDetails,
                                          args=(list_report_option_instances, user_map_obj))
                    t1.start()

    # This id to create Records in Report Option Details table
    @staticmethod
    def createReportOptionDetails(list_report_option, user_map_obj):
        module = importlib.import_module("util.util")
        GenericUtilClass = getattr(module, "UtilClass")
        TestAnalyte = apps.get_model('tests', 'TestAnalyte')
        ReportOptionDtl = apps.get_model('analysis', 'ReportOptionDtl')
        if list_report_option is None or len(list_report_option) == 0:
            return
        if user_map_obj is None:
            return
        list_report_option_details_instances = []
        test_id_list = []
        for instance in list_report_option:
            test_id_list.append(instance.test_id)

        analyte_records = TestAnalyte.objects.filter(test_id__in=test_id_list).order_by('test_analyte_id')

        for instance in list_report_option:
            test_id = instance.test_id
            filtered_analytes = analyte_records.filter(test_id=test_id).order_by('test_analyte_id')
            report_option_details_version_prefix = instance.report_option_id
            version_id = UtilClass.get_next_sequence(report_option_details_version_prefix,
                                                     "ReportOptionDtl", user_map_obj.id)
            for analyte in filtered_analytes:
                report_dtl_instance = ReportOptionDtl()
                seq_no = GenericUtilClass.get_next_sequence("ROD", "ReportOptionDtl", user_map_obj.id)
                report_dtl_instance.report_option_dtl_id = f"ROD-{seq_no:08}"
                report_dtl_instance.report_option_id = instance
                report_dtl_instance.analyte_id = analyte.analyte_id
                report_dtl_instance.version_id = version_id
                report_dtl_instance.created_by = user_map_obj
                report_dtl_instance.mod_by = user_map_obj
                list_report_option_details_instances.append(report_dtl_instance)

        ReportOptionDtl.objects.bulk_create(list_report_option_details_instances)

    def resolve_sql(raw_sql, param_dict=None):
        """
        Replace :param placeholders in raw_sql with the right number of %s’s,
        bind values from param_dict (including semicolon-delimited strings for IN‑clauses),
        and execute the query safely.
        """
        param_dict = param_dict or {}
        param_order = []
        # Regex to find all :param_name placeholders
        placeholder_pattern = re.compile(r":(\w+)")

        def replacer(match):
            key = match.group(1)
            if key not in param_dict:
                raise ValueError(f"Missing SQL parameter: '{key}'")
            val = param_dict[key]

            # If it's a semicolon-delimited string, split into list
            if isinstance(val, str) and ";" in val:
                items = [v.strip() for v in val.split(";") if v.strip()]
                if not items:
                    raise ValueError(f"No values found for SQL IN‑clause '{key}'")
                # Expand placeholders for each item
                placeholders = ",".join(["%s"] * len(items))
                param_order.extend(items)
                return placeholders

            # If it's already a list/tuple
            if isinstance(val, (list, tuple)):
                if not val:
                    raise ValueError(f"Empty list passed for SQL IN‑clause '{key}'")
                placeholders = ",".join(["%s"] * len(val))
                param_order.extend(val)
                return placeholders

            # Single scalar value
            param_order.append(val)
            return "%s"

        # Substitute placeholders in the SQL
        sql_clean = placeholder_pattern.sub(replacer, raw_sql)

        # Execute safely
        with connection.cursor() as cursor:
            cursor.execute(sql_clean, param_order)
            return cursor.fetchall()

    # This is to generate pdf report
    @staticmethod
    def generate_report(input_file, output_file, filetype, merge_reporting_id, use_db=False, is_preview=True):
        base_name = os.path.basename(output_file)
        output_dir = os.path.dirname(output_file)
        name_without_ext = os.path.splitext(base_name)[0]
        final_output_file = os.path.join(output_dir, f"{name_without_ext}")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Setup Jasper report generator
        jasper = PyReportJasper()
        parameters = {}

        parameters['subreport_dir'] = os.path.abspath(
            os.path.join(settings.BASE_DIR, REPORT_DIR_INPUT_FOLDER_PATH)) + '/'
        parameters['subreport_dir'] = parameters['subreport_dir'].replace('\\', '/')

        if merge_reporting_id:
            parameters['mergereportid'] = merge_reporting_id

        config_logo_path = ""
        logo_img_att_id = UtilClass.get_logo_image_attachment_id(merge_reporting_id)
        if logo_img_att_id:
            config_logo_path = UtilClass.download_attachment_to_fixed_path(logo_img_att_id)
            parameters['LOGO_PATH'] = config_logo_path
        else:
            parameters['LOGO_PATH'] = os.path.abspath(
                os.path.join(settings.BASE_DIR, DEFAULT_REPORT_LOGO_PATH)).replace('\\', '/')

        signed_image_path = None
        parameters['signed_image_path'] = None
        if not is_preview:
            signed_img_att_id = UtilClass.get_signed_image_attachment_id(merge_reporting_id)
            if signed_img_att_id:
                signed_image_path = UtilClass.download_attachment_to_fixed_path(signed_img_att_id)
                parameters['signed_image_path'] = signed_image_path

        body_site_image_path = UtilClass.build_image_map(merge_reporting_id)
        parameters['bodysite_image_path'] = body_site_image_path

        config_args = {
            'input_file': input_file,
            'output_file': final_output_file,
            'output_formats': [filetype],
            'parameters': parameters,
            'locale': 'en_US'
        }

        if use_db:
            config_args['db_connection'] = {
                'driver': 'postgres',
                'jdbc_driver': 'org.postgresql.Driver',
                'username': settings.DATABASES['default']['USER'],
                'password': settings.DATABASES['default']['PASSWORD'],
                'host': settings.DATABASES['default']['HOST'],
                'database': settings.DATABASES['default']['NAME'],
                'port': '5432'
            }

        jasper.config(**config_args)
        jasper.process_report()

        # rel_output_dir = os.path.relpath(output_dir, os.path.join(settings.BASE_DIR, 'static'))
        UtilClass.cleanup_temp_image(f"{body_site_image_path};{config_logo_path};{signed_image_path}")
        # return os.path.join(rel_output_dir, f"{name_without_ext}.{filetype}")

        full_file_path = f"{final_output_file}.{filetype}"
        from analysis.models import Attachment
        dummy_instance = Attachment(merge_reporting_id_id=merge_reporting_id)

        try:
            with open(full_file_path, 'rb') as f:
                class DummyUploadedFile:
                    def __init__(self, file_obj):
                        self.name = os.path.basename(full_file_path)
                        self.file = file_obj
                        self.content_type = 'application/pdf'

                uploaded_file = DummyUploadedFile(f)
                s3_key = UtilClass.upload_attachment_to_s3_fixed_path(dummy_instance, uploaded_file,
                                                                      preview_flag=is_preview)
        except Exception as e:
            s3_key = None
        UtilClass.remove_local_report_files(dummy_instance)
        return s3_key

    def remove_local_report_files(instance):
        folders_to_clean = [
            os.path.join(settings.BASE_DIR, settings.REPORT_FINAL_OUTPUT_PATH),
            os.path.join(settings.BASE_DIR, settings.REPORT_PREVIEW_OUTPUT_PATH)
        ]

        for folder in folders_to_clean:
            try:
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):  # ensure it's a file, not a directory
                        os.remove(file_path)
                        print(f"🗑️ Deleted file: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not delete files in {folder}: {e}")

    def get_logo_image_attachment_id(merge_reporting_id):
        from analysis.models import MergeReporting, Attachment

        default_type = 'Global'

        try:
            mr = (
                MergeReporting.objects
                .select_related('accession_id__accession_type', 'accession_id__client_id')
                .get(merge_reporting_id=merge_reporting_id)
            )
        except MergeReporting.DoesNotExist:
            return None

        acc = mr.accession_id
        acc_type_value = getattr(acc.accession_type, 'accession_type', '').lower()
        if acc_type_value != default_type.lower():
            att = (
                Attachment.objects
                .filter(client_id=acc.client_id, attachment_type=ATTACHMENT_TYPE_LOGO)
                .order_by('-created_dt')
                .first()
            )
            if att:
                return att.attachment_id

        return None

    def get_signed_image_attachment_id(merge_reporting_id):
        from analysis.models import MergeReporting, Attachment

        try:
            mr = MergeReporting.objects.select_related('last_signed_by') \
                .get(merge_reporting_id=merge_reporting_id)
        except MergeReporting.DoesNotExist:
            return None

        signer = mr.last_signed_by
        if not signer:
            return None

        try:
            phys = Physician.objects.get(user_id=signer)
        except Physician.DoesNotExist:
            return None

        att = (Attachment.objects
               .filter(physician_id=phys, attachment_type=ATTACHMENT_TYPE_SIGNATURE)
               .order_by('-created_dt')
               .first())

        return att.attachment_id if att else None

    def download_attachment_to_fixed_path(attachment_id, download_dir=REPORT_IMAGE_OUTPUT_PATH):
        Attachment = apps.get_model('analysis', 'Attachment')
        att = Attachment.objects.get(pk=attachment_id)
        if not att.file_path:
            raise FileNotFoundError(f"No file stored on attachment {attachment_id}")

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        key = att.file_path.name
        basename = os.path.basename(key)

        # Make download_dir absolute and ensure it exists
        download_dir = os.path.join(settings.BASE_DIR, download_dir)
        os.makedirs(download_dir, exist_ok=True)
        # Build the full file path
        full_path = os.path.join(download_dir, basename)

        # Ask S3 to download _into that file_
        s3 = UtilClass.get_s3_client()
        s3.download_file(bucket, key, full_path)

        return full_path

    def validate_backward_movement_popup(admin_instance, request):
        """
        AJAX validation endpoint for backward movement popup.
        Returns JSON with validation messages.
        """
        ids_param = request.GET.get('ids', '')
        if not ids_param:
            return JsonResponse({'success': False, 'message': 'No records selected.'})

        id_list = [x.strip() for x in ids_param.split(',') if x.strip()]
        queryset = admin_instance.model.objects.filter(pk__in=id_list)

        SampleTestMap = apps.get_model('sample', 'SampleTestMap')
        Sample = apps.get_model('sample', 'Sample')

        if not queryset.exists():
            return JsonResponse({'success': False, 'message': "Please select at least one record."})

        first_child_creation = None

        for obj in queryset:
            try:
                container_type = ContainerType.objects.get(pk=obj.container_type_id)
                current_child_creation = container_type.child_sample_creation
                if first_child_creation is None:
                    first_child_creation = current_child_creation
                elif current_child_creation != first_child_creation:
                    return JsonResponse({
                        'success': False,
                        'message': "All selected records must have the same 'Child Sample Creation' status for their Container Type."
                    })
            except ContainerType.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f"Container Type with ID '{obj.container_type_id}' does not exist for record '{getattr(obj, 'sample_id', obj.pk)}'."
                })

        if first_child_creation and queryset.count() > 1:
            return JsonResponse({
                'success': False,
                'message': "For records where 'Child Sample Creation' is True, only single selection is allowed."
            })

        if not first_child_creation and queryset.count() > 1:
            first_record_data = None
            first_workflow_driven = None
            for obj in queryset:
                try:
                    samples_with_workflow = Sample.objects.filter(sample_id=obj).annotate(
                        effective_workflow_id=Case(
                            When(accession_sample_id__isnull=True, then=F('workflow_id')),
                            When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                            default=Value(None),
                            output_field=IntegerField()
                        )
                    )

                    workflow_id_from_samples = samples_with_workflow.values_list('effective_workflow_id',
                                                                                 flat=True).first()

                    if workflow_id_from_samples:
                        current_record_data = {
                            'workflow_id': workflow_id_from_samples,
                            'current_step': obj.current_step,
                        }
                        current_workflow_driven = True

                    else:
                        sample_id_for_map = getattr(obj, 'sample_id', obj.pk)
                        sample_test_map = SampleTestMap.objects.get(sample_id_id=sample_id_for_map)
                        current_record_data = {
                            'test_id': sample_test_map.test_id_id,
                            'sample_type_id': obj.sample_type_id,
                            'container_type_id': obj.container_type_id,
                            'workflow_id': sample_test_map.workflow_id_id,
                            'current_step': obj.current_step,
                        }
                        current_workflow_driven = False

                    if first_workflow_driven is None:
                        first_workflow_driven = current_workflow_driven
                    elif current_workflow_driven != first_workflow_driven:
                        return JsonResponse({
                            'success': False,
                            'message': "Mixed mode not allowed. Please select records which are all either driven by workflow or by tests."
                        })
                    elif current_workflow_driven == first_workflow_driven:
                        if first_record_data is None:
                            first_record_data = current_record_data
                        elif current_record_data != first_record_data and current_workflow_driven:
                            return JsonResponse({
                                'success': False,
                                'message': "For multiple selections (where 'Child Sample Creation' is False), all records must have the same Workflow and Current Step."
                            })
                        elif current_record_data != first_record_data and not current_workflow_driven:
                            return JsonResponse({
                                'success': False,
                                'message': "For multiple selections (where 'Child Sample Creation' is False), all records must have the same Test, Sample Type, Container Type, Workflow and Current Step."
                            })

                except SampleTestMap.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': f"Record '{getattr(obj, 'sample_id', obj.pk)}' has no associated test map."
                    })

        return JsonResponse({'success': True})

    def backward_movement_prompt_view(admin_instance, request):
        """
        Utility view function to render the backward movement prompt form.
        Takes the ModelAdmin instance to access model info.
        """
        SampleTestMap = apps.get_model('sample', 'SampleTestMap')
        TestWorkflowStep = apps.get_model('tests', 'TestWorkflowStep')
        TestWorkflowStepActionMap = apps.get_model('tests', 'TestWorkflowStepActionMap')
        WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
        Sample = apps.get_model('sample', 'Sample')

        model_ids = request.GET.get('ids', '').split(',')
        model_ids = [id for id in model_ids if id]

        selected_objects = admin_instance.model.objects.filter(pk__in=model_ids)
        first_obj = selected_objects.first()

        prior_steps = []
        error_message = None
        current_step_value = None

        if first_obj and hasattr(first_obj, 'current_step') and first_obj.current_step:
            current_step_value = first_obj.current_step

            try:
                obj_sample_id = getattr(first_obj, 'sample_id', first_obj.pk)

                first_sample_test_map = SampleTestMap.objects.filter(
                    sample_id_id=obj_sample_id
                ).order_by(
                    'sample_test_map_id'
                ).first()

                samples_with_workflow = Sample.objects.filter(sample_id=obj_sample_id).annotate(
                    effective_workflow_id=Case(
                        When(accession_sample_id__isnull=True, then=F('workflow_id')),
                        When(accession_sample_id__isnull=False, then=F('accession_sample__workflow_id')),
                        default=Value(None),
                        output_field=IntegerField()
                    )
                )

                workflow_id_from_samples = samples_with_workflow.values_list('effective_workflow_id', flat=True).first()

                if first_sample_test_map:
                    test_id = first_sample_test_map.test_id_id
                    workflow_id_from_test = first_sample_test_map.workflow_id_id
                else:
                    error_message = f"Record '{obj_sample_id}' has no associated test map."
                    test_id = None
                    workflow_id_from_test = None

                workflow_id = workflow_id_from_test or workflow_id_from_samples
                if test_id and workflow_id:
                    try:
                        current_step_obj = WorkflowStep.objects.get(
                            step_id=first_obj.current_step,
                            workflow_id=workflow_id,
                            workflow_type='WetLab'
                        )
                    except WorkflowStep.DoesNotExist:
                        error_message = f"Step '{first_obj.current_step}' not found in workflow '{workflow_id}' for the selected test."

                    if not error_message:
                        if workflow_id_from_test:
                            prior_steps = TestWorkflowStep.objects.filter(
                                backward_movement='Y',
                                container_type_id=first_obj.container_type_id,
                                sample_type_id_id=first_obj.sample_type_id,
                                test_id_id=test_id,
                                workflow_id_id=workflow_id_from_test,
                                workflow_step_id__step_no__lt=current_step_obj.step_no,
                                workflow_step_id__workflow_type='WetLab'
                            ).select_related('workflow_step_id').annotate(
                                action=Subquery(
                                    TestWorkflowStepActionMap.objects.filter(
                                        testwflwstepmap_id=OuterRef('pk'),
                                        sequence=1
                                    ).values('action')[:1]
                                )
                            ).annotate(
                                action=Coalesce('action', Value(''))
                            ).values(
                                'pk',
                                'workflow_id_id',
                                'workflow_step_id__step_id',
                                'workflow_step_id__step_no',
                                'workflow_step_id__department',
                                'action',
                            ).order_by('workflow_step_id__step_no')

                        if workflow_id_from_samples:
                            desired_step_no = current_step_obj.step_no - 1
                            prior_steps = WorkflowStep.objects.filter(
                                backward_movement='Y',
                                workflow_id_id=workflow_id_from_samples,
                                step_no=desired_step_no,
                                workflow_type='WetLab'
                            ).annotate(
                                action=Subquery(
                                    TestWorkflowStepActionMap.objects.filter(
                                        workflow_step_id_id=OuterRef('pk'),
                                        sequence=1
                                    ).values('action')[:1]
                                ),
                                test_workflow_step_id=Value('')  # static field
                            ).annotate(
                                action=Coalesce('action', Value('')),
                                workflow_step_id__step_id=F('step_id'),
                                workflow_step_id__step_no=F('step_no'),
                                workflow_step_id__department=F('department'),
                            ).values(
                                'test_workflow_step_id',
                                'workflow_id_id',
                                'workflow_step_id__step_id',
                                'workflow_step_id__step_no',
                                'workflow_step_id__department',
                                'action'
                            ).order_by('step_no')

            except Exception as e:
                error_message = f"An unexpected error occurred while fetching test information: {e}"

        else:
            error_message = "Selected record or its current step is missing."

        app_label = admin_instance.model._meta.app_label
        model_name = admin_instance.model._meta.model_name
        submit_url_name = f'controllerapp:{app_label}_{model_name}_backward_movement_submit_view'

        context = {
            'selected_objects': selected_objects,
            'prior_steps': prior_steps,
            'error_message': error_message,
            'current_step': current_step_value,
            'submit_url': reverse(submit_url_name),
            'model_name_plural_lower': admin_instance.model._meta.model_name + 's',
            'model_id_field_name': f'{admin_instance.model._meta.model_name}_id',
        }
        return render(request, 'admin/generic_backward_movement_prompt.html', context)

    def backward_movement_submit_view(admin_instance, request):
        """
        Utility view function to handle the submission of the backward movement form.
        Takes the ModelAdmin instance to access model info.
        """
        WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
        module = importlib.import_module("util.util")
        UtilClass = getattr(module, "UtilClass")

        if request.method == 'POST':
            try:
                data = json.loads(request.body.decode('utf-8'))

                model_name = admin_instance.model._meta.model_name
                ids_key = f'{model_name}s'

                selected_ids = data.get(ids_key, [])
                landing_step_id = data.get('landing_step')
                landing_step_no_str = data.get('landing_step_no')
                landing_step_action = data.get('landing_step_action')
                landing_workflow_id = data.get('landing_workflow_id')
                department_name = data.get('department')
                current_step = data.get('current_step')

                user_site_prefix = request.session.get('currentjobtype', '').split('-')[0]
                full_department_name = f"{user_site_prefix}-{department_name}"

                custodial_department_id = Department.objects.filter(name=full_department_name).values_list('id',
                                                                                                           flat=True).first()

                if not selected_ids or not landing_step_id or landing_step_no_str is None or landing_workflow_id is None or landing_step_action is None:
                    return JsonResponse({'status': 'error', 'message': 'Missing data.'}, status=400)

                try:
                    landing_step_no = int(landing_step_no_str)
                    next_step_no = landing_step_no + 1
                except (TypeError, ValueError):
                    return JsonResponse({'status': 'error', 'message': 'Invalid landing_step_no.'}, status=400)

                next_step_queryset = WorkflowStep.objects.filter(
                    workflow_id_id=landing_workflow_id,
                    workflow_type='WetLab',
                    step_no=next_step_no,
                ).values('step_id')

                next_step_id = None
                if next_step_queryset.exists():
                    next_step_id = next_step_queryset.first()['step_id']

                if landing_step_action == '':
                    landing_step_action = None

                old_instances = {str(obj.pk): obj for obj in admin_instance.model.objects.filter(pk__in=selected_ids)}

                updated_count = admin_instance.model.objects.filter(pk__in=selected_ids).update(
                    current_step=landing_step_id,
                    pending_action=landing_step_action,
                    next_step=next_step_id,
                    custodial_department_id=custodial_department_id,
                    previous_step=current_step
                )

                updated_instances = admin_instance.model.objects.filter(pk__in=selected_ids)

                if model_name == 'sample':
                    UtilClass.createRoutingInfoForSample(
                        new_samples=updated_instances,
                        old_samples=old_instances
                    )
                elif model_name == 'reportoption':
                    UtilClass.createRoutingInfoForReportOption(
                        new_reportoption=updated_instances,
                        old_reportoption=old_instances
                    )

                return JsonResponse({'status': 'ok', 'updated_count': updated_count})

            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    def dynamic_upload_path(instance, filename, preview_flag=False):
        from analysis.models import MergeReporting, ReportOption
        model_name = None
        pk = None

        # Determine which model is related
        if instance.accession_id_id:
            model_name = 'Accession'
            pk = instance.accession_id_id
        elif instance.merge_reporting_id_id:
            model_name = 'MergeReporting'
            merge_report = MergeReporting.objects.filter(merge_reporting_id=instance.merge_reporting_id_id).first()
            pk = merge_report.accession_id if merge_report else None
        elif instance.report_option_id_id:
            model_name = 'ReportOption'
            report_option = ReportOption.objects.filter(report_option_id=instance.report_option_id_id).first()
            pk = report_option.accession_id if report_option else None
        elif instance.client_id_id:
            model_name = 'Client'
            client = Client.objects.filter(client_id=instance.client_id_id).first()
            pk = client.name if client else None
        elif instance.physician_id_id:
            model_name = 'Physician'
            physician = Physician.objects.filter(physician_id=instance.physician_id_id).select_related(
                'user_id').first()
            pk = physician.user_id.username if physician and physician.user_id else None

        # Look up the path in AttachmentConfiguration
        default = None
        path = None
        try:
            if preview_flag:
                path = 'tempfiles/'
            else:
                config = AttachmentConfiguration.objects.get(model_name=model_name)
                path = config.path
        except ObjectDoesNotExist:
            path = 'attachments/default/'
            default = 'Y'

        # Get other dynamic fields
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H%M%S")
        user = getattr(instance, 'created_by', None)
        current_user = user.username if user else 'anonymous'
        orig_filename, extension = os.path.splitext(filename)
        replacements = {
            "[modelname]": str(model_name),
            "[pk]": str(pk),
            "[currentuser]": str(current_user),
            "[orgfilename]": str(orig_filename),
            "[date]": str(current_date),
            "[timestamp]": str(timestamp)
        }

        for old_string, new_string in replacements.items():
            path = path.replace(old_string, new_string)
        if default == 'Y':
            return f'{path}{orig_filename}_{current_date}_{timestamp}{extension}'
        elif preview_flag:
            return path + filename
        else:
            return path + extension

    def upload_attachment_to_s3(instance, uploaded_file):
        path = UtilClass.dynamic_upload_path(instance, uploaded_file.name)
        body = getattr(uploaded_file, 'file', uploaded_file)
        content_type = getattr(uploaded_file, 'content_type', 'application/octet-stream')
        s3_client = UtilClass.get_s3_client()

        s3_params = {
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": path,
            "Body": body,
            "ContentType": content_type
        }

        if getattr(settings, "AWS_S3_KMS_KEY_ARN", None):
            s3_params.update({
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": settings.AWS_S3_KMS_KEY_ARN
            })

        s3_client.put_object(**s3_params)
        print(f"✅ Uploaded {uploaded_file.name} to S3: {path}")
        return path

    def download_attachment(request, attachment_id):
        Attachment = apps.get_model('analysis', 'Attachment')
        try:
            attachment = Attachment.objects.get(pk=attachment_id)
            if not attachment.file_path:
                raise Http404("File not found.")

            s3_client = UtilClass.get_s3_client()

            s3_key = attachment.file_path.name
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME

            presigned_url = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket_name, 'Key': s3_key,
                        'ResponseContentDisposition': f'attachment; filename="{os.path.basename(s3_key)}"',
                        'ResponseContentType': 'application/octet-stream',
                        },
                ExpiresIn=60,
            )
            return HttpResponseRedirect(presigned_url)

        except Attachment.DoesNotExist:
            raise Http404("Attachment not found.")
        except ClientError as e:
            raise Http404(f"Failed to generate download link: {str(e)}")

    def upload_attachment_to_s3_fixed_path(instance, uploaded_file, preview_flag=False):
        path = UtilClass.dynamic_upload_path(instance, uploaded_file.name, preview_flag)
        body = getattr(uploaded_file, 'file', uploaded_file)

        # Content Type Handling
        content_type = getattr(uploaded_file, 'content_type', None)
        if not content_type:
            content_type, _ = mimetypes.guess_type(uploaded_file.name)
        if not content_type:
            content_type = 'application/octet-stream'

        if uploaded_file.name.endswith('.pdf'):
            content_type = 'application/pdf'
        s3_client = UtilClass.get_s3_client()

        s3_params = {
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": path,
            "Body": body,
            "ContentType": content_type
        }

        if getattr(settings, "AWS_S3_KMS_KEY_ARN", None):
            s3_params.update({
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": settings.AWS_S3_KMS_KEY_ARN
            })

        s3_client.put_object(**s3_params)
        print(f"✅ Uploaded {uploaded_file.name} to S3: {path}")
        return path

    @staticmethod
    def get_s3_url(s3_key):
        s3_client = UtilClass.get_s3_client()
        bucket = settings.AWS_STORAGE_BUCKET_NAME

        if getattr(settings, 'AWS_S3_PUBLIC_URL_PREFIX', None):
            return f"{settings.AWS_S3_PUBLIC_URL_PREFIX}/{s3_key}"

        # If private, return signed URL
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=300  # 5 minutes
        )

    @staticmethod
    def build_image_map(merge_reporting_id):
        from analysis.util import generate_image_map

        rel_paths_str = generate_image_map(merge_reporting_id)
        if rel_paths_str:
            rel_paths = rel_paths_str.split(';')
            abs_paths = []

            base_dir = str(settings.BASE_DIR).replace('\\', '/')

            for p in rel_paths:
                if os.path.isabs(p):
                    full = p
                else:
                    full = os.path.join(base_dir, p)
                abs_paths.append(os.path.abspath(full).replace('\\', '/'))

            return ";".join(abs_paths)
        return None

    @staticmethod
    def cleanup_temp_image(image_paths):
        """
        Deletes one or more temporary image files.
        `image_paths_str` may be:
          - a single filepath, or
          - multiple filepaths separated by semicolons.
        """
        paths = [p.strip() for p in image_paths.split(";") if p.strip()]

        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    print(f"Deleted temporary image: {path}")
                else:
                    print(f"No such file to delete: {path}")
            except Exception as e:
                print(f"Error deleting image {path}: {e}")

    @staticmethod
    def createRoutingInfoForSample(new_samples, old_samples=None, single=False):
        """
        Creates routing info entries for newly created or updated samples.

        :param new_samples: list of Sample instances (after create/update)
        :param old_samples: dict of old Sample instances (before update),
                            keyed by sample.sample_id (only needed for update case)
        :param single: True if called from save() for single instance
        """
        RoutingInfo = apps.get_model('routinginfo', 'RoutingInfo')
        routing_entries = []

        if single and not isinstance(new_samples, (list, tuple)):
            new_samples = [new_samples]

        for sample_instance in new_samples:
            if old_samples is None:
                routing_entries.append(
                    RoutingInfo(
                        sample_id_id=sample_instance.sample_id,
                        from_step=None,
                        to_step=sample_instance.current_step,
                        from_department=None,
                        to_department=sample_instance.custodial_department,
                        from_user=None,
                        to_user=sample_instance.custodial_user,
                        created_by=sample_instance.created_by,
                    )
                )
            else:
                old_instance = old_samples.get(sample_instance.sample_id)
                if old_instance and old_instance.current_step != sample_instance.current_step:
                    routing_entries.append(
                        RoutingInfo(
                            sample_id_id=sample_instance.sample_id,
                            from_step=old_instance.current_step,
                            to_step=sample_instance.current_step,
                            from_department=old_instance.custodial_department,
                            to_department=sample_instance.custodial_department,
                            from_user=old_instance.custodial_user,
                            to_user=sample_instance.custodial_user,
                            created_by=sample_instance.mod_by,
                        )
                    )

        if routing_entries:
            RoutingInfo.objects.bulk_create(routing_entries)

    @staticmethod
    def createRoutingInfoForReportOption(new_reportoption, old_reportoption=None, single=False):
        """
        Creates routing info entries for newly created or updated reportoptions.

        :param new_reportoption: list of Reportoption instances (after create/update)
        :param old_reportoption: dict of old Reportoption instances (before update),
                            keyed by analysis.report_option_id (only needed for update case)
        :param single: True if called from save() for single instance
        """
        RoutingInfo = apps.get_model('routinginfo', 'RoutingInfo')
        routing_entries = []

        if single and not isinstance(new_reportoption, (list, tuple)):
            new_reportoption = [new_reportoption]

        for reportop_instance in new_reportoption:
            if old_reportoption is None:
                routing_entries.append(
                    RoutingInfo(
                        report_option_id_id=reportop_instance.report_option_id,
                        from_step=None,
                        to_step=reportop_instance.current_step,
                        from_department=None,
                        to_department=reportop_instance.custodial_department,
                        from_user=None,
                        to_user=None,
                        created_by=reportop_instance.created_by,
                    )
                )
            else:
                old_instance = old_reportoption.get(reportop_instance.report_option_id)
                if old_instance and old_instance.current_step != reportop_instance.current_step:
                    routing_entries.append(
                        RoutingInfo(
                            report_option_id_id=reportop_instance.report_option_id,
                            from_step=old_instance.current_step,
                            to_step=reportop_instance.current_step,
                            from_department=old_instance.custodial_department,
                            to_department=reportop_instance.custodial_department,
                            from_user=None,
                            to_user=None,
                            created_by=reportop_instance.mod_by,
                        )
                    )

        if routing_entries:
            RoutingInfo.objects.bulk_create(routing_entries)

    @staticmethod
    def send_mail_for_pharma_implementation(mail_data):
        """
        Send mail after Accession Generation and Report Generation
        """

        if not mail_data:
            raise Exception("Mail data is empty")

        from_email = mail_data.get("from_email") or settings.DEFAULT_FROM_EMAIL
        to_email = mail_data.get("to_email")
        cc_email = mail_data.get("cc_email")
        subject = mail_data.get("subject")
        body = mail_data.get("body")
        attachments = mail_data.get("attachments", [])

        # Validations
        if not from_email:
            raise Exception("From Email ID is not present")

        if not to_email:
            raise Exception("To Email ID is not present")

        if not subject:
            raise Exception("Email Subject is not present")

        if not body:
            raise Exception("Email Body is not present")

        # Convert comma-separated emails to list
        to_list = [email.strip() for email in to_email.split(";") if email.strip()]
        cc_list = [email.strip() for email in (cc_email or "").split(";") if email.strip()]

        try:
            # ---- Build email ----
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to_list,
                cc=cc_list,
            )

            # HTML email body
            email.content_subtype = "html"

            # # ---- Add attachments ----
            # for file_path in attachments:
            #     if os.path.exists(file_path):
            #         email.attach_file(file_path)
            #     else:
            #         raise Exception(f"Attachment not found: {file_path}")

            for file_path in attachments:
                if file_path.startswith("http://") or file_path.startswith("https://"):
                    # Download the file
                    try:
                        response = requests.get(file_path)
                        response.raise_for_status()  # Raise if status != 200
                        filename = file_path.split("/")[-1].split("?")[0]  # Extract filename from URL
                        email.attach(filename, response.content)
                    except Exception as e:
                        raise Exception(f"Failed to download attachment from {file_path}: {e}")
                else:
                    # Local file path
                    if os.path.exists(file_path):
                        email.attach_file(file_path)
                    else:
                        raise Exception(f"Attachment not found: {file_path}")

            # ---- Send email ----
            email.send(fail_silently=False)
            return "Mail sent successfully."

        except Exception as e:
            raise Exception(f"Failed to send email: {e}")
