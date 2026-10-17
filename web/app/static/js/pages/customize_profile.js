/* Profile customization page: keeps the live preview in sync with the form (nothing is saved until "Enregistrer"). */
(function () {
    const form = document.getElementById('customizeForm');
    const preview = document.getElementById('profilePreview');
    if (!form || !preview) return;

    const hero = preview.querySelector('.profile-hero');
    const banner = preview.querySelector('.profile-banner');
    const bannerImg = banner.querySelector('img');
    const favorite = document.getElementById('previewFavorite');
    const discordBanner = preview.dataset.discordBanner;

    function hexToRgb(hex) {
        const v = parseInt(hex.slice(1), 16);
        return [(v >> 16) & 255, (v >> 8) & 255, v & 255].join(', ');
    }

    function applyColor() {
        const input = form.querySelector('input[name="accent_color"]:checked');
        if (!input) return;
        preview.style.setProperty('--accent', input.dataset.hex);
        preview.style.setProperty('--accent-rgb', hexToRgb(input.dataset.hex));
        preview.classList.toggle('accent-custom', input.value !== 'sky');
    }

    function applyBanner() {
        const input = form.querySelector('input[name="banner_mode"]:checked');
        const mode = input ? input.value : 'auto';
        banner.hidden = mode === 'none';
        hero.classList.toggle('has-banner', mode !== 'none');
        bannerImg.hidden = !(mode === 'auto' && discordBanner);
    }

    function applyFavorite() {
        const option = form.querySelector('#favoriteServer').selectedOptions[0];
        if (!option || !option.value) {
            favorite.hidden = true;
            return;
        }
        favorite.hidden = false;
        favorite.querySelector('img').src = option.dataset.avatar;
        favorite.querySelector('.profile-fav-server-name').textContent = option.dataset.name;
        favorite.querySelector('.profile-fav-server-meta').textContent = option.dataset.meta;
    }

    // Pickers limited to N checked cards: the others are disabled once the limit is reached
    function applyLimit(picker) {
        if (!picker) return;
        const max = parseInt(picker.dataset.max, 10);
        const boxes = [...picker.querySelectorAll('input[type="checkbox"]')];
        const count = boxes.filter(b => b.checked).length;
        boxes.forEach(b => { b.disabled = !b.checked && count >= max; });
        const counter = picker.querySelector('[data-counter]');
        if (counter) counter.textContent = count + ' / ' + max;
    }

    const badgePicker = document.getElementById('badgePicker');
    const showcase = document.getElementById('previewShowcase');

    function applyShowcase() {
        if (!badgePicker || !showcase) return;
        let boxes = [...badgePicker.querySelectorAll('input[name="featured_badges"]:checked')];
        if (!boxes.length) {
            // Nothing picked: the profile shows the rarest badges automatically
            const auto = (showcase.dataset.auto || '').split(',').filter(Boolean);
            boxes = auto.map(id => badgePicker.querySelector('input[value="' + CSS.escape(id) + '"]')).filter(Boolean);
        }
        showcase.replaceChildren(...boxes.map(b => b.nextElementSibling.cloneNode(true)));
    }

    form.addEventListener('change', function (e) {
        if (e.target.name === 'accent_color') applyColor();
        else if (e.target.name === 'banner_mode') applyBanner();
        else if (e.target.name === 'favorite_server_id') applyFavorite();
        else if (e.target.name === 'featured_badges') { applyLimit(badgePicker); applyShowcase(); }
        else if (e.target.name === 'pinned_records') applyLimit(document.getElementById('recordPicker'));
    });

    // Activity tab order: move rows up/down (the hidden inputs are submitted in DOM order)
    const order = document.getElementById('layoutOrder');
    function refreshMoveButtons() {
        if (!order) return;
        const items = [...order.children];
        items.forEach((li, i) => {
            li.querySelector('[data-move="-1"]').disabled = i === 0;
            li.querySelector('[data-move="1"]').disabled = i === items.length - 1;
        });
    }
    if (order) {
        order.addEventListener('click', function (e) {
            const btn = e.target.closest('.layout-move');
            if (!btn) return;
            const li = btn.closest('li');
            if (btn.dataset.move === '-1' && li.previousElementSibling) li.parentNode.insertBefore(li, li.previousElementSibling);
            else if (btn.dataset.move === '1' && li.nextElementSibling) li.parentNode.insertBefore(li.nextElementSibling, li);
            refreshMoveButtons();
            const target = li.querySelector(`[data-move="${btn.dataset.move}"]`);
            (target.disabled ? li.querySelector('.layout-move:not(:disabled)') : target)?.focus();
        });
        refreshMoveButtons();
    }

    // Private mode overrides the per-block visibility
    const privateBox = document.getElementById('layoutPrivate');
    const visibility = document.getElementById('layoutVisibility');
    if (privateBox && visibility) {
        privateBox.addEventListener('change', () => visibility.classList.toggle('is-disabled', privateBox.checked));
    }

    applyLimit(badgePicker);
    applyLimit(document.getElementById('recordPicker'));
    applyShowcase();
})();
