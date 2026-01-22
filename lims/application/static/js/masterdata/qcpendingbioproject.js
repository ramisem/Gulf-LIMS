/*
    This section handles the Perform QC modal open/close
*/
function openQCModal() {
    document.getElementById("performQCModal").style.display = "block";
    document.getElementById("modalOverlay").style.display = "block";
}

function cancelpopup() {
    document.getElementById("performQCModal").style.display = "none";
    document.getElementById("modalOverlay").style.display = "none";
    //Clear QC Reason and Password when cancel is clicked
    document.getElementById("qcReason").value = "";
    document.getElementById("qcPassword").value = "";
}

function performQC() {
    const bioproject_id = document.getElementById("id_bioproject_id").value;
    if (!bioproject_id) {
        alert("Project ID not found.");
        return;
    }

    const status = document.getElementById("qcStatus").value;
    const reason = document.getElementById("qcReason").value;
    const username = document.getElementById("qcUsername").value;
    const password = document.getElementById("qcPassword").value;

    if (status === "Fail" && !reason) {
        alert("Please provide a reason when QC status is Fail.");
        return;
    }
    //  Validate password
    if (!password) {
        alert("Please enter your password.");
        return;
    }

    const inputURL = window.location.protocol + "//" + window.location.host + '/masterdata/ajax/ajax_perform_qc/';
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    $('#confirmQC').prop('disabled', true);

    $.ajax({
        url: inputURL,
        type: 'POST',
        data: {
            bioproject_id: bioproject_id,
            qc_status: status,
            qc_reason: reason,
            username: username,
            password: password,
            csrfmiddlewaretoken: csrfToken
        },
        success: function(response) {
            if (response.status === 'success') {
                alert('QC performed successfully!');
                window.location.href = "/gulfcoastpathologists/masterdata/qcpendingbioproject/";
            } else {
                alert(response.message);
            }
        },
        error: function(xhr, status, error) {
            console.error("AJAX Error:", status, error);
            console.error("Response Text:", xhr.responseText);
            alert("Error occurred while performing QC: " + xhr.status + " " + error);
},
        complete: function() {
            $('#confirmQC').prop('disabled', false);
        }
    });
}
