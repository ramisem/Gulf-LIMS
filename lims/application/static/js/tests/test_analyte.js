function populateAnalyteUnit(id) {
    console.log('populateAnalyteUnit called');
    const value_obj = document.querySelector('#' + id);
    const value_unit_obj = document.querySelector('#' + id + '_unit');
    if (typeof value_obj == 'undefined' || value_obj == null) {
        console.error('Value Object cannot be obtained.');
        return;
    }
    if (typeof value_unit_obj == 'undefined' || value_unit_obj == null) {
        console.error('Value1 Unit Object cannot be obtained.');
        return;
    }
    var value = value_obj.value;
    if (typeof value == 'undefined' || value == null || value == '') {
        value_unit_obj.value = '';
        console.log('Value cannot be obtained.');
        return;
    }
    const delimiter = '-';
    const parts = id.split(delimiter);

    if (parts.length >= 2) {
        const extractedString = parts.slice(0, 2).join(delimiter);
        var analyte_id_obj = document.querySelector('#' + extractedString + '-analyte_id');
        if (typeof analyte_id_obj == 'undefined' || analyte_id_obj == null) {
            console.error('Analyte Id Object cannot be obtained.');
            return;
        }
        var analyte_id = analyte_id_obj.value;
        if (typeof analyte_id == 'undefined' || analyte_id == null || analyte_id == '') {
            value_unit_obj.value = '';
            console.log('Analyte Id cannot be obtained.');
            return;
        }
        var inputURL = window.location.protocol + "//" + window.location.host + '/tests/ajax/get_analyte_unit_by_analyte_id/';
        $.ajax({
            url: inputURL,
            type: 'GET',
            data: { 'analyte_id': analyte_id },
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            success: function (data) {
                value_unit_obj.value = data.unit || '';
            },
            error: function (error) {
                console.error('Error fetching Unit by Analyte Id:', error);
            }
        });

    } else {
        console.log('Delimiter not found in the string.');
    }

}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[id$="-value1"]').forEach(el => {
        if (el.value) {
            populateAnalyteUnit(el.id);
        }
    });
    document.querySelectorAll('input[id$="-value2"]').forEach(el => {
        if (el.value) {
            populateAnalyteUnit(el.id);
        }
    });
});