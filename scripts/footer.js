document.addEventListener("DOMContentLoaded", function() {
    const footerContainer = document.getElementById("footer-container");
    const footerUrl = "footer.html";

    fetch(footerUrl)
        .then(response => response.text())
        .then(html => {
            footerContainer.innerHTML = html;
        })
        .catch(error => {
            console.error("Error fetching footer:", error);
        });
});

