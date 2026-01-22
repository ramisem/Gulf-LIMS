// GenericScanner.js - Single, configurable scanner for any admin
class GenericScanner {
    constructor(config) {
        this.config = {
            title: 'Scanner',
            placeholder: 'Scan or type ID then press Tab',
            validatePath: '/admin/scan-validate/',
            submitPath: '/admin/scan-submit/',
            editPath: '/admin/scan-bulk-edit/',
            tableHeaders: [
                { key: 'index', label: '#' },
                { key: 'sampleId', label: 'Sample ID' },
                { key: 'action', label: 'Action' }
            ],
            ...config
        };

        this.isOpen = false;
        this.samples = [];
        this.isSubmitting = false;
        this.csrfToken = this.getCsrfToken();

        this.init();
    }

    init() {
        this.injectCSS();
        this.buildModal();
        this.bindEvents();
        this.setupGlobalKeyboardHandler();
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return null;
    }

    buildModal() {
        if (document.getElementById('scanner-modal-root')) {
            this.root = document.getElementById('scanner-modal-root');
            return;
        }

        const headerCells = this.config.tableHeaders
            .map(header => `<th>${header.label}</th>`)
            .join('');

        this.root = document.createElement('div');
        this.root.id = 'scanner-modal-root';
        this.root.className = 'scanner-modal-root hidden';
        this.root.setAttribute('aria-hidden', 'true');

        this.root.innerHTML = `
            <div class="scanner-overlay" id="scanner-overlay"></div>
            <div class="scanner-card" role="dialog" aria-modal="true" aria-labelledby="scanner-title">
                <div class="scanner-header">
                    <h3 id="scanner-title">${this.config.title}</h3>
                    <div class="scanner-controls">
                        <button type="button" id="scanner-clear" title="Clear list">Clear</button>
                        <button type="button" id="scanner-close" title="Close (Esc)">Close</button>
                    </div>
                </div>
                <div class="scanner-body">
                    <div class="scanner-input-row">
                        <input id="scanner-input" class="scanner-input" autocomplete="off" placeholder="${this.config.placeholder}">
                        <button id="scanner-add" type="button" title="Add (Tab)">Add</button>
                    </div>
                    <div class="scanner-table-wrapper">
                        <table id="scanner-table" class="scanner-table" aria-live="polite">
                            <thead>
                                <tr>${headerCells}</tr>
                            </thead>
                            <tbody id="scanner-table-body"></tbody>
                        </table>
                    </div>
                </div>
                <div class="scanner-footer">
                    <div class="scanner-hint">
                        <div style="font-weight: bold; color: #3a56a6; margin-bottom: 2px; display: flex; align-items: center;">
                            <span style="font-size: 12px; margin-right: 6px;"><kbd>⌨️ Ctrl+Z</kbd> to remove last added sample</span>
                        </div>
                    </div>
                    <div class="scanner-actions">
                        <button id="scanner-edit" type="button">Edit (Ctrl + Enter)</button>
                        <button id="scanner-submit" type="button">Submit (Enter)</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.root);
    }

    bindEvents() {
        // Get DOM elements
        this.overlay = this.root.querySelector('#scanner-overlay');
        this.inputEl = this.root.querySelector('#scanner-input');
        this.tableBody = this.root.querySelector('#scanner-table-body');
        this.editBtn = this.root.querySelector('#scanner-edit');
        this.submitBtn = this.root.querySelector('#scanner-submit');
        this.clearBtn = this.root.querySelector('#scanner-clear');
        this.closeBtn = this.root.querySelector('#scanner-close');
        this.addBtn = this.root.querySelector('#scanner-add');

        // Table row removal
        this.tableBody.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('.scanner-remove-row');
            if (!removeBtn) return;
            const idx = Number(removeBtn.dataset.index);
            this.removeByIndex(idx);
        });

        // Button events
        if (this.addBtn) {
            this.addBtn.addEventListener('click', async () => {
                const v = this.inputEl.value.trim();
                if (!v) {
                    this.flash('Enter sample ID', 1200, true);
                    return;
                }
                await this.validateAndAppend(v);
            });
        }

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                this.samples = [];
                this.renderTable();
                this.inputEl.value = '';
                this.inputEl.focus();
            });
        }

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.closeModal());
        }

        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.closeModal());
        }

        if (this.editBtn) {
            this.editBtn.addEventListener('click', async () => {
                const v = this.inputEl.value.trim();
                if (v) {
                    await this.validateAndAppend(v);
                }
                this.bulkEdit();
            });
        }

        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', async () => {
                const v = this.inputEl.value.trim();
                if (v) {
                    await this.validateAndAppend(v);
                }
                this.submitAll();
            });
        }

        // Input events
        this.inputEl.addEventListener('keydown', async e => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const v = this.inputEl.value.trim();
                if (!v) {
                    this.flash('Enter sample ID', 1200, true);
                    return;
                }
                await this.validateAndAppend(v);
            } else if (e.key === 'Enter') {
                if (e.ctrlKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    const v = this.inputEl.value.trim();
                    if (v) {
                        await this.validateAndAppend(v);
                    }
                    await this.bulkEdit({ ctrlKey: true });
                    return;
                }

                e.preventDefault();
                e.stopPropagation();
                const v = this.inputEl.value.trim();
                if (v) {
                    await this.validateAndAppend(v);
                }
                this.submitAll();
            }
        });

        // Paste support
        this.inputEl.addEventListener('paste', (e) => {
            const paste = (e.clipboardData || window.clipboardData).getData('text');
            if (!paste) return;

            if (paste.includes('\n') || paste.includes(',') || paste.includes(';')) {
                e.preventDefault();
                const parts = paste.split(/[\n,;]/).map(s => s.trim()).filter(Boolean);
                this.processPastedItems(parts);
            }
        });

        // Keep tab inside modal
        this.root.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            if (e.key === 'Tab') {
                e.preventDefault();
                this.inputEl.focus();
            }
        });
    }

    async processPastedItems(parts) {
        for (const part of parts) {
            await this.validateAndAppend(part);
        }
    }

    setupGlobalKeyboardHandler() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();

                // Check if there are any selected rows in the changelist
                const selectedCheckboxes = document.querySelectorAll('input[name="_selected_action"]:checked');

                if (selectedCheckboxes.length > 0 && !this.isOpen) {
                    // Open the modal first
                    this.openModal();

                    // Get all selected sample IDs
                    const selectedSampleIds = Array.from(selectedCheckboxes).map(cb => cb.value);

                    // Validate and add each sample automatically
                    this.autoLoadSelectedSamples(selectedSampleIds);
                } else {
                    // Normal toggle behavior when no samples selected or modal already open
                    this.toggleModal();
                }

                return;
            }

            const isUndo = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z';
            if (this.isOpen && isUndo) {
                e.preventDefault();
                this.removeLast();
                return;
            }

            // Handle Enter for submit when modal is open but input not focused
            if (this.isOpen && e.key === 'Enter') {
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.bulkEdit();
                    return;
                }

                if (document.activeElement !== this.inputEl) {
                    e.preventDefault();
                    this.submitAll();
                }
            }
        });
    }

    openModal() {
        if (this.isOpen) return;
        this.root.classList.remove('hidden');
        this.root.classList.add('visible');
        this.root.setAttribute('aria-hidden', 'false');
        this.isOpen = true;

        setTimeout(() => {
            try {
                this.inputEl.focus();
                this.inputEl.select();
            } catch (e) {
                // ignore focus errors
            }
        }, 40);
    }

    closeModal() {
        if (!this.isOpen) return;
        this.root.classList.remove('visible');
        this.root.classList.add('hidden');
        this.root.setAttribute('aria-hidden', 'true');
        this.isOpen = false;
    }

    toggleModal() {
        if (this.isOpen) {
            this.closeModal();
        } else {
            this.openModal();
        }
    }

    renderTable() {
        this.tableBody.innerHTML = '';
        this.samples.forEach((sample, idx) => {
            const tr = document.createElement('tr');
            tr.dataset.index = idx;

            const cells = this.config.tableHeaders.map(header => {
                if (header.key === 'action') {
                    return `<td><button class="scanner-remove-row" data-index="${idx}" title="Remove">Remove</button></td>`;
                } else if (header.key === 'index') {
                    return `<td>${idx + 1}</td>`;
                } else {
                    const value = sample[header.key] || '';
                    return `<td class="${header.key === 'tests' ? 'tests-cell' : ''}" title="${this.escapeHtml(value)}">${this.escapeHtml(value)}</td>`;
                }
            }).join('');

            tr.innerHTML = cells;
            this.tableBody.appendChild(tr);
        });
    }

    escapeHtml(text) {
        return String(text || '').replace(/[&<>"']/g, m => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[m]));
    }

    async validateAndAppend(id) {
        const v = id.trim();
        if (!v) return false;

        // Prevent duplicates - check the actual sample ID field from your backend
        const duplicateCheck = this.samples.some(s =>
            s.sample_id === v || s.sampleId === v || s.id === v
        );

        if (duplicateCheck) {
            this.flash(`Duplicate: ${v}`, 1500, true);
            this.inputEl.value = '';
            return false;
        }

        this.inputEl.classList.add('scanner-busy');

        try {
            const resp = await fetch(this.config.validatePath, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ id: v })
            });

            if (!resp.ok) {
                const txt = await resp.text();
                throw new Error(`Server error: ${txt}`);
            }

            const data = await resp.json();

            if (!data || data.valid !== true) {
                this.flash(data?.error || `Invalid: ${v}`, 2200, true);
                this.inputEl.value = '';
                return false;
            }

            // Append sample - use the exact data structure from your backend
            this.samples.push(data.sample);
            this.renderTable();
            this.inputEl.value = '';
            return true;

        } catch (err) {
            console.error('Validate error:', err);
            this.flash('Validation error', 2400, true);
            this.inputEl.value = '';
            return false;
        } finally {
            this.inputEl.classList.remove('scanner-busy');
        }
    }

    removeLast() {
        if (!this.samples.length) {
            this.flash('No items to remove', 1200, true);
            return;
        }
        const removed = this.samples.pop();
        this.renderTable();
        this.inputEl.focus();
        // Use the correct field name for display
        const displayId = removed.sample_id || removed.sampleId || removed.id || 'item';
        this.flash(`Removed: ${displayId}`);
    }

    async autoLoadSelectedSamples(sampleIds) {
        if (!sampleIds || sampleIds.length === 0) {
            return;
        }

        // Filter out samples that are already in the scanner table
        const existingSampleIds = new Set();
        this.samples.forEach(sample => {
            // Check all possible ID fields
            if (sample.sample_id) existingSampleIds.add(sample.sample_id);
            if (sample.sampleId) existingSampleIds.add(sample.sampleId);
            if (sample.id) existingSampleIds.add(sample.id);
        });

        // Filter to only new samples not already in the scanner
        const newSampleIds = sampleIds.filter(id => !existingSampleIds.has(id));

        // If no new samples to add
        if (newSampleIds.length === 0) {
            const alreadyLoadedCount = sampleIds.length;
            this.flash(`All ${alreadyLoadedCount} sample(s) already in scanner`, 2000);
            this.inputEl.focus();
            return;
        }

        // Show message about new vs already loaded
        const alreadyLoadedCount = sampleIds.length - newSampleIds.length;
        if (alreadyLoadedCount > 0) {
            this.flash(`Loading ${newSampleIds.length} new sample(s), ${alreadyLoadedCount} already loaded`, 2000);
        } else {
            this.flash(`Loading ${newSampleIds.length} selected sample(s)...`, 1500);
        }

        let successCount = 0;
        let failCount = 0;

        // Process each NEW sample ID sequentially
        for (const sampleId of newSampleIds) {
            try {
                const success = await this.validateAndAppend(sampleId);
                if (success) {
                    successCount++;
                } else {
                    failCount++;
                }

                // Small delay to avoid overwhelming the server
                await this.sleep(100);

            } catch (error) {
                console.error(`Error loading sample ${sampleId}:`, error);
                failCount++;
            }
        }

        // Show summary
        if (successCount > 0) {
            const summary = `✓ Loaded ${successCount} sample(s)`;
            const extras = [];
            if (failCount > 0) extras.push(`${failCount} failed`);
            if (alreadyLoadedCount > 0) extras.push(`${alreadyLoadedCount} already loaded`);

            const fullMessage = extras.length > 0
                ? `${summary}, ${extras.join(', ')}`
                : summary;

            this.flash(fullMessage, 2500);
        } else if (failCount > 0) {
            this.flash(`Failed to load ${failCount} sample(s)`, 2000, true);
        }

        // Focus the input for additional scanning
        this.inputEl.focus();
    }

    // Helper method: Sleep utility for delays
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }


    removeByIndex(idx) {
        if (idx < 0 || idx >= this.samples.length) return;
        const removed = this.samples.splice(idx, 1)[0];
        this.renderTable();
        const displayId = removed.sample_id || removed.sampleId || removed.id || 'item';
        this.flash(`Removed: ${displayId}`);
    }

    async bulkEdit(opts = {}) {
        if (!this.samples.length) {
            this.flash('No samples to edit', 1200, true);
            return;
        }

        if (this.isSubmitting) {
            console.warn('bulkEdit: already submitting, ignoring duplicate call');
            return;
        }

        // Group samples by model type
        const sampleGroups = this.groupSamplesByModelType();

        // If mixed types, show error or handle accordingly
        if (Object.keys(sampleGroups).length > 1) {
            this.flash('Unable to edit mixed worklist samples. Please separate Enterprise and IHC worklist samples.', 4000, true);
            return;
        }

        // Get the model type and appropriate URL
        const modelType = Object.keys(sampleGroups)[0];
        const sampleIds = sampleGroups[modelType];

        const baseEditUrl = this.getBulkEditUrl(modelType);
        const ids = sampleIds.join(',');
        const q = encodeURIComponent(this.currentQuery || '');

        let url = baseEditUrl;
        url += url.includes('?') ? '&' : '?';
        url += `ids=${ids}`;
        if (q) {
            url += `&q=${q}`;
        }

        const features = 'noopener,noreferrer';

        // Delay window.open slightly to help browser focus the tab
        setTimeout(() => {
            const newWindow = window.open(url, '_blank', features);
            if (newWindow) {
                newWindow.focus();
            }
        }, 50);

//        this.flash(`Bulk edit opened for ${modelType} samples`, 2000);
    }

    /**
     * Group samples by their model type
     */
    groupSamplesByModelType() {
        const groups = {};

        for (const sample of this.samples) {
            const modelType = sample.model_type || 'sample';
            const sampleId = sample.sample_id || sample.sampleId || sample.id;

            if (!groups[modelType]) {
                groups[modelType] = [];
            }
            groups[modelType].push(sampleId);
        }

        return groups;
    }

    /**
     * Get the appropriate bulk edit URL based on model type
     */
    getBulkEditUrl(modelType) {
        switch (modelType) {
            case 'ihc':
                return '/gulfcoastpathologists/bulk-edit-ihc-samples/';
            case 'sample':
            default:
                return '/gulfcoastpathologists/bulk-edit-samples/';
        }
    }



    async submitAll() {
        if (!this.samples.length) {
            this.flash('No samples to submit', 1200, true);
            return;
        }
        if (this.isSubmitting) {
            console.warn('submitAll: already submitting');
            return;
        }
        this.isSubmitting = true;
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Submitting...';

        const ids = this.samples.map(s => s.sample_id || s.sampleId || s.id);
        let data;
        try {
            const resp = await fetch(this.config.submitPath, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ ids })
            });

            // Handle non-ok responses
            if (!resp.ok) {
                const errorText = await resp.text();
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                    // Check if it's a validation error
                    if (errorData.status === "error" && errorData.message) {
                        this.flash(errorData.message, 5000, true);
                        this._resetSubmitState();
                        return;
                    }
                } catch {
                    // Not JSON, throw original error
                    throw new Error(`HTTP ${resp.status}: ${errorText}`);
                }
                throw new Error(errorData.message || `HTTP ${resp.status}`);
            }

            data = await resp.json();

            // Check for validation errors in successful responses
            if (data.status === "error") {
                this.flash(data.message || "Validation failed", 5000, true);
                this._resetSubmitState();
                return;
            }

        } catch (err) {
            console.error('Submit error:', err);
            this.flash('Submit error: ' + err.message, 3000, true);
            this._resetSubmitState();
            return;
        }

        // 1) If backend returned form HTML for QC or smearing:
        if (data.status === 'form_html') {
            this.openFormPopup(data);
            return;
        }

        // 2) Automatic results
        if (data.action_results) {
            const ok = data.action_results.filter(r => r.status === 'success').length;
            const fail = data.action_results.length - ok;
            if (ok) this.flash(`Automatically processed ${ok} samples`, 2000);
            if (fail) this.flash(`${fail} failures`, 2000, true);
        }

        // 3) Routing
        if (data.routing_results) {
            this.flash(`Routed ${data.routing_results.length} samples`, 2000);
        }

        // 4) Summary
        if (data.summary) {
            const s = data.summary;
            this.flash(`Total: ${s.automatic_samples + s.routed_samples} processed`, 3000);
        }

        // 5) Cleanup and reload
        this.samples = [];
        this.renderTable();
        this.inputEl.value = '';
        this.inputEl.focus();
        this.closeModal();
        window.location.reload();
    }


    async openFormPopup(data) {
        // Open blank popup window
        const popup = window.open("", "scanpopup", "width=1000,height=700,scrollbars=yes");
        if (!popup) {
            this.flash("Popup blocked—please enable popups.", true);
            this._resetSubmitState();
            return;
        }

        popup.document.open();
        popup.document.write(data.html);
        popup.document.close();

        popup.onload = () => {
            const form = popup.document.querySelector("form");
            if (!form) {
                this.flash("No form found in popup.", true);
                popup.close();
                return;
            }

            // Check if this is the smearing selection form (it has its own submission logic)
            const isSmearingForm = form.id === "sample-data-form" ||
                popup.document.querySelector("#smearing-checkbox") !== null;

            if (isSmearingForm) {
                // Let the template's built-in JavaScript handle submission
                console.log("Smearing form detected - using template's own submission handler");

                // Just handle the close event to reset scanner state
                popup.addEventListener("beforeunload", () => {
                    this._resetSubmitState();
                    // Reload parent window after popup closes
                    window.location.reload();
                });

                return; // Exit early - don't attach our own submit handler
            }

            // For other forms (like QC status), handle submission here
            // Find the Cancel button
            const cancelBtn = popup.document.querySelector(".btn.btn-secondary, .cancel-btn");
            if (cancelBtn) {
                cancelBtn.addEventListener("click", (e) => {
                    e.preventDefault();
                    popup.close();
                    this._resetSubmitState();
                });
            }

            // Handle popup close
            popup.addEventListener("beforeunload", () => {
                this._resetSubmitState();
            });

            form.addEventListener("submit", async (e) => {
                e.preventDefault();

                // Build the IDs array
                const idsArray = [];
                this.samples.forEach((s) => {
                    let idStr;
                    if (typeof s === "string") {
                        idStr = s;
                    } else if (s && (s.sample_id || s.id || s.sampleId)) {
                        idStr = s.sample_id || s.id || s.sampleId;
                    } else {
                        idStr = String(s);
                    }
                    idsArray.push(idStr);
                });

                // QC status form
                const qcStatusEl = popup.document.querySelector("select[name='qc_status']");
                const qcStatusValue = qcStatusEl ? qcStatusEl.value : null;

                const payload = {
                    ids: idsArray,
                    qc_status: qcStatusValue,
                    apply: 1
                };

                console.group("Form submit JSON payload");
                console.log(payload);
                console.groupEnd();

                try {
                    const fetchOptions = {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": data.csrf_token
                        },
                        body: JSON.stringify(payload),
                    };

                    const response = await fetch(data.post_url, fetchOptions);
                    if (!response.ok) {
                        const text = await response.text();
                        throw new Error(`Server error: ${text}`);
                    }

                    const json = await response.json();
                    this.flash(json.message || "Form completed", 3000);
                } catch (err) {
                    console.error("Error submitting form:", err);
                    this.flash(`Error submitting form: ${err.message}`, 5000, true);
                } finally {
                    popup.close();
                    this.closeModal();
                    window.location.reload();
                }
            });
        };
    }




    _resetSubmitState() {
        this.isSubmitting = false;
        this.submitBtn.disabled = false;
        this.submitBtn.textContent = 'Submit (Enter)';
    }


    flash(msg, duration = 2200, isError = false) {
        let toast = document.getElementById('scanner-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'scanner-toast';
            toast.className = 'scanner-toast';
            document.body.appendChild(toast);
        }

        toast.textContent = msg;
        toast.classList.add('visible');

        if (isError) {
            toast.classList.add('error');
        } else {
            toast.classList.remove('error');
        }

        setTimeout(() => {
            toast.classList.remove('visible');
            toast.classList.remove('error');
        }, duration);
    }

    injectCSS() {
        if (document.getElementById('scanner-inline-css')) return;

        const css = `
        /* ==== Scanner Modal Styles ==== */
        .scanner-modal-root.hidden { display: none; }
        .scanner-modal-root.visible { display: block; }

        .scanner-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            z-index: 2000;
        }

        .scanner-card {
            position: fixed;
            top: 10%;
            left: 50%;
            transform: translateX(-50%);
            width: min(1100px, 96%);
            max-height: 76vh;
            overflow: hidden;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 16px 40px rgba(10,10,20,0.35);
            z-index: 2001;
            display: flex;
            flex-direction: column;
        }

        .scanner-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
        }

        .scanner-header h3 {
            margin: 0;
            font-size: 18px;
        }

        .scanner-controls button {
            margin-left: 8px;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #ddd;
            background: #fafafa;
            cursor: pointer;
        }

        .scanner-body {
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow: auto;
        }

        .scanner-input-row {
            display: flex;
            gap: 8px;
        }

        .scanner-input {
            flex: 1;
            padding: 12px 14px;
            border-radius: 8px;
            border: 1px solid #d6d6d6;
            font-size: 16px;
            outline: none;
        }

        .scanner-input:focus {
            border-color: #7aa7ff;
            box-shadow: 0 0 0 3px rgba(122,167,255,0.12);
        }

        .scanner-input-row button {
            padding: 10px 14px;
            border-radius: 8px;
            border: none;
            background: #f0f4ff;
            cursor: pointer;
        }

        .scanner-table-wrapper {
            max-height: 42vh;
            overflow: auto;
            border-radius: 8px;
            border: 1px solid #eaecef;
            background: #fff;
            padding: 8px;
        }

        .scanner-table {
            width: 100%;
            border-collapse: collapse;
            font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
        }

        .scanner-table thead th {
            position: sticky;
            top: 0;
            background: linear-gradient(180deg, #f7f9fc, #ffffff);
            border-bottom: 2px solid #eef1f6;
            padding: 8px 10px;
            text-align: left;
            font-size: 13px;
            color: #3a3f46;
        }

        .scanner-table tbody td {
            padding: 10px 8px;
            border-bottom: 1px solid #f1f4f8;
            font-size: 13px;
            color: #222;
        }

        .scanner-table tbody tr:nth-child(even) {
            background: #fbfcfe;
        }

        .scanner-table tbody tr:hover {
            background: #f0f6ff;
        }

        .scanner-remove-row {
            background: #fff;
            border: 1px solid #e0e6ef;
            padding: 6px 8px;
            border-radius: 6px;
            cursor: pointer;
        }

        .scanner-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 16px;
            border-top: 1px solid #eee;
        }

        .scanner-hint {
            color: #333;
            background: #f0f4ff;
            font-size: 13px;
            padding: 8px 12px;
            border-radius: 6px;
        }

        .scanner-hint kbd {
            background: #333;
            border: 1px solid #777;
            border-radius: 3px;
            padding: 2px 4px;
            font-size: 11px;
            color: #fff;
        }

        .scanner-actions button {
            padding: 8px 14px;
            border-radius: 8px;
            border: none;
            background: #357ae8;
            color: white;
            cursor: pointer;
            margin-left: 8px;
        }

        .scanner-actions button:hover {
            background: #2c6bd6;
        }

        .scanner-actions button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .scanner-toast {
            position: fixed;
            right: 18px;
            top: 18px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px 14px;
            border-radius: 8px;
            z-index: 3000;
            opacity: 0;
            transform: translateY(-6px);
            transition: opacity 0.18s ease, transform 0.18s ease;
            pointer-events: none;
        }

        .scanner-toast.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .scanner-toast.error {
            background: rgba(200,55,65,0.92) !important;
        }

        .scanner-input.scanner-busy {
            background-image: linear-gradient(90deg, rgba(0,0,0,0.03), rgba(0,0,0,0));
            background-repeat: no-repeat;
            background-size: 20px 20px;
        }

        .scanner-table td.tests-cell {
            max-width: 220px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .scanner-table td.tests-cell:hover {
            white-space: normal;
            background: #f8fbff;
        }
        `;

        const style = document.createElement('style');
        style.id = 'scanner-inline-css';
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
    }

    // API for debugging
    getSamples() {
        return this.samples.slice();
    }

    open() {
        this.openModal();
    }

    close() {
        this.closeModal();
    }

    toggle() {
        this.toggleModal();
    }

    // Helper method to build generic form URLs
    buildGenericFormUrl(formAction) {
        // Build URL based on action method and sample IDs
        const baseUrl = '/admin/sample/sample/';
        const params = new URLSearchParams({
            'pending_action': formAction.action,
            'sample_ids': formAction.sample_ids.join(','),
            'action_method': formAction.action_method
        });

        return `${baseUrl}?${params.toString()}`;
    }

    // Optional: Add method to manually close scanner and reload after forms are done
    completeFormProcessing() {
        this.flash('All forms completed! Closing scanner and refreshing page...', 2000);
        setTimeout(() => {
            this.closeModal();
            window.location.reload();
        }, 2000);
    }

}


// Expose the class globally
window.GenericScanner = GenericScanner;

