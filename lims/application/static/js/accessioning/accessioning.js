let initialProject, initialVisit, initialInvestigator, initialReportingDoctor;
$(document).ready(function () {
    var id_accession_id_obj = document.getElementById('id_accession_id');
    document.getElementById("id_previous_accession").value = '';
    document.getElementById("id_isupdate_accession_prefix").value = '';
    document.getElementById("id_parent_seq").disabled=true;
    document.getElementById("id_is_generate_parent_seq").value = '';
    initialProject = $('#id_project').val();
    initialVisit = $('#id_visit').val();
    initialInvestigator = $('#id_investigator').val();
    initialReportingDoctor = $('#id_reporting_doctor').val();
    const sponsorSelect = $('#id_sponsor');
    if (sponsorSelect.length && sponsorSelect.val()) {
        setTimeout(function() {
            sponsorSelect.trigger('change');
        }, 200);
    }
    var id_accession_category = document.getElementById("id_accession_category").value;
    accession_cat = id_accession_category;
    if(id_accession_category == 'Clinical'){
        document.querySelector('div[class="form-group field-parent_seq"]').style.display = "none";
        document.querySelector('div[class="form-group field-part_no"]').style.display = "none";
    }

    let sampleRows = $("#sample_set-group tbody tr").not(".empty-form"); // Ignore the empty template row
    if (sampleRows.length > 0) {
        console.log("Samples exist in the inline tab.");
    } else {
        console.log("No samples exist.");
    }

    if (typeof id_accession_id_obj != 'undefined' && id_accession_id_obj != null) {
        var id_accession_id = id_accession_id_obj.value;
        if (id_accession_id == null || id_accession_id == '') {
            document.getElementById("id_case_id").readOnly = true;
            if (document.getElementById('id_accession_category').value != 'Pharma'){
                document.querySelector('div[class="form-group field-insurance_id"]').style.display = "none";
                document.querySelector('div[class="form-group field-insurance_group"]').style.display = "none";
                document.querySelector('div[class="form-group field-street_address"]').style.display = "none";
                document.querySelector('div[class="form-group field-apt"]').style.display = "none";
                document.querySelector('div[class="form-group field-city"]').style.display = "none";
                document.querySelector('div[class="form-group field-zipcode"]').style.display = "none";
                document.querySelector('div[class="form-group field-state"]').style.display = "none";
                document.querySelector('div[class="form-group field-phone_number"]').style.display = "none";
                document.querySelector('div[class="form-group field-fax_number"]').style.display = "none";
                document.querySelector('div[class="form-group field-email"]').style.display = "none";
            }
            const id_is_auto_gen_pk_obj = document.getElementById("id_is_auto_gen_pk");
            id_is_auto_gen_pk_obj.checked = true;
            const reportingDoctorSelect = document.getElementById("id_reporting_doctor");
            if (reportingDoctorSelect) {
            reportingDoctorSelect.innerHTML = '';
            const optionElement = document.createElement('option');
            optionElement.value = "";
            optionElement.text = "Select";
            optionElement.selected = true;
            reportingDoctorSelect.appendChild(optionElement);
            }
        } else if (id_accession_id != null && id_accession_id != '') {
            document.getElementById("id_hidden_accession_template").value = document.getElementById("id_accession_template").value;
            document.getElementById("id_accession_template").disabled = true;
            populateAccessionTypeInfo();
            document.getElementById("id_case_id").readOnly = true;
            const id_is_auto_gen_pk_obj = document.getElementById("id_is_auto_gen_pk");
            document.getElementById("id_hidden_auto_gen_pk").value = document.getElementById("id_is_auto_gen_pk").checked;
            id_is_auto_gen_pk_obj.disabled = true;
            document.getElementById("id_hidden_accession_prefix").value = document.getElementById("id_accession_prefix").value;
            document.getElementById("id_accession_prefix").disabled = true;
            const id_payment_type_obj = document.querySelector('#id_payment_type');
            if (id_payment_type_obj){
                var id_payment_type = id_payment_type_obj.value;
                if (id_payment_type == 'Insurance') {
                    document.querySelector('div[class="form-group field-insurance_id"]').style.display = "block";
                    document.querySelector('div[class="form-group field-insurance_group"]').style.display = "block";
                    document.querySelector('div[class="form-group field-street_address"]').style.display = "none";
                    document.querySelector('div[class="form-group field-apt"]').style.display = "none";
                    document.querySelector('div[class="form-group field-city"]').style.display = "none";
                    document.querySelector('div[class="form-group field-zipcode"]').style.display = "none";
                    document.querySelector('div[class="form-group field-state"]').style.display = "none";
                    document.querySelector('div[class="form-group field-phone_number"]').style.display = "none";
                    document.querySelector('div[class="form-group field-fax_number"]').style.display = "none";
                    document.querySelector('div[class="form-group field-email"]').style.display = "none";

                }
                else {
                    document.querySelector('div[class="form-group field-insurance_id"]').style.display = "none";
                    document.querySelector('div[class="form-group field-insurance_group"]').style.display = "none";
                    document.querySelector('div[class="form-group field-street_address"]').style.display = "block";
                    document.querySelector('div[class="form-group field-apt"]').style.display = "block";
                    document.querySelector('div[class="form-group field-city"]').style.display = "block";
                    document.querySelector('div[class="form-group field-zipcode"]').style.display = "block";
                    document.querySelector('div[class="form-group field-state"]').style.display = "block";
                    document.querySelector('div[class="form-group field-phone_number"]').style.display = "block";
                    document.querySelector('div[class="form-group field-fax_number"]').style.display = "block";
                    document.querySelector('div[class="form-group field-email"]').style.display = "block";

                }
            }
            const urlParams = new URLSearchParams(window.location.search);
            const is_move_to_sample_creation_tab = urlParams.get('move_to_sample_creation_tab');
            const is_move_to_sample_tab = urlParams.get('move_to_sample_tab');
            if ("Y" == is_move_to_sample_creation_tab) {
                removeUrlParam("move_to_sample_creation_tab");
                if (window.location.hash) {
                    window.location.hash = '';
                }
                const tab = document.querySelector("[aria-controls=sample-creation-tab]");
                if (tab) {
                   tab.click();
                }
            }
            if ("Y" == is_move_to_sample_tab) {
                const tab = document.querySelector("[aria-controls=samples-tab]");
                if (tab) {
                   tab.click();
                }
                removeUrlParam("move_to_sample_tab");
            }

        }

    }
    function checkAndHideCreateSamples() {
        var activeTabText = $("#jazzy-tabs .nav-link.active").text().trim();
        if (activeTabText === "Sample Creation") {
            $("#create-more-samples").hide();
        } else {
            $("#create-more-samples").show();
        }
    }

    setTimeout(function() {
        checkAndHideCreateSamples();
    }, 100);

    $("#jazzy-tabs a").on("click", function () {
        var tabName = $(this).text().trim();
        if(document.getElementById("id_accession_id").value == '' && tabName == 'Sample Creation' && 'Y' != document.getElementById("id_is_create_samples").value){
            alert("Accession must be generated before Sample Creation. Click 'Next' on Payment Tab to generate Accession.");
            setTimeout(function () {
                $('#jazzy-tabs a').each(function () {
                    if ($(this).text().trim() == 'Payment') {
                        $(this).click();
                    }
                });
            }, 100);
        }
        setTimeout(function() {
            checkAndHideCreateSamples();
        }, 100);
    });
    document.getElementById('id_is_create_samples').value = '';

});

function populateInsuranceDetails() {
    const id_patient_id_obj = document.querySelector('#id_patient_id');
    const id_insurance_id_obj = document.querySelector('#id_insurance_id');
    var id_patient_id = id_patient_id_obj.value;
    var id_insurance_id = id_insurance_id_obj.value;
    if (typeof id_patient_id_obj == 'undefined' || id_patient_id_obj == null) {
        console.error('Patient Object cannot be obtained.');
        return;
    }
    var id_patient_id = id_patient_id_obj.value;
    populatePatientDetails();
    if (id_patient_id != null && id_patient_id != '' && id_patient_id != 'undefined') {
        inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_insurance_by_patient/';
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'patient_id': id_patient_id },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                id_insurance_id_obj.innerHTML = "<option value=''>Select</option>";
                for (var i = 0; i < data.length; i++) {
                    var optionElement = document.createElement('option');
                    optionElement.value = data[i].patientinfo_id;
                    optionElement.text = data[i].insurance + '-' + data[i].policy;
                    id_insurance_id_obj.appendChild(optionElement);
                }
                if (id_insurance_id && Array.from(id_insurance_id_obj.options).some(option => option.value === id_insurance_id)) {
                    id_insurance_id_obj.value = id_insurance_id;
                }
            },
            error: function (error) {
                console.error('Error fetching Insurance Details:', error);
            }
        });
    } else {
        id_insurance_id_obj.innerHTML = '';
        var optionElement = document.createElement('option');
        optionElement.value = '';
        optionElement.text = '------------';
        id_insurance_id_obj.appendChild(optionElement);
    }
}



function populatePaymentDetails() {
    const id_patient_id_obj = document.querySelector('#id_patient_id');
    if (typeof id_patient_id_obj != 'undefined' && id_patient_id_obj != null) {
        var id_patient_id = id_patient_id_obj.value;
        if (id_patient_id == null || id_patient_id == '' || id_patient_id == 'undefined') {
            alert("Please select patient");
            return;
        }
    }
    const id_payment_type_obj = document.querySelector('#id_payment_type');
    var id_payment_type = id_payment_type_obj.value;

    if (id_payment_type == 'Insurance') {
        document.querySelector('div[class="form-group field-insurance_id"]').style.display = "block";
        document.querySelector('div[class="form-group field-insurance_group"]').style.display = "block";
        document.querySelector('div[class="form-group field-street_address"]').style.display = "none";
        document.querySelector('div[class="form-group field-apt"]').style.display = "none";
        document.querySelector('div[class="form-group field-city"]').style.display = "none";
        document.querySelector('div[class="form-group field-zipcode"]').style.display = "none";
        document.querySelector('div[class="form-group field-state"]').style.display = "none";
        document.querySelector('div[class="form-group field-phone_number"]').style.display = "none";
        document.querySelector('div[class="form-group field-fax_number"]').style.display = "none";
        document.querySelector('div[class="form-group field-email"]').style.display = "none";

    }
    else {
        document.querySelector('div[class="form-group field-insurance_id"]').style.display = "none";
        document.querySelector('div[class="form-group field-insurance_group"]').style.display = "none";
        document.querySelector('div[class="form-group field-street_address"]').style.display = "block";
        document.querySelector('div[class="form-group field-apt"]').style.display = "block";
        document.querySelector('div[class="form-group field-city"]').style.display = "block";
        document.querySelector('div[class="form-group field-zipcode"]').style.display = "block";
        document.querySelector('div[class="form-group field-state"]').style.display = "block";
        document.querySelector('div[class="form-group field-phone_number"]').style.display = "block";
        document.querySelector('div[class="form-group field-fax_number"]').style.display = "block";
        document.querySelector('div[class="form-group field-email"]').style.display = "block";

    }
}

function populatePatientDetails() {
    const id_patient_id_obj = document.querySelector('#id_patient_id');
    if (typeof id_patient_id_obj != 'undefined' && id_patient_id_obj != null) {
        var id_patient_id = id_patient_id_obj.value;
        if (id_patient_id != null && id_patient_id != '' && id_patient_id != 'undefined') {
            inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_patient_details_by_patient/';
            $.ajax({
                url: inputURL,
                type: 'GET',
                data: { 'patient_id': id_patient_id },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    const id_street_address_obj = document.querySelector('#id_street_address');
                    if (id_street_address_obj != null && id_street_address_obj != 'undefined') {
                        id_street_address_obj.value = data[0].street_address;
                    }
                    const id_apt_obj = document.querySelector('#id_apt');
                    if (id_apt_obj != null && id_apt_obj != 'undefined') {
                        id_apt_obj.value = data[0].apt;
                    }
                    const id_city_obj = document.querySelector('#id_city');
                    if (id_city_obj != null && id_city_obj != 'undefined') {
                        id_city_obj.value = data[0].city;
                    }
                    const id_zipcode_obj = document.querySelector('#id_zipcode');
                    if (id_zipcode_obj != null && id_zipcode_obj != 'undefined') {
                        id_zipcode_obj.value = data[0].zipcode;
                    }
                    const id_state_obj = document.querySelector('#id_state');
                    if (id_state_obj != null && id_state_obj != 'undefined') {
                        id_state_obj.value = data[0].state;
                    }
                    const id_phone_number_obj = document.querySelector('#id_phone_number');
                    if (id_phone_number_obj != null && id_phone_number_obj != 'undefined') {
                        id_phone_number_obj.value = data[0].phone_number;
                    }
                    const id_fax_number_obj = document.querySelector('#id_fax_number');
                    if (id_fax_number_obj != null && id_fax_number_obj != 'undefined') {
                        id_fax_number_obj.value = data[0].fax_number;
                    }
                    const id_email_obj = document.querySelector('#id_email');
                    if (id_email_obj != null && id_email_obj != 'undefined') {
                        id_email_obj.value = data[0].email;
                    }
                },
                error: function (error) {
                    console.error('Error fetching Patient Details:', error);
                }
            });
        } else {
            const id_street_address_obj = document.querySelector('#id_street_address');
            if (id_street_address_obj != null && id_street_address_obj != 'undefined') {
                id_street_address_obj.value = '';
            }
            const id_apt_obj = document.querySelector('#id_apt');
            if (id_apt_obj != null && id_apt_obj != 'undefined') {
                id_apt_obj.value = '';
            }
            const id_city_obj = document.querySelector('#id_city');
            if (id_city_obj != null && id_city_obj != 'undefined') {
                id_city_obj.value = '';
            }
            const id_zipcode_obj = document.querySelector('#id_zipcode');
            if (id_zipcode_obj != null && id_zipcode_obj != 'undefined') {
                id_zipcode_obj.value = '';
            }
            const id_state_obj = document.querySelector('#id_state');
            if (id_state_obj != null && id_state_obj != 'undefined') {
                id_state_obj.value = '';
            }
            const id_phone_number_obj = document.querySelector('#id_phone_number');
            if (id_phone_number_obj != null && id_phone_number_obj != 'undefined') {
                id_phone_number_obj.value = '';
            }
            const id_fax_number_obj = document.querySelector('#id_fax_number');
            if (id_fax_number_obj != null && id_fax_number_obj != 'undefined') {
                id_fax_number_obj.value = '';
            }
            const id_email_obj = document.querySelector('#id_email');
            if (id_email_obj != null && id_email_obj != 'undefined') {
                id_email_obj.value = '';
            }
        }
    }
}


function populateInsuranceGroup() {
    const id_insurance_id_obj = document.querySelector('#id_insurance_id');
    if (typeof id_insurance_id_obj != 'undefined' && id_insurance_id_obj != null) {
        var id_insurance_id = id_insurance_id_obj.value;
        if (id_insurance_id != null && id_insurance_id != '' && id_insurance_id != 'undefined') {
            inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_insurance_details_by_insurance_id/';
            $.ajax({
                url: inputURL,
                type: 'GET',
                data: { 'insurance_id': id_insurance_id },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    const id_insurance_group_obj = document.querySelector('#id_insurance_group');
                    if (id_insurance_group_obj != null && id_insurance_group_obj != 'undefined') {
                        id_insurance_group_obj.value = data[0].group;
                    }

                },
                error: function (error) {
                    console.error('Error fetching Insurance Group:', error);
                }
            });
        } else {
            const id_insurance_group_obj = document.querySelector('#id_insurance_group');
            if (id_insurance_group_obj != null && id_insurance_group_obj != 'undefined') {
                id_insurance_group_obj.value = '';
            }

        }
    }
}

function checkuncheckautogenprimarykey(obj) {
    if (obj.checked) {
        document.getElementById("id_case_id").readOnly = true;
    } else {
        document.getElementById("id_case_id").readOnly = false;
    }
}
function populateClientDetails() {
    const id_client_id_obj = document.querySelector('#id_client_id');
    if (typeof id_client_id_obj != 'undefined' && id_client_id_obj != null) {
        var id_client_id = id_client_id_obj.value;
        if (id_client_id != null && id_client_id != '' && id_client_id != 'undefined') {
            inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_client_details_by_client/';
            $.ajax({
                url: inputURL,
                type: 'GET',
                data: { 'client_id': id_client_id },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    const id_client_address_line1_obj = document.querySelector('#id_client_address_line1');
                    if (id_client_address_line1_obj != null && id_client_address_line1_obj != 'undefined') {
                        id_client_address_line1_obj.value = data[0].address1;
                    }
                    const id_client_address_line2_obj = document.querySelector('#id_client_address_line2');
                    if (id_client_address_line2_obj != null && id_client_address_line2_obj != 'undefined') {
                        id_client_address_line2_obj.value = data[0].address2;
                    }
                    const id_client_city_obj = document.querySelector('#id_client_city');
                    if (id_client_city_obj != null && id_client_city_obj != 'undefined') {
                        id_client_city_obj.value = data[0].city;
                    }
                    const id_client_state_obj = document.querySelector('#id_client_state');
                    if (id_client_state_obj != null && id_client_state_obj != 'undefined') {
                        id_client_state_obj.value = data[0].state;
                    }
                    const id_client_postalcode_obj = document.querySelector('#id_client_postalcode');
                    if (id_client_postalcode_obj != null && id_client_postalcode_obj != 'undefined') {
                        id_client_postalcode_obj.value = data[0].postalcode;
                    }
                    const id_client_country_obj = document.querySelector('#id_client_country');
                    if (id_client_country_obj != null && id_client_country_obj != 'undefined') {
                        id_client_country_obj.value = data[0].country;
                    }
                    const id_client_phone_number_obj = document.querySelector('#id_client_phone_number');
                    if (id_client_phone_number_obj != null && id_client_phone_number_obj != 'undefined') {
                        id_client_phone_number_obj.value = data[0].telephone;
                    }
                    const id_client_fax_number_obj = document.querySelector('#id_client_fax_number');
                    if (id_client_fax_number_obj != null && id_client_fax_number_obj != 'undefined') {
                        id_client_fax_number_obj.value = data[0].fax_number;
                    }
                    const id_client_email_obj = document.querySelector('#id_client_email');
                    if (id_client_email_obj != null && id_client_email_obj != 'undefined') {
                        id_client_email_obj.value = data[0].primaryemail;
                    }
                },
                error: function (error) {
                    console.error('Error fetching Patient Details:', error);
                }
            });
        } else {
            const id_client_address_line1_obj = document.querySelector('#id_client_address_line1');
            if (id_client_address_line1_obj != null && id_client_address_line1_obj != 'undefined') {
                id_client_address_line1_obj.value = '';
            }
            const id_client_address_line2_obj = document.querySelector('#id_client_address_line2');
            if (id_client_address_line2_obj != null && id_client_address_line2_obj != 'undefined') {
                id_client_address_line2_obj.value = '';
            }
            const id_client_city_obj = document.querySelector('#id_client_city');
            if (id_client_city_obj != null && id_client_city_obj != 'undefined') {
                id_client_city_obj.value = '';
            }
            const id_client_state_obj = document.querySelector('#id_client_state');
            if (id_client_state_obj != null && id_client_state_obj != 'undefined') {
                id_client_state_obj.value = '';
            }
            const id_client_postalcode_obj = document.querySelector('#id_client_postalcode');
            if (id_client_postalcode_obj != null && id_client_postalcode_obj != 'undefined') {
                id_client_postalcode_obj.value = '';
            }
            const id_client_country_obj = document.querySelector('#id_client_country');
            if (id_client_country_obj != null && id_client_country_obj != 'undefined') {
                id_client_country_obj.value = '';
            }
            const id_client_phone_number_obj = document.querySelector('#id_client_phone_number');
            if (id_client_phone_number_obj != null && id_client_phone_number_obj != 'undefined') {
                id_client_phone_number_obj.value = '';
            }
            const id_client_fax_number_obj = document.querySelector('#id_client_fax_number');
            if (id_client_fax_number_obj != null && id_client_fax_number_obj != 'undefined') {
                id_client_fax_number_obj.value = '';
            }
            const id_client_email_obj = document.querySelector('#id_client_email');
            if (id_client_email_obj != null && id_client_email_obj != 'undefined') {
                id_client_email_obj.value = '';
            }
        }
    }
}
function updateContainerDropdown(id_sample_type_id_obj) {
    if (typeof id_sample_type_id_obj != 'undefined' && id_sample_type_id_obj != null) {
        var id_sample_type_id = id_sample_type_id_obj.value;
        if (id_sample_type_id != null && id_sample_type_id != '' && id_sample_type_id != 'undefined') {
            inputURL = window.location.protocol + "//" + window.location.host +
                '/accessioning/ajax/get_containertype_by_sampletype/';
            $.ajax({
                url: inputURL,
                type: 'GET',
                data: { 'sample_type_id': id_sample_type_id },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    const id_container_type_id_obj = document.getElementById("id_container_type");
                    if (id_container_type_id_obj != null && id_container_type_id_obj != 'undefined') {
                        var id_container_type_id = id_container_type_id_obj.value;
                        id_container_type_id_obj.innerHTML = "<option value=''>Select</option>";
                        for (var i = 0; i < data.length; i++) {
                            var optionElement = document.createElement('option');
                            optionElement.value = data[i].container_type_id;
                            optionElement.text = data[i].container_type;
                            id_container_type_id_obj.appendChild(optionElement);
                        }
                        if (id_container_type_id && Array.from(id_container_type_id_obj.options).some(option => option.value === id_container_type_id)) {
                            id_container_type_id_obj.value = id_container_type_id;
                        }
                    }
                },
                error: function (error) {
                    console.error('Error fetching Container Type Details:', error);
                }
            });

        }
        else {
            id_container_type_id_obj.innerHTML = '';
            var optionElement = document.createElement('option');
            optionElement.value = '';
            optionElement.text = '------------';
            id_container_type_id_obj.appendChild(optionElement);
        }

    }
}
function createSample() {
    var id_accession_id = document.getElementById("id_accession_id").value;
    if (id_accession_id == '') {
        alert("Please create Accession");
        return false;
    }
    var id_sample_type = document.getElementById("id_sample_type").value;
    if (id_sample_type == '') {
        alert("Please select Sample Type");
        return false;
    }
    var id_container_type = document.getElementById("id_container_type").value;
    if (id_container_type == '') {
        alert("Please select Container Type");
        return false;
    }
    var id_part_no = document.getElementById("id_part_no").value;
    var accession_cat = document.getElementById('id_accession_category').value;
    if ((id_part_no == null || id_part_no == '') && accession_cat != 'Clinical') {
        alert("Please provide Part No");
        return false;
    }

    var id_workflow = document.getElementById("id_workflow").value;

    var id_is_child_sample_creation = document.getElementById("id_is_child_sample_creation").value;
    var id_is_generate_parent_seq = document.getElementById("id_is_generate_parent_seq").value;
    var id_is_gen_slide_seq = document.getElementById("id_is_gen_slide_seq").value;
    if("true" != id_is_child_sample_creation && "Y" !=id_is_generate_parent_seq && "true" == id_is_gen_slide_seq) {
            var id_parent_seq = document.getElementById("id_parent_seq").value;
            if((id_parent_seq == null || id_parent_seq == '') && accession_cat != 'Clinical'){
                alert("Please select Block/Cassette No.");
                return false;

            }

   }
    var id_count = document.getElementById("id_count").value;
    if (id_count != null && id_count != '' && id_count != 'undefined') {
        if (id_count != '' && !isNaN(Number(id_count))) {
            const id_sample_type_id_obj = document.getElementById("id_sample_type");
            if (id_sample_type_id_obj.value == '') {
                alert("Please select Sample Type")
                return false;
            }
            const id_container_type_id_obj = document.getElementById("id_container_type");
            if (id_container_type_id_obj.value == '') {
                alert("Please select Container Type")
                return false;
            }
            var tests = document.getElementById("id_test_id").value;
            var is_generate_parent_seq = document.getElementById("id_is_generate_parent_seq").value;
            var parent_seq = document.getElementById("id_parent_seq").value;
            inputURL = window.location.protocol + "//" + window.location.host +
                '/accessioning/ajax/createSample/';
            disableBeforeUnloadWarning();
            $.ajax({
                url: inputURL,
                type: 'POST',
                data: { 'accession_id': id_accession_id, 'sample_type_id': id_sample_type_id_obj.value, 'container_type_id': id_container_type_id_obj.value, 'count': id_count, 'test_id': tests, 'part_no': id_part_no, 'is_child_sample_creation': id_is_child_sample_creation, 'is_generate_parent_seq': is_generate_parent_seq, 'parent_seq': parent_seq, 'workflow_id': id_workflow },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    var currurl = window.location.protocol + "//" + window.location.host + window.location.pathname;
                    if (currurl != '') {
                        var arrcururl = currurl.split("?");
                        if (arrcururl != null && arrcururl.length > 0) {
                            var newurl = arrcururl[0] + "?move_to_sample_tab=Y";
                            window.location.href = newurl;
                        }
                    }
                },
                error: function (error) {
                    if (error.responseJSON && error.responseJSON.message) {
                        alert(error.responseJSON.message);
                    } else {
                        alert("Error Creating Samples");
                    }
                    document.getElementById("id_associate_test").value="";
                    document.getElementById("id_test_id").value="";
                    return false;
                }
            });
        } else {
            alert('please enter a valid Number');
            document.getElementById("id_count").value = '';
            return false;
        }
    }
}

function removeUrlParam(param) {
    const url = new URL(window.location);
    url.searchParams.delete(param);
    history.replaceState(null, "", url);
}

function associateTest() {
    var accession_id = document.getElementById("id_accession_id").value;
    if (accession_id == null || accession_id == '') {
        alert("Please create Accession");
        return false;
    }
    var sample_type = document.getElementById("id_sample_type").value;
    if (sample_type == null || sample_type == '') {
        alert("Please select Sample Type");
        return false;
    }
    var container_type = document.getElementById("id_container_type").value;
    if (container_type == null || container_type == '') {
        alert("Please select Container Type");
        return false;
    }

    var url = window.location.protocol + "//" + window.location.host + "/gulfcoastpathologists/tests/test/?_popup=1";

    var screenWidth = window.screen.width;
    var screenHeight = window.screen.height;
    var popupWidth = 800;
    var popupHeight = 600;
    var left = (screenWidth - popupWidth) / 2;
    var top = (screenHeight - popupHeight) / 2;

    var popup = window.open(url, "lookupPopup", `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${top}`);

    if (popup) {
        popup.focus();
    } else {
        alert("Popup blocked! Please allow popups for this site.");
    }
}

function resetAssociateTest() {
                    document.getElementById('id_associate_test').value = '';
                    var hiddenField = document.getElementById('id_test_id');
                    if (hiddenField) hiddenField.value = '';
                }

window.addEventListener("message", function (event) {
    if (event.data) {
        var associate_test = document.getElementById("id_associate_test");
        var test = document.getElementById("id_test_id");
        if (associate_test) {
            if (associate_test.value != null && associate_test.value != '') {
                associate_test.value = associate_test.value + ", " + event.data.map(item => `${item[0]}`).join(", ");
            } else {
                associate_test.value = event.data.map(item => `${item[0]}`).join(", ");
            }
        }
        if (test) {
            if (test.value != null && test.value != '') {
                test.value = test.value + "|" + event.data.map(item => `${item[1]}`).join("|");
            } else {
                test.value = event.data.map(item => `${item[1]}`).join("|");
            }
        }
        document.getElementById("id_count").focus();
    }
});

function updatedeletetest() {
    var accession_id = document.getElementById("id_accession_id").value;
    if (accession_id == null || accession_id == '') {
        alert("Please create Accession");
        return false;
    }
    var url = window.location.protocol + "//" + window.location.host + "/gulfcoastpathologists/sample/sampletestmap/?_popup=1&sample_id__accession_id__exact=" + accession_id;
    var screenWidth = window.screen.width;
    var screenHeight = window.screen.height;
    var popupWidth = 800;
    var popupHeight = 600;
    var left = (screenWidth - popupWidth) / 2;
    var top = (screenHeight - popupHeight) / 2;
    var popup = window.open(url, "lookupPopup", `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${top}`);
    if (popup) {
        popup.focus();
    } else {
        alert("Popup blocked! Please allow popups for this site.");
    }
}

function adddeletetest() {
    var accession_id = document.getElementById("id_accession_id").value;
    if (accession_id == null || accession_id == '') {
        alert("Please create Accession");
        return false;
    }
    var url = window.location.protocol + "//" + window.location.host + "/gulfcoastpathologists/sample/sample/?_popup=1&accession_id__exact=" + accession_id;
    var screenWidth = window.screen.width;
    var screenHeight = window.screen.height;
    var popupWidth = 800;
    var popupHeight = 600;
    var left = (screenWidth - popupWidth) / 2;
    var top = (screenHeight - popupHeight) / 2;
    var popup = window.open(url, "lookupPopup", `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${top}`);
    if (popup) {
        popup.focus();
    } else {
        alert("Popup blocked! Please allow popups for this site.");
    }
}

function moveToPrevTab(objname) {
    if(objname=='reporting-doctor-tab'){
        reporting_type = document.getElementById("id_reporting_type").value
        if(reporting_type==null || reporting_type==''){
            objname = "client-tab";
        }
    }
    var elmnt = document.querySelector("[aria-controls=" + objname + "]");
    elmnt.click();
}

function moveToNextTab(objname) {
    const accessionCategory = document.getElementById("id_accession_category").value;
    if(objname=='reporting-doctor-tab'){
        reporting_type = document.getElementById("id_reporting_type").value
        if(reporting_type==null || reporting_type==''){
            if (accessionCategory !== 'Pharma') {
                objname = "payment-tab";
            }
        }
    }
    var elmnt = document.querySelector("[aria-controls=" + objname + "]");
    if (objname == 'sample-creation-tab') {
        let isCreateSamplesField = document.querySelector("input[name='is_create_samples']");
        if (isCreateSamplesField) {
            isCreateSamplesField.value = 'Y';
        }
        elmnt.click();
        let form = document.querySelector("form");
        disableBeforeUnloadWarning();
        form.submit();
    } else {
        elmnt.click();
    }
}

function populateDoctorsBasedOnClient() {
    populateClientDetails();
    populateDoctors();

}
function populateDoctors() {
    const id_doctor_obj = document.getElementById("id_doctor");
    var id_doctor_id = '';
    if (typeof id_doctor_obj != 'undefined' && id_doctor_obj != null) {
        id_doctor_id = id_doctor_obj.value;
    }

    var id_client_id = document.getElementById("id_client_id").value;
    if (id_client_id == null || id_client_id == '') {
        return false;
    }
    let inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_doctors_by_client/';
    $.ajax({
        url: inputURL,
        type: 'GET',
        data: { 'id_client_id': id_client_id },
        dataType: 'json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        success: function (data) {
            if (typeof id_doctor_obj != 'undefined' && id_doctor_obj != null) {
                id_doctor_obj.innerHTML = "<option value=''>Select</option>";
                for (var i = 0; i < data.length; i++) {
                    var optionElement = document.createElement('option');
                    optionElement.value = data[i].physician_id;
                    optionElement.text = data[i].first_name + ' ' + data[i].last_name;
                    id_doctor_obj.appendChild(optionElement);
                }
                if (id_doctor_id && Array.from(id_doctor_obj.options).some(option => option.value === id_doctor_id)) {
                    id_doctor_obj.value = id_doctor_id;
                }
            }
        },
        error: function (error) {
            console.error('Error fetching Doctor Details:', error);
        }

    });

}

function updateaccessionprefix() {
    var status = document.getElementById("id_status").value;
    if (status != "Initial") {
        alert("This Operation Is Allowed Only When the Status is Initial.");
        return false;
    }
    const userConfirmed = confirm("This is for updating Accession Prefix. Do you want to continue?");
    if (!userConfirmed) {
        return false;
    }
    else {
        document.querySelector("[aria-controls='accession-info-tab']").click();
        document.getElementById("id_previous_accession").value = document.getElementById("id_accession_id").value;
        document.getElementById("id_isupdate_accession_prefix").value = 'Y';
        document.getElementById("id_accession_prefix").disabled = false;
        document.getElementById("id_is_auto_gen_pk").disabled = false;
        document.getElementById("id_case_id").value = '';
    }
}



//update description on changing ICD Code Id
function updateICDDetails(element) {
    var id_icd_code_id = element.value;
    if (id_icd_code_id != null && id_icd_code_id != '' && id_icd_code_id != 'undefined') {
        inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_details_by_icdcode/';
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'icd_code_id': id_icd_code_id },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                var nameAttr = $(element).attr('name');
                var match = nameAttr.match(/-(\d+)-/);
                if (match) {
                    var index = match[1];
                    var id_description = 'id_accessionicdcodemap_set-' + index + '-description';
                    document.getElementById(id_description).value = data[0].description;

                }
            },
            error: function () {
                alert('Error retrieving ICD Code details.');
            }
        });
    }
    else {
        var nameAttr = $(element).attr('name');
        var match = nameAttr.match(/-(\d+)-/);
        if (match) {
            var index = match[1];
            var id_description = 'id_accessionicdcodemap_set-' + index + '-description';
            document.getElementById(id_description).value = '';

        }
    }
}


//create more samples
function createMoreSamples() {
    document.querySelector("[aria-controls=sample-creation-tab]").click();

}

//update container details on changing containter_type
function populateContainerDetails(id_container_type_id_obj) {
    if (typeof id_container_type_id_obj !== 'undefined' && id_container_type_id_obj !== null) {
        const parent_seq = document.getElementById("id_parent_seq");
        if (parent_seq) {
            let opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "Select";
            parent_seq.innerHTML = "";
            parent_seq.appendChild(opt);
            parent_seq.disabled = true;
        }

        document.getElementById("id_part_no").value = '';

        var id_container_type_id = id_container_type_id_obj.value;
        if (id_container_type_id) {
            const inputURL = window.location.protocol + "//" + window.location.host +
                '/accessioning/ajax/get_containerdetails_by_containertype/';
            $.ajax({
                url: inputURL,
                type: 'GET',
                data: { 'id_container_type_id': id_container_type_id },
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                success: function (data) {
                    const id_is_child_sample_creation_obj = document.getElementById("id_is_child_sample_creation");
                    const id_is_gen_slide_seq_obj = document.getElementById("id_is_gen_slide_seq");
                    const workflowDropdown = document.getElementById("id_workflow");

                    if (data) {
                        if (id_is_child_sample_creation_obj) id_is_child_sample_creation_obj.value = data.is_child_sample_creation || "";
                        if (id_is_gen_slide_seq_obj) id_is_gen_slide_seq_obj.value = data.is_gen_slide_seq || "";

                        if (workflowDropdown) {
                            const workflowVal = String(data.workflow_id || "");
                            const optionExists = Array.from(workflowDropdown.options).some(opt => opt.value === workflowVal);

                            if (optionExists && workflowVal) {
                                workflowDropdown.value = workflowVal;
                                workflowDropdown.dispatchEvent(new Event('change'));
                            } else {
                                setTimeout(() => {
                                    const delayedOptionExists = Array.from(workflowDropdown.options).some(opt => opt.value === workflowVal);
                                    if (delayedOptionExists && workflowVal) {
                                        workflowDropdown.value = workflowVal;
                                        workflowDropdown.dispatchEvent(new Event('change'));
                                    } else {
                                        workflowDropdown.value = "";
                                    }
                                }, 500);
                            }
                        }
                    } else {
                        if (id_is_child_sample_creation_obj) id_is_child_sample_creation_obj.value = "";
                        if (id_is_gen_slide_seq_obj) id_is_gen_slide_seq_obj.value = "";
                        if (workflowDropdown) workflowDropdown.value = "";
                    }
                },
                error: function (error) {
                    console.error('Error fetching Container Type Details:', error);
                }
            });
        } else {

            const id_is_child_sample_creation_obj = document.getElementById("id_is_child_sample_creation");
            if (id_is_child_sample_creation_obj) {
                id_is_child_sample_creation_obj.value = "";
            }
        }
    }
}


// Function to validate and convert part_no to uppercase
function validatePartNoInput(event) {
    const inputField = event.target;
    const charCode = event.which || event.keyCode;
    if ((charCode >= 65 && charCode <= 90) || (charCode >= 97 && charCode <= 122)) {
        setTimeout(() => {
            inputField.value = inputField.value.toUpperCase();
        }, 0);
    } else {
        alert("Only alphabetic characters (A-Z) are allowed.");
        inputField.value = "";
        return false;
    }
}

function onchangePartNo(){
    const part_no = document.getElementById("id_part_no").value;
    const is_child_sample_creation = document.getElementById("id_is_child_sample_creation").value;
    const parent_seq = document.getElementById("id_parent_seq");
    const is_generate_parent_seq = document.getElementById("id_is_generate_parent_seq");
    const accession_id = document.getElementById("id_accession_id").value;
    const is_gen_slide_seq = document.getElementById("id_is_gen_slide_seq").value;

    if (part_no!='' && is_child_sample_creation != "true" && is_gen_slide_seq == "true") {
        let inputURL = window.location.protocol + "//" + window.location.host + "/accessioning/ajax/get_parent_seq/";
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { part_no: part_no, accession_id: accession_id },
            dataType: 'json',
            success: function (data) {
                 if (data.parent_seq_options.length > 0) {
                    let confirmMessage = "Do you want to register the sample against the existing Block/Cassette No.?";
                    if (window.confirm(confirmMessage)) {
                        parent_seq.style.display = "block";
                        parent_seq.disabled = false;
                        parent_seq.innerHTML = "";
                        let opt = document.createElement("option");
                        opt.value = "";
                        opt.textContent = "Select";
                        parent_seq.appendChild(opt);
                        data.parent_seq_options.forEach(option => {
                            let opt = document.createElement("option");
                            opt.value = option.value;
                            opt.textContent = option.label;
                            parent_seq.appendChild(opt);
                        });
                    } else {
                        is_generate_parent_seq.value = "Y";
                        let opt = document.createElement("option");
                        opt.value = "";
                        opt.textContent = "Select";
                        parent_seq.innerHTML = opt;
                        parent_seq.disabled = true;
                    }
                } else {
                    is_generate_parent_seq.value = "Y";
                    let opt = document.createElement("option");
                    opt.value = "";
                    opt.textContent = "Select";
                    parent_seq.innerHTML = opt;
                    parent_seq.disabled = true;
                }
            },
            error: function (xhr, status, error) {
               console.error('Error fetching Block/Cassette No.:', error);
               console.error('Status:', status);
               console.error('Response:', xhr.responseText);
            }
        });
    }
}

//var accession_cat = document.getElementById("id_accession_category").value;
var accessionCatElem = document.getElementById("id_accession_category");
var accession_cat = accessionCatElem ? accessionCatElem.value : null;

function onChangeAccessionCategory(){
    const accession_id = document.getElementById("id_accession_id").value;
    if(accession_id != '' && accession_id != null){
        let inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_samples_created/';
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'accession_id': accession_id },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                if(data.samples_count > 0){
                    alert("Accession Category cannot be changed after Samples are created.");
                    disableBeforeUnloadWarning();
                    window.location.reload();
                    return;
                }else{
                    accession_cat = document.getElementById("id_accession_category").value;
                }
            },
            error: function (error) {
                console.error('Error fetching Doctor Details:', error);
            }
        });
    }

    const accession_category = document.getElementById("id_accession_category").value;
    let shouldHide = accession_category === 'Clinical';
    document.querySelectorAll('td.field-block_or_cassette_seq, td.field-slide_seq')
            .forEach(field => field.style.display = shouldHide ? "none" : "");
    document.querySelectorAll('th.column-block_or_cassette_seq, th.column-slide_seq')
        .forEach(header => header.style.display = shouldHide ? "none" : "");
    document.querySelector('div[class="form-group field-parent_seq"]').style.display = shouldHide ? "none" : "";
    document.querySelector('div[class="form-group field-part_no"]').style.display = shouldHide ? "none" : "";
}

//convert partno into uppercase
function convertToUppercase(el) {
    el.value = el.value.toUpperCase();
}


// populate reporting_type on change accession_type
function populateAccessionTypeInfo() {
    const accessionCategory = document.getElementById("id_accession_category").value;
    if (accessionCategory === 'Pharma') {
        return;
    }
    const id_accession_type_obj = document.getElementById('id_accession_type');
    var id_accession_type = id_accession_type_obj.value;

    if (typeof id_accession_type_obj === 'undefined' || id_accession_type_obj === null) {
        console.error('Accession Type Object cannot be obtained.');
        return;
    }

    if (id_accession_type != null && id_accession_type !== '' && id_accession_type !== 'undefined') {
        inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_reportingtype_by_accessiontype/';

        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'accession_type': id_accession_type },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                if (data.length > 0) {
                    const reporting_type = data[0].reporting_type;
                    const id_reporting_type_obj = document.getElementById("id_reporting_type");

                    if (id_reporting_type_obj) {
                        id_reporting_type_obj.value = reporting_type;
                    }

                    if ("internal" === reporting_type) {
                        populateInternalReportingDoctors();
                        var elmnt = document.querySelector("[aria-controls=reporting-doctor-tab]");
                        elmnt.style.display='block';
                    } else if ("external" === reporting_type) {
                        populateExternalReportingDoctors();
                        var elmnt = document.querySelector("[aria-controls=reporting-doctor-tab]");
                        elmnt.style.display='block';
                    } else {
                        const reportingDoctorSelect = document.getElementById("id_reporting_doctor");
                        if (reportingDoctorSelect) {
                            reportingDoctorSelect.innerHTML = ''; // clear all options
                            const optionElement = document.createElement('option');
                            optionElement.value = "";
                            optionElement.text = "Select";
                            optionElement.selected = true;
                            reportingDoctorSelect.appendChild(optionElement);
                        }
                        var elmnt = document.querySelector("[aria-controls=reporting-doctor-tab]");
                        elmnt.style.display='none';

                    }
                }
            },
            error: function (error) {
                console.error('Error fetching Reporting Type Details:', error);
            }
        });
    } else {
        // If no accession type is selected, clear the reporting type field
        const id_reporting_type_obj = document.querySelector('#id_reporting_type');
        if (id_reporting_type_obj) {
            id_reporting_type_obj.value = '';
        }
    }
}


//function to populate internal doctors when reporting type is internal
function populateInternalReportingDoctors() {
    const id_reporting_doctor_obj = document.getElementById("id_reporting_doctor");
    var id_reporting_doctor_id = '';
    if (typeof id_reporting_doctor_obj != 'undefined' && id_reporting_doctor_obj != null) {
        id_reporting_doctor_id = id_reporting_doctor_obj.value;
    }
    inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_internal_external_doctors/';
    $.ajax({
        url: inputURL,
        type: 'GET',
        data: { 'is_external': 'N' },
        dataType: 'json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        success: function (data) {
            if (typeof id_reporting_doctor_obj != 'undefined' && id_reporting_doctor_obj != null) {
                id_reporting_doctor_obj.innerHTML = '';
                for (var i = 0; i < data.length; i++) {
                    var optionElement = document.createElement('option');
                    optionElement.value = data[i].physician_id;
                    optionElement.text = data[i].first_name + ' ' + data[i].last_name;
                    id_reporting_doctor_obj.appendChild(optionElement);
                }
                if (id_reporting_doctor_id && Array.from(id_reporting_doctor_obj.options).some(option => option.value === id_reporting_doctor_id)) {
                    id_reporting_doctor_obj.value = id_reporting_doctor_id;
                }

            }

        },
        error: function (error) {
            console.error('Error fetching Doctor Details:', error);
        }
    });


}


//function to populate external doctors when reporting type is external
function populateExternalReportingDoctors() {
    const id_reporting_doctor_obj = document.getElementById("id_reporting_doctor");
    var id_reporting_doctor_id = '';
    if (typeof id_reporting_doctor_obj != 'undefined' && id_reporting_doctor_obj != null) {
        id_reporting_doctor_id = id_reporting_doctor_obj.value;
    }
    inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_internal_external_doctors/';
    $.ajax({
        url: inputURL,
        type: 'GET',
        data: { 'is_external': 'Y' },
        dataType: 'json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        success: function (data) {
            if (typeof id_reporting_doctor_obj != 'undefined' && id_reporting_doctor_obj != null) {
                id_reporting_doctor_obj.innerHTML = '';
                for (var i = 0; i < data.length; i++) {
                    var optionElement = document.createElement('option');
                    optionElement.value = data[i].physician_id;
                    optionElement.text = data[i].first_name + ' ' + data[i].last_name;
                    id_reporting_doctor_obj.appendChild(optionElement);
                }
                if (id_reporting_doctor_id && Array.from(id_reporting_doctor_obj.options).some(option => option.value === id_reporting_doctor_id)) {
                    id_reporting_doctor_obj.value = id_reporting_doctor_id;
                }
            }
        },
        error: function (error) {
            console.error('Error fetching Doctor Details:', error);
        }

    });
}

function printLabels(){
    const totalForms = parseInt(document.getElementById(`id_AccessionID-TOTAL_FORMS`).value);
    ids = '';
    for (let i = 0; i < totalForms; i++) {
        const pkField = document.getElementById(`id_AccessionID-${i}-sample_id`);
        if (pkField && pkField.value) {
            ids = ids == '' ? pkField.value : ids + ',' + pkField.value;
        }
    }
    if(ids != ''){
        var baseUrl = '/gulfcoastpathologists/sample/sample/print-label-prompt/';
        var printerCategory = 'Accessioning';
        const url = window.location.protocol + "//" + window.location.host + `${baseUrl}?ids=${ids}&printercategory=${encodeURIComponent(printerCategory)}`;

        const popupWidth = 1000;
        const popupHeight = 700;

        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;

        const left = Math.floor((screenWidth - popupWidth) / 2);
        const topPos = Math.floor((screenHeight - popupHeight) / 2);

        window.open(url, '_blank', `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${topPos}`);
    }else{
        alert('Accession has no Samples. Cannot Print Labels');
    }
}

function populateSubSite(el) {
    const bodySiteSelect = el;
    const row = el.closest('tr');
    const subSiteSelect = row.querySelector('select[id$="-sub_site"]');

    if (!bodySiteSelect || !subSiteSelect) {
        console.error('Cannot find Body Site or Sub Site dropdown.');
        return;
    }

    const bodySiteValue = bodySiteSelect.value;

    if (bodySiteValue && bodySiteValue !== 'undefined') {
        const inputURL = window.location.protocol + "//" + window.location.host + '/masterdata/ajax/get-sub-sites/';

        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'body_site': bodySiteValue },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (response) {
                // Clear previous options
                subSiteSelect.innerHTML = "<option value=''>Select Sub Site</option>";

                // Add new options
                response.sub_sites.forEach(function(item) {
                    const option = document.createElement('option');
                    option.value = item.id;
                    option.text = item.text;
                    subSiteSelect.appendChild(option);
                });

                // Refresh Select2 UI
                $(subSiteSelect).trigger('change.select2');
            },
            error: function (error) {
                console.error('Error fetching Sub Site details:', error);
            }
        });
    } else {
        subSiteSelect.innerHTML = "<option value=''>------------</option>";
        $(subSiteSelect).trigger('change.select2');
    }
}

/*
* Populate the tests based on the selected bodysite
*/
function populateRelatedTest(el) {
    const bodySiteSelect = el;
    const row = el.closest('tr');
    const testIdElement = row.querySelector('[id$="-test_id"]');
    const testCodeElement = row.querySelector('[id$="-test_code"]');
    const sampleIdElement = row.querySelector('[id$="-sample_id"]');
    const childSampleCreationIdElement = row.querySelector('[id$="-child_sample_creation"]');

    if(!sampleIdElement){
        alert("Sample ID not found");
        return;
    }

    if (!bodySiteSelect || !testIdElement || !testCodeElement) {
        alert('Cannot find Body Site or Test Id or Test Name');
        return;
    }

    const bodySiteValue = bodySiteSelect.value;
    const sampleIdValue = sampleIdElement ? sampleIdElement.value : null;
    const childSampleCreationIdValue = childSampleCreationIdElement ? childSampleCreationIdElement.value : null;

    if (bodySiteValue && bodySiteValue != 'undefined' && sampleIdValue!=null && childSampleCreationIdValue!=null) {
        const inputURL = window.location.protocol + "//" + window.location.host +
            '/masterdata/ajax/get_tests_based_on_bodysite_and_sample/';

        $.ajax({
            url: inputURL,
            type: 'GET',
            data: {
                'body_site': bodySiteValue,
                'sample_id': sampleIdValue,
                'child_sample_creation': childSampleCreationIdValue
            },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (response) {
                if(response.iserror!=null && response.iserror=="Y" && response.errormsg!=null && response.errormsg!=""){
                    alert(response.errormsg);
                }else{
                    // Build unique test list
                    let testIdSet = new Set();
                    let testNameSet = new Set();

                    response.tests.forEach(function(item) {
                        testIdSet.add(item.test_id);
                        testNameSet.add(item.test_name);
                    });

                    // Convert sets to comma-separated strings
                    let str_test_id = Array.from(testIdSet).join(",");
                    let str_test_name = Array.from(testNameSet).join(",");

                    // Assign fresh (no old append)
                    testIdElement.value = str_test_id;
                    testCodeElement.value = str_test_name;
                }
            },
            error: function (error) {
               console.error('Error fetching Test details:', error);


                const realSelect = bodySiteSelect.tagName === "SELECT"
                    ? bodySiteSelect
                    : bodySiteSelect.querySelector("select");

                if (realSelect) {
                    // Reset dropdown to "Select an Option"
                    realSelect.value = "";
                    realSelect.selectedIndex = 0;
                    $(realSelect).trigger('change');
                }

                // Clear the dependent test fields
                if (testIdElement) testIdElement.value = "";
                if (testCodeElement) testCodeElement.value = "";

                alert("Some tests for the selected Body Site are not available for this Project. Please reselect a valid Body Site.");

            }
        });
    }
}

function populateSponsorDetails() {
    const sponsorId = $(this).val();

    const nameField = $('#id_sponsor_name');
    const numberField = $('#id_sponsor_number');
    const descField = $('#id_sponsor_description');
    const addressField = $('#id_sponsor_address_info');

    if (!sponsorId) {
        nameField.val('');
        numberField.val('');
        descField.val('');
        addressField.val('');
        return;
    }

    const inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/get_sponsor_details_by_sponsor/';

    $.ajax({
        url: inputURL,
        type: 'GET',
        data: { 'sponsor_id': sponsorId },
        dataType: 'json',
        success: function (data) {
            nameField.val(data.sponsor_name || '');
            numberField.val(data.sponsor_number || '');
            descField.val(data.sponsor_description || '');
            addressField.val(data.sponsor_address_info || '');
        },
        error: function (error) {
            console.error('Error fetching Sponsor Details:', error);
            nameField.val('');
            numberField.val('');
            descField.val('');
            addressField.val('');
        }
    });
}

function sponsorChanged(element) {
    populateSponsorDetails.call(element);
    const sponsorId = element.value;
    const projectSelect = $('#id_project');

    projectSelect.empty().append('<option value="">---------</option>').trigger('change');

    if (sponsorId) {
        $.ajax({
            url: '/accessioning/ajax/get_projects_by_sponsor/',
            data: { 'sponsor_id': sponsorId },
            success: function(data) {
                $.each(data, function(key, value) {
                    projectSelect.append($('<option>', {
                        value: value.bioproject_id,
                        text: value.project_protocol_id
                    }));
                });
                if (initialProject) {
                    projectSelect.val(initialProject).trigger('change');
                }
            }
        });
    }
}

function applyFieldVisibility(settings) {
    for (const fieldName in settings) {
        const fieldRow = $(`.field-${fieldName}`);

        if (settings[fieldName]) {
            fieldRow.show();
        } else {
            fieldRow.hide();
        }
    }
}

function applySampleColumnVisibility(settings) {
    const inlineContainerSelector = '#AccessionID-group';

    $(inlineContainerSelector).find('th[class*="column-"], td[class*="field-"]').show();

    if (settings) {
        for (const fieldName in settings) {
            if (!settings[fieldName]) {
                const columnHeaderSelector = `${inlineContainerSelector} .column-${fieldName}`;
                const columnCellSelector = `${inlineContainerSelector} .field-${fieldName}`;

                $(columnHeaderSelector).hide();
                $(columnCellSelector).hide();
            }
        }
    }
}

function projectChanged(element) {
    const projectId = element.value;
    const visitSelect = $('#id_visit');
    const investigatorSelect = $('#id_investigator');
    const reportingDoctorSelect = $('#id_reporting_doctor');

    visitSelect.empty().append('<option value="">---------</option>').trigger('change');
    investigatorSelect.empty().append('<option value="">---------</option>').trigger('change');
    reportingDoctorSelect.empty().append('<option value="">---------</option>');

    if (projectId) {

        const restoreInitialValues = (projectId === initialProject);
        $.ajax({
            url: '/accessioning/ajax/get_physicians_by_project/',
            data: { 'project_id': projectId },
            success: function(data) {
                reportingDoctorSelect.empty().append('<option value="">---------</option>');
                //const initialDoctor = reportingDoctorSelect.val(); // Remember current selection before clearing
                //reportingDoctorSelect.empty().append('<option value="">---------</option>');

                $.each(data, function(key, value) {
                    reportingDoctorSelect.append($('<option>', {
                        value: value.physician_id,
                        text: `${value.first_name} ${value.last_name}`
                    }));
                });

                // Re-select the initial doctor if it's still a valid choice
                if (restoreInitialValues && initialReportingDoctor) {
                    reportingDoctorSelect.val(initialReportingDoctor);
                }
            }
        });

        $.ajax({
            url: '/accessioning/ajax/get_project_field_demographics/',
            data: { 'project_id': projectId },
            success: function(data) {
                applyFieldVisibility(data.ACCESSION || {});
                applySampleColumnVisibility(data.SAMPLE || {});
            }
        });

        $.ajax({
            url: '/accessioning/ajax/get_visits_by_project/',
            data: { 'project_id': projectId },
            success: function(data) {
                $.each(data, function(key, value) {
                    visitSelect.append($('<option>', {
                        value: value.pk,
                        text: value.visit_id
                    }));
                });
                if (initialVisit) {
                    visitSelect.val(initialVisit);
                }
            }
        });

        $.ajax({
            url: '/accessioning/ajax/get_investigators_by_project/',
            data: { 'project_id': projectId },
            success: function(data) {
                $.each(data, function(key, value) {
                    investigatorSelect.append($('<option>', {
                        value: value.pk,
                        text: value.investigator_name
                    }));
                });
                if (initialInvestigator) {
                    investigatorSelect.val(initialInvestigator);
                }
            }
        });
    } else {
        applyFieldVisibility(null);
        applySampleColumnVisibility(null);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Delay init to let Django Admin finish rendering
    setTimeout(initializeChangeTracking, 500);

    // Bind jQuery-based listeners for <select> and Select2 after init
    setTimeout(function(){
        jQuery('body').on('change', 'select', function() {
            markDirty();
            console.log('Native select change detected:', this.id||this.name);
        });
        jQuery('body').on('select2:select select2:unselect select2:clear', 'select', function() {
            markDirty();
            console.log('Select2 change detected:', this.id||this.name);
        });
    }, 600);
});

let hasUnsavedChanges = false;
let beforeUnloadHandler = null;

// Mark the form dirty and enable warning
function markDirty() {
    hasUnsavedChanges = true;
    enableBeforeUnloadWarning();
}

// Reset dirty and disable warning
function resetDirty() {
    hasUnsavedChanges = false;
    disableBeforeUnloadWarning();
}

// Install beforeunload handler
function enableBeforeUnloadWarning() {
    if (beforeUnloadHandler) return;
    beforeUnloadHandler = function(e) {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    };
    window.addEventListener('beforeunload', beforeUnloadHandler);
}

// Remove beforeunload handler
function disableBeforeUnloadWarning() {
    if (!beforeUnloadHandler) return;
    window.removeEventListener('beforeunload', beforeUnloadHandler);
    beforeUnloadHandler = null;
}

function initializeChangeTracking() {
    console.log('Initializing unsaved‐changes tracking…');
    captureInlineCounts();

    // Delegate input and change events
    document.body.addEventListener('input', onAnyFieldChange, true);
    document.body.addEventListener('change', onAnyFieldChange, true);

    // Delegate inline add/delete
    document.body.addEventListener('click', onPotentialInlineAdd, true);
    document.body.addEventListener('change', onPotentialInlineDelete, true);

    // Reset on form submit (save) — disable warning before saving
    document.querySelectorAll('form').forEach(f => {
        f.addEventListener('submit', function() {
            disableBeforeUnloadWarning();
            console.log('Form submitted, warning disabled');
        });
    });

    // Guard Generate Accession button
    const gen = document.getElementById('btn-generate-accession');
    if (gen) {
        gen.addEventListener('click', function(e) {
            if (hasUnsavedChanges) {
                alert('Unsaved changes exist. Please save before generating the accession.');
                e.preventDefault();
            }
        });
    }

    console.log('Tracking initialized');
}

const inlineCounts = {};
function captureInlineCounts() {
    document.querySelectorAll('input[name$="-TOTAL_FORMS"]').forEach(input => {
        inlineCounts[input.name] = parseInt(input.value,10) || 0;
    });
}

function onAnyFieldChange(e) {
    const t = e.target, tag = (t.tagName||'').toLowerCase();
    if (tag==='input' || tag==='textarea' || tag==='select') {
        markDirty();
    }
}

function onPotentialInlineAdd(e) {
    if (e.target.matches('.add-row a, .addlink')) {
        setTimeout(() => {
            markDirty();
            console.log('Inline row added');
        }, 50);
    }
}

function onPotentialInlineDelete(e) {
    if (e.target.name && e.target.name.match(/-DELETE$/)) {
        markDirty();
        console.log('Inline row marked for deletion');
    }
}

// Keyboard shortcuts
window.addEventListener('keydown', function(e) {
    // Ctrl+Enter -> Generate Accession
    if (e.ctrlKey && e.key==='Enter') {
        e.preventDefault();
        if (hasUnsavedChanges) {
            alert('Unsaved changes exist. Please save before generating the accession.');
            return;
        }
        const btn = document.getElementById('btn-generate-accession');
        if (btn) btn.click();
    }
    // Ctrl+Space -> Create More Samples
    if (e.ctrlKey && (e.key===' '||e.code==='Space')) {
        e.preventDefault();
        const btn = document.getElementById('create-more-samples');
        if (btn) btn.click();
    }
    // Ctrl+S -> Save form (disable warning before save)
    if (e.ctrlKey && (e.key==='s'||e.key==='S')) {
        e.preventDefault();
        disableBeforeUnloadWarning();
        const form = document.querySelector('form');
        if (form) form.submit();
    }
});


// ==============================================
// CONFIG
// ==============================================

//const WS_NOTIFY_URL = "ws://127.0.0.1:8001/ws/notify/admin/";
const WS_NOTIFY_URL = "ws://ec2-3-85-112-56.compute-1.amazonaws.com:8001/gulfcoastpathologists/ws/notify/admin/";
//const WS_NOTIFY_URL = "ws://127.0.0.1:8001/gulfcoastpathologists/ws/notify/admin/";

const START_SCAN_API = "/api/start-scan";
//const START_SCAN_API = "/gulfcoastpathologists/api/start-scan";


// ==============================================
// 1. Connect WebSocket (Admin Notification)
// ==============================================

let notifySocket = null;

function connectNotifySocket() {
    notifySocket = new WebSocket(WS_NOTIFY_URL);

    notifySocket.onopen = () => {
        console.log("Notify WebSocket connected.");
    };

    notifySocket.onclose = () => {
        console.warn("Notify socket closed. Retrying in 3s...");
        setTimeout(connectNotifySocket, 3000);
    };

    notifySocket.onerror = (err) => {
        console.error("Notify WS Error:", err);
    };

    notifySocket.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.action === "scan_completed") {
            if (data.error) {
                alert("Scan failed: " + data.error);
                return;
            }

            console.log("Scan completed:", data);

            // Show preview image
            document.getElementById("preview").src = data.file_url;

            // Show modal
            if (document.getElementById("scanPreviewModal"))
                document.getElementById("scanPreviewModal").style.display = "block";

            if (document.getElementById("modalOverlay"))
                document.getElementById("modalOverlay").style.display = "block";

            alert("Scan completed successfully.");
        }
    };
}

connectNotifySocket();
/*
 * Scan and Upload file
*/
function scanandupload(){
    startScan();
}

async function startScan() {
    try {
        const response = await fetch(START_SCAN_API, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                agent_id: "agent1"   // — change if you want multiple agents
            })
        });

        if (!response.ok) {
            throw new Error("Server failed to trigger scan.");
        }

        const data = await response.json();
        console.log("Scan request sent:", data);

        alert("Scan started. Waiting for scanner...");
    }
    catch (err) {
        alert("Error starting scan: " + err.message);
    }
}

// Close modal function
function closeModal() {
    document.getElementById("scanPreviewModal").style.display = "none";
    document.getElementById("modalOverlay").style.display = "none";
}

// Upload function placeholder
async function uploadScan() {
    try {
        const previewImg = document.getElementById("preview");

        // If no image is displayed, stop here
        if (!previewImg.src) {
            alert("No image to upload!");
            return;
        }

        // Fetch the displayed image from the <img> tag and convert it to a blob
        const response = await fetch(previewImg.src);
        const blob = await response.blob();
        const accession_id = document.getElementById("id_accession_id").value;

        // Prepare a FormData object for upload
        const formData = new FormData();
        formData.append("file", blob, "scanned_document.png");
        formData.append("accession_id", accession_id);

        // Send to backend (Flask endpoint)
        const inputURL = window.location.protocol + "//" + window.location.host + '/accessioning/ajax/upload_scanned_images/';
        $.ajax({
            url: inputURL,
            type: "POST",
            data: formData,
            processData: false,      // important: don’t convert FormData to string
            contentType: false,      // important: let browser set Content-Type
            headers: {
                'X-CSRFToken': getCSRFToken() // Django CSRF protection
            },
            success: function(response) {
                alert("✅ Uploaded Successfully!");
                console.log("Upload successful:", response);
                // Close the modal after upload
                closeModal();
                window.location.reload();
            },
            error: function(xhr, status, error) {
                alert("❌ Upload failed: ");
                console.error("Upload failed:", error);
                console.error("Response:", xhr.responseText);
            }
        });
    } catch (error) {
        console.error("Upload error:", error);
        alert("❌ Upload failed: " + error);
    }
}
