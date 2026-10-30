/* Drop-down lists in the Arène style. The opened list of a native <select> is drawn by the browser and
   cannot be styled, so each select.top-select / select.cz-select gets a button and a list of its own.
   The native select stays in the form (hidden): it keeps the value that is submitted, and every pick
   sets its value and fires "change", so the existing handlers (auto-submit of the filters) still run.
   The list is placed in <body> (position: fixed) so that no cut-corner box or overflow can clip it.
   Keyboard: Enter / Space / ↓ open, ↑ ↓ Home End move, Enter picks, Esc and Tab close, typing a letter
   jumps to the next option starting with it. */
(() => {
    const SELECTOR = 'select.top-select, select.cz-select';
    const CHEVRON = '<svg width="12" height="12" viewBox="0 0.5 9 9" fill="currentColor" shape-rendering="crispEdges" aria-hidden="true" data-px="chevron_down"><path d="M0 2h1v1h-1zM8 2h1v1h-1zM0 3h2v1h-2zM7 3h2v1h-2zM1 4h2v1h-2zM6 4h2v1h-2zM2 5h2v1h-2zM5 5h2v1h-2zM3 6h3v1h-3zM4 7h1v1h-1z"/></svg>';
    const CHECK = '<svg width="12" height="12" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" aria-hidden="true" data-px="check"><path d="M8 1h1v1h-1zM7 2h2v1h-2zM6 3h2v1h-2zM0 4h1v1h-1zM5 4h2v1h-2zM0 5h2v1h-2zM4 5h2v1h-2zM1 6h4v1h-4zM2 7h2v1h-2z"/></svg>';
    const GAP = 6;
    let uid = 0;
    let open = null; // { select, button, list, active }

    const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const options = (select) => Array.from(select.options).filter((o) => !o.hidden);

    function enhance(select) {
        if (select.dataset.hgSelect) return;
        select.dataset.hgSelect = String(++uid);
        const id = select.id || `hg-select-${uid}`;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'hg-select-btn';
        button.id = `${id}-btn`;
        button.setAttribute('role', 'combobox');
        button.setAttribute('aria-haspopup', 'listbox');
        button.setAttribute('aria-expanded', 'false');
        button.innerHTML = `<span class="hg-select-value"></span><span class="hg-select-chevron">${CHEVRON}</span>`;
        // The labels of the select now point to the button
        if (select.id) document.querySelectorAll(`label[for="${CSS.escape(select.id)}"]`).forEach((l) => { l.htmlFor = button.id; });
        if (select.getAttribute('aria-label')) button.setAttribute('aria-label', select.getAttribute('aria-label'));
        select.classList.add('hg-select-native');
        select.tabIndex = -1;
        select.setAttribute('aria-hidden', 'true');
        select.after(button);
        select._hgButton = button;
        sync(select);

        select.addEventListener('change', () => sync(select));
        button.addEventListener('click', () => (open && open.select === select ? close(true) : show(select)));
        button.addEventListener('keydown', (e) => {
            if (!open || open.select !== select) {
                if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
                    e.preventDefault();
                    show(select);
                }
                return;
            }
            keyInList(e);
        });
    }

    function sync(select) {
        const button = select._hgButton;
        if (!button) return;
        const current = select.options[select.selectedIndex];
        button.querySelector('.hg-select-value').textContent = current ? current.textContent.trim() : '';
        button.disabled = select.disabled;
    }

    function show(select) {
        close(false);
        const button = select._hgButton;
        const list = document.createElement('div');
        list.className = 'hg-select-list';
        list.id = `${button.id}-list`;
        list.setAttribute('role', 'listbox');
        list.tabIndex = -1;
        const opts = options(select);
        list.innerHTML = opts.map((o, i) => `<div class="hg-select-opt${o.disabled ? ' is-disabled' : ''}" role="option" id="${list.id}-${i}" data-index="${i}" aria-selected="${o.selected}"${o.disabled ? ' aria-disabled="true"' : ''}><span class="hg-select-opt-text">${esc(o.textContent.trim())}</span><span class="hg-select-check">${CHECK}</span></div>`).join('');
        document.body.appendChild(list);
        button.setAttribute('aria-expanded', 'true');
        button.setAttribute('aria-controls', list.id);
        button.classList.add('is-open');
        open = { select, button, list, active: Math.max(0, opts.findIndex((o) => o.selected)) };
        place();
        setActive(open.active);

        list.addEventListener('mousedown', (e) => e.preventDefault()); // keep the focus on the button
        list.addEventListener('click', (e) => {
            const opt = e.target.closest('.hg-select-opt');
            if (opt && !opt.classList.contains('is-disabled')) pick(Number(opt.dataset.index));
        });
        list.addEventListener('mousemove', (e) => {
            const opt = e.target.closest('.hg-select-opt');
            if (opt && Number(opt.dataset.index) !== open.active) setActive(Number(opt.dataset.index), false);
        });
    }

    // Under the button, or above it when the space below is too short; as wide as the button at least
    function place() {
        if (!open) return;
        const r = open.button.getBoundingClientRect();
        const list = open.list;
        list.style.minWidth = `${r.width}px`;
        list.style.left = '0px';
        list.style.maxHeight = '';
        const below = window.innerHeight - r.bottom - GAP - 8;
        const above = r.top - GAP - 8;
        const wanted = Math.min(list.scrollHeight, 320);
        const up = below < Math.min(wanted, 180) && above > below;
        list.style.maxHeight = `${Math.max(120, Math.min(320, up ? above : below))}px`;
        // Scrollbar only for a list really taller than its room (sub-pixel borders overflow by 1 px when zoomed)
        list.style.overflowY = list.scrollHeight > list.clientHeight + 2 ? 'auto' : 'hidden';
        const height = list.getBoundingClientRect().height;
        list.style.top = `${up ? r.top - GAP - height : r.bottom + GAP}px`;
        const width = list.getBoundingClientRect().width;
        list.style.left = `${Math.max(8, Math.min(r.left, window.innerWidth - width - 8))}px`;
        list.classList.toggle('is-up', up);
    }

    function setActive(index, scroll = true) {
        if (!open) return;
        const items = open.list.querySelectorAll('.hg-select-opt');
        if (!items.length) return;
        open.active = Math.max(0, Math.min(items.length - 1, index));
        items.forEach((el, i) => el.classList.toggle('is-active', i === open.active));
        open.button.setAttribute('aria-activedescendant', items[open.active].id);
        if (scroll) items[open.active].scrollIntoView({ block: 'nearest' });
    }

    function move(step) {
        const opts = options(open.select);
        let i = open.active;
        for (let n = 0; n < opts.length; n++) {
            i = (i + step + opts.length) % opts.length;
            if (!opts[i].disabled) break;
        }
        setActive(i);
    }

    function keyInList(e) {
        const opts = options(open.select);
        if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
        else if (e.key === 'Home') { e.preventDefault(); setActive(0); }
        else if (e.key === 'End') { e.preventDefault(); setActive(opts.length - 1); }
        else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!opts[open.active].disabled) pick(open.active); }
        else if (e.key === 'Escape') { e.preventDefault(); close(true); }
        else if (e.key === 'Tab') close(false);
        else if (e.key.length === 1 && /\S/.test(e.key)) {
            const k = e.key.toLowerCase();
            for (let n = 1; n <= opts.length; n++) {
                const i = (open.active + n) % opts.length;
                if (opts[i].textContent.trim().toLowerCase().startsWith(k)) { setActive(i); break; }
            }
        }
    }

    function pick(index) {
        const { select } = open;
        const opt = options(select)[index];
        close(true);
        if (!opt || opt.selected) return;
        select.value = opt.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function close(focus) {
        if (!open) return;
        const { button, list } = open;
        list.remove();
        button.setAttribute('aria-expanded', 'false');
        button.removeAttribute('aria-activedescendant');
        button.removeAttribute('aria-controls');
        button.classList.remove('is-open');
        open = null;
        if (focus) button.focus();
    }

    function scan(root) {
        if (root.nodeType !== 1) return;
        if (root.matches(SELECTOR)) enhance(root);
        root.querySelectorAll(SELECTOR).forEach(enhance);
    }

    document.addEventListener('mousedown', (e) => {
        if (open && !open.list.contains(e.target) && !open.button.contains(e.target)) close(false);
    });
    window.addEventListener('resize', () => close(false));
    // Scrolling the page moves the button: the list follows it (scrolling inside the list itself is ignored)
    window.addEventListener('scroll', (e) => { if (open && e.target !== open.list) place(); }, true);

    const start = () => {
        scan(document.body);
        new MutationObserver((records) => records.forEach((r) => r.addedNodes.forEach(scan)))
            .observe(document.body, { childList: true, subtree: true });
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})();
