document.addEventListener('DOMContentLoaded', () => {
    const researchersListContainer = document.getElementById('researchersListFormer');

    // Fetch JSON data and render researchers
    fetch('files/researchers-former.json')
        .then(response => response.json())
        .then(data => {
            // Group researchers into pairs for display
            const pairedResearchers = pairResearchers(data);

            pairedResearchers.forEach(pair => {
                const pairDiv = document.createElement('div');
                pairDiv.classList.add('researcher-pair');

                pair.forEach(researcher => {
                    const researcherDiv = document.createElement('div');
                    researcherDiv.classList.add('researcher_former');

                    const socialLinks = Object.entries(researcher.socials).map(([platform, url]) => {
                        // Check if the platform is 'email', then prepend 'mailto:' to the URL
                        if (platform === 'mail') {
                            url = `mailto:${url}`; // Add 'mailto:' to the URL
                        }
                        
                        // Generate the HTML for the social link with the updated URL
                        return `<a href="${url}" target="_blank"><img src="images/icons/${platform}.svg" alt="${platform}"></a>`;
                    }).join('');

                    researcherDiv.innerHTML = `
                        <div class="profile-img">
                            <img src="${researcher.image}" alt="${researcher.name}">
                        </div>
                        <div class="profile-details">
                            <h2>${researcher.name}</h2>
                            <p class="title">${researcher.title}</p>
                            <p class="mail">${researcher.socials.mail}</p>
                            <div class="social-links">${socialLinks}</div>
                        </div>
                    `;

                    pairDiv.appendChild(researcherDiv);
                });

                researchersListContainer.appendChild(pairDiv);
            });
        })
        .catch(error => {
            console.error('Error fetching researchers:', error);
        });
});

// Function to pair researchers into arrays of two
function pairResearchers(data) {
    const paired = [];
    for (let i = 0; i < data.length; i += 2) {
        const pair = [data[i]];
        if (i + 1 < data.length) {
            pair.push(data[i + 1]);
        }
        paired.push(pair);
    }
    return paired;
}
