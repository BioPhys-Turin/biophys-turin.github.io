if (location.pathname.endsWith('.html')) {
    history.replaceState({}, document.title, location.pathname.slice(0, -5));
}