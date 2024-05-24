document.addEventListener("DOMContentLoaded", function() {
    const footerContainer = document.getElementById("nav-container");
    const footerUrl = "nav.html";

    fetch(footerUrl)
        .then(response => response.text())
        .then(html => {
            footerContainer.innerHTML = html;
        })
        .catch(error => {
            console.error("Error fetching footer:", error);
        });
});

