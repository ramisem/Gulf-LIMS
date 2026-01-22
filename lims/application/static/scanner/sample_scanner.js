// sample-scanner.js - Sample Scanner Configuration
(function() {
    'use strict';
    
    function onDomReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            setTimeout(fn, 0);
        }
    }
    
    // Initialize Sample Scanner
    onDomReady(function() {
        try {
            const sampleConfig = {
                title: 'Scan Samples',
                placeholder: 'Scan or type sample id then press Tab',
                validatePath: '/sample/admin/scan-validate/',
                submitPath: '/sample/admin/scan-submit/',
                editPath: '/sample/admin/scan-bulk-edit/',
                tableHeaders: [
                    { key: 'index', label: '#' },
                    { key: 'accession_id', label: 'Accession ID' },
                    { key: 'part_no', label: 'Part No' },
                    { key: 'tests', label: 'Test(s)' },
                    { key: 'current_step', label: 'Current Step' },
                    { key: 'next_step', label: 'Next Step' },
                    { key: 'pending_action', label: 'Pending Action' },
                    { key: 'sample_id', label: 'Sample ID' },
                    { key: 'action', label: 'Action' }
                ]
            };
            
            // Create scanner instance
            window.sampleScanner = new GenericScanner(sampleConfig);
            
            // Expose minimal API for console debugging
            window.adminScanner = {
                open: () => window.sampleScanner.open(),
                close: () => window.sampleScanner.close(),
                toggle: () => window.sampleScanner.toggle(),
                getSamples: () => window.sampleScanner.getSamples(),
                undoLast: () => window.sampleScanner.removeLast()
            };
            
        } catch (err) {
            console.error('Sample scanner init failed:', err);
        }
    });
})();