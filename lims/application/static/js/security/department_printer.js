$(document).ready(function () {
    function updatePrinterPath($selectElement) {
    const printerid = $selectElement.val();
    const $row = $selectElement.closest('.dynamic-departmentprinter_set');
    const $printerPathField = $row.find('.field-printer_path');

    if (printerid) {
        console.log(printerid);
        const inputURL = `${window.location.protocol}//${window.location.host}/security/ajax/get_printer_path/`;
        //const inputURL = "ajax/get_printer_path/";
        $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'printer_id': printerid },
                success: function (data) {
                    if (data && data.length > 0) {
                        console.log("Fetched Some Data" + data[0].printer_path);
                        $printerPathField.text(data[0].printer_path);
                    } else {
                        console.error("No step_no received in the response.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching steps:", error);
                }
            });
    }


    }

    $(document).on("change", '.field-printer_id select', function () {
        updatePrinterPath($(this));
    });

});
