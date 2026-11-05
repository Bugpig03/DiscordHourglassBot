/* Badge page: the server list applies as soon as it changes (the page is a plain GET form otherwise). */
document.querySelectorAll('select[data-autosubmit]').forEach((select) => {
    select.addEventListener('change', () => select.form.submit());
});

// Phone strip of badges: the current one scrolled into view
const activeBadge = document.querySelector('.bg-nav-item.is-active');
if (activeBadge && window.matchMedia('(max-width: 900px)').matches) {
    activeBadge.scrollIntoView({ block: 'nearest', inline: 'center' });
}
