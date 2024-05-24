document.addEventListener("DOMContentLoaded", function() {
    // Get all loading and content elements
    const loadingElements = document.querySelectorAll(".loading");
    const contentElements = document.querySelectorAll(".content");

    // Iterate over each loading/content pair
    contentElements.forEach((contentElement, index) => {

        // Simulate loading time (e.g., 2 seconds) before displaying content
        setTimeout(function() {
            loadingElements[0].style.display = "none";
            contentElement.style.display = "block";
        }, 500); // Adjust timeout duration as needed
    });
});
