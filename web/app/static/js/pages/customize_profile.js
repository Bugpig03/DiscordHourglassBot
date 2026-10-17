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

    form.addEventListener('change', function (e) {
        if (e.target.name === 'accent_color') applyColor();
        else if (e.target.name === 'banner_mode') applyBanner();
        else if (e.target.name === 'favorite_server_id') applyFavorite();
    });
})();
