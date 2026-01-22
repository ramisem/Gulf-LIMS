from django.apps import apps
from django.contrib import messages


class TechnicalProfessionalComponentUtilClass:
    @staticmethod
    def populate_pc(request, merge_reporting_id):
        # This is to populate PC post report signout
        if not merge_reporting_id:
            raise Exception("Merge Reporting Id is blank")

        user_obj = request.user
        JobType = apps.get_model('security', 'JobType')
        TechnicalProfessionalComponentMap = apps.get_model('tpcm', 'TechnicalProfessionalComponentMap')

        # Step 1: Get jobtype name from session
        jobtype_name = request.session.get('currentjobtype', None)
        if not jobtype_name:
            raise Exception("Job Type doesn't exists")

        # Step 2: Get JobType instance
        try:
            jobtype_obj = JobType.objects.get(name=jobtype_name)
        except JobType.DoesNotExist:
            raise Exception("Job Type doesn't exists")

        # Step 3: Get Department and Site
        department = jobtype_obj.departmentid
        if not department or not department.siteid:
            if not department:
                raise Exception("Department doesn't exists")
            if not department.siteid:
                raise Exception("Site doesn't exists")
            return  # or log error

        site = department.siteid

        MergeReporting = apps.get_model('analysis', 'MergeReporting')
        merge_reporting_obj = MergeReporting.objects.get(merge_reporting_id=merge_reporting_id)
        accession_id = merge_reporting_obj.accession_id
        if not accession_id:
            raise Exception("Accession Id is blank")

        qs_existing_tpcm_records = TechnicalProfessionalComponentMap.objects.filter(accession_id=accession_id,
                                                                            compontent_site_id=site,
                                                                            component_type="PC")
        if not qs_existing_tpcm_records:
            tpcm_obj = TechnicalProfessionalComponentMap(
                accession_id=accession_id,
                compontent_site_id=site,
                component_type="PC",
                created_by=user_obj,
                mod_by=user_obj
            )
            tpcm_obj.save()

    @staticmethod
    def populate_tc_tca(accession_list, request, user_obj):
        # This is used to populate tc and tca on wetlab completion
        if not accession_list:
            messages.error(request, "Accession Id is blank.")
            return
        accession_list = set(accession_list)

        JobType = apps.get_model('security', 'JobType')
        Accession = apps.get_model('accessioning', 'Accession')
        TechnicalProfessionalComponentMap = apps.get_model('tpcm', 'TechnicalProfessionalComponentMap')

        # Step 1: Get jobtype name from session
        jobtype_name = request.session.get('currentjobtype', None)
        if not jobtype_name:
            messages.error(request, "Job Type doesn't exists")
            return  # or log error

        # Step 2: Get JobType instance
        try:
            jobtype_obj = JobType.objects.get(name=jobtype_name)
        except JobType.DoesNotExist:
            messages.error(request, "Job Type doesn't exists")
            return  # or log error

        # Step 3: Get Department and Site
        department = jobtype_obj.departmentid
        if not department or not department.siteid:
            if not department:
                messages.error(request, "Department doesn't exists")
            if not department.siteid:
                messages.error(request, "Site doesn't exists")
            return  # or log error

        site = department.siteid

        # Step 4: Prepare TPCM records for all accessions
        tpcm_objects = []
        accessions = Accession.objects.filter(accession_id__in=accession_list)
        qs_existing_tpcm_records = TechnicalProfessionalComponentMap.objects.filter(accession_id__in=accession_list,
                                                                                    component_type__in=['TC', 'TCA'])
        for accession in accessions:
            for component_type in ['TC', 'TCA']:
                if qs_existing_tpcm_records:
                    filter_qs_tpcm_records = qs_existing_tpcm_records.filter(accession_id=accession,
                                                                             compontent_site_id=site,
                                                                             component_type=component_type)
                    if not filter_qs_tpcm_records:
                        tpcm_obj = TechnicalProfessionalComponentMap(
                            accession_id=accession,
                            compontent_site_id=site,
                            component_type=component_type,
                            created_by=user_obj,
                            mod_by=user_obj
                        )
                        tpcm_objects.append(tpcm_obj)
                else:
                    tpcm_obj = TechnicalProfessionalComponentMap(
                        accession_id=accession,
                        compontent_site_id=site,
                        component_type=component_type,
                        created_by=user_obj,
                        mod_by=user_obj
                    )
                    tpcm_objects.append(tpcm_obj)

        # Step 5: Bulk create (with conflict ignore for safety)
        if tpcm_objects:
            TechnicalProfessionalComponentMap.objects.bulk_create(tpcm_objects, ignore_conflicts=True)
