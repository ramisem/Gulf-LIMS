(function waitForJQuery() {
    if (typeof django !== "undefined" && typeof django.jQuery !== "undefined") {
        var $ = django.jQuery; // Use Django's jQuery

        $(document).ready(function() {
            var s3bucket = $("#id_s3bucket");
            var apiDriven = $("#id_api_driven");
            var exportLocation = $("#id_export_location");

            function toggleExportLocation(clearValue = true) {
                if (apiDriven.is(":checked")) {
                    exportLocation.prop("readonly", true);
                    exportLocation.css("background-color", "#e9ecef"); // Grey out field
                    if (clearValue) {
                        exportLocation.val(""); // Clear only when triggered by change event
                    }
                } else {
                    exportLocation.prop("readonly", false);
                    exportLocation.css("background-color", ""); // Reset background color
                }
            }

            // Handle change on s3bucket
            s3bucket.change(function() {
                if ($(this).is(":checked")) {
                    apiDriven.prop("checked", false).trigger("change"); // Uncheck api_driven
                }
            });

            // Handle change on apiDriven
            apiDriven.change(function() {
                if ($(this).is(":checked")) {
                    s3bucket.prop("checked", false);
                }
                toggleExportLocation(true); // Clear value on change
            });

            // Run once on page load to ensure correct state but without clearing the value
            toggleExportLocation(false);
        });
    } else {
        setTimeout(waitForJQuery, 100); // Retry until jQuery is available
    }
})();
