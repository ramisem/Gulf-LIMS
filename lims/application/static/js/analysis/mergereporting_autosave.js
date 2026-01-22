(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const $ = window.jQuery;

        function getCSRFToken() {
            const name = 'csrftoken';
            return document.cookie
                .split(';')
                .map(c => c.trim())
                .find(c => c.startsWith(name + '='))
                ?.split('=')[1] || null;
        }

        const csrftoken = getCSRFToken();
        const currentPath = window.location.pathname;
        const autoSaveUrl = `${window.location.protocol}//${window.location.host}/${currentPath
            .replace(/^\/?gulfcoastpathologists\//, '')
            .replace(/change\/?$/, 'autosave/')}`;

        console.log("autoSaveUrl:", autoSaveUrl);

        function showAutosaveToast(message = "✅ Autosaved Success! ") {
            $('#autosave-toast').remove();
            const html = `
        <div id="autosave-toast" class="toast bg-success text-white" role="alert"
             style="position: fixed; top:60px; right:30px; z-index:9999; min-width:300px;">
          <div class="toast-body d-flex justify-content-between">
            <span><strong>${message}</strong></span>
            <button type="button" class="close text-white" data-bs-dismiss="toast" aria-label="Close">
              &times;
            </button>
          </div>
        </div>`;
            $('body').append(html);
            const $t = $('#autosave-toast');

            $t.find('.close').on('click', () => {
                $t.fadeOut(200, () => $t.remove());
            });

            if ($t.toast) {
                $t.toast({
                    delay: 2000
                }).toast('show');
            } else {
                $t.fadeIn(200).delay(2000).fadeOut(300, () => $t.remove());
            }
        }

        const stored = localStorage.getItem('postReloadErrorToast');
        if (stored) {
            showErrorToast(stored);
            localStorage.removeItem('postReloadErrorToast');
        }

        function showErrorToast(message) {
            // remove any old toast
            $('#autosave-toast').remove();

            // proper HTML (no ellipses!)
            const html = `
            <div id="autosave-toast" class="toast bg-danger text-white" role="alert"
                 style="position: fixed; top:60px; right:30px; z-index:9999; min-width:300px;">
              <div class="toast-body">
                <strong>❌ Autosaved Failed!</strong><br><br>
                  Reason: ${message}
                <button type="button" class="close text-white" data-bs-dismiss="toast" aria-label="Close">
                    &times;
                </button>
              </div>
            </div>`;

            $('body').append(html);

            const $t = $('#autosave-toast');

            $t.find('.close').on('click', () => {
                $t.fadeOut(200, () => $t.remove());
            });

            if ($t.toast) {
                $t.toast({ delay: 8000 }).toast('show');
            } else {
                $t.fadeIn(200).delay(8000).fadeOut(300, () => $t.remove());
            }
        }

        function getRowKey($row, index) {
            return $row.find('input[name$="-hidden_merge_reporting_dtl_id"]').val() || `row-${index}`;
        }


        function getAnalyteValue($row) {
            // Find Summernote iframe inside analyte_value cell, if any
            const iframe = $row.find('td.field-analyte_value iframe')[0];
            if (iframe && iframe.contentDocument) {
                // Get the .note-editable inside iframe
                const editable = iframe.contentDocument.querySelector('.note-editable');
                if (editable) {
                    return editable.innerHTML;
                }
            }
            // Fall back: check inline .note-editable (non-iframe mode)
            const $noteEditable = $row.find('td.field-analyte_value .note-editable');
            if ($noteEditable.length) {
                return $noteEditable.html();
            }
            // Fall back: select or input
            const $valEl = $row.find('td.field-analyte_value :input');
            if ($valEl.is('select')) {
                var selVal = '';
                selVal = $valEl.find('option:selected').text().trim();
                if (selVal == '') {
                    selVal = ($valEl.val() || '').trim()
                }
                if (selVal == '') {
                    const storedVal = $valEl.attr('data-last-set-value') || '';
                    selVal = (storedVal || '').trim()
                }

                return selVal;
            }
            return $valEl.val() ? $valEl.val().trim() : '';
        }

        function triggerAutosave($row) {
            const data = {
                merge_reporting_dtl_id: $row.find('input[name$="-hidden_merge_reporting_dtl_id"]').val(),
                merge_reporting_id: $row.find('input[name$="-merge_reporting_id"]').val(),
                analyte_id: $row.find('td.field-analyte_id a').text().trim(),
                analyte_value: getAnalyteValue($row),
            };
            console.log("Autosaving:", data);
            console.log("autoSaveUrl:", autoSaveUrl);
            $.ajax({
                url: autoSaveUrl,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data,
                success() {
                    console.log("Autosave OK");
                    showAutosaveToast();
                },
                error(xhr) {
                    if (xhr.status === 400 && xhr.responseJSON) {
                        const body = xhr.responseJSON;
                        const errs = body.errors || {};
                        const expected = body.expected || null;
                        const current = body.current || null;

                        let combinedMsg = Object.values(errs).flat().map(msg => {
                            let detail = '';
                            if (expected !== null || current !== null) {
                                detail = ` Expected: ${expected ?? 'N/A'}<br><br> Entered: ${current ?? 'N/A'}`;
                            }
                            return `${msg}<br><br>${detail}`;
                        }).join('<br><br>');

                        showErrorToast(combinedMsg);
                    } else {
                        console.error("Autosave failed:", xhr.responseText);
                    }
                }

            });
        }



        // Autosave polling to detect value changes
        const lastValues = {};

        // Helper to detect and handle changes
        function handleAnalyteChange($changedRow) {
            const key = getRowKey($changedRow);
            const prevValue = lastValues[key];
            const currentValue = getAnalyteValue($changedRow);
            console.log(`[handleAnalyteChange] prevValue="${prevValue}", currentValue="${currentValue}"`);

            if (currentValue !== prevValue) {
                lastValues[key] = currentValue;
                triggerAutosave($changedRow);

                const changedAnalyte = $changedRow.find('td.field-analyte_id a').text().trim();

                // figure out which "set" this row belongs to, e.g. "dynamic-mergereportingdtl_set-3"
                const setClass = $changedRow
                    .attr('class')
                    .split(/\s+/)                                // split on whitespace
                    .find(c => /^dynamic\-mergereportingdtl_set(?:\-\d+)?$/.test(c));

                if (!setClass) return;  // safety

                // only loop the rows in that exact set
                $('tr.' + setClass).each(function () {
                    const $row = $(this);
                    const rawLookups = $row.find('[data-dropdown-lookups]')
                        .attr('data-dropdown-lookups') || '';
                    const lookups = rawLookups.split(';').map(s => s.trim()).filter(Boolean);

                    if (lookups.includes(changedAnalyte)) {
                        $row.data('dep-changed', true);
                        processRow($row, currentValue, true);
                    }
                });
            }
        }


        function registerChangeListeners() {
            // Inputs & selects
            $('fieldset.module')
                .on(
                    'change',
                    'tr[class*="dynamic-mergereportingdtl_set"] td.field-analyte_value :input',
                    function () {
                        const $row = $(this).closest('tr[class*="dynamic-mergereportingdtl_set"]');
                        handleAnalyteChange($row);
                    }
                );


            // Rich text inputs in iframes (Summernote)
            $('iframe').each(function () {
                const iframe = this;
                const editable = iframe.contentDocument?.querySelector('.note-editable');
                if (editable) {
                    editable.addEventListener('input', function () {
                        const $row = $(iframe).closest('tr[class*="dynamic-mergereportingdtl_set"]');
                        handleAnalyteChange($row);
                    });
                }
            });
        }

        $(function () {
            // Register analyte baseline
            $('tr[class*="dynamic-mergereportingdtl_set"]').each(function (i) {
                lastValues[getRowKey($(this), i)] = getAnalyteValue($(this));
            });

            // Register onchange listeners once DOM is ready
            registerChangeListeners();
        });

        setTimeout(() => {
            $('tr[class*="dynamic-mergereportingdtl_set"]').each(function (i) {
                lastValues[getRowKey($(this), i)] = getAnalyteValue($(this));
            });

            setInterval(() => {
                $('tr[class*="dynamic-mergereportingdtl_set"]').each(function (i) {
                    const $changedRow = $(this);
                    const key = getRowKey($changedRow, i);
                    const prevValue = lastValues[key];
                    const currentValue = getAnalyteValue($changedRow);

                    if (currentValue !== prevValue) {
                        lastValues[key] = currentValue;
                        triggerAutosave($changedRow);
                    }

                });
            }, 5000);
        }, 500);

        // Autosave on exit
        let skipBeacon = false;
        window.addEventListener('keydown', e => {
            if (
                e.key === 'F5' ||
                ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r')
            ) {
                skipBeacon = true;
            }
        });

        function autosaveOnExit() {
            if (skipBeacon) return;
            $('tr[class*="dynamic-mergereportingdtl_set"]').each(function () {
                const $row = $(this);
                const form = new FormData();
                form.append('merge_reporting_dtl_id', $row.find('input[name$="-hidden_merge_reporting_dtl_id"]').val());
                form.append('merge_reporting_id', $row.find('input[name$="-merge_reporting_id"]').val());
                form.append('analyte_id', $row.find('td.field-analyte_id a').text().trim());
                form.append('analyte_value', getAnalyteValue($row));
                form.append('csrfmiddlewaretoken', csrftoken);
                navigator.sendBeacon(autoSaveUrl, form);
            });
        }
        window.addEventListener('beforeunload', autosaveOnExit);

        // Focus handlers
        $(document).on('focus', 'tr[class*="dynamic-mergereportingdtl_set"] textarea', function () {
            this.setSelectionRange(0, 0);
        });

        $(document).on('focus', 'tr[class*="dynamic-mergereportingdtl_set"] .note-editing-area textarea', function () {
            const range = document.createRange();
            range.setStart(this, 0);
            range.collapse(true);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
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


        $(document).on('keydown', 'tr[class*="dynamic-mergereportingdtl_set"] textarea', function (e) {
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


        function getCursorOffsetInEditable(editable) {
            const sel = editable.ownerDocument.getSelection();
            if (!sel.rangeCount) return 0;

            const range = sel.getRangeAt(0).cloneRange();
            const plain = getPlainText(editable);

            // Now create a Range from start→cursor, but only counting text nodes
            const walker = editable.ownerDocument.createTreeWalker(
                editable,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let offset = 0,
                node;
            // start a clone of range to walk from editable start up to cursor
            const preRange = range.cloneRange();
            preRange.selectNodeContents(editable);
            preRange.setEnd(range.startContainer, range.startOffset);

            // Build a temporary div from preRange contents
            const div = document.createElement('div');
            div.appendChild(preRange.cloneContents());
            return div.innerText.length;
        }


        window.moveFocusFromIframe = function (e, iframeEl, direction = 'forward') {
            // build a list of all real form controls + iframes
            const focusable = Array.from(
                document.querySelectorAll('input, select, textarea, iframe, [tabindex]:not([tabindex="-1"])')
            ).filter(el => !el.disabled && el.tabIndex >= 0 && el.offsetParent !== null);

            const currentIndex = focusable.indexOf(iframeEl);
            if (currentIndex === -1) return;

            const nextIndex = direction === 'backward' ?
                currentIndex - 1 :
                currentIndex + 1;

            if (focusable[nextIndex]) {
                e.preventDefault();
                focusable[nextIndex].focus();
                console.log(`Moved ${direction} from iframe to`, focusable[nextIndex]);
            }
        };


        window.handleTodoTabForSummernote = function handleTodoTabForSummernote(e, editable, text, offset, setSelection) {
            const todos = [...text.matchAll(/TODO/g)];
            if (!todos.length) return false;

            const isShift = e.shiftKey;

            let target;
            if (isShift) {
                // Go to previous TODO
                for (let i = todos.length - 1; i >= 0; i--) {
                    if (todos[i].index < offset) {
                        target = todos[i];
                        break;
                    }
                }
                // If none found behind, exit editable
                if (!target) return false;
            } else {
                // Go to next TODO
                for (let i = 0; i < todos.length; i++) {
                    if (todos[i].index > offset) {
                        target = todos[i];
                        break;
                    }
                }
                // If none found ahead, exit editable
                if (!target) return false;
            }

            const start = target.index;
            const end = start + target[0].length;

            setSelection(start, end);
            return true;
        };

        function getPlainText(editable) {
            // Walk only the TEXT nodes in document order
            const walker = editable.ownerDocument.createTreeWalker(
                editable,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let node;
            let text = '';
            while ((node = walker.nextNode())) {
                text += node.textContent;
            }
            return text;
        }

        // Summernote iframe focus & change detection
        function setupSummernoteFocusAndChange() {
            const $ = window.jQuery;

            // Helper to initialize events for a single iframe
            function setupIframeEvents(iframe) {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                const editable = doc.querySelector('.note-editable');

                if (!editable) {
                    console.warn('.note-editable not found in iframe');
                    return;
                }

                // Make editable area focusable
                editable.setAttribute('tabindex', '0');

                doc.addEventListener('focusin', e => {
                    if (e.target === editable) {
                        console.log('Editable area focused');

                        // Always reset cursor to the beginning
                        const range = doc.createRange();
                        range.setStart(editable, 0);
                        range.collapse(true);

                        const sel = doc.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                });


                editable.addEventListener('focusout', () => {
                    console.log('Editable area blurred (focusout)');
                    const $row = $(iframe).closest('tr[class*="dynamic-mergereportingdtl_set"]');
                });

                editable.addEventListener('input', () => {
                    console.log('Editable area input changed');
                    const $row = $(iframe).closest('tr[class*="dynamic-mergereportingdtl_set"]');
                });


                doc.addEventListener('keydown', e => {
                    if (e.key !== 'Tab' || e.target !== editable) return;

                    console.log("Tab inside Summernote");

                    e.preventDefault(); // stop default tab

                    const text = getPlainText(editable) || '';
                    const offset = getCursorOffsetInEditable(editable);
                    const isShift = e.shiftKey;

                    console.log("Text:", text);
                    console.log("TODOs:", [...text.matchAll(/TODO/g)]);
                    console.log("Cursor offset:", offset);

                    const handled = window.handleTodoTabForSummernote(
                        e,
                        editable,
                        text,
                        offset,
                        (start, end) => {
                            const range = doc.createRange();
                            const walker = doc.createTreeWalker(editable, NodeFilter.SHOW_TEXT, null, false);
                            let node = walker.nextNode();
                            let charCount = 0;

                            while (node) {
                                const nextCharCount = charCount + node.textContent.length;
                                if (charCount <= start && start < nextCharCount) {
                                    const rangeStart = start - charCount;
                                    const rangeEnd = end - charCount;

                                    range.setStart(node, rangeStart);
                                    range.setEnd(node, rangeEnd);

                                    const sel = doc.getSelection();
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                    editable.focus();
                                    console.log("Focused on TODO");
                                    return;
                                }
                                charCount = nextCharCount;
                                node = walker.nextNode();
                            }

                            console.warn("Could not find TODO node, collapsing to end");
                            const sel = doc.getSelection();
                            sel.removeAllRanges();
                            const fallbackRange = doc.createRange();
                            fallbackRange.selectNodeContents(editable);
                            fallbackRange.collapse(false);
                            sel.addRange(fallbackRange);
                            editable.focus();
                        }
                    );

                    if (!handled) {
                        window.moveFocusFromIframe(e, iframe, isShift ? 'backward' : 'forward');
                    }
                });
            }

            // Small delay to ensure Summernote loads its iframe
            setTimeout(() => {
                $('tr[class*="dynamic-mergereportingdtl_set"] td.field-analyte_value iframe').each(function () {
                    const iframe = this;
                    iframe.setAttribute('tabindex', '0');

                    if (iframe.contentDocument?.readyState === 'complete') {
                        setupIframeEvents(iframe);
                    } else {
                        iframe.addEventListener('load', () => setupIframeEvents(iframe));
                    }
                });
            }, 800);

        } // closes setupSummernoteFocusAndChange IIFE
        setupSummernoteFocusAndChange();


        // ============================================
        // FIX: Preserve text selection on toolbar click (CORRECTED FOR CUSTOM IFRAME)
        // ============================================
        (function() {
            function setupSummernoteSelectionFix() {
                console.log('Setting up Summernote selection fix for custom iframes...');

                // Find all Summernote iframes in your custom structure
                const iframes = document.querySelectorAll('iframe.note-preview, iframe[id*="analyte_value_iframe"]');

                if (!iframes.length) {
                    console.log('No Summernote iframes found, will retry...');
                    return;
                }

                console.log('Found', iframes.length, 'iframe(s)');

                iframes.forEach(function(iframe, index) {
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (!iframeDoc) {
                            console.warn('Iframe', index, 'contentDocument not accessible');
                            return;
                        }

                        // Find the toolbar INSIDE the iframe
                        const toolbar = iframeDoc.querySelector('.note-toolbar');
                        if (!toolbar) {
                            console.log('Iframe', index, 'has no .note-toolbar inside');
                            return;
                        }

                        console.log('Iframe', index, 'has toolbar, setting up selection fix');

                        const editable = iframeDoc.querySelector('.note-editable');
                        if (!editable) {
                            console.warn('Iframe', index, 'has no .note-editable');
                            return;
                        }

                        // Prevent default on toolbar buttons to preserve selection
                        toolbar.addEventListener('mousedown', function(e) {
                            const isButton = e.target.closest('button, [data-toggle="dropdown"], .dropdown-toggle');

                            if (!isButton) return;

                            console.log('Toolbar button clicked in iframe', index);

                            // IMPORTANT: Don't prevent default yet - let Summernote handle it
                            // Just save the selection
                            const sel = iframeDoc.getSelection();
                            let savedRange = null;

                            if (sel && sel.rangeCount > 0) {
                                savedRange = sel.getRangeAt(0).cloneRange();
                                console.log('Selection saved for iframe', index);
                            }

                            // After formatting is applied, restore selection
                            setTimeout(function() {
                                if (savedRange && sel) {
                                    try {
                                        sel.removeAllRanges();
                                        sel.addRange(savedRange);
                                        console.log('Selection restored for iframe', index);
                                    } catch (e) {
                                        console.error('Error restoring selection:', e);
                                    }
                                }
                            }, 50);

                        }, true); // Capture phase

                        console.log('Selection fix applied to iframe', index);

                    } catch (err) {
                        console.error('Error setting up iframe', index, ':', err);
                    }
                });
            }

            // Try multiple times as iframe loads asynchronously
            const retries = [500, 1000, 2000, 3000];
            retries.forEach(function(delay) {
                setTimeout(setupSummernoteSelectionFix, delay);
            });

            // Also bind to window load
            window.addEventListener('load', setupSummernoteSelectionFix);

            // And on DOM changes (for dynamic inline forms)
            const observer = new MutationObserver(function() {
                setupSummernoteSelectionFix();
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

        })();
        // ============================================
        // END: Selection fix
        // ============================================


        /**
         * For a given inline row <tr>, potentially fetch a new analyte value
         * from the server and inject it + autosave.
         */
        function processRow($row, changedValue, reloadAfter = false) {
            const taId = $row.find('[data-ta-id]').data('ta-id');
            const reportoption = $row.find('input[name$="-report_option_id"]').val();
            const current = getAnalyteValue($row).trim();
            const dirty = $row.data('dep-changed') === true;
            const should = (current === '' || dirty) && !!taId;

            if (!should) {
                console.log("SKIPPED FETCH: condition not met", { taId, current, dirty });
                return;
            }

            const rawWrapper = $row.find('.analyte-value-wrapper');
            let rawLookups = rawWrapper.length ? rawWrapper.data('dropdown-lookups') : null;

            if (!rawLookups) {
                rawLookups = $row.find('[data-dropdown-lookups]').data('dropdown-lookups');
            }

            const lookups = (rawLookups || '').split(';').map(s => s.trim()).filter(Boolean);
            console.log("Lookups fetched:", lookups);

            const params = {};

            lookups.forEach(analyteName => {
                const safeKey = analyteName.replace(/[^0-9A-Za-z]+/g, '_');
                const $relatedRow = $row
                    .closest('fieldset.module')
                    .find('tr.form-row')
                    .filter(function () {
                        return $(this).find('td.field-analyte_id a').text().trim() === analyteName;
                    });

                const analyteVal = getAnalyteValue($relatedRow);
                params[`analyte_id__${safeKey}`] = analyteVal;
            });

            const origin = `${window.location.protocol}//${window.location.host}`;
            const fetchAnalyteUrl = `${origin}/analysis/fetch_analyte_value/`;
            merge_reporting_dtl_id = $row.find('input[name$="-hidden_merge_reporting_dtl_id"]').val();
            merge_reporting_id = $row.find('input[name$="-merge_reporting_id"]').val();
            analyte_id = $row.find('td.field-analyte_id a').text().trim();

            if (!Object.values(params).every(v => v)) {
                console.warn("SKIPPED FETCH: Some lookup values missing", params);
                //                return;
            }

            console.log(`[processRow] for row ${$row.attr('id')} – lookups:`, lookups);
            console.log('TRIGGER: analyte fetch', {
                row: $row.attr('id'), taId, reportoption,
                merge_reporting_dtl_id, merge_reporting_id, analyte_id, params
            });

            $.ajax({
                url: fetchAnalyteUrl,
                type: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                data: {
                    ta_id: taId,
                    merge_reporting_dtl_id: merge_reporting_dtl_id,
                    merge_reporting_id: merge_reporting_id,
                    analyte_id: analyte_id,
                    ...params
                },
                success(res) {
                    console.log(`[AJAX Success] Response for row ${$row.attr('id')}:`, res);
                    const val = res.value || '';

                    const current = getAnalyteValue($row).trim();

                    console.log(`[Comparison] Current: "${current}", Fetched: "${val}"`);
                    if (val.trim() !== current.trim()) {
                        const $textarea = $row.find('textarea[name$="-analyte_value"]');
                        const hasIframe = $row.find('td.field-analyte_value iframe').length > 0;
                        if (hasIframe) {
                            console.log(`[FORCE UPDATE] Updating Summernote iframe content for row ${$row.attr('id')}`);
                            forceUpdateSummernoteIframeContent($row, val);
                        } else if ($textarea.length) {
                            console.log(`[UPDATE] Updating regular textarea/select for row ${$row.attr('id')}`);
                            $textarea.val(val).trigger('input').trigger('change');
                        } else {
                            const $select = $row.find('td.field-analyte_value select');
                            const $input = $row.find('td.field-analyte_value input');

                            if ($select.length) {
                                console.log(`[UPDATE] Updating SELECT for row ${$row.attr('id')} with value: "${val}"`);
                                setSelectAndTrigger($select, val);
                            } else if ($input.length) {
                                console.log(`[UPDATE] Updating INPUT for row ${$row.attr('id')} with value: "${val}"`);
                                $input.val(val).trigger('input').trigger('change');
                            }
                        }
                    }
                    $row.data('dep-changed', false);

                    if (reloadAfter) {
                        console.log("Reloading after processRow...");
                        setTimeout(() => {
                            window.location.reload();
                        }, 200);
                    }
                }
            });
        }

        function forceUpdateSummernoteIframeContent($row, val) {
            const iframe = $row.find('td.field-analyte_value iframe')[0];
            const $textarea = $row.find('textarea[name$="-analyte_value"]');

            if (!iframe || !iframe.contentDocument) {
                console.warn(`[forceUpdate] No iframe or contentDocument found`);
                return;
            }

            const editable = iframe.contentDocument.querySelector('.note-editable');
            if (editable) {
                console.log(`[forceUpdate] Writing HTML into iframe editable`);
                editable.innerHTML = val;
            } else {
                console.warn(`[forceUpdate] .note-editable not found inside iframe`);
            }

            if ($textarea.length) {
                console.log(`[forceUpdate] Syncing hidden textarea`);
                $textarea.val(val).trigger('input').trigger('change');
            }
        }

        function setSelectAndTrigger($sel, val) {
            console.log(`setSelectAndTrigger(val): "${val}"`);
            console.log(`setSelectAndTrigger($sel): ` + $sel);
            const $row = $sel.closest('tr[class*="dynamic-mergereportingdtl_set"]');
            const key = getRowKey($row);
            lastValues[key] = "__force_diff__" + Math.random();

            $sel.val(val);
            $sel.attr('data-last-set-value', val);
            $sel.trigger('change', { force: true });
        }

    }); // closes DOMContentLoaded
})();