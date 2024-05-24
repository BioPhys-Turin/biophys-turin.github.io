document.addEventListener('DOMContentLoaded', async () => {
    try {
        const papersResponse = await fetch('papers/paper.json');
        const papersData = await papersResponse.json();

        // Sort papers by date (assuming each paper has a "year" field)
        papersData.sort((a, b) => parseInt(b.year) - parseInt(a.year)); // Sort by most recent year first

        const papersListContainer = document.getElementById('papersList');

        // Render each paper
        papersData.forEach(paper => {
            const paperDiv = document.createElement('div');
            paperDiv.classList.add('paper');

            // Construct paper info HTML
            const paperInfoHTML = `
                <img src="images/icons/doc.svg" alt="Document Icon">
                <div class="paper-info">
                    <p><span class="author">${paper.author} (${paper.year})</span></p>
                    <p><a href="${paper.link}" target="_blank" class="paper-title">${paper.title}</a></p>
                    <span class="journal">${paper.journal}${paper.volume ? ` ${paper.volume}` : ''}${paper.number ? `, ${paper.number}` : ''}</span>
                    <div class="cite-button">
                        <button onclick="openCitePopup('${paper.title}', '${paper.author}', '${paper.journal}', '${paper.year}', '${paper.volume || ''}', '${paper.number || ''}', '${paper.pages    || ''}')">Cite</button>
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

function openCitePopup(title, author, journal, year, volume, number, pages) {
    const popupTitle = document.getElementById('popupTitle');
    const popupContent = document.getElementById('popupContent');
    let first_author = author.split(",")
    let first_surname = first_author[0].split(" ")

    if (popupTitle && popupContent) {
        popupTitle.textContent = 'BibTeX Citation: ' + title;

        // Construct the formatted BibTeX citation including volume and number if available
        const bibtexContent = `
@article{${first_surname[first_surname.length-1]}_${year},
    title = {${title}},
    author = {${author}},
    journal = {${journal}},
    year = {${year}},
    ${volume ? `volume = {${volume}}` : ''}
    ${number ? `number = {${number}},` : ''}
    ${pages ? `pages = {${pages}},` : ''}
}`;

        // Apply left alignment to the popup content
        popupContent.style.textAlign = 'left';
        popupContent.textContent = bibtexContent;
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
