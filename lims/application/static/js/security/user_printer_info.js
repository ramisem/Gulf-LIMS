$(document).ready(function () {
    function updatePrinterDropdown($selectElement) {
        const jobtype = $selectElement.val();
        const printerPathField = $('.field-printer_id select');
        printerPathField.empty().append('<option value="">---------</option>');
        
        if(jobtype != null || jobtype != ''){
            const inputURL = `${window.location.protocol}//${window.location.host}/security/ajax/get_printers_by_jobtype/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: {
                        jobtype_id: jobtype
                    },
                success: function(data) {
                        $.each(data, function(printerId, printerName) {
                            printerPathField.append('<option value="' + printerId + '">' + printerName + '</option>');
                        });
                        printerPathField.trigger('change.select2');
                    },
                error: function (xhr, status, error) {
                    console.error("Error fetching data:", error);
                    }
                });
        }
    }

    $(document).on("change", '.field-jobtype_id select', function () {
        updatePrinterDropdown($(this));
    });

});
