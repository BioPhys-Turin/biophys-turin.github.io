// Mobile menu: show/hide the navigation links
document.querySelector('.navbar-toggle').addEventListener('click', function () {
    const expanded = document.getElementById('navbarLinks').classList.toggle('active');
    this.setAttribute('aria-expanded', expanded);
});
