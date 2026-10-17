/* Profile customization page: tabs, live preview, selection limits and unsaved-changes hint.
   Nothing is saved until "Enregistrer". */
(function () {
    const form = document.getElementById('customizeForm');
    const preview = document.getElementById('profilePreview');
    if (!form || !preview) return;

    // ---- Tabs (without JavaScript every panel stays visible) ----
    const tabs = [...form.querySelectorAll('.cz-tab')];
    const panels = [...form.querySelectorAll('.cz-panel')];
    function showPanel(name) {
        tabs.forEach(t => {
            const on = t.dataset.panel === name;
            t.classList.toggle('active', on);
            t.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name));
        try { sessionStorage.setItem('hgCustomizePanel', name); } catch (e) {}
    }
    form.classList.add('cz-js');
    tabs.forEach(t => t.addEventListener('click', () => showPanel(t.dataset.panel)));
    let initial = 'appearance';
    try {
        const saved = sessionStorage.getItem('hgCustomizePanel');
        if (saved && panels.some(p => p.dataset.panel === saved)) initial = saved;
    } catch (e) {}
    showPanel(initial);

    // ---- Live preview ----
    const hero = preview.querySelector('.profile-hero');
    const banner = preview.querySelector('.profile-banner');
    const bannerImg = banner.querySelector('img');
    const favorite = document.getElementById('previewFavorite');
    const showcase = document.getElementById('previewShowcase');
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
        favorite.hidden = !option || !option.value;
        if (!favorite.hidden) {
            favorite.querySelector('img').src = option.dataset.avatar;
            favorite.querySelector('.profile-vitrine-server-name').textContent = option.dataset.name;
            favorite.querySelector('.profile-vitrine-server-meta').textContent = option.dataset.meta;
        }
    }

    const badgePicker = document.getElementById('badgePicker');
    function applyShowcase() {
        if (!badgePicker) return;
        let boxes = [...badgePicker.querySelectorAll('input[name="featured_badges"]:checked')];
        if (!boxes.length) {
            // Nothing picked: the profile shows the rarest badges automatically
            const auto = (showcase.dataset.auto || '').split(',').filter(Boolean);
            boxes = auto.map(id => badgePicker.querySelector('input[value="' + CSS.escape(id) + '"]')).filter(Boolean);
        }
        showcase.replaceChildren(...boxes.map(b => b.closest('label').querySelector('template[data-showcase]').content.cloneNode(true)));
    }

    // ---- Pickers limited to N choices: the others are disabled once the limit is reached ----
    function applyLimit(picker) {
        if (!picker) return;
        const max = parseInt(picker.dataset.max, 10);
        const boxes = [...picker.querySelectorAll('input[type="checkbox"]')];
        const count = boxes.filter(b => b.checked).length;
        boxes.forEach(b => { b.disabled = !b.checked && count >= max; });
        const counter = picker.querySelector('[data-counter]');
        if (counter) counter.textContent = count + ' / ' + max;
    }
    const recordPicker = document.getElementById('recordPicker');

    // ---- Private mode overrides the per-block visibility ----
    const privateBox = document.getElementById('layoutPrivate');
    const visibility = document.getElementById('layoutVisibility');

    // ---- Unsaved changes hint ----
    const dirtyHint = document.getElementById('dirtyHint');
    const initialState = new URLSearchParams(new FormData(form)).toString();
    function refreshDirty() {
        dirtyHint.hidden = new URLSearchParams(new FormData(form)).toString() === initialState;
    }
    let submitting = false;
    form.addEventListener('submit', () => { submitting = true; });
    window.addEventListener('beforeunload', e => {
        if (!submitting && !dirtyHint.hidden) { e.preventDefault(); e.returnValue = ''; }
    });

    form.addEventListener('change', function (e) {
        const name = e.target.name;
        if (name === 'accent_color') applyColor();
        else if (name === 'banner_mode') applyBanner();
        else if (name === 'favorite_server_id') applyFavorite();
        else if (name === 'featured_badges') { applyLimit(badgePicker); applyShowcase(); }
        else if (name === 'pinned_records') applyLimit(recordPicker);
        else if (name === 'layout_private' && visibility) visibility.classList.toggle('is-disabled', privateBox.checked);
        refreshDirty();
    });

    applyLimit(badgePicker);
    applyLimit(recordPicker);
    applyShowcase();
    applyFavorite();
})();
