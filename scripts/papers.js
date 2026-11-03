let papersData = [];

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const papersResponse = await fetch('papers/paper.json');
        papersData = await papersResponse.json();

        // Sort papers by date (assuming each paper has a "year" field)
        papersData.sort((a, b) => parseInt(b.year) - parseInt(a.year)); // Sort by most recent year first

        const papersListContainer = document.getElementById('papersList');

        // Render each paper
        papersData.forEach((paper, index) => {
            const paperDiv = document.createElement('div');
            paperDiv.classList.add('paper');
            const venue = paper.journal || paper.booktitle || '';

            // Construct paper info HTML
            const paperInfoHTML = `
                <img src="images/icons/doc.svg" alt="Document Icon">
                <div class="paper-info">
                    <p><span class="author">${paper.author} (${paper.year})</span></p>
                    <p><a href="${paper.link}" target="_blank" class="paper-title">${paper.title}</a></p>
                    <span class="journal">${venue}${paper.volume ? ` ${paper.volume}` : ''}${paper.number ? `, ${paper.number}` : ''}</span>
                    <div class="cite-button">
                        <button onclick="openCitePopup(${index})">Cite</button>
                    </div>
                </div>
            `;

            paperDiv.innerHTML = paperInfoHTML;
            papersListContainer.appendChild(paperDiv);
        });

    } catch (error) {
        console.error('Error fetching papers:', error);
    }
});

function openCitePopup(index) {
    const paper = papersData[index];
    const popupTitle = document.getElementById('popupTitle');
    const popupContent = document.getElementById('popupContent');
    const firstAuthor = paper.author.split(',')[0].trim().split(' ');
    const key = `${firstAuthor[firstAuthor.length - 1]}_${paper.year}`;
    const entryType = paper.type || 'article';
    const venueField = entryType === 'incollection' ? 'booktitle' : 'journal';

    const fields = [
        ['title', paper.title],
        ['author', paper.author.split(', ').join(' and ')],
        [venueField, paper.journal || paper.booktitle],
        ['year', paper.year],
        ['volume', paper.volume],
        ['number', paper.number],
        ['pages', paper.pages],
        ['publisher', paper.publisher],
        ['url', paper.link],
    ].filter(([, value]) => value);

    if (popupTitle && popupContent) {
        popupTitle.textContent = 'BibTeX Citation: ' + paper.title;
        popupContent.style.textAlign = 'left';
        popupContent.textContent =
            `@${entryType}{${key},\n` +
            fields.map(([name, value]) => `    ${name} = {${value}}`).join(',\n') +
            '\n}';
    }

    const citePopup = document.getElementById('citePopup');
    if (citePopup) {
        citePopup.style.display = 'block';
    }
}

function closeCitePopup() {
    const citePopup = document.getElementById('citePopup');
    if (citePopup) {
        citePopup.style.display = 'none';
    }
}
