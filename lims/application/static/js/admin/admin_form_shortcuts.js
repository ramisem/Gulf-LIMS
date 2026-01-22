// admin_form_shortcuts.js - Global keyboard shortcuts for Django admin form buttons
// Ctrl+S: Save (Save and continue editing)
// Ctrl+Q: Return to changelist
// Ctrl+Alt+S: Save and add another

(function() {
    'use strict';

    /**
     * Initialize keyboard shortcuts for form buttons
     */
    function initializeFormShortcuts() {
        console.log('[FormShortcuts] Initializing admin form keyboard shortcuts...');
        setupKeyboardShortcuts();
    }

    /**
     * Find the Save button (Save and continue editing)
     */
    function getSaveButton() {
        return document.querySelector('input[name="_continue"][type="submit"]');
    }

    /**
     * Find the Return link
     */
    function getReturnLink() {
        // Look for any anchor tag with class containing 'btn' and 'secondary'
        const allLinks = document.querySelectorAll('a.btn.btn-secondary');
        for (const link of allLinks) {
            // Check if it contains "Return" or "Close" text
            if (link.textContent.includes('Return') || link.textContent.includes('Close')) {
                return link;
            }
        }

        // Fallback: look for any link containing "changelist"
        return document.querySelector('a[href*="changelist"]');
    }

    /**
     * Find the Save and add another button
     */
    function getSaveAndAddAnotherButton() {
        return document.querySelector('input[name="_addanother"][type="submit"]');
    }

    /**
     * Setup global keyboard shortcuts
     */
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            let handled = false;

            // Ctrl+S - Save (Save and continue editing)
            if (e.ctrlKey && e.key === 's' && !e.altKey && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();

                const saveBtn = getSaveButton();
                if (saveBtn) {
                    console.log('[FormShortcuts] ✓ Ctrl+S: Clicking Save');
                    flashButton(saveBtn);
                    saveBtn.click();
                    handled = true;
                } else {
                    console.log('[FormShortcuts] ✗ Save button not found');
                }
            }

            // Ctrl+Q - Return to changelist
            else if (e.ctrlKey && e.key === 'q' && !e.altKey && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();

                const returnLink = getReturnLink();
                if (returnLink) {
                    console.log('[FormShortcuts] ✓ Ctrl+Q: Navigating Return');
                    flashLink(returnLink);

                    setTimeout(() => {
                        const href = returnLink.getAttribute('href') || returnLink.href;

                        // If href is '#' / empty OR element has an onclick handler, trigger a real click
                        if (href === '#' || href.trim() === '' || returnLink.hasAttribute('onclick')) {
                            // try the straightforward DOM click()
                            try {
                                returnLink.click();
                            } catch (err) {
                                // fallback: dispatch a MouseEvent if click() doesn't work
                                const ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                                returnLink.dispatchEvent(ev);
                            }
                        } else {
                            // real navigation for normal hrefs
                            window.location.href = href;
                        }
                    }, 100);
                    handled = true;
                } else {
                    console.log('[FormShortcuts] ✗ Return link not found');
                }
            }

            // Ctrl+Shift+S - Save and add another (Shift key added to avoid conflicts)
            else if (e.ctrlKey && e.shiftKey && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                e.stopPropagation();

                const addAnotherBtn = getSaveAndAddAnotherButton();
                if (addAnotherBtn) {
                    console.log('[FormShortcuts] ✓ Ctrl+Shift+S: Clicking Save and add another');
                    flashButton(addAnotherBtn);
                    addAnotherBtn.click();
                    handled = true;
                } else {
                    console.log('[FormShortcuts] ✗ Save and add another button not found');
                }
            }

            if (handled) {
                return false;
            }
        }, true);

        console.log('[FormShortcuts] ✓ Keyboard shortcuts active:');
        console.log('  • Ctrl+S: Save (and continue editing)');
        console.log('  • Ctrl+Q: Return to changelist');
        console.log('  • Ctrl+Shift+S: Save and add another');
    }


    /**
     * Visual feedback for button click
     */
    function flashButton(buttonElement) {
        const originalBg = buttonElement.style.backgroundColor;
        const originalTransform = buttonElement.style.transform;
        const originalTransition = buttonElement.style.transition;

        buttonElement.style.transition = 'all 0.15s ease';
        buttonElement.style.transform = 'scale(0.95)';
        buttonElement.style.opacity = '0.8';

        setTimeout(() => {
            buttonElement.style.transform = originalTransform;
            buttonElement.style.opacity = '1';
            setTimeout(() => {
                buttonElement.style.transition = originalTransition;
            }, 150);
        }, 150);
    }

    /**
     * Visual feedback for link click
     */
    function flashLink(linkElement) {
        const originalBg = linkElement.style.backgroundColor;
        const originalTransform = linkElement.style.transform;
        const originalTransition = linkElement.style.transition;

        linkElement.style.transition = 'all 0.15s ease';
        linkElement.style.transform = 'scale(0.95)';
        linkElement.style.opacity = '0.7';

        setTimeout(() => {
            linkElement.style.transform = originalTransform;
            linkElement.style.opacity = '1';
            setTimeout(() => {
                linkElement.style.transition = originalTransition;
            }, 150);
        }, 150);
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFormShortcuts);
    } else {
        initializeFormShortcuts();
    }

    // Expose API for manual control if needed
    window.AdminFormShortcuts = {
        triggerSave: function() {
            const btn = getSaveButton();
            if (btn) {
                console.log('[FormShortcuts] Manually triggering Save');
                btn.click();
            }
        },
        triggerReturn: function() {
            const link = getReturnLink();
            if (link) {
                console.log('[FormShortcuts] Manually triggering Return');
                window.location.href = link.getAttribute('href');
            }
        },
        triggerAddAnother: function() {
            const btn = getSaveAndAddAnotherButton();
            if (btn) {
                console.log('[FormShortcuts] Manually triggering Save and add another');
                btn.click();
            }
        }
    };

})();
