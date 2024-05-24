document.addEventListener('DOMContentLoaded', () => {
    const newsContainer = document.querySelector('.news-container');

    // Fetch news data from JSON file
    fetch('files/news.json')
        .then(response => response.json())
        .then(newsData => {
            // Loop through each news article in the JSON data
            newsData.forEach(article => {
                // Create a new div element for the news article
                const articleDiv = document.createElement('div');
                articleDiv.classList.add('news-item');

                // Create the title element
                const titleElement = document.createElement('h2');
                titleElement.textContent = article.title;

                // Append the title to the articleDiv
                articleDiv.appendChild(titleElement);

                // Create the date paragraph
                const dateElement = document.createElement('p');
                dateElement.classList.add('date');
                dateElement.textContent = article.date;

                // Append the date to the articleDiv
                articleDiv.appendChild(dateElement);

                // Create the summary paragraph
                const summaryElement = document.createElement('p');
                summaryElement.classList.add('summary');
                summaryElement.textContent = article.summary;

                // Append the summary to the articleDiv
                articleDiv.appendChild(summaryElement);

                // Check if the article has a link field
                if (article.link) {
                    // Create a container for the link
                    const linkContainer = document.createElement('div');
                    linkContainer.classList.add('link-container');

                    // Create the link element with the external link icon
                    const linkElement = document.createElement('a');
                    linkElement.href = article.link;
                    linkElement.target = '_blank'; // Open link in a new tab

                    // Create an icon element for the external link
                    const externalLinkIcon = document.createElement('img');
                    externalLinkIcon.src = 'images/icons/external-link.svg';
                    externalLinkIcon.alt = 'External Link';

                    // Append the icon to the link element
                    linkElement.appendChild(externalLinkIcon);

                    // Append the link to the linkContainer
                    linkContainer.appendChild(linkElement);

                    // Append the linkContainer to the articleDiv
                    articleDiv.appendChild(linkContainer);
                }

                // Append the populated div to the newsContainer
                newsContainer.appendChild(articleDiv);
            });
        })
        .catch(error => {
            console.error('Error fetching news:', error);
        });
});
