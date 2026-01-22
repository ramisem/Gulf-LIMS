function previewreport() {
   reportoption_id = document.getElementById("id_hidden_reportoption_id").value;
   window.open('/analysis/report_preview/?reportoption_id=' + reportoption_id, '_self');
}
function reportsignout() {
    document.getElementById("esigModal").style.display = "block";
    document.getElementById("modalOverlay").style.display = "block";
}

function cancelSignout(){
    document.getElementById("esigModal").style.display = "none";
    document.getElementById("modalOverlay").style.display = "none";
}

function confirmSignout(){
    const username = $('#username').val();
    const password = $('#password').val();
     inputURL = window.location.protocol + "//" + window.location.host + '/security/ajax/ajax_authenticate_user/'
    $.ajax({
        url: inputURL,
        type: 'POST',
        data: {
            username: username,
            password: password
        },
        success: function(response) {
            if (response.success) {
                const urlParams = new URLSearchParams(window.location.search);
                const reportoption_id = urlParams.get('reportoption_id');
                if (reportoption_id!=null && reportoption_id!="") {
                    const url = `/analysis/report_signout/?reportoption_id=${reportoption_id}`;
                    window.open(url, '_self');
                }
            } else {
                alert(response.message);
            }
        },
        error: function() {
            alert("An error occurred during authentication.");
        }
    });
}
function backToReportEdit() {
    const urlParams = new URLSearchParams(window.location.search);
    const reportoption_id = urlParams.get('reportoption_id');
    if (reportoption_id) {
        const url = `/gulfcoastpathologists/analysis/reportoption/${reportoption_id}/change/`;
        window.open(url, '_self');
    } else {
        alert("Report Option ID is missing.");
    }
}
function backToReportEditFromSignout() {
    const urlParams = new URLSearchParams(window.location.search);
    const reportoption_id = urlParams.get('reportoption_id');
    if (reportoption_id) {
        const url = `/gulfcoastpathologists/analysis/historicalreportoption/${reportoption_id}/change/`;
        window.open(url, '_self');
    } else {
        alert("Report Option ID is missing.");
    }
}