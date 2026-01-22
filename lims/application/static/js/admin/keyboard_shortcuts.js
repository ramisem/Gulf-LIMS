// keyboard_shortcuts.js - Modern keyboard shortcuts popup with EXPANDABLE SECTIONS

(function() {
    'use strict';

    const SHORTCUTS = [
        {
            category: 'Generic Edit Page Actions',
            items: [
                { key: 'Ctrl + S', description: 'Save' },
                { key: 'Ctrl + Q', description: 'Return' },
                { key: 'Ctrl + Shift + S', description: 'Save and add another' }
            ]
        },
        {
            category: 'Tab Navigation',
            items: [
                { key: 'Ctrl + Left / Right', description: 'Navigate horizontal tabs' },
                { key: 'Ctrl + Up / Down', description: 'Navigate vertical tabs ' }
            ]
        },
        {
            category: 'Scanner',
            items: [
                { key: 'Esc', description: 'Open/close scanner panel' },
                { key: 'Enter', description: 'Submit samples for executing pending actions / routing' },
                { key: 'Ctrl + Enter', description: 'Edit sample info' },
                { key: 'Ctrl + Z', description: 'Remove last added sample' },
            ]
        },
        {
            category: 'Accessioning Edit Page Actions',
            items: [
                { key: 'Ctrl + S', description: 'Save' },
                { key: 'Ctrl + Q', description: 'Return' },
                { key: 'Ctrl + Enter', description: 'Generate Accession' },
                { key: 'Ctrl + Space', description: 'Create Samples' }
            ]
        }
    ];

    /**
     * Initialize keyboard shortcuts popup
     */
    function initializeShortcutsPanel() {
        createShortcutsPanel();
        attachEventListeners();
        console.log('[KeyboardShortcuts] Initialized');
    }

    /**
     * Create the shortcuts popup HTML structure
     */
    function createShortcutsPanel() {
        // Check if already exists
        if (document.getElementById('keyboard-shortcuts-panel')) {
            return;
        }

        // Create icon button
        const iconButton = document.createElement('button');
        iconButton.id = 'keyboard-shortcuts-btn';
        iconButton.className = 'keyboard-shortcuts-icon-btn';
        iconButton.innerHTML = '⌨️';
        iconButton.title = 'System Keyboard Shortcuts (Alt+?)';
        iconButton.setAttribute('aria-label', 'Keyboard shortcuts');

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'keyboard-shortcuts-overlay';
        overlay.className = 'keyboard-shortcuts-overlay';

        // Create modal panel
        const panel = document.createElement('div');
        panel.id = 'keyboard-shortcuts-panel';
        panel.className = 'keyboard-shortcuts-panel';

        // Create header
        const header = document.createElement('div');
        header.className = 'keyboard-shortcuts-header';
        header.innerHTML = `
            <div class="keyboard-shortcuts-title-wrapper">
                <span class="keyboard-shortcuts-title-icon">⌨️</span>
                <h2 class="keyboard-shortcuts-title">System Keyboard Shortcuts</h2>
            </div>
            <button class="keyboard-shortcuts-close" aria-label="Close shortcuts">&times;</button>
        `;

        // Create content
        const content = document.createElement('div');
        content.className = 'keyboard-shortcuts-content';

        SHORTCUTS.forEach((section, index) => {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'keyboard-shortcuts-section';
            sectionDiv.setAttribute('data-section-index', index);

            // Create collapsible header
            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'keyboard-shortcuts-section-header';
            sectionHeader.innerHTML = `
                <span class="keyboard-shortcuts-toggle-icon">▼</span>
                <h3 class="keyboard-shortcuts-category">${escapeHtml(section.category)}</h3>
            `;
            sectionHeader.style.cursor = 'pointer';
            sectionHeader.style.userSelect = 'none';

            // Create items container
            const itemsContainer = document.createElement('div');
            itemsContainer.className = 'keyboard-shortcuts-items';
            itemsContainer.setAttribute('data-section', index);

            section.items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'keyboard-shortcuts-item';
                itemDiv.innerHTML = `
                    <kbd class="keyboard-shortcuts-key">${escapeHtml(item.key)}</kbd>
                    <span class="keyboard-shortcuts-desc">${escapeHtml(item.description)}</span>
                `;
                itemsContainer.appendChild(itemDiv);
            });

            sectionDiv.appendChild(sectionHeader);
            sectionDiv.appendChild(itemsContainer);
            content.appendChild(sectionDiv);
        });

        // Create footer
        const footer = document.createElement('div');
        footer.className = 'keyboard-shortcuts-footer';
        footer.innerHTML = `
            <p>Press <kbd class="keyboard-shortcuts-key">Alt+?</kbd> to toggle this panel</p>
        `;

        panel.appendChild(header);
        panel.appendChild(content);
        panel.appendChild(footer);

        // Append to body
        document.body.appendChild(overlay);
        document.body.appendChild(panel);
        document.body.appendChild(iconButton);

        // Inject styles
        injectStyles();
    }

    /**
     * Attach event listeners
     */
    function attachEventListeners() {
        const btn = document.getElementById('keyboard-shortcuts-btn');
        const panel = document.getElementById('keyboard-shortcuts-panel');
        const overlay = document.getElementById('keyboard-shortcuts-overlay');
        const closeBtn = document.querySelector('.keyboard-shortcuts-close');

        // Toggle on button click
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            togglePanel();
        });

        // Close on overlay click
        overlay.addEventListener('click', closePanel);

        // Close on close button click
        closeBtn.addEventListener('click', closePanel);

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePanel();
            }
            // Toggle on Alt+?
            if (e.altKey && (e.key === '?' || e.key === '/')) {
                e.preventDefault();
                togglePanel();
            }
        });

        // Prevent close when clicking inside panel
        panel.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Attach section toggle listeners
        const sectionHeaders = document.querySelectorAll('.keyboard-shortcuts-section-header');
        sectionHeaders.forEach(header => {
            header.addEventListener('click', (e) => {
                const section = header.closest('.keyboard-shortcuts-section');
                const items = section.querySelector('.keyboard-shortcuts-items');
                const toggleIcon = header.querySelector('.keyboard-shortcuts-toggle-icon');

                items.classList.toggle('collapsed');
                toggleIcon.classList.toggle('rotated');
            });
        });
    }

    /**
     * Toggle panel visibility
     */
    function togglePanel() {
        const panel = document.getElementById('keyboard-shortcuts-panel');
        const overlay = document.getElementById('keyboard-shortcuts-overlay');

        if (panel.classList.contains('keyboard-shortcuts-open')) {
            closePanel();
        } else {
            panel.classList.add('keyboard-shortcuts-open');
            overlay.classList.add('keyboard-shortcuts-open');
        }
    }

    /**
     * Close panel
     */
    function closePanel() {
        const panel = document.getElementById('keyboard-shortcuts-panel');
        const overlay = document.getElementById('keyboard-shortcuts-overlay');
        panel.classList.remove('keyboard-shortcuts-open');
        overlay.classList.remove('keyboard-shortcuts-open');
    }

    /**
     * Inject CSS styles
     */
    function injectStyles() {
        if (document.getElementById('keyboard-shortcuts-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'keyboard-shortcuts-styles';
        style.textContent = `
            /* Icon button - FIXED POSITION ALWAYS ON TOP RIGHT */
            #keyboard-shortcuts-btn {
                position: fixed;
                top: 60px;
                right: 6px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                width: 25px;
                height: 25px;
                font-size: 18px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 2px 6px rgba(102, 126, 234, 0.35);
                z-index: 998;
                padding: 0;
            }

            #keyboard-shortcuts-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.45);
                background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            }

            #keyboard-shortcuts-btn:active {
                transform: translateY(0);
                box-shadow: 0 2px 6px rgba(102, 126, 234, 0.35);
            }

            /* Overlay - HIGH Z-INDEX */
            .keyboard-shortcuts-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0);
                z-index: 1998;
                transition: background 0.3s ease;
            }

            .keyboard-shortcuts-overlay.keyboard-shortcuts-open {
                display: block;
                background: rgba(0, 0, 0, 0.4);
            }

            /* Panel - VERY HIGH Z-INDEX TO STAY ON TOP */
            .keyboard-shortcuts-panel {
                display: flex;
                flex-direction: column;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.95);
                width: 500px;
                max-height: 80vh;
                background: white;
                border-radius: 12px;
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.25);
                z-index: 1999;
                overflow: hidden;
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: none;
            }

            .keyboard-shortcuts-panel.keyboard-shortcuts-open {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
                pointer-events: auto;
            }

            /* Header */
            .keyboard-shortcuts-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                flex-shrink: 0;
            }

            .keyboard-shortcuts-title-wrapper {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .keyboard-shortcuts-title-icon {
                font-size: 24px;
            }

            .keyboard-shortcuts-title {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
                letter-spacing: -0.3px;
            }

            .keyboard-shortcuts-close {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                font-size: 28px;
                width: 32px;
                height: 32px;
                cursor: pointer;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s ease;
                flex-shrink: 0;
            }

            .keyboard-shortcuts-close:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            /* Content */
            .keyboard-shortcuts-content {
                overflow-y: auto;
                flex: 1;
                padding: 0;
            }

            .keyboard-shortcuts-content::-webkit-scrollbar {
                width: 6px;
            }

            .keyboard-shortcuts-content::-webkit-scrollbar-track {
                background: #f1f5f9;
            }

            .keyboard-shortcuts-content::-webkit-scrollbar-thumb {
                background: #cbd5e1;
                border-radius: 3px;
            }

            .keyboard-shortcuts-content::-webkit-scrollbar-thumb:hover {
                background: #94a3b8;
            }

            /* Section */
            .keyboard-shortcuts-section {
                border-bottom: 1px solid #e5e7eb;
                transition: all 0.2s ease;
            }

            .keyboard-shortcuts-section:last-child {
                border-bottom: none;
            }

            /* Section Header - Clickable */
            .keyboard-shortcuts-section-header {
                padding: 16px 20px;
                display: flex;
                align-items: center;
                gap: 12px;
                background: #f8fafc;
                transition: all 0.2s ease;
            }

            .keyboard-shortcuts-section-header:hover {
                background: #f0f4ff;
            }

            .keyboard-shortcuts-section-header:active {
                background: #e8ecff;
            }

            /* Toggle Icon */
            .keyboard-shortcuts-toggle-icon {
                display: inline-block;
                font-size: 12px;
                color: #667eea;
                font-weight: bold;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 16px;
            }

            .keyboard-shortcuts-toggle-icon.rotated {
                transform: rotate(-90deg);
            }

            /* Category */
            .keyboard-shortcuts-category {
                margin: 0;
                font-size: 13px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                color: #667eea;
                flex: 1;
            }

            /* Items Container - Collapsible */
            .keyboard-shortcuts-items {
                display: flex;
                flex-direction: column;
                gap: 0;
                max-height: 500px;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                padding: 8px 20px 16px 20px;
                background: white;
            }

            .keyboard-shortcuts-items.collapsed {
                max-height: 0;
                padding: 0 20px;
                overflow: hidden;
            }

            /* Items */
            .keyboard-shortcuts-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 12px;
                background: #f8fafc;
                border-radius: 6px;
                transition: all 0.2s ease;
                margin-bottom: 8px;
            }

            .keyboard-shortcuts-item:last-child {
                margin-bottom: 0;
            }

            .keyboard-shortcuts-item:hover {
                background: #f0f4ff;
                transform: translateX(4px);
            }

            /* Key */
            .keyboard-shortcuts-key {
                background: white;
                color: #667eea;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #e2e8f0;
                font-family: 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
                min-width: 100px;
                text-align: center;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }

            /* Description */
            .keyboard-shortcuts-desc {
                color: #475569;
                font-size: 13px;
                flex: 1;
            }

            /* Footer */
            .keyboard-shortcuts-footer {
                background: #f8fafc;
                padding: 12px 20px;
                border-top: 1px solid #e2e8f0;
                font-size: 12px;
                color: #64748b;
                text-align: center;
                flex-shrink: 0;
            }

            .keyboard-shortcuts-footer p {
                margin: 0;
            }

            /* Responsive */
            @media (max-width: 600px) {
                #keyboard-shortcuts-btn {
                    top: 60px;
                    right: 6px;
                    width: 25px;
                    height: 25px;
                    font-size: 16px;
                }

                .keyboard-shortcuts-panel {
                    width: calc(100vw - 24px);
                    max-height: 70vh;
                }

                .keyboard-shortcuts-title {
                    font-size: 16px;
                }

                .keyboard-shortcuts-item {
                    flex-direction: column;
                    align-items: flex-start;
                }

                .keyboard-shortcuts-key {
                    width: 100%;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeShortcutsPanel);
    } else {
        initializeShortcutsPanel();
    }

})();
