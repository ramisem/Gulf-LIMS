from django.http import JsonResponse

from logutil.log import log
from masterdata.models import PatientInsuranceInfo, Patient, Physician, ClientDoctorInfo, Client, AccessionType, \
    Sponsor, ProjectVisitMap, BioSite, BioProject, ProjectFieldsMap, ProjectPhysicianMap
from process.models import ContainerType, SampleTypeContainerType
from sample.models import Sample
from sample.util import SampleUtilClass
from tests.models import ICDCode


# This is for getting insurance details based on the selected patient
def get_insurance_by_patient(request):
    patient_id = request.GET.get('patient_id', None)
    log.info(f"Patient ID ---> {patient_id}")
    if patient_id is not None:
        if patient_id != '':
            patient_insurance_details = PatientInsuranceInfo.objects.filter(patient_id=patient_id).values(
                'patientinfo_id', 'policy', 'insurance')
        return JsonResponse(list(patient_insurance_details), safe=False)
    else:
        log.error(f"Missing patientid")
        return JsonResponse({'error': 'Missing patientid'}, status=400)


# This is to get the patient details based on the selected patient
def get_patient_details_by_patient(request):
    patient_id = request.GET.get('patient_id', None)
    log.info(f"Patient ID ---> {patient_id}")
    if patient_id is not None:
        if patient_id != '':
            patient_details = Patient.objects.filter(patient_id=patient_id).values('street_address', 'apt', 'city',
                                                                                   'zipcode', 'state', 'phone_number',
                                                                                   'fax_number', 'email')
            return JsonResponse(list(patient_details), safe=False)
    else:
        log.error(f"Missing patientid")
        return JsonResponse({'error': 'Missing patientid'}, status=400)


# This is for getting the insurance detqails based on the selected insurance
def get_insurance_details_by_insurance_id(request):
    insurance_id = request.GET.get('insurance_id', None)
    log.info(f"Insurance ID ---> {insurance_id}")
    if insurance_id is not None:
        if insurance_id != '':
            insurance_details = PatientInsuranceInfo.objects.filter(patientinfo_id=insurance_id).values('group')
        return JsonResponse(list(insurance_details), safe=False)
    else:
        log.error(f"Missing insurance details")
        return JsonResponse({'error': 'Missing insurance details'}, status=400)


# This is for getting the internal and external pathologists
def get_internal_external_doctors(request):
    is_external = request.GET.get('is_external', None)
    log.info(f"Is External Doctor? ---> {is_external}")
    if is_external is not None:
        if is_external == 'Y':

            doctor_details = Physician.objects.filter(external=True, category='Pathologist').values(
                'physician_id', 'first_name', 'last_name')
            return JsonResponse(list(doctor_details), safe=False)

        else:
            doctor_details = Physician.objects.filter(external=False, category='Pathologist').values('physician_id',
                                                                                                     'first_name',
                                                                                                     'last_name')
            return JsonResponse(list(doctor_details), safe=False)
    else:
        log.error(f"Missing doctor details")
        return JsonResponse({'error': 'Missing doctor details'}, status=400)


# This is for getting the client details
def get_client_details_by_client(request):
    client_id = request.GET.get('client_id', None)
    log.info(f"Client Id ---> {client_id}")
    if client_id is not None:
        if client_id != '':
            client_details = Client.objects.filter(client_id=client_id).values('address1', 'address2', 'city', 'state',
                                                                               'postalcode', 'country', 'telephone',
                                                                               'fax_number',
                                                                               'primaryemail')
            return JsonResponse(list(client_details), safe=False)
    else:
        log.error(f"Missing client ID")
        return JsonResponse({'error': 'Missing client ID'}, status=400)


# This is for getting the container type based on the selected sample type
def get_containertype_by_sampletype(request):
    sample_type_id = request.GET.get('sample_type_id', None)
    log.info(f"Sample Type Id ---> {sample_type_id}")
    if sample_type_id is not None:
        if sample_type_id != '':
            container_type_objects = SampleTypeContainerType.objects.filter(sample_type_id=sample_type_id).values(
                'container_type_id')
            if container_type_objects is not None:
                list_container_type_id = []
                for container_type_obj in container_type_objects:
                    list_container_type_id.append(container_type_obj['container_type_id'])

                container_type_details_list = []

                if list_container_type_id is not None:
                    container_type_details = ContainerType.objects.filter(
                        container_type_id__in=list_container_type_id).values(
                        'container_type_id', 'container_type')
                    container_type_details_list = list(container_type_details)

                return JsonResponse(container_type_details_list, safe=False)

    else:
        log.error(f"Missing sample type id")
        return JsonResponse({'error': 'Missing sample type id'}, status=400)


# This is for creating samples
def createSample(request):
    log.info(f"request.method ---> {request.method}")
    if request.method == "POST":
        accession_id = request.POST.get("accession_id", None)
        sample_type_id = request.POST.get("sample_type_id", None)
        container_type_id = request.POST.get("container_type_id", None)
        test_id = request.POST.get("test_id", None)
        count = request.POST.get("count", None)
        part_no = request.POST.get("part_no", None)
        is_child_sample_creation = request.POST.get("is_child_sample_creation", None)
        is_generate_parent_seq = request.POST.get("is_generate_parent_seq", None)
        parent_seq = request.POST.get("parent_seq", None)
        workflow_id = request.POST.get("workflow_id", None)
        if workflow_id == '':
            workflow_id = None
        log.info(
            f" accession_id: {accession_id}, sample_type_id: {sample_type_id}, container_type_id: {container_type_id}, count: {count}, tests: {test_id}, part_no: {part_no}, is_child_sample_creation: {is_child_sample_creation}, workflow_id: {workflow_id}")
        try:
            count = int(count)
        except ValueError:
            log.error("Invalid count value")
            return JsonResponse({"status": "error", "message": "Invalid count value"}, status=400)

        if accession_id is None or sample_type_id is None or container_type_id is None or count is None:
            log.error("Missing required fields")
            return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)

        try:
            SampleUtilClass.create_sample(accession_id, sample_type_id, container_type_id, count, test_id, request,
                                          part_no, is_child_sample_creation, is_generate_parent_seq, parent_seq, workflow_id)
        except Exception as e:
            message = str(e).strip("[]").replace("'", "")
            log.error(f"Error Message : {message}")
            return JsonResponse({"status": "error", "message": message}, status=400)

        response_data = {
            "status": "success",
            "message": "Sample created successfully",
            "accession_id": accession_id,
            "sample_type_id": sample_type_id,
            "container_type_id": container_type_id,
            "count": count
        }

        return JsonResponse(response_data)

    log.error(f"Invalid request")
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=405)


# This is for getting the referring doctors associated with the clients
def get_doctors_by_client(request):
    id_client_id = request.GET.get('id_client_id', None)
    log.info(f"Client Id ---> {id_client_id}")
    if id_client_id is not None:
        client_doctor_details = ClientDoctorInfo.objects.filter(client_id=id_client_id).values_list(
            'physician_id', flat=True
        )

        doctor_details = Physician.objects.filter(physician_id__in=client_doctor_details).values(
            'physician_id', 'first_name', 'last_name'
        )

        return JsonResponse(list(doctor_details), safe=False)
    else:
        log.error(f"Missing client ID")
        return JsonResponse({'error': 'Missing client ID'}, status=400)


# This is for getting the ICD Code details from the selected ICD Code
def get_details_by_icdcode(request):
    icd_code_id = request.GET.get('icd_code_id')
    log.info(f"ICD Code Id ---> {icd_code_id}")
    if icd_code_id is not None:
        if icd_code_id != '':
            icdcode_details = ICDCode.objects.filter(icd_code_id=icd_code_id).values(
                'description')
        return JsonResponse(list(icdcode_details), safe=False)
    else:
        log.error(f"Missing ICDCode ID")
        return JsonResponse({'error': 'Missing ICDCode ID'}, status=400)


# This is for getting the container details from the selected container
def get_containerdetails_by_containertype(request):
    container_type_id = request.GET.get('id_container_type_id')
    log.info(f"Container Type Id ---> {container_type_id}")
    try:
        container_type = ContainerType.objects.get(container_type_id=container_type_id)
        return JsonResponse({
            'is_child_sample_creation': container_type.child_sample_creation,
            'is_gen_slide_seq': container_type.gen_slide_seq,
            'workflow_id': container_type.workflow_id.workflow_id if container_type.workflow_id else None,
            'workflow_name': container_type.workflow_id.workflow_name if container_type.workflow_id else ''
        })
    except ContainerType.DoesNotExist:
        log.error(f"Container type not found")
        return JsonResponse({'error': 'Container type not found'}, status=404)


# This is for getting the existing Block Or Cassette Sequqence for the selected Accession and Part No
def get_parent_seq(request):
    try:
        part_no = request.GET.get("part_no")
        accession_id = request.GET.get("accession_id")
        log.info(f"part_no ---> {part_no}")
        log.info(f"accession_id ---> {accession_id}")
        if not part_no or not accession_id:
            return JsonResponse({"error": "Invalid data"}, status=400)

        parent_seqs = Sample.objects.filter(accession_id=accession_id, part_no=part_no).values_list(
            "block_or_cassette_seq",
            flat=True).distinct()

        if not parent_seqs:
            return JsonResponse({"parent_seq_options": []})

        parent_seq_options = [{"value": seq, "label": seq} for seq in parent_seqs]

        return JsonResponse({"parent_seq_options": parent_seq_options})
    except Exception as e:
        log.error(f"Error Message : {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def get_samples_created(request):
    try:
        accession_id = request.GET.get("accession_id")
        log.info(f"accession_id ---> {accession_id}")
        if not accession_id:
            return JsonResponse({"error": "Invalide Data"}, status=400)
        samples = Sample.objects.filter(accession_id=accession_id).count()
        return JsonResponse({'samples_count': samples})
    except Exception as e:
        log.error(f"Error Message : {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


# populate reporting_type on the basis of accession_type
def get_reportingtype_by_accessiontype(request):
    accession_type = request.GET.get('accession_type', None)
    log.info(f"accession_type ---> {accession_type}")
    if accession_type is not None:
        if accession_type != '':
            reporting_type = AccessionType.objects.filter(accession_type_id=accession_type).values('reporting_type')
            return JsonResponse(list(reporting_type), safe=False)
    else:
        log.error(f"Missing Accession Type")
        return JsonResponse({'error': 'Missing Accession Type '}, status=400)


def get_sponsor_details_by_sponsor(request):
    """
    Fetches details for a given Sponsor ID from a GET parameter.
    """
    sponsor_id = request.GET.get('sponsor_id', None)
    log.info(f"Sponsor Id ---> {sponsor_id}")

    if not sponsor_id:
        log.error("Missing sponsor_id parameter")
        return JsonResponse({'error': 'Missing sponsor ID'}, status=400)

    try:
        sponsor = Sponsor.objects.get(pk=sponsor_id)

        data = {
            'sponsor_name': sponsor.sponsor_name,
            'sponsor_number': sponsor.sponsor_number,
            'sponsor_description': sponsor.sponsor_description,
            'sponsor_address_info': sponsor.sponsor_address_info,
        }
        return JsonResponse(data)
    except Sponsor.DoesNotExist:
        log.error(f"Sponsor with id {sponsor_id} not found")
        return JsonResponse({'error': 'Sponsor not found'}, status=404)


def get_projects_by_sponsor(request):
    sponsor_id = request.GET.get('sponsor_id', None)
    if not sponsor_id:
        return JsonResponse([], safe=False)

    projects = BioProject.objects.filter(sponsor_id=sponsor_id, qc_status='Pass', is_active=True).values(
        'bioproject_id', 'project_protocol_id')
    return JsonResponse(list(projects), safe=False)


def get_visits_by_project(request):
    project_id = request.GET.get('project_id', None)
    if not project_id:
        return JsonResponse([], safe=False)

    visits = ProjectVisitMap.objects.filter(bioproject_id=project_id).values('pk', 'visit_id')
    return JsonResponse(list(visits), safe=False)


def get_investigators_by_project(request):
    project_id = request.GET.get('project_id', None)
    if not project_id:
        return JsonResponse([], safe=False)

    # The BioSite model is what you use for Investigators
    investigators = BioSite.objects.filter(bioproject_id=project_id).values('pk', 'investigator_name')
    return JsonResponse(list(investigators), safe=False)


def get_project_field_demographics(request):
    project_id = request.GET.get('project_id', None)
    if not project_id:
        return JsonResponse({})

    settings = ProjectFieldsMap.objects.filter(
        project_id=project_id,
        category__in=['ACCESSION', 'SAMPLE']
    ).values('model_field_name', 'is_visible', 'category')

    field_visibility = {
        'ACCESSION': {},
        'SAMPLE': {}
    }

    for setting in settings:
        if setting['model_field_name']:  # Ensure the field name is not empty
            category = setting['category']
            field_name = setting['model_field_name']
            is_visible = setting['is_visible']
            if category in field_visibility:
                field_visibility[category][field_name] = is_visible

    return JsonResponse(field_visibility)


def get_physicians_by_project(request):
    project_id = request.GET.get('project_id', None)
    if not project_id:
        return JsonResponse([], safe=False)

    # 1. Find all physician IDs linked to this project in the map table.
    physician_ids = ProjectPhysicianMap.objects.filter(
        bioproject_id=project_id
    ).values_list('physician_id', flat=True)

    # 2. Fetch the details for those physicians.
    doctors = Physician.objects.filter(
        pk__in=physician_ids
    ).values('physician_id', 'first_name', 'last_name')

    return JsonResponse(list(doctors), safe=False)

def upload_scanned_images(request):
    from accessioning.models import Accession
    from analysis.models import Attachment
    from util.util import UtilClass as GenericUtilClass
    """
    Receives an uploaded image (scanned document) from the frontend
    and uploads it directly to Amazon S3.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    # Check if file is uploaded
    if 'file' not in request.FILES:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    uploaded_file = request.FILES['file']

    # Get accession_id from POST data
    accession_id = request.POST.get("accession_id", None)
    if not accession_id:
        return JsonResponse({"error": "No accession_id provided"}, status=400)

    accesssion_obj = Accession.objects.get(pk=accession_id)
    if not accesssion_obj:
        return JsonResponse({"error": "Accession does not exists"}, status=400)

    obj = Attachment()
    obj.accession_id = accesssion_obj
    s3_key = GenericUtilClass.upload_attachment_to_s3(obj, uploaded_file)

    obj.file_path = None  # Prevent actual file save
    obj.file_path.name = s3_key  # Store S3 key manually
    obj.created_by = request.user
    obj.mod_by = request.user
    obj.save()

    return JsonResponse({"successs": "File uploaded successfully"})