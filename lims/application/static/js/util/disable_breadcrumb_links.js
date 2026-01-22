document.addEventListener('DOMContentLoaded', function () {
    const links = document.querySelectorAll('.breadcrumb a');
    links.forEach(link => {
        const text = link.textContent.trim();
        if (text === 'Pathology' || text === 'Reporting'
        || text === 'Enterprise' || text === 'Samples'
        || text === 'IHC Workflow' || text === 'IHC Samples') {
            const span = document.createElement('span');
            span.className = 'breadcrumb-item'; // keep styling
            span.textContent = text;
            const li = link.closest('li');
            if (li) {
                li.innerHTML = '';
                li.appendChild(span);
            }
        }
    });
});
