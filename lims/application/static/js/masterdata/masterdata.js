function updatePhysicianDetails(element) {
    var id_physician_id = element.value;
    if (id_physician_id != null && id_physician_id != '' && id_physician_id != 'undefined') {
        inputURL = window.location.protocol + "//" + window.location.host + '/masterdata/ajax/get_physician_details_by_physician/';
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'physician_id': id_physician_id },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                var nameAttr = $(element).attr('name');
                var match = nameAttr.match(/-(\d+)-/);
                if(match){
                    var index = match[1];
                    var id_phone_number = 'id_clientdoctorinfo_set-' + index + '-phone_number';
                    document.getElementById(id_phone_number).value = data[0].phone_number;
                    var id_fax_number = 'id_clientdoctorinfo_set-' + index + '-fax_number';
                    document.getElementById(id_fax_number).value = data[0].fax_number;
                    var id_email = 'id_clientdoctorinfo_set-' + index + '-email';
                    document.getElementById(id_email).value = data[0].email;
                }
            },
            error: function () {
                alert('Error retrieving physician details.');
            }
        });
    }
    else {
        var nameAttr = $(element).attr('name');
        var match = nameAttr.match(/-(\d+)-/);
        if(match){
            var index = match[1];
            var id_phone_number = 'id_clientdoctorinfo_set-' + index + '-phone_number';
            document.getElementById(id_phone_number).value = '';
            var id_fax_number = 'id_clientdoctorinfo_set-' + index + '-fax_number';
            document.getElementById(id_fax_number).value = '';
            var id_email = 'id_clientdoctorinfo_set-' + index + '-email';
            document.getElementById(id_email).value = '';
        }
    }
}

//  Helper function for CSRF token
function getCSRFToken() {
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}
