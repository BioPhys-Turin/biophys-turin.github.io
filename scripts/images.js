document.addEventListener("DOMContentLoaded", function() {
    const images = document.querySelectorAll('.mission-image img');
    const lightbox = document.createElement('div');
    lightbox.id = 'lightbox';
    document.body.appendChild(lightbox);

    images.forEach(image => {
        image.addEventListener('click', e => {
            const fullSrc = image.getAttribute('data-full-src');
            const description = image.getAttribute('data-description');

            // Create the lightbox content
            lightbox.innerHTML = `
                <div class="lightbox-content">
                    <img src="${fullSrc}" alt="${description}" />
                    <p class="image-description">${description}</p>
                </div>
            `;

            // Show the lightbox
            lightbox.style.display = 'flex';
        });
    });

    // Close lightbox on click outside the image
    lightbox.addEventListener('click', e => {
        lightbox.style.display = 'none';
    });
});
