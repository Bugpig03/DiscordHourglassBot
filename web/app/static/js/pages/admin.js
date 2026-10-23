/* Admin page: cards, charts and ranked lists fed by /admin/data (cached 60 s server side). */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const IS_EN = PAGE_CFG.current_lang === 'en';
const T = (fr, en) => (IS_EN ? en : fr);
const charts = {};
const initializedTabs = new Set();
let data = null;
let currentTab = 'tab-overview';
let trafficRange = 30;

const TOOLTIP = { backgroundColor: 'rgba(15, 23, 42, 0.95)', titleColor: '#fff', bodyColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.12)', borderWidth: 1, padding: 10 };
const GRID = { color: 'rgba(255, 255, 255, 0.06)' };

function switchGraphTab(tabId) {
    const OLD_TABS = { 'tab-custom': 'tab-accounts', 'tab-commands': 'tab-bot', 'tab-health': 'tab-tech' };
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
    return d.toLocaleString(IS_EN ? 'en-GB' : 'fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function ago(minutes) {
    const text = minutes >= 1440 ? `${HG.fmt(Math.floor(minutes / 1440))} ${T('j', 'd')}` : minutes >= 60 ? `${HG.fmt(Math.floor(minutes / 60))} h` : `${HG.fmt(minutes)} min`;
    return IS_EN ? `${text} ago` : `il y a ${text}`;
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
    wrap.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
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
            plugins: { legend: { display: datasets.length > 1, labels: { color: '#e2e8f0', usePointStyle: true } }, tooltip: TOOLTIP },
            scales: {
                x: { stacked: !!opts.stacked, grid: { display: false }, ticks: { color: '#94a3b8', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                y: { stacked: !!opts.stacked, beginAtZero: true, grid: GRID, ticks: { color: '#94a3b8', precision: 0 } },
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
        area(T('Pages vues', 'Page views'), t.views.slice(-n), '#38bdf8'),
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
    'tab-traffic': T('Site web', 'Website'), 'tab-accounts': T('Comptes', 'Accounts'),
    'tab-community': T('Communauté', 'Community'), 'tab-bot': 'Bot', 'tab-tech': T('Technique', 'Technical'),
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
        ['tab-accounts', T('Profils personnalisés', 'Customized profiles'), HG.fmt(o.customized), `${HG.fmt(o.customized_percent, 1)} % ${T('des comptes liés', 'of linked accounts')}`, ''],
        ['tab-community', T('Membres présents', 'Members present'), a ? HG.fmt(a.unique) : '—',
            a ? `${HG.fmt(a.silent_percent, 1)} % ${T('jamais actifs', 'never active')}` : T('en attente du bot v3.3.0', 'waiting for bot v3.3.0'), ''],
        ['tab-community', T('Serveurs du bot', 'Bot servers'), HG.fmt(b.servers_present), `${HG.fmt(b.servers_active30)} ${T('actifs sur 30 j', 'active in 30 d')}`, ''],
        ['tab-bot', T('Commandes · 30 jours', 'Commands · 30 days'), HG.fmt(c.total), `${HG.fmt(c.failed_percent, 1)} % ${T('d’erreurs', 'errors')}`, c.failed ? 'warn' : ''],
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
        area(T('Pages vues', 'Page views'), t.views.slice(-30), '#38bdf8'),
        area(T('Visiteurs uniques', 'Unique visitors'), t.uniques.slice(-30), '#a78bfa'),
    ]);
    document.getElementById('overviewSummary').textContent =
        `${HG.fmt(sum(t.views.slice(-30)))} ${T('pages vues', 'page views')} · ${HG.fmt(sum(t.uniques.slice(-30)))} ${T('visiteurs-jour', 'visitor-days')}`;
}

function sectionTraffic() {

        renderTraffic();
        const t = data.traffic;
        lineChart('hourlyChart', [...Array(24).keys()].map(h => `${h}h`), [bars(T('Pages vues', 'Page views'), t.hourly, '#38bdf8')], { type: 'bar' });
        const dev = t.devices, totalDev = Math.max(1, dev.mobile + dev.desktop);
        const langs = t.langs, totalLang = Math.max(1, (langs.fr || 0) + (langs.en || 0));
        document.getElementById('trafficSplits').innerHTML =
            `<span>📱 ${HG.fmt(dev.mobile / totalDev * 100)} %</span><span>💻 ${HG.fmt(dev.desktop / totalDev * 100)} %</span>` +
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
        lineChart('commandsChart', c.labels, [bars(T('Commandes', 'Commands'), c.daily, '#38bdf8')], { type: 'bar' });
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
                area(T('Membres uniques', 'Unique members'), a.unique_daily, '#38bdf8'),
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
        lineChart('statusChart', h.labels, [bars('404', h.s404, '#94a3b8'), bars('429', h.s429, '#fbbf24'), bars('500', h.s500, '#f87171')], { type: 'bar', stacked: true });
}

const TAB_SECTIONS = {
    'tab-overview': [sectionOverview],
    'tab-traffic': [sectionTraffic],
    'tab-accounts': [sectionAccounts, sectionCustomization],
    'tab-community': [sectionCommunity],
    'tab-bot': [sectionBotStatus, sectionCommands],
    'tab-tech': [sectionHealth, sectionDatabase],
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
    Chart.defaults.color = '#94a3b8';
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
