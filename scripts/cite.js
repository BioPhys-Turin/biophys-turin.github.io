// Papers page: show the pre-rendered BibTeX of a paper in the popup.
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
