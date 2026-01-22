window.onload = function () {
    const bioproject_id_obj = document.getElementById("id_bioproject_id");
    if (typeof bioproject_id_obj != 'undefined' && bioproject_id_obj != null) {
        var bioproject = bioproject_id_obj.value;
        if(bioproject==null || bioproject==''){
            bioproject_id_obj.innerHTML = '';
            const optionElement = document.createElement('option');
            optionElement.value = "";
            optionElement.text = "Select";
            optionElement.selected = true;
            bioproject_id_obj.appendChild(optionElement);
        }else{
            onSponsorChange();
        }
    }
};
/*
On changing the Spopnsor, Project(s) should be populated
*/
function onSponsorChange(){
    const sponsor_id = document.getElementById("id_sponsor_id").value;
    const bioproject_id = document.getElementById("id_bioproject_id").value;
    if(sponsor_id!=null && sponsor_id!=""){
        const inputURL = window.location.protocol + "//" + window.location.host + '/masterdata/ajax/get_projects_by_sponsor/';

        $.ajax({
            url: inputURL,
            type: "GET",
            data: {
                sponsor_id: sponsor_id,
            },
            success: function (data) {
                if(data){
                    if(data.length==0){
                        alert("No Projects available");
                        return
                    }else{
                        const id_bioproject_id = document.getElementById("id_bioproject_id");
                        if (typeof id_bioproject_id != 'undefined' && id_bioproject_id != null) {
                            id_bioproject_id.innerHTML = '';
                            var optionElement = document.createElement('option');
                            optionElement.value = '';
                            optionElement.text = 'Select';
                            id_bioproject_id.appendChild(optionElement);

                            for (var i = 0; i < data.length; i++) {
                                var optionElement = document.createElement('option');
                                optionElement.value = data[i].bioproject_id;
                                optionElement.text = data[i].project_protocol_id;
                                id_bioproject_id.appendChild(optionElement);
                            }

                            if (id_bioproject_id && Array.from(id_bioproject_id.options).some(option => option.value === bioproject_id)) {
                                id_bioproject_id.value = bioproject_id;
                            }

                        }
                    }
                }
            },
            error: function () {
                alert('Unable to retrieve BioPharma Project(s)');
                return
            }
        });
    }
}