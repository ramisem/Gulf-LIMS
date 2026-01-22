$(document).ready(function () {
    setTimeout(function () {
        $('select[name^="testwfstpconsumablemap_set-"][name$="-sample_type_id"]').not('[name*="__prefix__"]').each(function () {
            updateContainerType($(this), true);
        });

        $('.field-workflow_id select').each(function () {
            updateStepDropdown($(this), true);
        });

        $('.field-workflow_step_id select').each(function () {
            updateStepNoField($(this), true);
        });
    }, 0);

    $('.field-workflow_step_id select').each(function () {
        const $dropdown = $(this);
        const selectedValue = $dropdown.val();
        if (selectedValue) {
            $dropdown.attr('data-selected-value', selectedValue);
        }
    });

    function updateContainerType($sampleTypeDropDown, isPageLoad = false) {
        const selectSampleType = $sampleTypeDropDown.val();
        const $row = $sampleTypeDropDown.closest('.dynamic-testwfstpconsumablemap_set');
        const $containerDropDown = $row.find('.field-container_type select');
        const selectedContainerId = isPageLoad ? $containerDropDown.val() : null;

        if (isPageLoad) {
            $containerDropDown.find('option').not(`[value="${selectedContainerId}"]`).remove();
        } else {
            $containerDropDown.empty().append('<option value="">---------</option>');
        }

        if ($containerDropDown.find('option[value=""]').length === 0) {
            $containerDropDown.prepend('<option value="">---------</option>');
        }


        if (selectSampleType) {
            const inputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-container-type-id/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'sampletype_id': selectSampleType },
                success: function (data) {

                    if (Array.isArray(data) && data.length > 0) {
                        data.forEach(item => {
                            console.log(item);
                            if (item.value !== selectedContainerId) {
                                $containerDropDown.append(
                                    `<option value="${item.value}" ${selectedContainerId == item.value ? 'selected' : ''}>${item.label}</option>`
                                );
                            }
                        });
                    } else {
                        console.warn("No container types found.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching container types:", error);
                }
            });
        }
    }

    function updateStepDropdown($workflowDropdown, isPageLoad = false) {
        const workflowId = $workflowDropdown.val();
        const $row = $workflowDropdown.closest('.dynamic-testwfstpconsumablemap_set');
        const $stepDropdown = $row.find('.field-workflow_step_id select');
        const selectedStepId = isPageLoad ? $stepDropdown.data('selected-value') : null;

        $stepDropdown.empty().append('<option value="">---------</option>');

        if (workflowId) {
            const inputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-steps/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'workflow_id': workflowId },
                success: function (data) {
                    if (Array.isArray(data) && data.length > 0) {
                        data.forEach(item => {
                            $stepDropdown.append(`<option value="${item.workflow_step_id}" ${item.workflow_step_id == selectedStepId ? 'selected' : ''}>${item.step_id}</option>`);
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

    function updateStepNoField($stepIdDropdown, isPageLoad = false) {
        const selectedStepId = $stepIdDropdown.val();
        const $row = $stepIdDropdown.closest('.dynamic-testwfstpconsumablemap_set');
        const $stepNoField = $row.find('.field-step_no .readonly');
        const $workFlowTypeField = $row.find('.field-workflow_type .readonly');

        if (!isPageLoad && (!selectedStepId || selectedStepId === '--------')) {
            $stepNoField.text('');
            $workFlowTypeField.text('');
            return;
        }

        if (selectedStepId) {
            const inputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-step-no/`;
            $.ajax({
                url: inputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'step_id': selectedStepId },
                success: function (data) {
                    if (data && data.length > 0) {
                        $stepNoField.text(data[0].step_no);
                    } else {
                        console.error("No step_no received in the response.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching step_no:", error);
                }
            });
            const WorkflowTypeInputURL = `${window.location.protocol}//${window.location.host}/tests/ajax/get-workflow-type/`;
            $.ajax({
                url: WorkflowTypeInputURL,
                type: 'GET',
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
                data: { 'step_id': selectedStepId },
                success: function (data) {
                    if (data && data.length > 0) {
                        $workFlowTypeField.text(data[0].workflow_type);
                    } else {
                        console.error("No Workflow Type received in the response.");
                    }
                },
                error: function (xhr, status, error) {
                    console.error("Error fetching Workflow_type:", error);
                }
            });
        }
    }

    function setStepNoFieldBlank($workflowDropdown, isPageLoad = false) {
        const workflowId = $workflowDropdown.val();
        const $row = $workflowDropdown.closest('.dynamic-testwfstpconsumablemap_set');
        const $stepDropdown = $row.find('.field-workflow_step_id select');
        const selectedStepId = isPageLoad ? $stepDropdown.data('selected-value') : null;
        const $stepNoField = $row.find('.field-step_no .readonly');
        const $workflowTypeField = $row.find('.field-workflow_type .readonly');
        if (!isPageLoad && (!selectedStepId || selectedStepId === '--------')) {
            $stepNoField.text('');
            $workflowTypeField.text('');
            return;
        }
    }


    $(document).on('click', '#test-workflow-step-consumables-tab .add-row a', function () {
        setTimeout(function () {
            const $lastRow = $('#test-workflow-step-consumables-tab .dynamic-testwfstpconsumablemap_set.last-related').last();
            $lastRow.find('.field-workflow_step_id select')
                .empty()
                .append('<option value="">---------</option>');
        }, 0);
    });

    $(document).on('change', '.field-workflow_id select', function () {
        updateStepDropdown($(this));
        setStepNoFieldBlank($(this));
    });

    $(document).on('change', '.field-workflow_step_id select', function () {
        updateStepNoField($(this));
    });

    $(document).on('change', '.field-sample_type_id select', function () {
        updateContainerType($(this));
    });
});