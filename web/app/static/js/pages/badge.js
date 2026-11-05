/* Badge page: the server list applies as soon as it changes (the page is a plain GET form otherwise). */
document.querySelectorAll('select[data-autosubmit]').forEach((select) => {
    select.addEventListener('change', () => select.form.submit());
});
