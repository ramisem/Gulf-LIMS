from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from accessioning.models import BioPharmaAccession
from masterdata.models import Physician, BodySubSiteMap, BioProject, BodySiteTestMap, ProjectTestMap
from sample.models import SampleTestMap
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.utils.timezone import now


def get_physician_details_by_physician(request):
    physician_id = request.GET.get('physician_id')
    print("Physician Id is " + physician_id)
    if physician_id is not None:
        if physician_id != '':
            physician_details = Physician.objects.filter(physician_id=physician_id).values(
                'phone_number', 'fax_number', 'email')
        return JsonResponse(list(physician_details), safe=False)
    else:
        return JsonResponse({'error': 'Missing Physician ID'}, status=400)


def get_sub_sites(request):
    body_site = request.GET.get("body_site", None)
    if body_site is not None:
        subsites = BodySubSiteMap.objects.filter(body_site__body_site=body_site).values_list("sub_site",
                                                                                             flat=True).distinct()
        return JsonResponse({"sub_sites": [{"id": s, "text": s} for s in subsites]})
    else:
        return JsonResponse({'error': 'Missing Body Site'}, status=400)

def get_projects_by_sponsor(request):
    # This is to retrieve projects by sponsor

    sponsor_id = request.GET.get('sponsor_id')
    if sponsor_id:
        project_list = BioProject.objects.filter(sponsor_id=sponsor_id).values('bioproject_id','project_protocol_id')
        if project_list:
            return JsonResponse(list(project_list), safe=False)
        else:
            return JsonResponse([], safe=False)


@csrf_exempt
def push_to_qc_ajax(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        if not project_id:
            return JsonResponse({'status': 'error', 'message': 'Missing project ID'})
        try:
            project = BioProject.objects.get(pk=project_id)

            #  Check if already In Progress
            if project.qc_status == 'In Progress':
                return JsonResponse({'status': 'error', 'message': 'Project is already pushed to QC'})

            project.qc_status = 'In Progress'
            project.save(update_fields=['qc_status'])
            return JsonResponse({'status': 'success'})
        except BioProject.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Project not found'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# Perform QC Operation on Project
def ajax_perform_qc(request):
    if request.method == 'POST':
        bioproject_id = request.POST.get('bioproject_id')
        qc_status = request.POST.get('qc_status')
        qc_reason = request.POST.get('qc_reason')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Validate required fields
        if not all([bioproject_id, qc_status, username, password]):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})

        # Step 1: Authenticate user
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid username or password.'})

        try:
            # Step 2: Get BioProject
            bioproject = BioProject.objects.get(pk=bioproject_id)
            pushed_to_qc_by = bioproject.mod_by
            if pushed_to_qc_by and pushed_to_qc_by == user:
                return JsonResponse({'status': 'failed', 'message': 'Error: The user who submitted the project for review cannot perform the QC. Peer review is required.'})
            # Step 3: Update QC details
            bioproject.qc_status = qc_status
            bioproject.qc_reason = qc_reason
            bioproject.qced_by = user
            bioproject.qced_dt = now()
            bioproject.save()

            return JsonResponse({'status': 'success', 'message': 'QC performed successfully.'})

        except BioProject.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'BioProject not found.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

# def get_tests_based_on_bodysites(request):
#     """
#     This would return the tests associated with this bodysite
#     """
#     body_site = request.GET.get("body_site", None)
#     if body_site is not None:
#         bodysitetestmap = BodySiteTestMap.objects.filter(body_site__body_site=body_site).distinct()
#         return JsonResponse({"tests": [{"test_id": s.test_id_id, "test_name": s.test_id.test_name} for s in bodysitetestmap]})
#     else:
#         return JsonResponse({'error': 'Missing Body Site'}, status=400)
def get_tests_based_on_bodysite_and_sample(request):
    """
    Return unique tests associated with both the given bodysite and the sample.
    """
    body_site = request.GET.get("body_site")
    sample_id = request.GET.get("sample_id")
    child_sample_creation = request.GET.get("child_sample_creation")

    if not body_site:
        return JsonResponse({'error': 'Missing Body Site'}, status=400)

    # Fetch tests mapped to the selected Body Site
    bodysite_test_qs = BodySiteTestMap.objects.filter(
        body_site__body_site=body_site
    ).distinct()

    if not bodysite_test_qs.exists():
        return JsonResponse({
            "tests": [],
            "errormsg": "Could not associate any Test(s) as there are no Test(s) associated with this bodysite",
            "iserror": "Y"
        })

    if child_sample_creation == "False":
        if bodysite_test_qs:
            bodysite_test_qs = bodysite_test_qs .filter(is_default=True)

            if not bodysite_test_qs.exists():
                return JsonResponse({
                    "tests": [],
                    "errormsg": "Could not associate any Test as there is no default Test for this bodysite",
                    "iserror":"Y"
                })

    bodysite_test_ids = list(bodysite_test_qs.values_list('test_id_id', flat=True))
    project_id = None
    if sample_id:
        try:
            # from sample.models import Sample
            Sample = apps.get_model('sample', 'Sample')
            sample = Sample.objects.select_related('accession_id').get(pk=sample_id)
            accession = sample.accession_id
            # Check for BioPharmaAccession linked to this accession
            bio_accession = BioPharmaAccession.objects.filter(accession_id=accession.accession_id).first()
            if bio_accession and bio_accession.project_id:
                project_id = bio_accession.project_id
        except Exception as e:
            print(f"Error fetching BioPharmaAccession: {e}")

    # --- Project validation ---
    if project_id:
        # Fetch all test IDs linked to this project
        project_test_ids = set(
            ProjectTestMap.objects.filter(bioproject_id_id=project_id)
            .values_list('test_id_id', flat=True)
        )
        missing_tests = [t for t in bodysite_test_ids if t not in project_test_ids]

        if missing_tests:
            return JsonResponse({
                'error': 'Some tests for the selected Body Site are not available for this Project.',
                'missing_test_ids': missing_tests
            }, status=400)

    # Fetch tests already assigned to the given sample

    sampletestmap = SampleTestMap.objects.filter(
        sample_id=sample_id
    ).distinct() if sample_id else []

    # Combine results uniquely by test_id
    combined_tests = {}
    for s in bodysite_test_qs:
        combined_tests[s.test_id_id] = s.test_id.test_name
    for s in sampletestmap:
        combined_tests[s.test_id_id] = s.test_id.test_name

    # Prepare list for JSON
    tests = [
        {"test_id": tid, "test_name": tname}
        for tid, tname in combined_tests.items()
    ]

    return JsonResponse({"tests": tests, "errormsg":"", "iserror":"N"})
