/* Server management page: sections in tabs (kept in the address #section), dates shown in the visitor's own time,
   and the member search to choose a manager (owner only). */
(function () {
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const esc = v => HG.esc(v);

    // ---------------------------------------------------------------- tabs
    const buttons = Array.from(document.querySelectorAll('[data-sm-tab]'));
    const panes = Array.from(document.querySelectorAll('[data-sm-pane]'));
    function show(key, push) {
        if (!panes.some(p => p.dataset.smPane === key)) key = 'general';
        buttons.forEach(b => {
            const on = b.dataset.smTab === key;
            b.classList.toggle('active', on);
            b.setAttribute('aria-selected', String(on));
        });
        panes.forEach(p => { p.hidden = p.dataset.smPane !== key; });
        if (push) history.replaceState(null, '', `${location.pathname}#${key}`);
    }
    buttons.forEach(b => b.addEventListener('click', () => show(b.dataset.smTab, true)));
    const hash = location.hash.replace('#', '');
    if (hash) show(hash, false);
    // A saved form comes back with ?section=…&notice=…: keep only the section in the address
    if (location.search) {
        const active = (buttons.find(b => b.classList.contains('active')) || {}).dataset;
        history.replaceState(null, '', `${location.pathname}#${(active && active.smTab) || 'general'}`);
    }

    // ---------------------------------------------------------------- dates (stored in UTC)
    document.querySelectorAll('time[data-utc]').forEach(el => {
        const d = new Date(el.dataset.utc);
        if (isNaN(d)) return;
        el.dateTime = d.toISOString();
        el.textContent = d.toLocaleString(HG.locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    });

    // ---------------------------------------------------------------- choose a manager
    const form = document.getElementById('smAddManager');
    if (!form) return;
    const input = form.querySelector('input[type="search"]');
    const list = form.querySelector('.tl-suggest');
    const hidden = form.querySelector('input[name="user_id"]');
    let found = [], active = -1, timer = 0, call = null;

    function close() { list.hidden = true; list.innerHTML = ''; found = []; active = -1; }
    function render() {
        if (!found.length) {
            list.innerHTML = input.value.trim() ? `<li class="tl-suggest-empty">${esc(T('Aucun membre trouvé', 'No member found'))}</li>` : '';
            list.hidden = !input.value.trim();
            return;
        }
        list.innerHTML = found.map((m, i) => `<li role="option" data-index="${i}" class="${i === active ? 'is-active' : ''}" aria-selected="${i === active}">
            <img src="${esc(m.avatar || '/static/images/base_avatar_big.png')}" alt="" width="22" height="22" loading="lazy">
            <span>${esc(m.name)}${m.username && m.username !== m.name ? ` <small>@${esc(m.username)}</small>` : ''}</span></li>`).join('');
        list.hidden = false;
    }
    function pick(m) {
        if (!m) return;
        hidden.value = m.id;
        input.value = m.name;
        close();
        form.submit();
    }
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (!q) return close();
        timer = setTimeout(async () => {
            if (call) call.abort();
            call = new AbortController();
            try {
                const res = await fetch(`${input.dataset.membersUrl}?q=${encodeURIComponent(q)}`, { signal: call.signal, credentials: 'same-origin' });
                found = (await res.json()).members || [];
                active = found.length ? 0 : -1;
                render();
            } catch (e) { /* aborted */ }
        }, 180);
    });
    input.addEventListener('keydown', e => {
        if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && found.length) {
            e.preventDefault();
            active = (active + (e.key === 'ArrowDown' ? 1 : -1) + found.length) % found.length;
            render();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (active >= 0) pick(found[active]);
        } else if (e.key === 'Escape') {
            close();
        }
    });
    list.addEventListener('mousedown', e => {
        const li = e.target.closest('[data-index]');
        if (li) { e.preventDefault(); pick(found[Number(li.dataset.index)]); }
    });
    input.addEventListener('blur', () => setTimeout(close, 120));
})();
