/* Admin page: cards, charts and ranked lists fed by /admin/data (cached 60 s server side). */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const T = (fr, en, vars) => HG.tr(fr, en, vars);
const charts = {};
const initializedTabs = new Set();
let data = null;
let currentTab = 'tab-overview';
let trafficRange = 30;

const TOOLTIP = { backgroundColor: 'rgba(24, 25, 29, 0.95)', titleColor: '#fff', bodyColor: '#e3e5e8', borderColor: 'rgba(255,255,255,0.12)', borderWidth: 1, padding: 10 };
const GRID = { color: 'rgba(255, 255, 255, 0.06)' };

function switchGraphTab(tabId) {
    const OLD_TABS = { 'tab-custom': 'tab-profiles', 'tab-commands': 'tab-bot', 'tab-health': 'tab-tech' };
    tabId = OLD_TABS[tabId] || tabId;
    if (!document.getElementById(tabId)) tabId = 'tab-overview';
    currentTab = tabId;
    document.querySelectorAll('.graphs-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
    document.querySelectorAll('.graphs-tab-pane').forEach(p => p.classList.toggle('active', p.id === tabId));
    initTab(tabId);
    requestAnimationFrame(() => Object.values(charts).forEach(c => { try { c.resize(); } catch (e) {} }));
    if (window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + tabId);
}

function pct(value) {
    if (value === null || value === undefined) return '';
    return `${value > 0 ? '+' : ''}${HG.fmt(value, Math.abs(value) < 10 ? 1 : 0)} %`;
}

function dateText(iso) {
    if (!iso) return '—';
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString(HG.locale, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function ago(minutes) {
    const text = minutes >= 1440 ? `${HG.fmt(Math.floor(minutes / 1440))} ${T('j', 'd')}` : minutes >= 60 ? `${HG.fmt(Math.floor(minutes / 60))} h` : `${HG.fmt(minutes)} min`;
    return T('il y a {t}', '{t} ago', { t: text });
}

function get(path) {
    return path.split('.').reduce((o, k) => (o ? o[k] : undefined), data);
}

// Ranked list with proportional bars (avatars and links when available)
function renderList(el, rows) {
    rows = rows || [];
    const max = Math.max(1, ...rows.map(r => r.value));
    el.innerHTML = rows.map((r, i) => {
        const name = r.url ? `<a class="an-rank-name" href="${HG.esc(r.url)}">${HG.esc(r.name)}</a>` : `<span class="an-rank-name">${HG.esc(r.name)}</span>`;
        const avatar = r.avatar ? `<img src="${HG.esc(r.avatar)}" alt="">` : (r.color ? `<i class="adm-dot" style="background:${HG.esc(r.color)}"></i>` : '');
        return `<li class="an-rank-item${i < 3 ? ' podium-' + (i + 1) : ''}">
            <span class="an-rank-pos">${i + 1}</span>${avatar}${name}
            <span class="an-rank-bar"><i style="width:${Math.max(3, r.value / max * 100)}%"></i></span>
            <span class="an-rank-value">${HG.fmt(r.value)}</span></li>`;
    }).join('') || `<li class="an-rank-empty">${T('Pas encore de données', 'No data yet')}</li>`;
}

// Long lists and tables: scroll inside the card, with a search field to filter the rows
const SEARCH_FROM = 8;
const fold = text => (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

function enhanceLong(box, itemSelector) {
    const items = [...box.querySelectorAll(itemSelector)];
    box.classList.toggle('adm-scroll', items.length > SEARCH_FROM);
    if (items.length <= SEARCH_FROM || box.previousElementSibling?.classList.contains('adm-search')) return;
    const wrap = document.createElement('label');
    wrap.className = 'adm-search';
    wrap.innerHTML = `<svg width="15" height="15" aria-hidden="true" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" data-px="search"><path d="M2 0h3v1h-3zM1 1h1v1h-1zM5 1h1v1h-1zM0 2h1v1h-1zM6 2h1v1h-1zM0 3h1v1h-1zM6 3h1v1h-1zM0 4h1v1h-1zM6 4h1v1h-1zM1 5h1v1h-1zM5 5h1v1h-1zM2 6h3v1h-3zM6 6h1v1h-1zM6 7h2v1h-2zM7 8h2v1h-2z"/><path d="M2 1h3v1h-3zM1 2h5v1h-5zM1 3h5v1h-5zM1 4h5v1h-5zM2 5h3v1h-3z" opacity="0.3"/></svg>
        <input type="search" placeholder="${T('Rechercher', 'Search')}…" aria-label="${T('Rechercher dans la liste', 'Search the list')}">
        <span class="adm-search-count"></span>`;
    box.before(wrap);
    const input = wrap.querySelector('input');
    const count = wrap.querySelector('.adm-search-count');
    const empty = document.createElement('p');
    empty.className = 'adm-search-empty';
    empty.textContent = T('Aucun résultat', 'No result');
    empty.hidden = true;
    box.after(empty);
    const update = () => {
        const q = fold(input.value.trim());
        let shown = 0;
        box.querySelectorAll(itemSelector).forEach(el => {
            const match = !q || fold(el.textContent).includes(q);
            el.hidden = !match;
            shown += match;
        });
        count.textContent = q ? `${HG.fmt(shown)} / ${HG.fmt(items.length)}` : HG.fmt(items.length);
        empty.hidden = shown > 0;
        box.scrollTop = 0;
    };
    input.addEventListener('input', update);
    update();
}

function renderStats(el, items) {
    el.innerHTML = items.map(([label, value, sub, tone]) => `
        <div class="adm-stat ${tone ? 'is-' + tone : ''}">
            <span class="adm-stat-label">${HG.esc(label)}</span>
            <span class="adm-stat-value">${value}</span>
            ${sub ? `<span class="adm-stat-sub">${HG.esc(sub)}</span>` : ''}
        </div>`).join('');
}

function lineChart(id, labels, datasets, opts = {}) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), {
        type: opts.type || 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: datasets.length > 1, labels: { color: '#e3e5e8', usePointStyle: true } }, tooltip: TOOLTIP },
            scales: {
                x: { stacked: !!opts.stacked, grid: { display: false }, ticks: { color: '#a3a6b0', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                y: { stacked: !!opts.stacked, beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0', precision: 0 } },
            },
        },
    });
}

const area = (label, values, color) => ({ label, data: values, borderColor: color, backgroundColor: color + '33', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 0 });
const bars = (label, values, color) => ({ label, data: values, backgroundColor: color, borderRadius: 4 });

// ---------------------------------------------------------------------------
// Header: bot status and update time (the key figures are in the Overview tab)
function renderKpis() {
    const o = data.overview;
    const b = data.bot;
    const status = document.getElementById('admBotStatus');
    status.textContent = b.bot_online ? T('Bot en ligne', 'Bot online') : T('Bot silencieux', 'Bot silent');
    status.className = 'adm-bot-status ' + (b.bot_online ? 'ok' : 'ko');
    status.title = `${T('Dernier relevé de présence', 'Last presence snapshot')} : ${dateText(b.last_presence)}`;
    document.getElementById('admMeta').textContent = `${T('Mis à jour', 'Updated')} ${dateText(data.generated_at)}`
        + (o.tracking_since ? ` · ${T('mesure d’audience depuis le', 'audience tracked since')} ${o.tracking_since}` : '');
}

function renderTraffic() {
    const t = data.traffic;
    const n = trafficRange;
    lineChart('trafficChart', t.labels.slice(-n), [
        area(T('Pages vues', 'Page views'), t.views.slice(-n), '#717cf8'),
        area(T('Visiteurs uniques', 'Unique visitors'), t.uniques.slice(-n), '#a78bfa'),
    ]);
    const total = t.views.slice(-n).reduce((a, b) => a + b, 0);
    const uniq = t.uniques.slice(-n).reduce((a, b) => a + b, 0);
    document.getElementById('trafficSummary').textContent = `${HG.fmt(total)} ${T('pages vues', 'page views')} · ${HG.fmt(uniq)} ${T('visiteurs-jour', 'visitor-days')}`;
}

// ---------------------------------------------------------------------------
// Tabs are made of sections; each tab renders its sections once, when first opened
// ---------------------------------------------------------------------------
const TAB_LABELS = {
    'tab-traffic': T('Site web', 'Website'), 'tab-accounts': T('Comptes', 'Accounts'), 'tab-profiles': T('Profils', 'Profiles'),
    'tab-community': T('Communauté', 'Community'), 'tab-bot': 'Bot', 'tab-tech': T('Technique', 'Technical'),
    'tab-security': T('Sécurité', 'Security'),
};

function sectionOverview() {
    const o = data.overview, b = data.bot, c = data.commands, h = data.health, a = b.audience;
    const sum = arr => (arr || []).reduce((x, y) => x + y, 0);
    const errors500 = sum(h.s500);
    const tiles = [
        ['tab-traffic', T('Visites · 7 jours', 'Visits · 7 days'), HG.fmt(o.views_7),
            o.delta_7 === null ? T('mesure en cours de démarrage', 'tracking just started') : `${pct(o.delta_7)} ${T('vs 7 j précédents', 'vs previous 7 d')}`, ''],
        ['tab-traffic', T('Visiteurs uniques · aujourd’hui', 'Unique visitors · today'), HG.fmt(o.uniques_today), `${T('moyenne 7 j', '7-day average')} : ${HG.fmt(o.uniques_7_avg, 1)}`, ''],
        ['tab-accounts', T('Comptes Discord liés', 'Linked Discord accounts'), HG.fmt(o.accounts), `+${HG.fmt(o.accounts_new_week)} ${T('cette semaine', 'this week')}`, ''],
        ['tab-profiles', T('Profils personnalisés', 'Customized profiles'), HG.fmt(o.customized), `${HG.fmt(o.customized_percent, 1)} % ${T('des comptes liés', 'of linked accounts')}`, ''],
        ['tab-community', T('Membres présents', 'Members present'), a ? HG.fmt(a.unique) : '—',
            a ? `${HG.fmt(a.silent_percent, 1)} % ${T('jamais actifs', 'never active')}` : T('en attente du bot v3.3.0', 'waiting for bot v3.3.0'), ''],
        ['tab-community', T('Serveurs du bot', 'Bot servers'), HG.fmt(b.servers_present), `${HG.fmt(b.servers_active30)} ${T('actifs sur 30 j', 'active in 30 d')}`, ''],
        ['tab-bot', T('Commandes · 30 jours', 'Commands · 30 days'), HG.fmt(c.total), `${HG.fmt(c.failed_percent, 1)} % ${T('d’erreurs', 'errors')}`, c.failed ? 'warn' : ''],
        ['tab-security', T('Alertes de sécurité · 24 h', 'Security alerts · 24 h'), HG.fmt(securityAlerts(24)),
            `${HG.fmt(securityAlerts(7))} ${T('sur 7 jours', 'in 7 days')}`, securityAlerts(24) > 50 ? 'ko' : securityAlerts(24) ? 'warn' : 'ok'],
        ['tab-tech', T('Erreurs serveur · 30 j', 'Server errors · 30 d'), HG.fmt(errors500), `${HG.fmt(sum(h.s404))} ${T('pages introuvables', 'pages not found')}`, errors500 ? 'ko' : 'ok'],
    ];
    const box = document.getElementById('overviewTiles');
    box.innerHTML = tiles.map(([tab, label, value, sub, tone]) => `
        <button type="button" class="adm-tile ${tone ? 'is-' + tone : ''}" data-goto="${tab}">
            <span class="adm-stat-label">${HG.esc(label)}</span>
            <span class="adm-tile-value">${value}</span>
            <span class="adm-stat-sub">${HG.esc(sub)}</span>
            <span class="adm-tile-go">${HG.esc(TAB_LABELS[tab])}</span>
        </button>`).join('');
    box.querySelectorAll('[data-goto]').forEach(btn => btn.addEventListener('click', () => switchGraphTab(btn.dataset.goto)));
    const t = data.traffic;
    lineChart('overviewChart', t.labels.slice(-30), [
        area(T('Pages vues', 'Page views'), t.views.slice(-30), '#717cf8'),
        area(T('Visiteurs uniques', 'Unique visitors'), t.uniques.slice(-30), '#a78bfa'),
    ]);
    document.getElementById('overviewSummary').textContent =
        `${HG.fmt(sum(t.views.slice(-30)))} ${T('pages vues', 'page views')} · ${HG.fmt(sum(t.uniques.slice(-30)))} ${T('visiteurs-jour', 'visitor-days')}`;
}

function sectionTraffic() {

        renderTraffic();
        const t = data.traffic;
        lineChart('hourlyChart', [...Array(24).keys()].map(h => `${h}h`), [bars(T('Pages vues', 'Page views'), t.hourly, '#717cf8')], { type: 'bar' });
        const dev = t.devices, totalDev = Math.max(1, dev.mobile + dev.desktop);
        const langs = t.langs, totalLang = Math.max(1, (langs.fr || 0) + (langs.en || 0));
        document.getElementById('trafficSplits').innerHTML =
            `<span><svg width="14" height="14" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" aria-hidden="true" data-px="phone"><path d="M2 0h5v1h-5zM2 1h1v1h-1zM6 1h1v1h-1zM2 2h1v1h-1zM6 2h1v1h-1zM2 3h1v1h-1zM6 3h1v1h-1zM2 4h1v1h-1zM6 4h1v1h-1zM2 5h1v1h-1zM6 5h1v1h-1zM2 6h5v1h-5zM2 7h2v1h-2zM5 7h2v1h-2zM2 8h5v1h-5z"/></svg> ${HG.fmt(dev.mobile / totalDev * 100)} %</span><span><svg width="14" height="14" viewBox="0 -0.5 9 9" fill="currentColor" shape-rendering="crispEdges" aria-hidden="true" data-px="desktop"><path d="M0 0h9v1h-9zM0 1h1v1h-1zM8 1h1v1h-1zM0 2h1v1h-1zM8 2h1v1h-1zM0 3h1v1h-1zM8 3h1v1h-1zM0 4h1v1h-1zM8 4h1v1h-1zM0 5h9v1h-9zM3 6h3v1h-3zM2 7h5v1h-5z"/></svg> ${HG.fmt(dev.desktop / totalDev * 100)} %</span>` +
            `<span>FR ${HG.fmt((langs.fr || 0) / totalLang * 100)} %</span><span>EN ${HG.fmt((langs.en || 0) / totalLang * 100)} %</span>`;
}

function sectionAccounts() {

        const a = data.accounts;
        renderStats(document.getElementById('accountStats'), [
            [T('Comptes liés au moins une fois', 'Accounts linked at least once'), HG.fmt(a.total), `${HG.fmt(a.linked_percent, 1)} % ${T('des', 'of the')} ${HG.fmt(a.members_total)} ${T('membres suivis', 'tracked members')}`],
            [T('Nouveaux cette semaine', 'New this week'), HG.fmt(a.new_week)],
            [T('Actifs · 7 jours', 'Active · 7 days'), HG.fmt(a.active7)],
            [T('Actifs · 30 jours', 'Active · 30 days'), HG.fmt(a.active30)],
        ]);
        lineChart('weeksChart', a.weeks.labels, [bars(T('Nouveaux comptes', 'New accounts'), a.weeks.values, '#a78bfa')], { type: 'bar' });
        lineChart('activeChart', a.active_daily.labels, [area(T('Comptes actifs', 'Active accounts'), a.active_daily.values, '#34d399')]);
        document.querySelector('#recentLogins tbody').innerHTML = a.recent.map(r => `<tr>
            <td><a href="${HG.esc(r.url)}" class="adm-user">${r.avatar ? `<img src="${HG.esc(r.avatar)}" alt="">` : ''}${HG.esc(r.name)}</a></td>
            <td>${dateText(r.last)}</td><td>${HG.fmt(r.count)} ${T('connexion(s)', 'login(s)')}</td>
            <td class="adm-muted">${T('depuis', 'since')} ${dateText(r.first)}</td></tr>`).join('')
            || `<tr><td>${T('Aucune connexion enregistrée', 'No login recorded')}</td></tr>`;
}

function sectionCustomization() {

        const c = data.customization;
        renderStats(document.getElementById('customStats'), [
            [T('Profils personnalisés', 'Customized profiles'), HG.fmt(c.customized), `${HG.fmt(c.customized_percent, 1)} % ${T('des comptes liés', 'of linked accounts')}`],
            [T('Profils privés', 'Private profiles'), HG.fmt(c.private)],
            [T('Serveur favori choisi', 'Favorite server set'), HG.fmt(c.favorite)],
        ]);
}

function sectionCommands() {

        const c = data.commands;
        document.getElementById('commandsNotice').hidden = c.total > 0;
        renderStats(document.getElementById('commandStats'), [
            [T('Commandes · 30 jours', 'Commands · 30 days'), HG.fmt(c.total), `${HG.fmt(c.today)} ${T("aujourd'hui", 'today')}`],
            [T('En messages privés', 'In direct messages'), HG.fmt(c.dm)],
            [T('Erreurs', 'Errors'), HG.fmt(c.failed), `${HG.fmt(c.failed_percent, 1)} %`, c.failed ? 'warn' : 'ok'],
        ]);
        lineChart('commandsChart', c.labels, [bars(T('Commandes', 'Commands'), c.daily, '#717cf8')], { type: 'bar' });
        document.querySelector('#commandPerf tbody').innerHTML = c.perf.map(r => `<tr><td><code>${HG.esc(r.name)}</code></td>
            <td>${HG.fmt(r.count)}</td><td>${T('moy.', 'avg')} ${HG.fmt(r.avg_ms)} ms</td><td class="adm-muted">p95 ${HG.fmt(r.p95_ms)} ms</td>
            <td class="${r.failed ? 'adm-bad' : 'adm-muted'}">${HG.fmt(r.failed)} ${T('erreur(s)', 'error(s)')}</td></tr>`).join('')
            || `<tr><td>${T('Pas encore de données', 'No data yet')}</td></tr>`;
}

function sectionBotStatus() {

        const b = data.bot;
        renderStats(document.getElementById('botStats'), [
            [T('Serveurs où le bot est présent', 'Servers with the bot'), HG.fmt(b.servers_present), `${HG.fmt(b.servers_left)} ${T('quittés', 'left')} · ${HG.fmt(b.servers_active30)} ${T('actifs sur 30 j', 'active in 30 d')}`],
            [T('Membres suivis', 'Tracked members'), HG.fmt(b.members_total)],
            [T('En vocal maintenant', 'In voice now'), HG.fmt(b.voice_now), `${HG.fmt(b.messages_24h)} ${T('messages sur 24 h', 'messages in 24 h')}`],
            [T('Dernier relevé du bot', 'Last bot snapshot'), dateText(b.last_presence),
                b.presence_age_min === null ? '' : ago(b.presence_age_min), b.bot_online ? 'ok' : 'ko'],
            [T('Sessions vocales orphelines', 'Orphan voice sessions'), HG.fmt(b.orphans), T('ouvertes depuis plus de 24 h', 'open for more than 24 h'), b.orphans ? 'warn' : 'ok'],
        ]);
}

function sectionCommunity() {
        const b = data.bot;
        lineChart('serversChart', b.months.labels, [bars(T('Arrivées', 'Joins'), b.months.joins, '#34d399'), bars(T('Départs', 'Leaves'), b.months.leaves, '#f87171')], { type: 'bar' });
        // Unique members present on the servers (active or not)
        const a = b.audience;
        document.getElementById('audienceNotice').hidden = !!a;
        document.getElementById('audienceChartWrap').hidden = !a;
        if (a) {
            renderStats(document.getElementById('audienceStats'), [
                [T('Membres uniques', 'Unique members'), HG.fmt(a.unique), `${T('relevé', 'snapshot')} ${dateText(a.at)}`],
                [T('En ligne', 'Online'), HG.fmt(a.online), `${HG.fmt(a.unique ? a.online / a.unique * 100 : 0, 1)} %`],
                [T('Jamais actifs', 'Never active'), HG.fmt(a.silent), `${HG.fmt(a.silent_percent, 1)} % ${T('n’ont jamais parlé ni rejoint un vocal', 'never talked nor joined voice')}`, a.silent_percent > 50 ? 'warn' : ''],
                [T('Déjà actifs', 'Already active'), HG.fmt(a.known), T('ont un profil Hourglass', 'have a Hourglass profile')],
                [T('Serveurs par membre', 'Servers per member'), HG.fmt(a.per_member, 2), `${HG.fmt(a.memberships)} ${T('appartenances sur', 'memberships on')} ${HG.fmt(a.servers)} ${T('serveurs', 'servers')}`],
            ]);
            lineChart('audienceChart', a.labels, [
                area(T('Membres uniques', 'Unique members'), a.unique_daily, '#717cf8'),
                area(T('Déjà actifs', 'Already active'), a.known_daily, '#34d399'),
            ]);
        }
        const avatar = r => (r.avatar ? `<img src="${HG.esc(r.avatar)}" alt="">` : '');
        document.querySelector('#recentMembers tbody').innerHTML = b.arrivals.members.map(r => `<tr>
            <td><a href="${HG.esc(r.url)}" class="adm-user">${avatar(r)}${HG.esc(r.name)}</a></td>
            <td class="adm-muted">${r.server_url ? `<a href="${HG.esc(r.server_url)}" class="adm-link">${HG.esc(r.server)}</a>` : '—'}</td>
            <td>${dateText(r.at)}</td></tr>`).join('') || `<tr><td>${T('Aucun membre', 'No member')}</td></tr>`;
        document.querySelector('#recentServers tbody').innerHTML = b.arrivals.servers.map(r => `<tr>
            <td><a href="${HG.esc(r.url)}" class="adm-user">${avatar(r)}${HG.esc(r.name)}</a></td>
            <td>${dateText(r.at)}</td>
            <td class="${r.left ? 'adm-bad' : 'adm-muted'}">${r.left ? `${T('parti le', 'left on')} ${dateText(r.left)}` : T('présent', 'present')}</td></tr>`).join('')
            || `<tr><td>${T('Aucun serveur', 'No server')}</td></tr>`;
}

function sectionDatabase() {
        const b = data.bot;
        document.getElementById('dbSize').textContent = `${T('Taille totale', 'Total size')} : ${HG.fmt(b.db_mb, 1)} Mo`;
        document.querySelector('#dbTables tbody').innerHTML = b.tables.map(r => `<tr><td><code>${HG.esc(r.name)}</code></td>
            <td>${HG.fmt(r.rows)} ${T('lignes', 'rows')}</td><td>${HG.fmt(r.mb, 1)} Mo</td></tr>`).join('');
}

function sectionHealth() {

        const h = data.health;
        const r = h.analytics_refresh || {};
        renderStats(document.getElementById('healthStats'), [
            ['404 · 30 j', HG.fmt(h.s404.reduce((a, b) => a + b, 0))],
            ['429 · 30 j', HG.fmt(h.s429.reduce((a, b) => a + b, 0)), T('limite de requêtes atteinte', 'rate limit reached')],
            ['500 · 30 j', HG.fmt(h.s500.reduce((a, b) => a + b, 0)), '', h.s500.some(v => v) ? 'ko' : 'ok'],
            [T('Calcul de la page Analyses', 'Analytics page computation'), r.ms !== undefined ? `${HG.fmt(r.ms)} ms` : '—',
                r.at ? `${T('dernier rafraîchissement', 'last refresh')} ${dateText(r.at)} (${T('ce worker', 'this worker')})` : T('pas encore rafraîchi sur ce worker', 'not refreshed on this worker yet'),
                r.ms > 2000 ? 'warn' : ''],
        ]);
        // Session key: anything but a stored key means members are logged out when the container is recreated
        const keySources = {
            env: [T('Variable SECRET_KEY', 'SECRET_KEY variable'), T('stable entre les mises à jour', 'stable across updates'), 'ok'],
            discord: [T('Dérivée de DISCORD_CLIENT_SECRET', 'Derived from DISCORD_CLIENT_SECRET'), T('stable entre les mises à jour', 'stable across updates'), 'ok'],
            database: [T('Enregistrée en base', 'Stored in the database'), T('stable entre les mises à jour', 'stable across updates'), 'ok'],
            file: [T('Fichier du conteneur', 'Container file'), T('perdue à chaque mise à jour : membres déconnectés', 'lost on every update: members logged out'), 'ko'],
            random: [T('Aléatoire', 'Random'), T('change à chaque démarrage : membres déconnectés', 'changes on every start: members logged out'), 'ko'],
        };
        const ks = keySources[h.session_key_source] || keySources.random;
        const tiles = document.getElementById('healthStats');
        tiles.insertAdjacentHTML('beforeend', `<div class="adm-stat is-${ks[2]}"><span class="adm-stat-label">${T('Clé de session', 'Session key')}</span>
            <span class="adm-stat-value" style="font-size:1.05rem">${HG.esc(ks[0])}</span><span class="adm-stat-sub">${HG.esc(ks[1])}</span></div>`);
        lineChart('statusChart', h.labels, [bars('404', h.s404, '#a3a6b0'), bars('429', h.s429, '#fbbf24'), bars('500', h.s500, '#f87171')], { type: 'bar', stacked: true });
}

// ---------------------------------------------------------------------------
// Security journal
// ---------------------------------------------------------------------------
const SECURITY_COLORS = {
    login_fail: '#f87171', admin_denied: '#fb923c', csrf_fail: '#facc15', rate_limited: '#a3a6b0', scan: '#b07cff',
    card_token_fail: '#ef4444', csp_violation: '#38bdf8', server_error: '#ff6b5e', too_large: '#4f9dff',
};
const QUIET_KINDS = ['login_ok', 'admin_access'];

// Suspicious events (everything but successful logins and admin access) over the last 24 h or 7 days
function securityAlerts(hoursOrDays) {
    const s = data.security || {};
    const totals = (hoursOrDays === 24 ? s.totals_24h : s.totals_7d) || {};
    return Object.entries(totals).filter(([k]) => !QUIET_KINDS.includes(k)).reduce((a, [, n]) => a + n, 0);
}

function securityRow(e, withPath = true) {
    const who = e.user
        ? (e.user_url ? `<a href="${HG.esc(e.user_url)}" class="adm-link">${HG.esc(e.user)}</a>` : HG.esc(e.user))
        : (e.ip ? `<code>${HG.esc(e.ip)}</code>` : '');
    return `<tr data-kind="${HG.esc(e.kind)}">
        <td><span class="adm-sev is-${HG.esc(e.severity)}">${HG.esc(e.label)}</span>${e.hits > 1 ? ` <span class="adm-hits">×${HG.fmt(e.hits)}</span>` : ''}</td>
        <td class="adm-muted">${dateText(e.at)}</td>
        <td>${who}${e.user && e.ip ? ` <code class="adm-muted">${HG.esc(e.ip)}</code>` : ''}</td>
        ${withPath && e.path ? `<td><code>${HG.esc(e.path)}</code></td>` : ''}
        ${e.detail ? `<td class="adm-muted">${HG.esc(e.detail)}</td>` : ''}</tr>`;
}

function sectionSecurity() {
    const s = data.security;
    document.getElementById('securityNotice').hidden = s.enabled;
    const t24 = s.totals_24h, t7 = s.totals_7d;
    const n = (k, src = t24) => src[k] || 0;
    const tile = (kind, label, warnAt = 1, koAt = Infinity) =>
        [label, HG.fmt(n(kind)), `${HG.fmt(n(kind, t7))} ${T('sur 7 j', 'in 7 d')}`, n(kind) >= koAt ? 'ko' : n(kind) >= warnAt ? 'warn' : 'ok'];
    renderStats(document.getElementById('securityStats'), [
        tile('login_fail', T('Connexions échouées', 'Failed logins'), 5, 30),
        [T('Connexions réussies', 'Successful logins'), HG.fmt(n('login_ok')), `${HG.fmt(n('login_ok', t7))} ${T('sur 7 j', 'in 7 d')}`, ''],
        tile('scan', T('Scans de robots', 'Bot scans'), 20, 500),
        tile('rate_limited', T('Limites de requêtes (429)', 'Rate limits (429)'), 10, 200),
        tile('admin_denied', T('Accès admin refusés', 'Admin access denied'), 1, 20),
        tile('csrf_fail', T('Formulaires refusés (CSRF)', 'Forms refused (CSRF)'), 1, 10),
        tile('card_token_fail', T('Jetons de carte invalides', 'Invalid card tokens'), 1, 1),
        tile('csp_violation', T('Violations CSP', 'CSP violations'), 1, 50),
        tile('server_error', T('Erreurs serveur (500)', 'Server errors (500)'), 1, 10),
        tile('too_large', T('Requêtes trop grosses', 'Requests too large'), 1, 20),
    ]);
    const kinds = s.kinds.filter(k => !QUIET_KINDS.includes(k.key) && (s.daily[k.key] || []).some(v => v));
    lineChart('securityChart', s.labels,
        kinds.map(k => bars(k.label, s.daily[k.key], SECURITY_COLORS[k.key] || '#a3a6b0')), { type: 'bar', stacked: true });
    document.getElementById('securityRetention').textContent =
        T('300 derniers événements · conservés {n} jours · IP abrégée', 'Last 300 events · kept {n} days · shortened IP', { n: s.retention_days });

    const log = document.querySelector('#securityLog tbody');
    log.innerHTML = s.recent.map(e => securityRow(e)).join('') || `<tr><td>${T('Aucun événement enregistré', 'No event recorded')}</td></tr>`;
    const select = document.getElementById('securityKind');
    s.kinds.forEach(k => select.insertAdjacentHTML('beforeend', `<option value="${HG.esc(k.key)}">${HG.esc(k.label)}</option>`));
    select.dispatchEvent(new Event('change'));  // redraws the custom list with the new options
    select.addEventListener('change', () => {
        log.querySelectorAll('tr[data-kind]').forEach(tr => { tr.classList.toggle('is-filtered', !!select.value && tr.dataset.kind !== select.value); });
    });

    document.querySelector('#adminLog tbody').innerHTML = s.admin_log.map(e => securityRow(e, false)).join('')
        || `<tr><td>${T('Aucun accès enregistré', 'No access recorded')}</td></tr>`;
    document.getElementById('securityCheckup').innerHTML = s.checkup.map(c => `
        <li class="${c.ok ? 'is-ok' : 'is-ko'}"><span class="adm-check">${c.ok ? '✓' : '✕'}</span>
            <span class="adm-check-text"><strong>${HG.esc(c.label)}</strong><span class="adm-muted">${HG.esc(c.detail || '')}</span></span></li>`).join('');
}

const TAB_SECTIONS = {
    'tab-overview': [sectionOverview],
    'tab-traffic': [sectionTraffic],
    'tab-accounts': [sectionAccounts],
    'tab-profiles': [sectionCustomization],
    'tab-community': [sectionCommunity],
    'tab-bot': [sectionBotStatus, sectionCommands],
    'tab-tech': [sectionHealth, sectionDatabase],
    'tab-security': [sectionSecurity],
};

function initTab(tabId) {
    if (!data || initializedTabs.has(tabId)) return;
    initializedTabs.add(tabId);
    const pane = document.getElementById(tabId);
    pane.querySelectorAll('[data-list]').forEach(el => renderList(el, get(el.dataset.list)));
    (TAB_SECTIONS[tabId] || []).forEach(render => render());
    pane.querySelectorAll('[data-list]').forEach(el => enhanceLong(el, 'li.an-rank-item'));
    pane.querySelectorAll('.adm-table-wrap').forEach(el => enhanceLong(el, 'tbody tr'));
}

document.addEventListener('DOMContentLoaded', () => {
    Chart.defaults.color = '#a3a6b0';
    Chart.defaults.font.family = 'Arial, sans-serif';
    document.querySelectorAll('[data-range]').forEach(btn => btn.addEventListener('click', () => {
        trafficRange = parseInt(btn.dataset.range, 10);
        document.querySelectorAll('[data-range]').forEach(b => b.classList.toggle('active', b === btn));
        if (data) renderTraffic();
    }));
    switchGraphTab(window.location.hash.replace('#', '') || 'tab-overview');
    fetch('/admin/data', { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(json => {
            data = json;
            renderKpis();
            initTab(currentTab);
            document.querySelectorAll('.chart-loading-overlay').forEach(el => el.classList.add('loaded'));
        })
        .catch(err => {
            console.error('Admin data failed:', err);
            document.querySelectorAll('.chart-spinner-text').forEach(el => { el.textContent = T('Erreur de chargement', 'Loading error'); el.style.color = '#ef4444'; });
        });
});
