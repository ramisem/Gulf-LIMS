document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('change', function (e) {

        if (e.target && e.target.name.endsWith('-is_default') && e.target.type === 'checkbox') {

            const currentCheckbox = e.target;

            if (!currentCheckbox.checked) {
                return;
            }

            const inlineGroup = currentCheckbox.closest('.js-inline-admin-formset');

            if (!inlineGroup) {
                console.error("Could not find parent inline group for checkbox:", currentCheckbox);
                return;
            }

            const allCheckboxesInGroup = inlineGroup.querySelectorAll("input[name$='-is_default']");

            allCheckboxesInGroup.forEach(function (checkbox) {
                if (checkbox !== currentCheckbox) {
                    checkbox.checked = false;
                }
            });
        }
    });
});