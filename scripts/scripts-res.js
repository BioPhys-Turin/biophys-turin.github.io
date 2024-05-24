document.addEventListener('DOMContentLoaded', () => {
    const researchersListContainer = document.getElementById('researchersList');

    // Fetch JSON data and render researchers
    fetch('files/researchers.json')
        .then(response => response.json())
        .then(data => {
            data.forEach(researcher => {
                const researcherDiv = document.createElement('div');
                researcherDiv.classList.add('researcher');

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
                        <p class="description">${researcher.description}</p>
                        <hr>
                        <p class="mail">${researcher.socials.mail}</p>
                        <div class="social-links">${socialLinks}</div>
                    </div>
                `;

                researchersListContainer.appendChild(researcherDiv);
            });
        })
        .catch(error => {
            console.error('Error fetching researchers:', error);
        });
});
