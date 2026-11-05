/* Admin console: sidebar sections, a period for the whole page (7 / 30 / 90 days), cards, charts and lists fed by
   /admin/data?days=N (cached 60 s server side). Each section renders once per loaded period, when first opened. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const T = (fr, en, vars) => HG.tr(fr, en, vars);
const charts = {};
const initializedTabs = new Set();
let data = null;
let currentTab = 'tab-overview';
let days = 30;
const PERIODS = [7, 30, 90];

const TOOLTIP = { backgroundColor: '#1d1f26', titleColor: '#e8e9ee', bodyColor: '#b6b9c3', borderColor: '#333744', borderWidth: 1, padding: 10 };
const GRID = { color: '#22252d' };
const periodLabel = () => T('{n} j', '{n} d', { n: days });

function switchGraphTab(tabId) {
    const OLD_TABS = { 'tab-custom': 'tab-profiles', 'tab-commands': 'tab-bot', 'tab-health': 'tab-tech' };
    tabId = OLD_TABS[tabId] || tabId;
    if (!document.getElementById(tabId)) tabId = 'tab-overview';
    currentTab = tabId;
    document.querySelectorAll('.adm-nav-item[data-tab]').forEach(b => {
        const on = b.dataset.tab === tabId;
        b.classList.toggle('active', on);
        if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    });
    document.querySelectorAll('.graphs-tab-pane').forEach(p => p.classList.toggle('active', p.id === tabId));
    const item = document.querySelector(`.adm-nav-item[data-tab="${tabId}"] .adm-nav-label`);
    if (item) {
        document.getElementById('admTitle').textContent = item.textContent;
        document.title = `${item.textContent} · Admin · Hourglass`;
    }
    setDrawer(false);
    initTab(tabId);
    if (tabId === 'tab-logs') startLogs(); else stopLogs();
    requestAnimationFrame(() => Object.values(charts).forEach(c => { try { c.resize(); } catch (e) {} }));
    if (window.history && window.history.replaceState) window.history.replaceState(null, '', `?days=${days}#${tabId}`);
}

function setDrawer(open) {
    document.getElementById('admApp').classList.toggle('side-open', open);
    document.getElementById('admScrim').hidden = !open;
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

// Items: [label, value, sub, tone, tip]; the tip says in a sentence what the figure counts (shown on hover)
function renderStats(el, items) {
    el.innerHTML = items.map(([label, value, sub, tone, tip]) => `
        <div class="adm-stat ${tone ? 'is-' + tone : ''}"${tipAttr(tip)}>
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
            plugins: { legend: { display: datasets.length > 1, labels: { color: '#b6b9c3', usePointStyle: true, boxWidth: 8 } }, tooltip: TOOLTIP },
            scales: {
                x: { stacked: !!opts.stacked, grid: { display: false }, ticks: { color: '#868a96', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                y: { stacked: !!opts.stacked, beginAtZero: true, grid: GRID, border: { display: false }, ticks: { color: '#868a96', precision: 0 } },
            },
        },
    });
}

// data-tip attribute (ui.js tooltip: hover, keyboard focus and tap); tabindex lets the keyboard reach it
const tipAttr = tip => (tip ? ` data-tip="${HG.esc(tip)}" tabindex="0"` : '');

const area = (label, values, color) => ({ label, data: values, borderColor: color, backgroundColor: color + '33', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 0 });
const bars = (label, values, color) => ({ label, data: values, backgroundColor: color, borderRadius: 4 });

// ---------------------------------------------------------------------------
// Header: bot status and update time (the key figures are in the Overview tab)
function renderKpis() {
    const o = data.overview;
    const b = data.bot;
    const status = document.getElementById('admBotStatus');
    status.textContent = b.bot_online ? T('Bot en ligne', 'Bot online') : T('Bot silencieux', 'Bot silent');
    status.className = 'adm-pill ' + (b.bot_online ? 'ok' : 'ko');
    status.title = `${T('Dernier relevé de présence', 'Last presence snapshot')} : ${dateText(b.last_presence)}`;
    document.getElementById('admMeta').textContent = `${T('Mis à jour', 'Updated')} ${dateText(data.generated_at)}`
        + (o.tracking_since ? ` · ${T('mesure d’audience depuis le', 'audience tracked since')} ${o.tracking_since}` : '');
    document.querySelectorAll('[data-period-label]').forEach(el => { el.textContent = periodLabel(); });
    document.querySelectorAll('#admPeriod [data-days]').forEach(btn => btn.classList.toggle('active', +btn.dataset.days === days));
    // Sidebar badges: what needs a look (security alerts of the day, server errors, bot silent)
    const sum = arr => (arr || []).reduce((x, y) => x + y, 0);
    setBadge('navBadgeSecurity', securityAlerts(24), securityAlerts(24) > 50);
    setBadge('navBadgeTech', sum(data.health.s500), true);
    setBadge('navBadgeBot', b.bot_online ? 0 : '!', true);
}

function setBadge(id, value, severe) {
    const el = document.getElementById(id);
    if (!el) return;
    el.hidden = !value;
    el.textContent = typeof value === 'number' ? HG.fmt(value) : value;
    el.classList.toggle('is-ko', !!severe);
}

function renderTraffic() {
    const t = data.traffic;
    lineChart('trafficChart', t.labels, [
        area(T('Pages vues', 'Page views'), t.views, '#717cf8'),
        area(T('Visiteurs uniques', 'Unique visitors'), t.uniques, '#3fd1a0'),
    ]);
    const total = t.views.reduce((a, b) => a + b, 0);
    const uniq = t.uniques.reduce((a, b) => a + b, 0);
    document.getElementById('trafficSummary').textContent = `${HG.fmt(total)} ${T('pages vues', 'page views')} · ${HG.fmt(uniq)} ${T('visiteurs-jour', 'visitor-days')}`;
}

function deltaText(value, label) {
    if (value === null || value === undefined) return T('pas encore de période à comparer', 'no previous period yet');
    return `<span class="${value >= 0 ? 'adm-delta-up' : 'adm-delta-down'}">${pct(value)}</span> ${label}`;
}

// ---------------------------------------------------------------------------
// Tabs are made of sections; each tab renders its sections once, when first opened
// ---------------------------------------------------------------------------
const TAB_LABELS = {
    'tab-traffic': T('Site web', 'Website'), 'tab-accounts': T('Comptes', 'Accounts'), 'tab-profiles': T('Profils', 'Profiles'),
    'tab-community': T('Communauté', 'Community'), 'tab-bot': 'Bot', 'tab-tech': T('Technique', 'Technical'),
    'tab-security': T('Sécurité', 'Security'),
};

// Descriptions of the figures shown in more than one place
const TIP_VIEWS = T('Pages du site affichées sur la période choisie (robots, images et API exclus), comparées à la période précédente de même durée.',
              'Site pages shown over the chosen period (bots, images and API left out), compared with the previous period of the same length.');
const TIP_UNIQUES = T('Moyenne par jour des visiteurs différents, comptés sans cookie (empreinte anonyme renouvelée chaque jour). Quelqu’un qui revient 3 jours compte 3 fois.',
              'Average number of different visitors per day, counted without cookies (anonymous fingerprint renewed daily). Someone coming back on 3 days counts 3 times.');
const TIP_ACCOUNTS = T('Membres qui se sont connectés au moins une fois au site avec leur compte Discord.',
    'Members who logged in to the site with their Discord account at least once.');
const TIP_CUSTOMIZED = T('Comptes liés qui ont changé au moins un réglage de leur profil : couleur, bannière, fond, vitrine, records épinglés, serveur favori, blocs masqués ou mode privé.',
    'Linked accounts that changed at least one profile setting: color, banner, background, showcase, pinned records, favorite server, hidden blocks or private mode.');
const TIP_UNIQUE_MEMBERS = T('Personnes différentes sur tous les serveurs du bot, actives ou non, comptées une seule fois même sur plusieurs serveurs. Relevé du bot toutes les 15 minutes.',
    'Different people on all the bot’s servers, active or not, counted once even on several servers. Bot snapshot every 15 minutes.');
const TIP_SERVERS = T('Serveurs où le bot est actuellement. « Actifs » : au moins un message ou une session vocale enregistrée sur les 30 derniers jours.',
    'Servers the bot is in right now. “Active”: at least one message or voice session recorded over the last 30 days.');
const TIP_COMMANDS = T('Commandes slash du bot utilisées sur la période, et la part qui a échoué (erreur ou délai dépassé).',
    'Bot slash commands used over the period, and the share that failed (error or timeout).');
const TIP_ACTIVE7 = T('Comptes liés qui ont utilisé le site en étant connectés au moins un jour sur les 7 derniers (30 derniers pour le chiffre du dessous).',
    'Linked accounts that used the site while logged in on at least one of the last 7 days (last 30 for the figure below).');

function sectionOverview() {
    const o = data.overview, b = data.bot, c = data.commands, h = data.health, a = b.audience;
    const sum = arr => (arr || []).reduce((x, y) => x + y, 0);
    const errors500 = sum(h.s500);
    const alerts = securityAlerts(24);
    const failing = (data.security.checkup || []).filter(x => !x.ok).length;
    const health = [
        ['tab-bot', b.bot_online ? 'ok' : 'ko', b.bot_online ? T('Bot en ligne', 'Bot online') : T('Bot silencieux', 'Bot silent'),
            b.presence_age_min === null ? T('aucun relevé', 'no snapshot') : `${T('relevé', 'snapshot')} ${ago(b.presence_age_min)}`,
            T('Le bot enregistre qui est en ligne toutes les 15 minutes. Sans relevé depuis plus de 30 minutes, il est sans doute arrêté ou déconnecté.',
              'The bot records who is online every 15 minutes. With no snapshot for over 30 minutes, it is probably stopped or disconnected.')],
        ['tab-security', alerts > 50 ? 'ko' : alerts ? 'warn' : 'ok', T('{n} alerte(s) de sécurité', '{n} security alert(s)', { n: HG.fmt(alerts) }), T('dernières 24 h', 'last 24 h'),
            T('Événements suspects des dernières 24 h : connexions échouées, scans de robots, limites de requêtes, accès admin refusés… Les connexions réussies ne comptent pas.',
              'Suspicious events of the last 24 h: failed logins, bot scans, rate limits, refused admin access… Successful logins are left out.')],
        ['tab-tech', errors500 ? 'ko' : 'ok', T('{n} erreur(s) serveur', '{n} server error(s)', { n: HG.fmt(errors500) }), periodLabel(),
            T('Pages du site qui ont planté (erreur 500) sur la période : un bug à corriger, le détail est dans les logs du site.',
              'Site pages that crashed (error 500) over the period: a bug to fix, the details are in the site logs.')],
        ['tab-security', failing ? 'warn' : 'ok', failing ? T('{n} réglage(s) à revoir', '{n} setting(s) to check', { n: failing }) : T('Configuration saine', 'Healthy configuration'),
            T('check-up de sécurité', 'security check-up'),
            T('Réglages du site vérifiés à chaque ouverture (clé de session, HTTPS, connexion Discord…). Le détail est dans l’onglet Sécurité.',
              'Site settings checked each time the page opens (session key, HTTPS, Discord login…). Details are in the Security tab.')],
        ['tab-bot', b.orphans ? 'warn' : 'ok', T('{n} session(s) orpheline(s)', '{n} orphan session(s)', { n: HG.fmt(b.orphans) }), T('vocal ouvert depuis plus de 24 h', 'voice open for over 24 h'),
            T('Sessions vocales jamais refermées depuis plus de 24 h : le bot a sans doute manqué un départ (redémarrage, coupure). Elles gonflent le temps en vocal.',
              'Voice sessions still open after more than 24 h: the bot probably missed someone leaving (restart, outage). They inflate voice time.')],
    ];
    const strip = document.getElementById('overviewHealth');
    strip.innerHTML = health.map(([tab, tone, title, sub, tip]) => `
        <button type="button" class="adm-health-item is-${tone}" data-goto="${tab}"${tipAttr(tip)}><span class="adm-health-dot"></span>
            <span class="adm-health-text"><strong>${HG.esc(title)}</strong><span>${HG.esc(sub)}</span></span></button>`).join('');
    const tiles = [
        ['tab-traffic', T('Pages vues', 'Page views'), HG.fmt(o.views), deltaText(o.delta, T('vs période précédente', 'vs previous period')), '', TIP_VIEWS],
        ['tab-traffic', T('Visiteurs uniques par jour', 'Unique visitors per day'), HG.fmt(o.uniques_avg, 1), deltaText(o.uniques_delta, T('vs période précédente', 'vs previous period')), '', TIP_UNIQUES],
        ['tab-accounts', T('Comptes Discord liés', 'Linked Discord accounts'), HG.fmt(o.accounts), `+${HG.fmt(o.accounts_new_week)} ${T('cette semaine', 'this week')}`, '', TIP_ACCOUNTS],
        ['tab-profiles', T('Profils personnalisés', 'Customized profiles'), HG.fmt(o.customized), `${HG.fmt(o.customized_percent, 1)} % ${T('des comptes liés', 'of linked accounts')}`, '', TIP_CUSTOMIZED],
        ['tab-community', T('Membres présents', 'Members present'), a ? HG.fmt(a.unique) : '—',
            a ? `${HG.fmt(a.silent_percent, 1)} % ${T('jamais actifs', 'never active')}` : T('en attente du bot v3.3.0', 'waiting for bot v3.3.0'), '', TIP_UNIQUE_MEMBERS],
        ['tab-community', T('Serveurs du bot', 'Bot servers'), HG.fmt(b.servers_present), `${HG.fmt(b.servers_active30)} ${T('actifs sur 30 j', 'active in 30 d')}`, '', TIP_SERVERS],
        ['tab-bot', T('Commandes', 'Commands'), HG.fmt(c.total), `${HG.fmt(c.failed_percent, 1)} % ${T('d’erreurs', 'errors')} · ${periodLabel()}`, c.failed ? 'warn' : '', TIP_COMMANDS],
        ['tab-accounts', T('Comptes actifs · 7 j', 'Active accounts · 7 d'), HG.fmt(data.accounts.active7), `${HG.fmt(data.accounts.active30)} ${T('sur 30 j', 'in 30 d')}`, '', TIP_ACTIVE7],
    ];
    const box = document.getElementById('overviewTiles');
    box.innerHTML = tiles.map(([tab, label, value, sub, tone, tip]) => `
        <button type="button" class="adm-tile ${tone ? 'is-' + tone : ''}" data-goto="${tab}"${tipAttr(tip)}>
            <span class="adm-stat-label">${HG.esc(label)}</span>
            <span class="adm-tile-value">${value}</span>
            <span class="adm-stat-sub">${sub}</span>
            <span class="adm-tile-go">${HG.esc(TAB_LABELS[tab])}</span>
        </button>`).join('');
    document.querySelectorAll('#tab-overview [data-goto]').forEach(btn => btn.addEventListener('click', () => switchGraphTab(btn.dataset.goto)));
    const t = data.traffic;
    lineChart('overviewChart', t.labels, [
        area(T('Pages vues', 'Page views'), t.views, '#717cf8'),
        area(T('Visiteurs uniques', 'Unique visitors'), t.uniques, '#3fd1a0'),
    ]);
    document.getElementById('overviewSummary').textContent =
        `${HG.fmt(sum(t.views))} ${T('pages vues', 'page views')} · ${HG.fmt(sum(t.uniques))} ${T('visiteurs-jour', 'visitor-days')}`;
    const events = (data.security.recent || []).filter(e => !QUIET_KINDS.includes(e.kind)).slice(0, 8);
    document.querySelector('#overviewEvents tbody').innerHTML = events.map(e => securityRow(e)).join('')
        || `<tr><td class="adm-muted">${T('Rien à signaler', 'Nothing to report')}</td></tr>`;
}

function sectionTraffic() {

        renderTraffic();
        const t = data.traffic, o = data.overview;
        const dev0 = t.devices, devTotal = Math.max(1, dev0.mobile + dev0.desktop);
        const vsPrev = T('vs période précédente', 'vs previous period');
        const stat = (label, value, subHtml, tip) => `<div class="adm-stat"${tipAttr(tip)}><span class="adm-stat-label">${HG.esc(label)}</span>
            <span class="adm-stat-value">${value}</span><span class="adm-stat-sub">${subHtml}</span></div>`;
        document.getElementById('trafficStats').innerHTML = [
            stat(T('Pages vues', 'Page views'), HG.fmt(o.views), deltaText(o.delta, vsPrev), TIP_VIEWS),
            stat(T('Visiteurs uniques par jour', 'Unique visitors per day'), HG.fmt(o.uniques_avg, 1), deltaText(o.uniques_delta, vsPrev), TIP_UNIQUES),
            stat(T('Aujourd’hui', 'Today'), HG.fmt(o.views_today), `${HG.fmt(o.uniques_today)} ${HG.esc(T('visiteurs', 'visitors'))}`,
                T('Pages vues et visiteurs différents depuis minuit (heure UTC, soit 1 h ou 2 h du matin en France).',
                  'Page views and different visitors since midnight (UTC time).')),
            stat(T('Sur téléphone', 'On phones'), `${HG.fmt(dev0.mobile / devTotal * 100)} %`,
                `${HG.fmt(dev0.desktop / devTotal * 100)} % ${HG.esc(T('sur ordinateur', 'on desktop'))}`,
                T('Part des visiteurs de la période venus d’un téléphone ou d’une tablette, d’après leur navigateur.',
                  'Share of the period’s visitors on a phone or tablet, from their browser.')),
        ].join('');
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
            [T('Comptes liés au moins une fois', 'Accounts linked at least once'), HG.fmt(a.total), `${HG.fmt(a.linked_percent, 1)} % ${T('des', 'of the')} ${HG.fmt(a.members_total)} ${T('membres suivis', 'tracked members')}`, '',
                T('Membres qui se sont connectés au moins une fois au site avec Discord. Le pourcentage les compare aux membres que le bot a déjà vus actifs (vocal ou messages).',
                  'Members who logged in to the site with Discord at least once. The percentage compares them with the members the bot has seen active (voice or messages).')],
            [T('Nouveaux cette semaine', 'New this week'), HG.fmt(a.new_week), '', '',
                T('Comptes connectés au site pour la toute première fois ces 7 derniers jours.', 'Accounts that logged in to the site for the very first time in the last 7 days.')],
            [T('Actifs · 7 jours', 'Active · 7 days'), HG.fmt(a.active7), '', '',
                T('Comptes liés qui ont utilisé le site en étant connectés au moins un jour sur les 7 derniers.', 'Linked accounts that used the site while logged in on at least one of the last 7 days.')],
            [T('Actifs · 30 jours', 'Active · 30 days'), HG.fmt(a.active30), '', '',
                T('Comptes liés qui ont utilisé le site en étant connectés au moins un jour sur les 30 derniers.', 'Linked accounts that used the site while logged in on at least one of the last 30 days.')],
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
            [T('Profils personnalisés', 'Customized profiles'), HG.fmt(c.customized), `${HG.fmt(c.customized_percent, 1)} % ${T('des comptes liés', 'of linked accounts')}`, '', TIP_CUSTOMIZED],
            [T('Profils privés', 'Private profiles'), HG.fmt(c.private), '', '',
                T('Membres qui ont mis leur profil en privé : les visiteurs ne voient que l’en-tête, le niveau et les totaux.',
                  'Members who made their profile private: visitors only see the header, level and totals.')],
            [T('Serveur favori choisi', 'Favorite server set'), HG.fmt(c.favorite), '', '',
                T('Membres qui ont choisi un serveur favori, mis en avant sur leur profil.', 'Members who picked a favorite server, shown on their profile.')],
        ]);
}

function sectionCommands() {

        const c = data.commands;
        document.getElementById('commandsNotice').hidden = c.total > 0;
        renderStats(document.getElementById('commandStats'), [
            [`${T('Commandes', 'Commands')} · ${periodLabel()}`, HG.fmt(c.total), `${HG.fmt(c.today)} ${T("aujourd'hui", 'today')}`, '',
                T('Commandes slash du bot utilisées sur la période, tous serveurs confondus (et celles d’aujourd’hui en dessous).',
                  'Bot slash commands used over the period, all servers together (and today’s below).')],
            [T('En messages privés', 'In direct messages'), HG.fmt(c.dm), '', '',
                T('Commandes utilisées en message privé avec le bot, hors de tout serveur.', 'Commands used in a direct message with the bot, outside any server.')],
            [T('Erreurs', 'Errors'), HG.fmt(c.failed), `${HG.fmt(c.failed_percent, 1)} %`, c.failed ? 'warn' : 'ok',
                T('Commandes qui ont échoué (erreur ou délai dépassé) : le membre a vu un message d’erreur. Le détail est dans les logs du bot.',
                  'Commands that failed (error or timeout): the member saw an error message. Details are in the bot logs.')],
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
            [T('Serveurs où le bot est présent', 'Servers with the bot'), HG.fmt(b.servers_present), `${HG.fmt(b.servers_left)} ${T('quittés', 'left')} · ${HG.fmt(b.servers_active30)} ${T('actifs sur 30 j', 'active in 30 d')}`, '',
                T('Serveurs où le bot est actuellement, ceux qu’il a quittés, et ceux avec au moins un message ou une session vocale sur 30 jours.',
                  'Servers the bot is in right now, those it left, and those with at least one message or voice session over 30 days.')],
            [T('Membres suivis', 'Tracked members'), HG.fmt(b.members_total), '', '',
                T('Membres que le bot a vus actifs au moins une fois (vocal ou messages) : ceux qui ont un profil Hourglass.',
                  'Members the bot has seen active at least once (voice or messages): those with a Hourglass profile.')],
            [T('En vocal maintenant', 'In voice now'), HG.fmt(b.voice_now), `${HG.fmt(b.messages_24h)} ${T('messages sur 24 h', 'messages in 24 h')}`, '',
                T('Sessions vocales en cours sur tous les serveurs, et messages comptés ces 24 dernières heures.',
                  'Voice sessions in progress on every server, and messages counted over the last 24 hours.')],
            [T('Dernier relevé du bot', 'Last bot snapshot'), dateText(b.last_presence),
                b.presence_age_min === null ? '' : ago(b.presence_age_min), b.bot_online ? 'ok' : 'ko',
                T('Le bot enregistre qui est en ligne toutes les 15 minutes. Sans relevé depuis plus de 30 minutes, il est sans doute arrêté ou déconnecté.',
                  'The bot records who is online every 15 minutes. With no snapshot for over 30 minutes, it is probably stopped or disconnected.')],
            [T('Sessions vocales orphelines', 'Orphan voice sessions'), HG.fmt(b.orphans), T('ouvertes depuis plus de 24 h', 'open for more than 24 h'), b.orphans ? 'warn' : 'ok',
                T('Sessions vocales jamais refermées depuis plus de 24 h : le bot a sans doute manqué un départ (redémarrage, coupure). Elles gonflent le temps en vocal.',
                  'Voice sessions still open after more than 24 h: the bot probably missed someone leaving (restart, outage). They inflate voice time.')],
        ]);
}

function sectionVotes() {
    const v = data.votes;
    const notice = document.getElementById('votesNotice');
    const missing = [!v.webhook_ready && 'TOPGG_WEBHOOK_SECRET', !v.api_ready && 'TOPGG_TOKEN'].filter(Boolean);
    notice.hidden = !missing.length;
    notice.textContent = missing.length
        ? T('À définir dans le .env du site : {v} (webhook en temps réel et historique des votes).', 'To set in the site .env: {v} (real-time webhook and vote history).', { v: missing.join(', ') })
        : '';
    renderStats(document.getElementById('voteStats'), [
        [`${T('Votes', 'Votes')} · ${periodLabel()}`, HG.fmt(v.period), `${HG.fmt(v.voters)} ${T('votant(s)', 'voter(s)')}`, '',
            T('Votes pour Hourglass sur top.gg pendant la période, et le nombre de membres différents qui ont voté.',
              'Votes for Hourglass on top.gg over the period, and how many different members voted.')],
        [T('Ce mois-ci', 'This month'), HG.fmt(v.month), '', '',
            T('Votes depuis le 1er du mois : top.gg classe les bots sur les votes du mois en cours.', 'Votes since the 1st of the month: top.gg ranks bots on the current month’s votes.')],
        [T('Votes en cours', 'Active votes'), HG.fmt(v.active), T('membres qui ont voté depuis moins de 12 h', 'members who voted less than 12 h ago'), '',
            T('Membres dont le vote compte encore : un vote dure 12 heures, ensuite ils peuvent revoter.', 'Members whose vote still counts: a vote lasts 12 hours, then they can vote again.')],
        [T('Total enregistré', 'Total recorded'), HG.fmt(v.total), '', '',
            T('Tous les votes enregistrés depuis le début : chacun rapporte 100 XP et compte pour le badge Soutien.', 'Every vote recorded since the start: each one gives 100 XP and counts for the Supporter badge.')],
    ]);
    lineChart('votesChart', v.labels, [bars(T('Votes', 'Votes'), v.daily, '#ff6b8a')], { type: 'bar' });
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
                [T('Membres uniques', 'Unique members'), HG.fmt(a.unique), `${T('relevé', 'snapshot')} ${dateText(a.at)}`, '', TIP_UNIQUE_MEMBERS],
                [T('En ligne', 'Online'), HG.fmt(a.online), `${HG.fmt(a.unique ? a.online / a.unique * 100 : 0, 1)} %`, '',
                    T('Parmi eux, ceux qui étaient en ligne, absents ou occupés sur Discord au moment du relevé (pas forcément sur le serveur).',
                      'Among them, those online, idle or busy on Discord at the time of the snapshot (not necessarily on the server).')],
                [T('Jamais actifs', 'Never active'), HG.fmt(a.silent), `${HG.fmt(a.silent_percent, 1)} % ${T('n’ont jamais parlé ni rejoint un vocal', 'never talked nor joined voice')}`, a.silent_percent > 50 ? 'warn' : '',
                    T('Membres présents sur les serveurs que le bot n’a jamais vus écrire ni rejoindre un vocal : ils n’ont pas de profil Hourglass.',
                      'Members on the servers the bot never saw write or join voice: they have no Hourglass profile.')],
                [T('Déjà actifs', 'Already active'), HG.fmt(a.known), T('ont un profil Hourglass', 'have a Hourglass profile'), '',
                    T('Membres présents qui ont déjà écrit ou été en vocal au moins une fois : ils ont un profil sur le site.',
                      'Members on the servers who already wrote or joined voice at least once: they have a profile on the site.')],
                [T('Serveurs par membre', 'Servers per member'), HG.fmt(a.per_member, 2), `${HG.fmt(a.memberships)} ${T('appartenances sur', 'memberships on')} ${HG.fmt(a.servers)} ${T('serveurs', 'servers')}`, '',
                    T('Nombre moyen de serveurs du bot dont chaque personne fait partie. Au-dessus de 1, beaucoup de membres sont sur plusieurs serveurs à la fois.',
                      'Average number of the bot’s servers each person is in. Above 1, many members are on several servers at once.')],
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
        // Reclaimable: space left by deleted rows, kept by the table until a VACUUM FULL
        const reclaim = b.tables.reduce((a, r) => a + (r.reclaim_mb || 0), 0);
        document.getElementById('dbSize').textContent = `${T('Taille totale', 'Total size')} : ${HG.fmt(b.db_mb, 1)} Mo`
            + (reclaim ? ` · ${T('environ {n} Mo récupérables avec VACUUM FULL', 'about {n} MB reclaimable with VACUUM FULL', { n: HG.fmt(reclaim, 1) })}` : '');
        document.querySelector('#dbTables tbody').innerHTML = b.tables.map(r => `<tr><td><code>${HG.esc(r.name)}</code></td>
            <td>${HG.fmt(r.rows)} ${T('lignes', 'rows')}</td><td>${HG.fmt(r.mb, 1)} Mo</td>
            ${r.reclaim_mb ? `<td class="adm-warn-text" title="${HG.esc(`VACUUM FULL ANALYZE ${r.name};`)}">≈ ${HG.fmt(r.reclaim_mb, 1)} Mo ${T('récupérables', 'reclaimable')}</td>` : ''}</tr>`).join('');
}

function sectionHealth() {

        const h = data.health;
        const r = h.analytics_refresh || {};
        renderStats(document.getElementById('healthStats'), [
            [`404 · ${periodLabel()}`, HG.fmt(h.s404.reduce((a, b) => a + b, 0)), T('pages introuvables', 'pages not found'), '',
                T('Adresses demandées qui n’existent pas : liens cassés, profils supprimés, ou robots qui testent des pages au hasard. La liste est dessous.',
                  'Requested addresses that do not exist: broken links, removed profiles, or bots probing random pages. The list is below.')],
            [`429 · ${periodLabel()}`, HG.fmt(h.s429.reduce((a, b) => a + b, 0)), T('limite de requêtes atteinte', 'rate limit reached'), '',
                T('Requêtes refusées parce qu’une même adresse IP en envoyait trop en une minute (protection contre les abus).',
                  'Requests refused because one IP address sent too many in a minute (abuse protection).')],
            [`500 · ${periodLabel()}`, HG.fmt(h.s500.reduce((a, b) => a + b, 0)), T('erreurs serveur', 'server errors'), h.s500.some(v => v) ? 'ko' : 'ok',
                T('Pages du site qui ont planté : un bug à corriger, le détail est dans les logs du site.', 'Site pages that crashed: a bug to fix, the details are in the site logs.')],
            [T('Calcul de la page Analyses', 'Analytics page computation'), r.ms !== undefined ? `${HG.fmt(r.ms)} ms` : '—',
                r.at ? `${T('dernier rafraîchissement', 'last refresh')} ${dateText(r.at)} (${T('ce worker', 'this worker')})` : T('pas encore rafraîchi sur ce worker', 'not refreshed on this worker yet'),
                r.ms > 2000 ? 'warn' : '',
                T('Temps pour recalculer toutes les données de la page Analyses, fait en arrière-plan par chacun des 4 workers. Au-delà de 2 s, la base commence à peiner.',
                  'Time to recompute all the Analytics page data, done in the background by each of the 4 workers. Over 2 s, the database starts to struggle.')],
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
        const keyTip = T('Clé qui signe les cookies de connexion. Si elle change (mise à jour du conteneur, redémarrage), tous les membres sont déconnectés.',
            'Key that signs the login cookies. If it changes (container update, restart), every member is logged out.');
        tiles.insertAdjacentHTML('beforeend', `<div class="adm-stat is-${ks[2]}"${tipAttr(keyTip)}><span class="adm-stat-label">${T('Clé de session', 'Session key')}</span>
            <span class="adm-stat-value" style="font-size:16px">${HG.esc(ks[0])}</span><span class="adm-stat-sub">${HG.esc(ks[1])}</span></div>`);
        lineChart('statusChart', h.labels, [bars('404', h.s404, '#5b5f6c'), bars('429', h.s429, '#f5b03b'), bars('500', h.s500, '#f87171')], { type: 'bar', stacked: true });
}

// ---------------------------------------------------------------------------
// Security journal
// ---------------------------------------------------------------------------
const SECURITY_COLORS = {
    login_fail: '#f87171', admin_denied: '#fb923c', csrf_fail: '#facc15', rate_limited: '#a3a6b0', scan: '#b07cff',
    card_token_fail: '#ef4444', webhook_fail: '#ff6b5e', csp_violation: '#38bdf8', server_error: '#ff6b5e', too_large: '#4f9dff',
};
const QUIET_KINDS = ['login_ok', 'admin_access'];

// Suspicious events (everything but successful logins and admin access) over the last 24 h or 7 days
function securityAlerts(hoursOrDays) {
    const s = data.security || {};
    const totals = (hoursOrDays === 24 ? s.totals_24h : s.totals_7d) || {};
    return Object.entries(totals).filter(([k]) => !QUIET_KINDS.includes(k)).reduce((a, [, n]) => a + n, 0);
}

// One journal line in fixed columns (type, time, who, page), the detail under it in full
function securityRow(e) {
    const who = e.user
        ? (e.user_url ? `<a href="${HG.esc(e.user_url)}" class="adm-link">${HG.esc(e.user)}</a>` : HG.esc(e.user))
        : '';
    const page = (e.path || '').replace(/^https?:\/\/[^/]+/, '');
    return `<tr data-kind="${HG.esc(e.kind)}">
        <td><span class="adm-sev is-${HG.esc(e.severity)}">${HG.esc(e.label)}</span>${e.hits > 1 ? ` <span class="adm-hits">×${HG.fmt(e.hits)}</span>` : ''}</td>
        <td class="adm-muted">${dateText(e.at)}</td>
        <td>${who}${who && e.ip ? ' ' : ''}${e.ip ? `<code class="adm-muted">${HG.esc(e.ip)}</code>` : ''}</td>
        <td>${page ? `<code>${HG.esc(page)}</code>` : ''}</td>
        <td class="adm-log-detail">${HG.esc(e.detail || '')}</td></tr>`;
}

function sectionSecurity() {
    const s = data.security;
    document.getElementById('securityNotice').hidden = s.enabled;
    const t24 = s.totals_24h, t7 = s.totals_7d;
    const n = (k, src = t24) => src[k] || 0;
    const tile = (kind, label, warnAt = 1, koAt = Infinity, tip = '') =>
        [label, HG.fmt(n(kind)), `${HG.fmt(n(kind, t7))} ${T('sur 7 j', 'in 7 d')}`, n(kind) >= koAt ? 'ko' : n(kind) >= warnAt ? 'warn' : 'ok', tip];
    // Figures of the last 24 h, the 7 days under them
    renderStats(document.getElementById('securityStats'), [
        tile('login_fail', T('Connexions échouées', 'Failed logins'), 5, 30,
            T('Connexions Discord qui n’ont pas abouti (24 h) : autorisation refusée, code expiré, Discord indisponible… La raison est dans le journal.',
              'Discord logins that did not go through (24 h): authorization declined, expired code, Discord unavailable… The reason is in the journal.')),
        [T('Connexions réussies', 'Successful logins'), HG.fmt(n('login_ok')), `${HG.fmt(n('login_ok', t7))} ${T('sur 7 j', 'in 7 d')}`, '',
            T('Connexions Discord au site réussies ces 24 dernières heures.', 'Successful Discord logins to the site over the last 24 hours.')],
        tile('scan', T('Scans de robots', 'Bot scans'), 20, 500,
            T('Robots qui testent des adresses connues de failles (/wp-admin, /.env…). Normal sur Internet : ces pages n’existent pas ici.',
              'Bots probing addresses of known flaws (/wp-admin, /.env…). Normal on the Internet: these pages do not exist here.')),
        tile('rate_limited', T('Limites de requêtes (429)', 'Rate limits (429)'), 10, 200,
            T('Requêtes refusées parce qu’une même adresse IP en envoyait trop en une minute.', 'Requests refused because one IP address sent too many in a minute.')),
        tile('admin_denied', T('Accès admin refusés', 'Admin access denied'), 1, 20,
            T('Quelqu’un qui n’est pas admin a essayé d’ouvrir une page de l’admin (il a vu une page introuvable).',
              'Someone who is not an admin tried to open an admin page (they saw a not found page).')),
        tile('csrf_fail', T('Formulaires refusés (CSRF)', 'Forms refused (CSRF)'), 1, 10,
            T('Formulaire envoyé sans le jeton de sécurité de la page : souvent une page restée ouverte longtemps, parfois une tentative depuis un autre site.',
              'Form sent without the page’s security token: often a page left open for a long time, sometimes an attempt from another site.')),
        tile('card_token_fail', T('Jetons de carte invalides', 'Invalid card tokens'), 1, 1,
            T('Demandes de cartes PNG réservées au bot avec un jeton faux ou absent : quelqu’un se fait passer pour le bot.',
              'Requests for the bot-only PNG cards with a wrong or missing token: someone posing as the bot.')),
        tile('webhook_fail', T('Webhooks top.gg refusés', 'top.gg webhooks refused'), 1, 5,
            T('Votes reçus sans la bonne signature top.gg (faux vote ou secret mal réglé) : ils ne sont pas comptés.',
              'Votes received without the right top.gg signature (fake vote or wrong secret): they are not counted.')),
        tile('csp_violation', T('Violations CSP', 'CSP violations'), 1, 50,
            T('Scripts ou images bloqués par la politique de sécurité du navigateur : souvent une extension, parfois une ressource oubliée dans la liste autorisée.',
              'Scripts or images blocked by the browser security policy: often an extension, sometimes a resource missing from the allowed list.')),
        tile('server_error', T('Erreurs serveur (500)', 'Server errors (500)'), 1, 10,
            T('Pages du site qui ont planté : un bug à corriger, le détail est dans les logs du site.', 'Site pages that crashed: a bug to fix, the details are in the site logs.')),
        tile('too_large', T('Requêtes trop grosses', 'Requests too large'), 1, 20,
            T('Envois refusés car trop lourds (au-delà de la taille permise) : souvent un robot ou une tentative d’abus.',
              'Uploads refused for being too large (over the allowed size): often a bot or an abuse attempt.')),
    ]);
    const kinds = s.kinds.filter(k => !QUIET_KINDS.includes(k.key) && (s.daily[k.key] || []).some(v => v));
    lineChart('securityChart', s.labels,
        kinds.map(k => bars(k.label, s.daily[k.key], SECURITY_COLORS[k.key] || '#a3a6b0')), { type: 'bar', stacked: true });
    document.getElementById('securityRetention').textContent =
        T('300 derniers événements · conservés {n} jours · IP abrégée', 'Last 300 events · kept {n} days · shortened IP', { n: s.retention_days });

    const log = document.querySelector('#securityLog tbody');
    log.innerHTML = s.recent.map(e => securityRow(e)).join('') || `<tr><td>${T('Aucun événement enregistré', 'No event recorded')}</td></tr>`;
    const select = document.getElementById('securityKind');
    const chosen = select.value;
    select.querySelectorAll('option[value]:not([value=""])').forEach(o => o.remove());
    s.kinds.forEach(k => select.insertAdjacentHTML('beforeend', `<option value="${HG.esc(k.key)}">${HG.esc(k.label)}</option>`));
    select.value = s.kinds.some(k => k.key === chosen) ? chosen : '';
    const filter = () => log.querySelectorAll('tr[data-kind]').forEach(tr => {
        tr.classList.toggle('is-filtered', !!select.value && tr.dataset.kind !== select.value);
    });
    if (!select.dataset.bound) {
        select.dataset.bound = '1';
        select.addEventListener('change', () => filter());
    }
    filter();

    document.querySelector('#adminLog tbody').innerHTML = s.admin_log.map(e => securityRow(e)).join('')
        || `<tr><td>${T('Aucun accès enregistré', 'No access recorded')}</td></tr>`;
    document.getElementById('securityCheckup').innerHTML = s.checkup.map(c => `
        <li class="${c.ok ? 'is-ok' : 'is-ko'}"><span class="adm-check">${c.ok ? '✓' : '✕'}</span>
            <span class="adm-check-text"><strong>${HG.esc(c.label)}</strong><span class="adm-muted">${HG.esc(c.detail || '')}</span></span></li>`).join('');
}

// ---------------- Bot logs: last 200 lines of bot_logs, refreshed every 10 s while the section is open ----------------
const LOG_MAX = 200;
const LOG_EVERY_MS = 10000;
let logLines = [];
let logTimer = null;
let logBusy = false;

// Level from the bot's own emoji and words (its log lines have no level field)
function logLevel(line) {
    if (/❌|🚨|panic|erreur|error|failed|échec|impossible/i.test(line)) return 'error';
    if (/⚠️|warn|attention|retry|timeout/i.test(line)) return 'warn';
    return '';
}

function logTime(iso) {
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString(HG.locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function renderLogs() {
    const box = document.getElementById('logsBox');
    const level = document.querySelector('#logsLevel button.active').dataset.level;
    const needle = fold(document.getElementById('logsSearch').value.trim());
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    const shown = logLines.filter(l => (!level || l.level === level || (level === 'warn' && l.level === 'error'))
        && (!needle || fold(l.line).includes(needle)));
    box.innerHTML = shown.map(l => `<div class="adm-log-line${l.level ? ' is-' + l.level : ''}"><time>${logTime(l.at)}</time><span>${HG.esc(l.line)}</span></div>`).join('')
        || `<p class="adm-muted adm-logs-empty">${logLines.length ? T('Aucune ligne ne correspond', 'No matching line') : T('Aucune ligne', 'No line')}</p>`;
    // Follows the newest line like Portainer, unless the reader scrolled up
    if (atBottom || !box.dataset.scrolled) { box.scrollTop = box.scrollHeight; box.dataset.scrolled = '1'; }
    const last = logLines[logLines.length - 1];
    document.getElementById('logsMeta').textContent = T('{n} dernières lignes · dernière le {d}', 'Last {n} lines · latest on {d}',
        { n: HG.fmt(logLines.length), d: last ? logTime(last.at) : '—' });
}

function fetchLogs() {
    if (logBusy) return Promise.resolve();
    logBusy = true;
    const after = logLines.length ? logLines[logLines.length - 1].id : 0;
    return fetch(`/admin/logs?after=${after}`, { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(json => {
            document.getElementById('logsNotice').hidden = json.available && (json.lines.length + logLines.length) > 0;
            if (!json.lines.length && logsDrawn()) return;
            logLines = logLines.concat(json.lines.map(l => ({ ...l, level: logLevel(l.line) }))).slice(-LOG_MAX);
            renderLogs();
        })
        .catch(err => console.error('Bot logs failed:', err))
        .finally(() => { logBusy = false; });
}

// The list was drawn once already (nothing new to add)
const logsDrawn = () => !!document.getElementById('logsBox').dataset.scrolled;

function startLogs() {
    fetchLogs();
    clearInterval(logTimer);
    logTimer = document.getElementById('logsLive').checked ? setInterval(() => { if (!document.hidden) fetchLogs(); }, LOG_EVERY_MS) : null;
}

function stopLogs() {
    clearInterval(logTimer);
    logTimer = null;
}

function bindLogs() {
    document.querySelectorAll('#logsLevel button').forEach(btn => btn.addEventListener('click', () => {
        document.querySelectorAll('#logsLevel button').forEach(b => b.classList.toggle('active', b === btn));
        renderLogs();
    }));
    document.getElementById('logsSearch').addEventListener('input', () => renderLogs());
    document.getElementById('logsLive').addEventListener('change', () => { if (currentTab === 'tab-logs') startLogs(); });
}

const TAB_SECTIONS = {
    'tab-overview': [sectionOverview],
    'tab-traffic': [sectionTraffic],
    'tab-accounts': [sectionAccounts],
    'tab-profiles': [sectionCustomization],
    'tab-community': [sectionVotes, sectionCommunity],
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
function load(newDays, opts = {}) {
    days = PERIODS.includes(newDays) ? newDays : 30;
    try { localStorage.setItem('hgAdminDays', String(days)); } catch (e) {}
    const refresh = document.getElementById('admRefresh');
    refresh.classList.add('is-spinning');
    return fetch(`/admin/data?days=${days}`, { credentials: 'same-origin' })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(json => {
            data = json;
            initializedTabs.clear();
            renderKpis();
            initTab(currentTab);
            document.querySelectorAll('.chart-loading-overlay').forEach(el => el.classList.add('loaded'));
            if (window.history && window.history.replaceState) window.history.replaceState(null, '', `?days=${days}#${currentTab}`);
        })
        .catch(err => {
            console.error('Admin data failed:', err);
            document.querySelectorAll('.chart-spinner-text').forEach(el => { el.textContent = T('Erreur de chargement', 'Loading error'); el.style.color = '#f87171'; });
            if (opts.quiet !== true) document.getElementById('admMeta').textContent = T('Erreur de chargement', 'Loading error');
        })
        .finally(() => refresh.classList.remove('is-spinning'));
}

document.addEventListener('DOMContentLoaded', () => {
    Chart.defaults.color = '#868a96';
    Chart.defaults.font.family = '"IBM Plex Sans", "Segoe UI", system-ui, sans-serif';
    Chart.defaults.font.size = 12;
    document.querySelectorAll('.adm-nav-item[data-tab]').forEach(btn => btn.addEventListener('click', () => switchGraphTab(btn.dataset.tab)));
    document.querySelectorAll('#admPeriod [data-days]').forEach(btn => btn.addEventListener('click', () => {
        if (+btn.dataset.days !== days) load(+btn.dataset.days);
    }));
    document.getElementById('admRefresh').addEventListener('click', () => { load(days); if (currentTab === 'tab-logs') fetchLogs(); });
    bindLogs();
    document.getElementById('admMenu').addEventListener('click', () => setDrawer(!document.getElementById('admApp').classList.contains('side-open')));
    document.getElementById('admScrim').addEventListener('click', () => setDrawer(false));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') setDrawer(false); });

    const fromUrl = parseInt(new URLSearchParams(window.location.search).get('days'), 10);
    let saved = NaN;
    try { saved = parseInt(localStorage.getItem('hgAdminDays'), 10); } catch (e) {}
    days = PERIODS.includes(fromUrl) ? fromUrl : PERIODS.includes(saved) ? saved : 30;
    document.querySelectorAll('#admPeriod [data-days]').forEach(btn => btn.classList.toggle('active', +btn.dataset.days === days));
    currentTab = window.location.hash.replace('#', '') || 'tab-overview';
    switchGraphTab(currentTab);
    load(days);
});
