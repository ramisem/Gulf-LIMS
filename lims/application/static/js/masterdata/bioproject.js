/*
    This function is for pushing projects to qc
*/
document.addEventListener("DOMContentLoaded", function() {
    const button = document.getElementById("push-to-qc")
    button.addEventListener("click", function (e) {
        e.preventDefault();
        const bioproject_id = document.getElementById("id_bioproject_id").value;
        const modification_notes = document.getElementById("id_modification_notes").value;

        if (!bioproject_id) {
            alert("Project ID not found.");
            return;
        }

        if(modification_notes==null || modification_notes==''){
            document.getElementById("id_modification_notes").focus();
            alert("Please provide Modification Notes");
            return false;
        }

        const inputURL = window.location.protocol + "//" + window.location.host + '/masterdata/ajax/push_to_qc/';

        //  Make AJAX call
        $.ajax({
            url: inputURL,
            type: "POST",
            data: {
                project_id: bioproject_id,
                csrfmiddlewaretoken: getCSRFToken()
            },
            success: function (response) {
                if (response.status === 'success') {
                    alert('Project pushed to QC successfully!');
                } else {
                    alert('Failed: ' + response.message);
                }
            },
            error: function () {
                alert('Error occurred while pushing to QC.');
            }
        });
    });
});

