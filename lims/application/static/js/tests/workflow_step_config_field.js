$(document).ready(function () {
    $('.field-field_id select').each(function () {
        const $dropdown = $(this);
        const selectedValue = $dropdown.val(); // Get the current value of the dropdown
        if (selectedValue) {
            $dropdown.attr('data-selected-value', selectedValue); // Set it as a data attribute
        }
    });

    function updateStepDropdown($selectedDropdown, isPageLoad = false) {
        const testId = $selectedDropdown.val();
        console.log("Selected Test ID:", testId);

        const $stepDropdown = $("#id_test_workflow_step_id");  // Corrected jQuery usage
        const selectedStepId = isPageLoad ? $stepDropdown.attr('data-selected-value') : null;

        $stepDropdown.empty().append('<option value="">---------</option>');

        if (testId) {
            const inputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-test-workflow-steps/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'test_id': testId },
                success: function (data) {
                    if (Array.isArray(data) && data.length > 0) {
                        data.forEach(step => {
                            //                            $stepDropdown.append(`<option value="${item.workflow_step_id}" ${item.workflow_step_id == selectedStepId ? 'selected' : ''}>${item.step_id}</option>`);
                            $stepDropdown.append(`<option value="${step.test_workflow_step_id}" ${step.test_workflow_step_id == selectedStepId ? 'selected' : ''}>${step.workflow_id__workflow_name + " - "
                                + step.workflow_step_id__step_id + " - "
                                + step.sample_type_id__sample_type}</option>`);
                        });
                    } else {
                        console.error("Expected 'options' to be an array.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching steps:", error);
                }
            });
        }
    }

    function updateColumnDropdown(modelDropdown, isPageLoad = false) {
        const model = modelDropdown.val();
        const row = modelDropdown.closest('.dynamic-workflowstepconfigfield_set');
        const columnDropdown = row.find('.field-field_id select');
        const selectedColumn = isPageLoad ? columnDropdown.data('selected-value') : null;

        columnDropdown.empty().append('<option value="">---------</option>');

        if (model) {
            const inputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-model-fields/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'model': model },
                success: function (data) {
                    console.log(data);
                    if (data.field_choices) {
                        console.log(data.field_choices);

                        $.each(data.field_choices, function (index, choice) {
                            console.log(choice)
                            columnDropdown.append(`<option value="${choice.value}" ${choice.value == selectedColumn ? 'selected' : ''}>${choice.display}</option>`);
                        });


                    } else {
                        console.error("Expected 'options' to be an array.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching steps:", error);
                }
            });
        }
    }

    // Trigger update on page load
    $(window).on("load", '#id_test_id', function () {
        console.log("Dropdown on load:", $(this).val());
        updateStepDropdown($(this), true);
    });

    $(document).on('change', '#id_test_id', function () {
        console.log("Dropdown changed:", $(this).val());
        updateStepDropdown($(this));
    });

    $(window).on("load", function () {
        $('.field-model select').each(function () {
            console.log("Dropdown on load:", $(this).val());
            updateColumnDropdown($(this), true);
        });
    });

    $(document).on('change', '.field-model select', function () {
        console.log("Dropdown changed:", $(this).val());
        updateColumnDropdown($(this));
    });

    $(document).on('click', '#workflow-step-config-fields-tab .add-row a', function () {
        setTimeout(function () {
            const $lastRow = $('#workflow-step-config-fields-tab .dynamic-workflowstepconfigfield_set.last-related').last();
            $lastRow.find('.field-field_id select')
                .empty()
                .append('<option value="">---------</option>');
        }, 0);
    });

});
