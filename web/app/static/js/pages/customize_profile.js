/* Profile customization page: tabs, live preview, selection limits and unsaved-changes hint.
   Nothing is saved until "Enregistrer". */
(function () {
    const form = document.getElementById('customizeForm');
    const preview = document.getElementById('profilePreview');
    if (!form || !preview) return;

    // ---- Tabs (without JavaScript every panel stays visible) ----
    const layout = form.closest('.cz-layout');
    const tabs = [...form.querySelectorAll('.cz-tab')];
    const panels = [...form.querySelectorAll('.cz-panel')];
    function showPanel(name) {
        tabs.forEach(t => {
            const on = t.dataset.panel === name;
            t.classList.toggle('active', on);
            t.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        panels.forEach(p => p.classList.toggle('active', p.dataset.panel === name));
        if (layout) layout.dataset.panel = name;
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

    function hexToRgb(hex) {
        const v = parseInt(hex.slice(1), 16);
        return [(v >> 16) & 255, (v >> 8) & 255, v & 255].join(', ');
    }

    function applyColor() {
        const input = form.querySelector('input[name="accent_color"]:checked');
        if (!input) return;
        preview.style.setProperty('--accent', input.dataset.hex);
        preview.style.setProperty('--accent-rgb', hexToRgb(input.dataset.hex));
        preview.classList.toggle('accent-custom', input.value !== 'blurple');
    }

    const bannerGallery = document.getElementById('bannerGallery');
    function applyBanner() {
        const picture = form.querySelector('input[name="banner_image"]:checked');
        const src = picture && picture.value ? picture.dataset.full : '';
        banner.hidden = !src;
        hero.classList.toggle('has-banner', !!src);
        bannerImg.hidden = !src;
        if (src && bannerImg.getAttribute('src') !== src) {
            delete bannerImg.dataset.fallbackDone;
            bannerImg.style.display = '';
            bannerImg.src = src;
        }
    }

    // Only the first pictures are shown; "Show the N others" unfolds the rest (open from the start when the
    // chosen picture is one of them)
    const bannerMore = document.getElementById('bannerMore');
    function setGalleryOpen(open) {
        if (!bannerMore) return;
        bannerGallery.classList.toggle('is-expanded', open);
        bannerMore.classList.toggle('is-open', open);
        bannerMore.querySelector('span').textContent = open ? bannerMore.dataset.less : bannerMore.dataset.more;
        bannerMore.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    if (bannerMore) {
        bannerMore.hidden = false;
        const chosen = bannerGallery.querySelector('input:checked');
        setGalleryOpen(!!(chosen && chosen.closest('.is-extra')));
        bannerMore.addEventListener('click', () => {
            const open = !bannerGallery.classList.contains('is-expanded');
            setGalleryOpen(open);
            if (!open) bannerGallery.scrollIntoView({ block: 'nearest' });
        });
    }

    function applyBackground() {
        const input = form.querySelector('input[name="background_color"]:checked');
        const hex = input ? input.dataset.hex : '';
        preview.classList.toggle('has-backdrop', !!hex);
        if (hex) preview.style.setProperty('--backdrop-color', hex);
        else preview.style.removeProperty('--backdrop-color');
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
    const cancel = document.getElementById('cancelChanges');
    const initialState = new URLSearchParams(new FormData(form)).toString();
    function refreshDirty() {
        dirtyHint.hidden = new URLSearchParams(new FormData(form)).toString() === initialState;
        cancel.hidden = dirtyHint.hidden;
    }
    let submitting = false;
    form.addEventListener('submit', () => { submitting = true; });
    window.addEventListener('beforeunload', e => {
        if (!submitting && !dirtyHint.hidden) { e.preventDefault(); e.returnValue = ''; }
    });

    // "Current choice" pill next to each Appearance setting
    function setCurrent(key, text) {
        const pill = form.querySelector(`[data-current="${key}"]`);
        if (pill && text) pill.textContent = text;
    }
    function refreshCurrent() {
        const checked = name => form.querySelector(`input[name="${name}"]:checked`);
        setCurrent('accent_color', checked('accent_color')?.dataset.label);
        setCurrent('background_color', checked('background_color')?.dataset.label);
        setCurrent('banner', checked('banner_image')?.dataset.label);
    }

    form.addEventListener('change', function (e) {
        const name = e.target.name;
        if (name === 'accent_color') applyColor();
        else if (name === 'banner_image') applyBanner();
        else if (name === 'background_color') applyBackground();
        else if (name === 'favorite_server_id') applyFavorite();
        else if (name === 'featured_badges') { applyLimit(badgePicker); applyShowcase(); }
        else if (name === 'pinned_records') applyLimit(recordPicker);
        else if (name === 'layout_private' && visibility) visibility.classList.toggle('is-disabled', privateBox.checked);
        refreshCurrent();
        refreshDirty();
    });

    function applyAll() {
        applyColor();
        applyBanner();
        applyBackground();
        applyFavorite();
        applyLimit(badgePicker);
        applyLimit(recordPicker);
        applyShowcase();
        if (visibility) visibility.classList.toggle('is-disabled', privateBox.checked);
        refreshCurrent();
    }

    // "Cancel": back to the saved choices (form.reset restores what the page was rendered with)
    cancel.addEventListener('click', () => {
        form.reset();
        const select = form.querySelector('#favoriteServer');
        if (select) select.dispatchEvent(new Event('change', { bubbles: true }));  // redraws the custom list button
        applyAll();
        refreshDirty();
    });

    applyLimit(badgePicker);
    applyLimit(recordPicker);
    applyShowcase();
    applyFavorite();
})();
