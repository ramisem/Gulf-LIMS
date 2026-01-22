$(window).on("load", function () {
    if (window.location.search.includes("_popup=1")) {
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.style.width = "400px";
            searchInput.value = '';
        }
        var urlforsearchbypartno = window.location.protocol + "//" + window.location.host + '/sample/ajax/get_unique_partno/';
        const urlParams = new URLSearchParams(window.location.search);
        const accessionid = urlParams.get('accession_id__exact');
        var selected_samples = "";
        var arr_selected_samples = [];

        $("#searchbar").on("click", function (e) {
            $(this).val('');
        });

        $("#searchbar").autocomplete({
            source: function (request, response) {
                $.ajax({
                    url: urlforsearchbypartno,
                    data: {
                        term: request.term, "accessionid": accessionid
                    },
                    success: function (data) {
                        if (!data.results.length) {
                            response([{ label: "No records found", value: "" }]);
                            return;
                        }
                        response($.map(data.results, function (item) {
                            return { label: item.part_no, value: item.part_no };
                        }));
                    }
                });
            },
            minLength: 1,
            select: function (event, ui) {
                event.preventDefault();
                var sample_item = ui.item.value;
                var is_exists = false;
                if (arr_selected_samples.length > 0) {
                    for (let i = 0; i < arr_selected_samples.length; i++) {
                        if (arr_selected_samples[i] == sample_item) {
                            arr_selected_samples.splice(i, 1);
                            is_exists = true;
                            break;
                        }
                    }
                    if (!is_exists) {
                        arr_selected_samples.push(sample_item);
                    }
                } else {
                    arr_selected_samples[0] = sample_item;
                }
                selected_samples = arr_selected_samples.join(',');
                $(this).val(selected_samples);
                $(this).blur();
            }
        }).autocomplete("instance")._renderItem = function (ul, item) {
            var is_exists = false;
            for (let i = 0; i < arr_selected_samples.length; i++) {
                if (arr_selected_samples[i] == item.label) {
                    is_exists = true;
                    break;
                }
            }
            if (is_exists) {
                return $("<li>")
                    .append('<div style="background-color:green; color:white; padding:5px;">' + item.label + '</div>')
                    .appendTo(ul);

            } else {
                return $("<li>")
                    .append('<div style="color:black;">' + item.label + '</div>')
                    .appendTo(ul);
            }

        };


        $(".autocomplete-field").each(function () {
            let $input = $(this);
            let objectId = $input.data("id");
            let fieldName = $input.data("field");
            $input.on("blur", function () {
                location.reload();
            });
            $input.dblclick(function () {
                $input.prop("readonly", false).css({
                    "border": "1px solid #ccc",
                    "background": "#fff",
                    "cursor": "text"
                });
                $input.val('');
                var inputurl = window.location.protocol + "//" + window.location.host + '/tests/ajax/get_test_by_test_name/';
                $input.autocomplete({
                    source: function (request, response) {
                        $.ajax({
                            url: inputurl,
                            data: { term: request.term, "sample_id": objectId },
                            success: function (data) {
                                response($.map(data.results, function (item) {
                                    return { label: item.test_name, value: item.test_id };
                                }));
                            }
                        });
                    },
                    select: function (event, ui) {
                        var saveurl = window.location.protocol + "//" + window.location.host + '/sample/ajax/update_test_in_sample_test_map/';
                        $.ajax({
                            url: saveurl,
                            type: "POST",
                            data: {
                                "id": objectId,
                                "field": fieldName,
                                "value": ui.item.value,
                                "csrfmiddlewaretoken": $("input[name=csrfmiddlewaretoken]").val()
                            },
                            success: function (response) {
                                alert(response['message']);
                                location.reload();
                                if (window.opener && !window.opener.closed) {
                                    window.opener.location.reload();
                                }
                            },
                            error: function (error) {
                                alert('Error associating test: ' + error);
                                return false;
                            }
                        });

                        return false;
                    }
                }).autocomplete("instance")._renderItem = function (ul, item) {
                    var item_label_arr = item.label.split("|");
                    if (item_label_arr != null) {
                        if (item_label_arr.length > 1 && "Y" == item_label_arr[1]) {
                            return $("<li>")
                                .append('<div style="background-color:green; color:white; padding:5px;">' + item_label_arr[0] + '</div>')
                                .appendTo(ul);
                        } else {
                            return $("<li>")
                                .append('<div style="color:black;">' + item_label_arr[0] + '</div>')
                                .appendTo(ul);
                        }
                    }

                };

                $input.focus();
            });

            $input.blur(function () {
                setTimeout(() => {
                    if (!$input.hasClass("ui-autocomplete-loading")) {
                        $input.prop("readonly", true).css({
                            "border": "none",
                            "background": "transparent",
                            "cursor": "pointer"
                        });
                    }
                }, 200);
            });
        });

        document.querySelectorAll('span.small.quiet').forEach(span => {
            span.style.display = 'none';
        });

        const dateHierarchyDiv = document.getElementById('change-list-date-hierarchy');
        if (dateHierarchyDiv) {
            dateHierarchyDiv.remove();
        }
    }
});

// Refresh the parent when this window is closed
window.addEventListener('unload', function () {
    if (window.opener && !window.opener.closed) {
        var elmnt = window.opener.document.querySelector("[aria-controls=samples-tab]");
        elmnt.click();
    }
});

$(document).ready(function () {
    var bulkEditIds = window.bulkEditIds;
    var workflow = window.workflow;  // Value from the template
    var sampleRouteUrl = window.sampleRouteUrl;
    var ihcSampleRouteUrl = window.ihcSampleRouteUrl;

    // Choose the route based on the workflow.
    var routeUrl;
    if (workflow === 'ihc') {
        routeUrl = ihcSampleRouteUrl;
    } else if (workflow === 'enterprise') {
        routeUrl = sampleRouteUrl;
    } else {
        // Default or additional conditions can go here.
        routeUrl = sampleRouteUrl;
    }

    // Next Sample button functionality (unchanged)
    $('#next-sample-btn').click(function (e) {
        e.preventDefault();
        var tabs = $('.vertical-tabs .nav-link');
        var activeTab = tabs.filter('.active');
        var activeIndex = tabs.index(activeTab);
        var nextTab = tabs.eq(activeIndex + 1);
        if (nextTab.length) {
            nextTab[0].click();
        } else {
            tabs.first()[0].click();
        }
    });

    // Route Current Sample button
    $('#route-sample-btn').click(function (e) {
        e.preventDefault();
        var activeTab = $('.vertical-tabs .nav-link.active');
        var activeId = activeTab.data('sample-id');
        if (activeId) {
            window.location.href = routeUrl +
                "?active_id=" + activeId +
                "&all_ids=" + bulkEditIds +
                "&origin=bulk";
        }
    });

    // Route All Samples button
    $('#route-all-btn').click(function (e) {
        e.preventDefault();
        var sampleIds = [];
        $('.vertical-tabs .nav-link').each(function () {
            var id = $(this).data('sample-id');
            if (id) { sampleIds.push(id); }
        });
        if (sampleIds.length > 0) {
            window.location.href = routeUrl +
                "?ids=" + sampleIds.join(',') +
                "&origin=bulk";
        }
    });

    // Listen to all select2-enabled gross_code dropdowns
    $("select[id$='gross_code']").on('select2:select', function (e) {
        var $this = $(this);
        var grossCode = $this.val();

        // Find corresponding gross_description field
        var fieldId = $this.attr('id');  // e.g., id_form-0-gross_code
        var descId = fieldId.replace('gross_code', 'gross_description');

        if (grossCode) {
            $.ajax({
                url: '/sample/ajax/gross-description/',
                data: {
                    'gross_code': grossCode
                },
                success: function (data) {
                    $('#' + descId).val(data.description);
                },
                error: function () {
                    console.error("Could not fetch gross description.");
                    $('#' + descId).val('');
                }
            });
        } else {
            $('#' + descId).val('');
        }
    });

    // TODO tab handling
    window.handleTodoTab = function handleTodoTab(e, el, textContent, setSelection) {
        const isBackward = e.shiftKey;
        const regex = /TODO/g;
        const matches = [];
        let m;
        while ((m = regex.exec(textContent)) !== null) {
            matches.push(m.index);
        }
        if (!matches.length) return false;

        let cursor;
        if (el.tagName === 'TEXTAREA') {
            cursor = el.selectionStart;
        } else {
            const sel = window.getSelection();
            if (!sel || sel.rangeCount === 0) {
                console.warn('No selection range found');
                return false; // Or handle gracefully
            }
            const range = sel.getRangeAt(0);
            const pre = range.cloneRange();
            pre.selectNodeContents(el);
            pre.setEnd(range.startContainer, range.startOffset);
            cursor = pre.toString().length;
        }

        let targetPos = null;
        if (isBackward) {
            for (let i = matches.length - 1; i >= 0; i--) {
                if (matches[i] < cursor) {
                    targetPos = matches[i];
                    break;
                }
            }
        } else {
            for (let i = 0; i < matches.length; i++) {
                if (matches[i] > cursor) {
                    targetPos = matches[i];
                    break;
                }
            }
            if (targetPos === null && cursor >= textContent.length) {
                return false;
            }
        }

        if (targetPos !== null) {
            e.preventDefault();
            setSelection(targetPos, targetPos + 4);
            return true;
        }
        return false;
    }

    window.moveFocus = function (e, currentEditable, direction = 'forward') {
        const focusable = Array.from(document.querySelectorAll('input, select, textarea, iframe, [tabindex]:not([tabindex="-1"])'))
            .filter(el => !el.disabled && el.tabIndex >= 0 && el.offsetParent !== null);

        const currentIndex = focusable.indexOf(currentEditable.closest('iframe'));
        if (currentIndex === -1) return;

        let nextIndex = direction === 'backward' ? currentIndex - 1 : currentIndex + 1;
        if (nextIndex >= 0 && nextIndex < focusable.length) {
            focusable[nextIndex].focus();
            console.log(`Moving ${direction} to`, focusable[nextIndex]);
        } else {
            console.log("No more focusable elements in direction", direction);
        }
    }

    $(document).on('keydown', 'div[id^="attributes-for-"] textarea, div[id^="dynamic-"] textarea', function (e) {
        if (e.key === 'Tab') {
            const handled = handleTodoTab(
                e,
                this,
                this.value,
                (s, e2) => this.setSelectionRange(s, e2)
            );
            if (!handled) moveFocus(e, this);
        }
    });

});

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

            if (selectedAction === 'print_label_popup') {
                e.preventDefault(); // Stop the normal form submission

                const selected = selectedCheckboxes();
                if (selected.length === 0) {
                    alert("Please select at least one item.");
                    return;
                }

                const ids = selected.map(cb => cb.value).join(',');
                fetch(`/gulfcoastpathologists/sample/sample/validate-label-popup/?ids=${ids}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const popupWidth = 1000;
                            const popupHeight = 700;
                            const screenWidth = window.screen.width;
                            const screenHeight = window.screen.height;
                            const left = Math.floor((screenWidth - popupWidth) / 2);
                            const topPos = Math.floor((screenHeight - popupHeight) / 2);

                            const url = `/gulfcoastpathologists/sample/sample/print-label-prompt/?ids=${ids}`;
                            window.open(url, '_blank', `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${topPos}`);
                        } else if (!data.success) {
                            if (data.message != '' || data.message != null) {
                                alert(data.message);
                            } else {
                                alert('Please select samples with the same Current step.');
                            }
                        } else {
                            alert("Validation failed for IDs: " + data.invalid_ids.join(', '));
                        }
                    })
                    .catch(error => {
                        console.error("Validation error:", error);
                        alert("Server validation failed.");
                    });

            } else if (selectedAction === 'prepare_liquid_sample') {
                e.preventDefault(); // Stop the normal form submission

                const selected = selectedCheckboxes();
                if (selected.length === 0) {
                    alert("Please select at least one item.");
                    return;
                }

                const ids = selected.map(cb => cb.value).join(',');
                fetch(`/gulfcoastpathologists/sample/sample/validate-smearing-popup/?ids=${ids}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const popupWidth = 1000;
                            const popupHeight = 700;
                            const screenWidth = window.screen.width;
                            const screenHeight = window.screen.height;
                            const left = Math.floor((screenWidth - popupWidth) / 2);
                            const topPos = Math.floor((screenHeight - popupHeight) / 2);

                            const url = `/gulfcoastpathologists/sample/sample/smearing-selection-prompt/?ids=${ids}`;
                            window.open(url, '_blank', `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${topPos}`);
                        } else if (!data.success) {
                            if (data.message != '' || data.message != null) {
                                alert(data.message);
                            } else {
                                alert('Please select samples Pending Prepare Liquid Sample.');
                            }
                        } else {
                            alert("Validation failed for IDs: " + data.invalid_ids.join(', '));
                        }
                    })
                    .catch(error => {
                        console.error("Validation error:", error);
                        alert("Server validation failed.");
                    });
            }
            else if (selectedAction === 'perform_backward_movement') {
                e.preventDefault(); // Stop the normal form submission

                const selected = selectedCheckboxes();
                if (selected.length === 0) {
                    alert("Please select at least one item.");
                    return;
                }
                const ids = selected.map(cb => cb.value).join(',');
                fetch(`/gulfcoastpathologists/sample/sample/validate-backward-movement-popup/?ids=${ids}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const popupWidth = 800;
                            const popupHeight = 400;
                            const screenWidth = window.screen.width;
                            const screenHeight = window.screen.height;
                            const left = Math.floor((screenWidth - popupWidth) / 2);
                            const topPos = Math.floor((screenHeight - popupHeight) / 2);

                            const url = `/gulfcoastpathologists/sample/sample/backward-movement-prompt/?ids=${ids}`;
                            window.open(url, '_blank', `width=${popupWidth},height=${popupHeight},scrollbars=yes,left=${left},top=${topPos}`);
                        } else if (!data.success) {
                            if (data.message != '' || data.message != null) {
                                alert(data.message);
                            } else {
                                alert("Validation failed for the selected records. Please ensure all selected items meet the criteria.");
                            }
                        } else {
                            alert("Validation failed for IDs: " + data.invalid_ids.join(', '));
                        }
                    })
                    .catch(error => {
                        console.error("Validation error:", error);
                        alert("Server validation failed.");
                    });
            }
        });
    }, 100);
});

document.addEventListener("DOMContentLoaded", function() {
  const form = document.getElementById('changelist-form');
  const actionSelect = document.querySelector('select[name="action"]');

  if (!form || !actionSelect) return;

  form.addEventListener('submit', function(event) {
    if (actionSelect.value === 'update_test') {
      event.preventDefault(); // prevent default form submission

      const selectedCheckboxes = document.querySelectorAll('input.action-select:checked');
      if (selectedCheckboxes.length === 0) {
        alert("Please select one or more samples first.");
        return;
      }

      const sampleIds = Array.from(selectedCheckboxes).map(cb => cb.value).join(',');
      const width = 900;
      const height = 600;
      const left = (window.screen.width / 2) - (width / 2);
      const top = (window.screen.height / 2) - (height / 2);

      // Get q param from current page URL
      const urlParams = new URLSearchParams(window.location.search);
      const qParam = urlParams.get('q') || '';

      fetch(`/gulfcoastpathologists/ihcworkflow/ihcworkflow/validate-update-test-popup/?ids=${sampleIds}`)
        .then(response => response.json())
        .then(data => {
          if (data.invalid_samples && data.invalid_samples.length > 0) {
            alert("Cannot update test for sample(s): " + data.invalid_samples.join(', ') + ". Staining has already started.");
            return;
          }
          else{
           let url = `/gulfcoastpathologists/ihcworkflow/ihcworkflow/update-test-popup/?ids=${sampleIds}&_popup=1`;
            if (qParam) {
              url += `&q=${encodeURIComponent(qParam)}`;
            }
            window.open(url, 'UpdateTestPopup', `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`);
            actionSelect.selectedIndex = 0;
            }
        });

    }
  });
});



