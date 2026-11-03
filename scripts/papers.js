// Papers page: search box and Cite popup.

// --- Search -----------------------------------------------------------------
(function () {
    const input = document.getElementById('paperSearch');
    const noResults = document.getElementById('noResults');
    const sections = Array.from(document.querySelectorAll('.paper-year'));

    // Lower-case and strip accents so "niccolo" matches "Niccolò"
    const normalize = text => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

    const papers = sections.flatMap(section =>
        Array.from(section.querySelectorAll('.paper')).map(paper => ({
            element: paper,
            section,
            text: normalize(
                ['.author', '.paper-title', '.journal']
                    .map(selector => paper.querySelector(selector).textContent)
                    .join(' ')
            ),
        }))
    );

    input.addEventListener('input', () => {
        const terms = normalize(input.value).split(/\s+/).filter(Boolean);
        const visibleSections = new Set();
        for (const paper of papers) {
            const match = terms.every(term => paper.text.includes(term));
            paper.element.hidden = !match;
            if (match) visibleSections.add(paper.section);
        }
        sections.forEach(section => { section.hidden = !visibleSections.has(section); });
        noResults.hidden = visibleSections.size > 0;
    });

    input.hidden = false; // only useful with JavaScript, so it starts hidden
})();

// --- Cite popup -------------------------------------------------------------
(function () {
    const popup = document.getElementById('citePopup');
    const popupTitle = document.getElementById('popupTitle');
    const popupContent = document.getElementById('popupContent');

    function open(paper) {
        popupTitle.textContent = 'BibTeX Citation: ' + paper.querySelector('.paper-title').textContent;
        popupContent.textContent = paper.querySelector('.bibtex').textContent;
        popup.style.display = 'block';
    }

    function close() {
        popup.style.display = 'none';
    }

    document.querySelectorAll('[data-cite]').forEach(button => {
        button.addEventListener('click', () => open(button.closest('.paper')));
    });
    document.getElementById('closeCitePopup').addEventListener('click', close);
    popup.addEventListener('click', event => { if (event.target === popup) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
})();
