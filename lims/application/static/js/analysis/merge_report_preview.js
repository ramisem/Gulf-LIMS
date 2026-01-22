function previewreport() {
    merge_reporting_id = document.getElementById("id_hidden_merge_reporting_id").value;
    window.open('/analysis/merge_report_preview/?merge_reporting_id=' + merge_reporting_id, '_self');
 }
 function previewreportforamendment() {
    merge_reporting_id = document.getElementById("id_hidden_merge_reporting_id").value;
    window.open('/analysis/merge_report_preview_for_amendment/?merge_reporting_id=' + merge_reporting_id, '_self');
 }
 function reportsignout() {
     console.log("reportsignout CALLED from:", new Error().stack);
     document.getElementById("esigModal").style.display = "block";
     document.getElementById("modalOverlay").style.display = "block";
 }

 function amendReport(){
     const inputURL = `${window.location.origin}/analysis/get_amendment_types/`;
     $.ajax({
         url: inputURL,
         type: 'GET',
         dataType: 'json',
         success: function (data) {
             const select = document.getElementById("amendmentTypeSelect");
             select.innerHTML = "";

             if (!data.amendment_types || data.amendment_types.length === 0) {
                 alert("No amendment types available.");
                 return;
             }

             const opt = document.createElement("option");
                 opt.value = "";
                 opt.textContent = "Select";
                 select.appendChild(opt);

             data.amendment_types.forEach(item => {
                 const opt = document.createElement("option");
                 opt.value = item.value;
                 opt.textContent = item.display_value;
                 select.appendChild(opt);
             });

             document.getElementById("esigModal").style.display = "block";
             document.getElementById("modalOverlay").style.display = "block";
         },
         error: function (error) {
             console.error('Error fetching Amendment Types:', error);
         }
     });
 }

 function cancelSignout(){
     document.getElementById("esigModal").style.display = "none";
     document.getElementById("modalOverlay").style.display = "none";
 }

 function confirmSignout(){
     const username = $('#username').val();
     const password = $('#password').val();

     if (!password) {
         alert("Please enter your password.");
         return;
     }

     const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
     $('#confirmsignout').prop('disabled', true);

     const inputURL = window.location.protocol + "//" + window.location.host + '/security/ajax/ajax_authenticate_user/';

     $.ajax({
         url: inputURL,
         type: 'POST',
         headers: {
             'X-CSRFToken': csrfToken
         },
         data: {
             username: username,
             password: password
         },
         success: function(response) {
             if (response.success) {
                 const urlParams = new URLSearchParams(window.location.search);
                 const merge_reporting_id = urlParams.get('merge_reporting_id');
                 if (merge_reporting_id != null && merge_reporting_id !== "") {
                     const url = `/analysis/merge_report_signout/?merge_reporting_id=${merge_reporting_id}`;
                     window.open(url, '_self');

                 }
             } else {
                 alert(response.message);
             }
         },
         error: function() {
             alert("An error occurred during authentication.");
         },
         complete: function () {
             $('#confirmsignout').prop('disabled', false);
         }
     });
 }
//
function confirmAmendReportSignOut() {
    const username = $('#username').val();
    const password = $('#password').val();
    const amendment_type = $('#amendmentTypeSelect').val();

    const amendment_comments = $('#macroContentEditor').summernote('code');

    if (!password || !amendment_type) {
        alert("Please enter your password and select amendment type.");
        return;
    }

    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
    $('#confirmsignout').prop('disabled', true);

    const inputURL =
        window.location.protocol + "//" + window.location.host +
        '/security/ajax/ajax_authenticate_user/';

    $.ajax({
        url: inputURL,
        type: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        data: { username: username, password: password },

        success: function (response) {
            if (response.success) {

                const urlParams = new URLSearchParams(window.location.search);
                const merge_reporting_id = urlParams.get('merge_reporting_id');

                if (merge_reporting_id) {

                    const url =
                        window.location.protocol + "//" + window.location.host +
                        `/analysis/merge_report_signout_view_for_amendment/?merge_reporting_id=${merge_reporting_id}&amendment_type=${encodeURIComponent(amendment_type)}`;

                    // build the form
                    const form = document.createElement("form");
                    form.method = "POST";
                    form.action = url;

                    // comments
                    const commentsInput = document.createElement("input");
                    commentsInput.type = "hidden";
                    commentsInput.name = "amendment_comments";
                    commentsInput.value = amendment_comments;

                    form.appendChild(commentsInput);

                    document.body.appendChild(form);
                    form.submit();
                }
            }
            else {
                alert(response.message);
            }
        },
        error: function () {
            alert("An error occurred during authentication.");
        },
        complete: function () {
            $('#confirmsignout').prop('disabled', false);
        }
    });
}

 function backToReportEdit() {
     const urlParams = new URLSearchParams(window.location.search);
     const merge_reporting_id = urlParams.get('merge_reporting_id');
     if (merge_reporting_id) {
         const url = `/gulfcoastpathologists/analysis/mergereporting/${merge_reporting_id}/change/`;
         window.open(url, '_self');
     } else {
         alert("Merge Reporting ID is missing.");
     }
 }
 function backToReportEditFromSignout() {
     const urlParams = new URLSearchParams(window.location.search);
     const merge_reporting_id = urlParams.get('merge_reporting_id');
     if (merge_reporting_id) {
         const url = `/gulfcoastpathologists/analysis/historicalmergereporting/${merge_reporting_id}/change/`;
         window.open(url, '_self');
     } else {
         alert("Merge Reporting ID is missing.");
     }
 }
 function populate_macros(){
    var amendmentType = document.getElementById("amendmentTypeSelect").value;
    if(amendmentType==null || amendmentType==""){
        alert("Please select Amendment Type");
        return false;
    }

    const inputURL = `${window.location.origin}/analysis/get_macros/`;
     $.ajax({
         url: inputURL,
         type: 'GET',
         dataType: 'json',
         data: {
             amendmenttype: amendmentType,
         },
         success: function (data) {
             const select = document.getElementById("macroSelect");
             select.innerHTML = "";

             if (!data.macros || data.macros.length === 0) {
                 alert("No macros available.");
                 return;
             }

             const opt = document.createElement("option");
                 opt.value = "";
                 opt.textContent = "Select";
                 select.appendChild(opt);

             data.macros.forEach(item => {
                 const opt = document.createElement("option");
                 opt.value = item.macros_id;
                 opt.textContent = item.macros_name;
                 select.appendChild(opt);
             });

             document.getElementById("esigModal").style.display = "block";
             document.getElementById("modalOverlay").style.display = "block";
         },
         error: function (error) {
             console.error('Error fetching Amendment Types:', error);
         }
     });
 }

 function populateMacroContent(){
    var macro = document.getElementById("macroSelect").value;
    if(macro==null || macro==""){
        alert("Please select Macro");
        return false;
    }
    const inputURL = `${window.location.origin}/analysis/get_macro_content/`;
     $.ajax({
         url: inputURL,
         type: 'GET',
         dataType: 'json',
         data: {
             macro: macro,
         },
         success: function (data) {
             if (data.success && data.content) {
                $("#macroContentEditor").summernote('code', data.content);
             } else {
                $("#macroContentEditor").summernote('reset');
             }

             document.getElementById("esigModal").style.display = "block";
             document.getElementById("modalOverlay").style.display = "block";
         },
         error: function (error) {
             console.error('Error fetching Amendment Types:', error);
         }
     });
 }