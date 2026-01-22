document.addEventListener('DOMContentLoaded', function () {
    setTimeout(() => {
        const actionForm = document.querySelector('#changelist-form');
        const actionSelect = document.querySelector('select[name="action"]');
        const selectedCheckboxes = () => Array.from(document.querySelectorAll('input.action-select:checked'));

        if (!actionForm || !actionSelect) {
            console.log('Could not find action form or action select');
            return;
        }

        actionForm.addEventListener('submit', function (e) {
            const selectedAction = actionSelect.value;

            // Handle both 'generate_report' and 'amend_report' actions
            if (selectedAction === 'generate_report' || selectedAction === 'amend_merge_report') {
                e.preventDefault(); // Stop normal form submission

                const selected = selectedCheckboxes();
                if (selected.length === 0) {
                    alert("Please select at least one item.");
                    return;
                }

                // Concatenate selected IDs as comma-separated string
                const ids = selected.map(cb => cb.value).join(',');

                // Determine AJAX validation URL based on the action
                let url = '';
                if (selectedAction === 'generate_report') {
                    url = `/gulfcoastpathologists/analysis/reportoption/validate-generate-report-selection/?ids=${encodeURIComponent(ids)}`;
                } else if (selectedAction === 'amend_merge_report') {
                    url = `/gulfcoastpathologists/analysis/historicalreportoption/validate-amend-report-selection/?ids=${encodeURIComponent(ids)}`;
                }

                // Perform AJAX request for validation
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.valid) {
                            alert(data.message);
                            return;
                        }
                        if (data.multiple_methodologies && data.popup_url) {
                            // Multiple methodologies: open popup for user to select one methodology
                            const popupWidth = 600;
                            const popupHeight = 300;
                            const screenWidth = window.screen.width;
                            const screenHeight = window.screen.height;
                            const left = Math.floor((screenWidth - popupWidth) / 2);
                            const topPos = Math.floor((screenHeight - popupHeight) / 2);

                            window.open(
                                data.popup_url,
                                '_blank',
                                `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${topPos}`
                            );
                        } else if (data.direct_url) {
                            // Single methodology or direct flow: redirect immediately
                            window.location.href = data.direct_url;
                        } else {
                            alert("Unexpected response from server. Please try again.");
                        }
                    })
                    .catch(error => {
                        console.error('Error during validation request:', error);
                        alert("An error occurred while validating your selection. Please try again." + data);
                    });
            }
        });
    });
});