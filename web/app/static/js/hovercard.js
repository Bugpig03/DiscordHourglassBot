/* Hover cards: resting the pointer on an element with data-hover="user:<id>" or "server:<id>" shows a small
   player / server card (mouse and trackpad only; touch screens keep the plain link). Data comes from
   /api/hover/..., fetched once per element and kept for the visit. */
(() => {
    if (!window.matchMedia || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const SHOW_DELAY = 280;
    const store = new Map();
    const card = document.createElement('div');
    card.className = 'hovercard';
    card.hidden = true;
    card.setAttribute('role', 'tooltip');
    document.body.appendChild(card);

    let timer = null;
    let current = null;
    let lastEvent = null;

    const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const num = (v, d = 0) => Number(v || 0).toLocaleString(HG.locale, { minimumFractionDigits: d, maximumFractionDigits: d });
    const stat = (label, value) => `<div><b>${value}</b><span>${esc(label)}</span></div>`;
    const rank = (d) => (d.rank ? `#${num(d.rank)}<small>/${num(d.rank_total)}</small>` : T('Non classé', 'Unranked'));

    function load(key) {
        if (!store.has(key)) {
            const [kind, id] = key.split(':');
            store.set(key, fetch(`/api/hover/${kind}/${encodeURIComponent(id)}`, { credentials: 'same-origin' })
                .then((r) => (r.ok ? r.json() : null))
                .catch(() => null));
        }
        return store.get(key);
    }

    function renderUser(d) {
        const showcase = d.showcase.length
            ? `<div class="hc-badges">${d.showcase.map((b) => `<span class="hc-badge" style="--rc:${esc(b.color)}" title="${esc(b.name)}">${b.icon}</span>`).join('')}<span class="hc-badge-count">${num(d.badges)} / ${num(d.badges_total)} ${T('paliers', 'tiers')}</span></div>`
            : `<div class="hc-badges"><span class="hc-badge-count">${num(d.badges)} / ${num(d.badges_total)} ${T('paliers', 'tiers')}</span></div>`;
        return `<div class="hc-top">
                <img class="hc-avatar" src="${esc(d.avatar || '/static/images/base_avatar_big.png')}" alt="">
                <div class="hc-id"><b>${esc(d.name)}${d.bot ? '<span class="bot-tag">BOT</span>' : ''}</b><span class="hc-title">${esc(d.title)}</span></div>
            </div>
            <div class="hc-level"><span class="hc-lvl">${num(d.level)}</span><span class="hc-bar"><i style="width:${Number(d.progress) || 0}%"></i></span><span class="hc-pct">${num(d.progress, 0)} %</span></div>
            <div class="hc-stats">
                ${stat(T('Rang global', 'Global rank'), rank(d))}
                ${stat(T('Vocal total', 'Total voice'), `${num(d.hours, 1)} h`)}
                ${stat(T('Vocal 30 j', 'Voice 30 d'), `${num(d.hours_30d, 1)} h`)}
                ${stat(T('Messages', 'Messages'), num(d.messages))}
            </div>
            ${showcase}
            ${d.since ? `<div class="hc-foot">${T('Suivi depuis le', 'Tracked since')} ${esc(d.since)}</div>` : ''}`;
    }

    function renderServer(d) {
        const status = d.bot_present
            ? `<span class="hc-chip ok">${T('Bot actif', 'Bot active')}</span>`
            : `<span class="hc-chip off">${T('Bot parti', 'Bot left')}</span>`;
        const voice = d.in_voice ? `<span class="hc-chip live"><i></i>${num(d.in_voice)} ${T('en vocal', 'in voice')}</span>` : '';
        return `<div class="hc-top">
                <img class="hc-avatar hc-square" src="${esc(d.avatar || '/static/images/base_avatar_big.png')}" alt="">
                <div class="hc-id"><b>${esc(d.name)}</b><span class="hc-chips">${status}${voice}</span></div>
            </div>
            <div class="hc-stats">
                ${stat(T('Rang', 'Rank'), rank(d))}
                ${stat(T('Membres suivis', 'Tracked members'), num(d.members))}
                ${stat(T('Vocal total', 'Total voice'), `${num(d.hours, 1)} h`)}
                ${stat(T('Vocal 30 j', 'Voice 30 d'), `${num(d.hours_30d, 1)} h`)}
                ${stat(T('Messages', 'Messages'), num(d.messages))}
            </div>
            ${d.since ? `<div class="hc-foot">${T('Suivi depuis le', 'Tracked since')} ${esc(d.since)}</div>` : ''}`;
    }

    function place(e) {
        const pad = 16;
        const w = card.offsetWidth;
        const h = card.offsetHeight;
        let x = e.clientX + 18;
        let y = e.clientY + 18;
        if (x + w > window.innerWidth - pad) x = Math.max(pad, e.clientX - w - 18);
        if (y + h > window.innerHeight - pad) y = Math.max(pad, window.innerHeight - h - pad);
        card.style.left = `${x}px`;
        card.style.top = `${y}px`;
    }

    function hide() {
        clearTimeout(timer);
        current = null;
        card.hidden = true;
    }

    document.addEventListener('mouseover', (e) => {
        const el = e.target.closest('[data-hover]');
        if (!el || el === current) return;
        hide();
        current = el;
        lastEvent = e;
        const key = el.dataset.hover;
        load(key); // start the request right away, the card appears after the delay
        timer = setTimeout(() => {
            load(key).then((d) => {
                if (current !== el || !d) return;
                card.innerHTML = d.kind === 'server' ? renderServer(d) : renderUser(d);
                card.style.setProperty('--hc-accent', d.accent || 'var(--ar-accent)');
                card.hidden = false;
                place(lastEvent);
            });
        }, SHOW_DELAY);
    });
    document.addEventListener('mousemove', (e) => {
        if (!current) return;
        lastEvent = e;
        if (!card.hidden) place(e);
    }, { passive: true });
    document.addEventListener('mouseout', (e) => {
        if (current && !current.contains(e.relatedTarget)) hide();
    });
    window.addEventListener('scroll', hide, { passive: true });
    document.addEventListener('click', hide);
})();
