document.addEventListener("DOMContentLoaded", function () {
    $('#test-attributes-tab .field-test_workflow_step_id select').each(function () {
        const $dropdown = $(this);
        const selectedValue = $dropdown.val();
        if (selectedValue) {
            $dropdown.attr('data-selected-value', selectedValue);
        }
    });

    const testIdField = document.getElementById("id_testattribute_set-__prefix__-test_id");
    console.log(testIdField.value);

    function updateWorkflowStepOptions($twsDropdown, isPageLoad = false) {
        $twsDropdown.empty().append('<option value="">---------</option>');
        const selectedStepId = isPageLoad ? $twsDropdown.data('selected-value') : null;
        const testId = testIdField.value;

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
                            $twsDropdown.append(`<option value="${step.test_workflow_step_id}" ${step.test_workflow_step_id == selectedStepId ? 'selected' : ''}>${step.workflow_id__workflow_name + " - "
                                + step.sample_type_id__sample_type + " - "
                                + step.container_type__container_type + " - "
                                + step.workflow_step_id__step_id
                                }</option>`);
                        });
                    }
                    else {
                        $twsDropdown.empty().append('<option value="">---------</option>');
                        return;
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching steps:", error);
                }
            })
        }
    }

    $('#test-attributes-tab .field-test_workflow_step_id select').each(function () {
        updateWorkflowStepOptions($(this), true);
    });

    $(document).on('click', '#test-attributes-tab .add-row a', function () {
        setTimeout(function () {
            if (!testIdField) {
                const $lastRow = $('#test-attributes-tab .dynamic-testattribute_set.last-related').last();
                $lastRow.find('.field-test_workflow_step_id select')
                    .empty()
                    .append('<option value="">---------</option>');
            } else {
                const lastRow = $('#test-attributes-tab .dynamic-testattribute_set.last-related').last();
                updateWorkflowStepOptions(lastRow.find('#test-attributes-tab .field-test_workflow_step_id select'), true);

            }

        }, 0);
    });
});
