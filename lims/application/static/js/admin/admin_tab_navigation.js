// admin_tab_navigation.js - Universal keyboard shortcuts for Django admin tab navigation
// Supports:
// 1. Bulk edit pages: Vertical tabs + context-specific horizontal tabs (Ctrl+Up/Down + Ctrl+Left/Right)
// 2. Regular Django admin: Standalone horizontal tabs (Ctrl+Left/Right)
// Circular navigation enabled for all scenarios

(function() {
    'use strict';

    let verticalTabElements = [];
    let currentVerticalTabIndex = -1;
    let hasVerticalTabs = false;

    /**
     * Initialize tab navigation
     */
    function initializeTabNavigation() {
        console.log('[TabNav] Initializing tab navigation...');

        // Check if we have vertical tabs (bulk edit mode)
        hasVerticalTabs = document.querySelector('.vertical-tabs') !== null;

        if (hasVerticalTabs) {
            initializeVerticalTabs();
            console.log(`[TabNav] Mode: Bulk Edit (Vertical tabs: ${verticalTabElements.length})`);
        } else {
            console.log('[TabNav] Mode: Regular Admin (Standalone horizontal tabs)');
        }

        setupKeyboardShortcuts();
    }

    /**
     * Initialize vertical tabs (bulk edit mode only)
     */
    function initializeVerticalTabs() {
        verticalTabElements = [];

        const verticalTabsContainers = document.querySelectorAll('.vertical-tabs');

        for (const container of verticalTabsContainers) {
            const tabs = container.querySelectorAll('.nav-link, a');
            if (tabs.length > 0) {
                verticalTabElements = Array.from(tabs);
                console.log(`[TabNav] Found ${verticalTabElements.length} vertical tabs`);
                updateCurrentVerticalTabIndex();
                return;
            }
        }
    }

    /**
     * Get all horizontal tabs (context-aware for both modes)
     */
    function getContextualHorizontalTabs() {
        if (hasVerticalTabs) {
            // Bulk edit mode: Get tabs from active vertical tab pane
            return getTabsFromActivePane();
        } else {
            // Regular admin mode: Get standalone horizontal tabs
            return getStandaloneHorizontalTabs();
        }
    }

    /**
     * Get standalone horizontal tabs (for regular Django admin changeform pages)
     * Looks for nav-tabs with standard Django admin structure
     */
    function getStandaloneHorizontalTabs() {
        // First, try to find tabs with id="jazzy-tabs" (Jazzmin/common pattern)
        let tabs = [];

        // Try to find in common Django admin tab patterns
        const tabContainers = document.querySelectorAll('ul.nav-tabs, .nav-tabs, [role="tablist"]');

        for (const container of tabContainers) {
            // Skip if inside vertical tabs
            if (container.closest('.vertical-tabs')) {
                continue;
            }

            // Get all tab links
            const tabLinks = container.querySelectorAll('a.nav-link, a[data-toggle="tab"], a[data-toggle="pill"]');

            if (tabLinks.length > 0) {
                tabs = Array.from(tabLinks);
                console.log(`[TabNav] Found ${tabs.length} standalone horizontal tabs in container`);
                return tabs;
            }
        }

        // Fallback: Look for nav-link elements directly
        if (tabs.length === 0) {
            const allNavLinks = document.querySelectorAll('.nav-link');
            tabs = Array.from(allNavLinks).filter(tab => {
                // Exclude vertical tabs and flex-column layouts
                return !tab.closest('.vertical-tabs') &&
                       !tab.closest('[aria-orientation="vertical"]') &&
                       !tab.classList.contains('flex-column');
            });

            if (tabs.length > 0) {
                console.log(`[TabNav] Found ${tabs.length} standalone tabs via fallback selector`);
                return tabs;
            }
        }

        console.log('[TabNav] No standalone horizontal tabs found');
        return [];
    }

    /**
     * Get horizontal tabs from the currently active vertical tab pane (bulk edit mode)
     */
    function getTabsFromActivePane() {
        const activePaneId = getActiveVerticalTabPaneId();

        if (!activePaneId) {
            console.log('[TabNav] No active pane ID found');
            return [];
        }

        const activePane = document.getElementById(activePaneId);

        if (!activePane) {
            console.log(`[TabNav] Active pane with ID "${activePaneId}" not found`);
            return [];
        }

        const navTabsContainers = activePane.querySelectorAll('.nav-tabs');

        for (const container of navTabsContainers) {
            const tabs = container.querySelectorAll('a.nav-link, a[data-toggle="tab"]');
            if (tabs.length > 0) {
                console.log(`[TabNav] Found ${tabs.length} horizontal tabs in pane "${activePaneId}"`);
                return Array.from(tabs);
            }
        }

        return [];
    }

    /**
     * Get the currently active vertical tab pane ID (bulk edit mode)
     */
    function getActiveVerticalTabPaneId() {
        const activeTab = document.querySelector('.vertical-tabs .nav-link.active');
        if (!activeTab) {
            return null;
        }

        const href = activeTab.getAttribute('href');
        if (href && href.startsWith('#')) {
            return href.substring(1);
        }
        return href;
    }

    /**
     * Get current active horizontal tab index
     */
    function getCurrentHorizontalTabIndex(tabs) {
        if (tabs.length === 0) return -1;

        const activeTabIndex = tabs.findIndex(tab => {
            return tab.classList.contains('active') ||
                   tab.getAttribute('aria-selected') === 'true';
        });

        return activeTabIndex >= 0 ? activeTabIndex : 0;
    }

    /**
     * Update the current active vertical tab index (bulk edit mode)
     */
    function updateCurrentVerticalTabIndex() {
        if (verticalTabElements.length === 0) return;

        currentVerticalTabIndex = verticalTabElements.findIndex(tab => {
            return tab.classList.contains('active') ||
                   tab.getAttribute('aria-selected') === 'true' ||
                   tab.parentElement?.classList.contains('active');
        });

        if (currentVerticalTabIndex === -1) {
            currentVerticalTabIndex = 0;
        }
    }

    /**
     * Navigate to a specific horizontal tab by index (circular)
     */
    function navigateToHorizontalTab(index) {
        const tabs = getContextualHorizontalTabs();

        if (tabs.length === 0) {
            console.log('[TabNav] No horizontal tabs available');
            return false;
        }

        // Circular navigation with proper modulo
        const wrappedIndex = ((index % tabs.length) + tabs.length) % tabs.length;

        const targetTab = tabs[wrappedIndex];
        console.log(`[TabNav] Navigating to horizontal tab ${wrappedIndex + 1}/${tabs.length}: "${targetTab.textContent.trim()}"`);

        targetTab.click();

        setTimeout(() => {
            targetTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            flashTabIndicator(targetTab);
        }, 50);

        return true;
    }

    /**
     * Navigate to a specific vertical tab by index (circular, bulk edit mode)
     */
    function navigateToVerticalTab(index) {
        if (verticalTabElements.length === 0) {
            console.log('[TabNav] No vertical tabs available');
            return false;
        }

        // Circular navigation with proper modulo
        const wrappedIndex = ((index % verticalTabElements.length) + verticalTabElements.length) % verticalTabElements.length;

        const targetTab = verticalTabElements[wrappedIndex];
        console.log(`[TabNav] Navigating to vertical tab ${wrappedIndex + 1}/${verticalTabElements.length}: "${targetTab.textContent.trim()}"`);

        targetTab.click();
        currentVerticalTabIndex = wrappedIndex;

        setTimeout(() => {
            targetTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            flashTabIndicator(targetTab);
        }, 50);

        return true;
    }

    /**
     * Navigate to previous horizontal tab (with circular wrap)
     */
    function navigateToPreviousHorizontalTab() {
        const tabs = getContextualHorizontalTabs();
        if (tabs.length === 0) return;

        const currentIndex = getCurrentHorizontalTabIndex(tabs);
        const newIndex = currentIndex - 1;
        navigateToHorizontalTab(newIndex);
    }

    /**
     * Navigate to next horizontal tab (with circular wrap)
     */
    function navigateToNextHorizontalTab() {
        const tabs = getContextualHorizontalTabs();
        if (tabs.length === 0) return;

        const currentIndex = getCurrentHorizontalTabIndex(tabs);
        const newIndex = currentIndex + 1;
        navigateToHorizontalTab(newIndex);
    }

    /**
     * Navigate to previous vertical tab (with circular wrap, bulk edit mode)
     */
    function navigateToPreviousVerticalTab() {
        if (!hasVerticalTabs || verticalTabElements.length === 0) return;

        updateCurrentVerticalTabIndex();
        const newIndex = currentVerticalTabIndex - 1;
        navigateToVerticalTab(newIndex);
    }

    /**
     * Navigate to next vertical tab (with circular wrap, bulk edit mode)
     */
    function navigateToNextVerticalTab() {
        if (!hasVerticalTabs || verticalTabElements.length === 0) return;

        updateCurrentVerticalTabIndex();
        const newIndex = currentVerticalTabIndex + 1;
        navigateToVerticalTab(newIndex);
    }

    /**
     * Setup keyboard shortcuts with proper event handling
     */
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Only process Ctrl key combinations
            if (!e.ctrlKey) {
                return;
            }

            let handled = false;

            // Ctrl + Left Arrow - Previous Horizontal Tab
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                e.stopPropagation();
                navigateToPreviousHorizontalTab();
                handled = true;
            }

            // Ctrl + Right Arrow - Next Horizontal Tab
            else if (e.key === 'ArrowRight') {
                e.preventDefault();
                e.stopPropagation();
                navigateToNextHorizontalTab();
                handled = true;
            }

            // Ctrl + Up Arrow - Previous Vertical Tab (only in bulk edit mode)
            else if (e.key === 'ArrowUp') {
                if (hasVerticalTabs) {
                    e.preventDefault();
                    e.stopPropagation();
                    navigateToPreviousVerticalTab();
                    handled = true;
                }
            }

            // Ctrl + Down Arrow - Next Vertical Tab (only in bulk edit mode)
            else if (e.key === 'ArrowDown') {
                if (hasVerticalTabs) {
                    e.preventDefault();
                    e.stopPropagation();
                    navigateToNextVerticalTab();
                    handled = true;
                }
            }

            if (handled) {
                console.log(`[TabNav] Handled key: Ctrl+${e.key}`);
                return false;
            }
        }, true);

        if (hasVerticalTabs) {
            console.log('[TabNav] ✓ Keyboard shortcuts active:');
            console.log('  • Ctrl+Left/Right: Navigate horizontal tabs in active sample (circular)');
            console.log('  • Ctrl+Up/Down: Navigate vertical sample tabs (circular)');
        } else {
            console.log('[TabNav] ✓ Keyboard shortcuts active:');
            console.log('  • Ctrl+Left/Right: Navigate horizontal tabs (circular)');
        }
    }

    /**
     * Visual feedback when navigating tabs
     */
    function flashTabIndicator(tabElement) {
        const originalBg = tabElement.style.backgroundColor;
        const originalTransition = tabElement.style.transition;

        tabElement.style.transition = 'background-color 0.3s ease';
        tabElement.style.backgroundColor = 'rgba(58, 86, 166, 0.4)';

        setTimeout(() => {
            tabElement.style.backgroundColor = originalBg;
            setTimeout(() => {
                tabElement.style.transition = originalTransition;
            }, 300);
        }, 300);
    }

    /**
     * Initialize when DOM is ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTabNavigation);
    } else {
        initializeTabNavigation();
    }

    // Re-initialize when tabs might be dynamically added
    if (window.MutationObserver) {
        const observer = new MutationObserver(function(mutations) {
            let shouldReinit = false;

            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === 1) {
                            if (node.classList?.contains('vertical-tabs') ||
                                node.classList?.contains('nav-tabs') ||
                                node.querySelector?.('.vertical-tabs') ||
                                node.querySelector?.('.nav-tabs')) {
                                shouldReinit = true;
                                break;
                            }
                        }
                    }
                }
            }

            if (shouldReinit) {
                console.log('[TabNav] Tabs changed, re-initializing');
                initializeTabNavigation();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Expose API for manual control
    window.AdminTabNavigation = {
        nextHorizontal: navigateToNextHorizontalTab,
        previousHorizontal: navigateToPreviousHorizontalTab,
        nextVertical: navigateToNextVerticalTab,
        previousVertical: navigateToPreviousVerticalTab,
        goToHorizontal: navigateToHorizontalTab,
        goToVertical: navigateToVerticalTab,
        refresh: initializeTabNavigation,
        getInfo: function() {
            const hTabs = getContextualHorizontalTabs();
            const hIndex = getCurrentHorizontalTabIndex(hTabs);
            return {
                mode: hasVerticalTabs ? 'bulk-edit' : 'regular-admin',
                horizontalTabs: hTabs.length,
                currentHorizontalTab: hIndex + 1,
                verticalTabs: verticalTabElements.length,
                currentVerticalTab: currentVerticalTabIndex + 1
            };
        }
    };

})();
