/* Analytics page: three tabs (Évolution, Horaires, Communauté) fed by /api/graphs/data (cached 5 min server side). */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const T = (fr, en, vars) => HG.tr(fr, en, vars);

const charts = {};
const initializedTabs = new Set();
let apiData = null;
let currentTab = 'tab-trends';

function switchGraphTab(tabId) {
    if (!document.getElementById(tabId)) tabId = 'tab-trends';
    currentTab = tabId;
    document.querySelectorAll('.graphs-tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tabId));
    document.querySelectorAll('.graphs-tab-pane').forEach(pane => pane.classList.toggle('active', pane.id === tabId));
    initTab(tabId);
    requestAnimationFrame(() => Object.values(charts).forEach(c => { try { c.resize(); } catch (e) {} }));
    if (window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + tabId);
}

const TOOLTIP = {
    backgroundColor: 'rgba(24, 25, 29, 0.95)',
    titleColor: '#ffffff',
    bodyColor: '#e3e5e8',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    borderWidth: 1,
    padding: 12,
    boxPadding: 6,
};
const GRID = { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false };
const COLORS = { hours: '#717cf8', messages: '#3fd1a0' };

function unit(metric) {
    return metric === 'hours' ? 'h' : HG.tr('msgs', 'msgs');
}

function fmtValue(metric, v) {
    return metric === 'hours' ? `${HG.fmt(v, 1)} h` : `${HG.fmt(v)} ${T('messages', 'messages')}`;
}

// ---------------------------------------------------------------------------
// Summary cards (last 30 days vs the 30 days before)
// ---------------------------------------------------------------------------
function renderKpis(summary) {
    const cur = summary.current, prev = summary.previous;
    const values = {
        hours: `${HG.fmt(cur.hours, 1)} h`,
        messages: HG.fmt(cur.messages),
        members: HG.fmt(cur.members),
        servers: HG.fmt(cur.servers),
    };
    Object.entries(values).forEach(([key, text]) => {
        document.getElementById('kpi-' + key).textContent = text;
        const delta = document.getElementById('delta-' + key);
        const before = prev[key] || 0;
        if (!before) {
            delta.textContent = T('Pas de comparaison', 'No comparison');
            delta.className = 'an-delta';
            return;
        }
        const pct = ((cur[key] - before) / before) * 100;
        const sign = pct > 0 ? '+' : '';
        delta.textContent = `${sign}${HG.fmt(pct, Math.abs(pct) < 10 ? 1 : 0)} % ${T('vs 30 j précédents', 'vs previous 30 d')}`;
        delta.className = 'an-delta ' + (pct >= 0 ? 'up' : 'down');
    });
}

// ---------------------------------------------------------------------------
// Tendances: a single chart, voice or messages, monthly or 30 days, per period or cumulative
// ---------------------------------------------------------------------------
const trendState = { metric: 'hours', period: 'month', mode: 'period' };

function renderTrends() {
    const key = trendState.period + (trendState.mode === 'cumul' ? '_cumul' : '');
    const series = apiData.trends[key];
    const metric = trendState.metric;
    const values = series[metric];
    const color = COLORS[metric];
    const canvas = document.getElementById('trendsChart');
    if (charts.trends) charts.trends.destroy();

    const summary = document.getElementById('trendsSummary');
    let datasets;
    if (trendState.mode === 'cumul') {
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color + '59');
        gradient.addColorStop(1, color + '00');
        datasets = [{
            label: T('Total cumulé', 'Running total'),
            data: values,
            borderColor: color,
            backgroundColor: gradient,
            fill: true,
            tension: 0.3,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
        }];
        summary.textContent = `${T('Total', 'Total')} : ${fmtValue(metric, values[values.length - 1] || 0)}`;
    } else {
        const complete = series.partial && values.length > 1 ? values.slice(0, -1) : values;
        const avg = complete.reduce((a, b) => a + b, 0) / Math.max(1, complete.length);
        const total = values.reduce((a, b) => a + b, 0);
        const per = trendState.period === 'month' ? T('mois', 'month') : T('jour', 'day');
        datasets = [
            {
                label: metric === 'hours' ? T('Heures en vocal', 'Voice hours') : T('Messages', 'Messages'),
                data: values,
                ...HG.partialBar(color),
                borderRadius: 6,
                borderSkipped: false,
                order: 2,
            },
            {
                label: `${T('Moyenne', 'Average')} (${fmtValue(metric, avg)} / ${per})`,
                data: values.map(() => Math.round(avg * 10) / 10),
                type: 'line',
                borderColor: '#fbbf24',
                borderWidth: 2,
                borderDash: [6, 6],
                pointRadius: 0,
                fill: false,
                order: 1,
            },
        ];
        summary.textContent = `${T('Total sur la période', 'Total over the period')} : ${fmtValue(metric, total)} · ${T('moyenne', 'average')} ${fmtValue(metric, avg)} / ${per}`;
    }

    charts.trends = new Chart(canvas, {
        type: trendState.mode === 'cumul' ? 'line' : 'bar',
        data: { labels: series.labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: trendState.mode !== 'cumul', labels: { color: '#e3e5e8', font: { weight: 'bold' } } },
                tooltip: {
                    ...TOOLTIP,
                    callbacks: { label: c => ` ${c.dataset.label.split(' (')[0]} : ${fmtValue(metric, c.parsed.y)}` },
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#a3a6b0', maxRotation: 45, autoSkip: true, maxTicksLimit: 16 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0', callback: v => `${HG.fmt(v)} ${unit(metric)}` } },
            },
        },
    });
    if (trendState.mode !== 'cumul') {
        HG.setPartial(charts.trends, series.partial);
        charts.trends.update();
    }
}

function bindTrendControls() {
    document.querySelectorAll('[data-trend]').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.dataset.trend;
            trendState[group] = btn.dataset.value;
            document.querySelectorAll(`[data-trend="${group}"]`).forEach(b => b.classList.toggle('active', b === btn));
            if (apiData) renderTrends();
        });
    });
}

// ---------------------------------------------------------------------------
// Horaires: presence over 48 h / 7 days, peak hours (one metric at a time) + day x hour grid
// ---------------------------------------------------------------------------
let peakMetric = 'hours';
const PUNCH_SHADES = {
    hours: ['rgba(113, 124, 248, 0.18)', 'rgba(113, 124, 248, 0.38)', 'rgba(113, 124, 248, 0.6)', 'rgba(113, 124, 248, 0.82)', '#717cf8'],
    messages: ['rgba(63, 209, 160, 0.18)', 'rgba(63, 209, 160, 0.38)', 'rgba(63, 209, 160, 0.6)', 'rgba(63, 209, 160, 0.82)', '#3fd1a0'],
};

function hourLabel(h) {
    return HG.lang === 'fr' ? `${h}h` : `${h}:00`;
}

function renderHourly() {
    const d = apiData.hourly;
    const isVoice = peakMetric === 'hours';
    const values = (isVoice ? d.voice_hours : d.messages_count) || [];
    const max = Math.max(0, ...values);
    const peak = max > 0 ? values.indexOf(max) : -1;
    const color = COLORS[peakMetric];
    document.getElementById('badgePeak').textContent = peak >= 0
        ? `${T('Pic', 'Peak')} : ${hourLabel(peak)} – ${hourLabel((peak + 1) % 24)}`
        : `${T('Pic', 'Peak')} : --`;
    document.getElementById('peakDesc').textContent = isVoice
        ? T('Nombre moyen de membres en vocal à chaque heure de la journée.', 'Average number of members in voice at each hour of the day.')
        : T('Nombre moyen de messages envoyés à chaque heure de la journée.', 'Average number of messages sent at each hour of the day.');
    const fmtVal = v => isVoice
        ? `${HG.fmt(v, 1)} ${T('membre(s) en vocal en moyenne', 'member(s) in voice on average')}`
        : `${HG.fmt(v, 1)} ${T('messages en moyenne', 'messages on average')}`;
    if (charts.hourly) charts.hourly.destroy();
    charts.hourly = new Chart(document.getElementById('hourlyChart'), {
        type: 'bar',
        data: {
            labels: values.map((_, h) => hourLabel(h)),
            datasets: [{
                data: values,
                backgroundColor: values.map((v, i) => (i === peak ? color : color + '59')),
                hoverBackgroundColor: color,
                borderRadius: 5,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { ...TOOLTIP, callbacks: {
                    title: items => `${hourLabel(items[0].dataIndex)} – ${hourLabel((items[0].dataIndex + 1) % 24)}`,
                    label: c => ` ${fmtVal(c.parsed.y)}`,
                } },
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#a3a6b0', autoSkip: true, maxTicksLimit: 12 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0', maxTicksLimit: 6, callback: v => HG.fmt(v, Number.isInteger(v) ? 0 : 1) } },
            },
        },
    });
    renderPunchcard(apiData.punchcard);
}

function renderPunchcard(data) {
    const container = document.getElementById('punchcardContent');
    if (!container || !data || !data.days) return;
    const isVoice = peakMetric === 'hours';
    const shades = PUNCH_SHADES[peakMetric];
    document.querySelectorAll('[data-punch-legend]').forEach(el => { el.style.background = shades[Number(el.dataset.punchLegend) - 1]; });
    document.getElementById('punchTitle').textContent = isVoice
        ? T('Détail par jour de la semaine (vocal)', 'Detail per day of the week (voice)')
        : T('Détail par jour de la semaine (messages)', 'Detail per day of the week (messages)');
    const val = c => (isVoice ? c.voice_hours : c.messages) || 0;
    const max = Math.max(0, ...data.days.flatMap(r => (r.hours || []).map(val)));
    let html = '<div class="an-punch-grid"><div></div>';
    for (let h = 0; h < 24; h++) html += `<div class="an-punch-hour">${h % 3 === 0 ? (h < 10 ? '0' + h : h) + 'h' : ''}</div>`;
    data.days.forEach(row => {
        const day = HG.lang === 'fr' ? row.day_name : HG.weekday(row.day_index);
        html += `<div class="an-punch-day">${HG.esc(day)}</div>`;
        (row.hours || []).forEach(c => {
            const v = val(c);
            const ratio = max > 0 ? v / max : 0;
            const bg = ratio > 0 ? shades[Math.min(4, Math.floor(ratio * 5 - 1e-9))] : 'rgba(255, 255, 255, 0.04)';
            const what = isVoice
                ? T('{n} h de vocal au total', '{n} h of voice in total', { n: HG.fmt(c.voice_hours, 1) })
                : T('{n} messages au total', '{n} messages in total', { n: HG.fmt(c.messages) });
            const tip = `${day} ${hourLabel(c.hour)} · ${what}`;
            html += `<div class="punch-cell" style="background: ${bg};" data-tip="${HG.esc(tip)}" aria-label="${HG.esc(tip)}"></div>`;
        });
    });
    container.innerHTML = html + '</div>';
}

function bindPeakControls() {
    document.querySelectorAll('[data-peak]').forEach(btn => {
        btn.addEventListener('click', () => {
            peakMetric = btn.dataset.peak;
            document.querySelectorAll('[data-peak]').forEach(b => b.classList.toggle('active', b === btn));
            if (apiData && initializedTabs.has('tab-rhythm')) renderHourly();
        });
    });
}

let presenceRange = '7d';

function dayTick(labels, i) {
    const day = l => (l || '').split(' ').slice(0, ['fr', 'ja'].includes(HG.lang) ? 1 : 2).join(' ');
    return i > 0 && day(labels[i]) !== day(labels[i - 1]) ? day(labels[i]) : '';
}

function renderPresence() {
    const p = apiData.presence[presenceRange];
    const label = presenceRange === '7d' ? T('sur 7 jours', 'over 7 days') : T('sur 48 h', 'over 48 h');
    document.getElementById('badgePresence').textContent = `${T('Connectés en moyenne', 'Online on average')} ${label} : ${HG.fmt(p.avg_ratio || 0, 1)} %`;
    const area = (name, data, color) => ({
        label: name, data, borderColor: color, backgroundColor: color + '33', fill: true, tension: 0.3, borderWidth: 1.5, pointRadius: 0,
    });
    if (charts.presence) charts.presence.destroy();
    const empty = !p.labels || !p.labels.length;
    document.getElementById('presenceEmpty').hidden = !empty;
    document.getElementById('presenceChart').hidden = empty;
    if (empty) {
        document.getElementById('badgePresence').textContent = `${T('Connectés en moyenne', 'Online on average')} ${label} : --`;
        delete charts.presence;
        return;
    }
    charts.presence = new Chart(document.getElementById('presenceChart'), {
        type: 'line',
        data: {
            labels: p.labels,
            datasets: [
                area(T('En ligne', 'Online'), p.online, '#22c55e'),
                area(T('Absent', 'Idle'), p.idle, '#f59e0b'),
                area(T('Ne pas déranger', 'Do not disturb'), p.dnd, '#ef4444'),
                // Offline members dwarf the other curves: hidden by default, one click on the legend shows it
                { ...area(T('Hors ligne', 'Offline'), p.offline, '#72767d'), hidden: true },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#e3e5e8', usePointStyle: true, pointStyle: 'circle' } },
                tooltip: { ...TOOLTIP, callbacks: { label: c => ` ${c.dataset.label} : ${HG.fmt(c.parsed.y)} ${T('membres', 'members')}` } },
            },
            scales: {
                // 7 days = 168 hourly points: one tick per day, on the first hour of each new date
                // (labels look like "dd/mm HHh" in French, "Mon DD HHAM" in English)
                x: {
                    grid: { display: false },
                    ticks: presenceRange === '7d'
                        ? { color: '#a3a6b0', autoSkip: false, maxRotation: 0, callback: (v, i) => dayTick(p.labels, i) }
                        : { color: '#a3a6b0', maxTicksLimit: 12, maxRotation: 0 },
                },
                y: { stacked: true, beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0' } },
            },
        },
    });
}

function bindPresenceControls() {
    document.querySelectorAll('[data-presence]').forEach(btn => {
        btn.addEventListener('click', () => {
            presenceRange = btn.dataset.presence;
            document.querySelectorAll('[data-presence]').forEach(b => b.classList.toggle('active', b === btn));
            if (apiData && initializedTabs.has('tab-rhythm')) renderPresence();
        });
    });
}

// ---------------------------------------------------------------------------
// Communauté: growth + compact rankings with links to the full pages
// ---------------------------------------------------------------------------
function renderGrowth() {
    const g = apiData.growth;
    charts.growth = new Chart(document.getElementById('growthChart'), {
        type: 'bar',
        data: {
            labels: g.labels,
            datasets: [{ label: T('Nouveaux membres', 'New members'), data: g.new_users, backgroundColor: '#a855f7', borderRadius: 6, borderSkipped: false }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { ...TOOLTIP, callbacks: { label: c => ` ${HG.fmt(c.parsed.y)} ${T('nouveaux membres', 'new members')}` } } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#a3a6b0', maxRotation: 45, autoSkip: true, maxTicksLimit: 16 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0', precision: 0 } },
            },
        },
    });
}

function renderRanking(card, metric) {
    const kind = card.dataset.ranking;
    const rows = (kind === 'servers' ? apiData.top_servers : apiData.top_members)[metric] || [];
    const max = Math.max(1, ...rows.map(r => r.value));
    const list = card.querySelector('[data-rank-list]');
    list.innerHTML = rows.map((r, i) => {
        const href = kind === 'servers'
            ? PAGE_CFG.server_url.replace(/0$/, encodeURIComponent(r.id))
            : PAGE_CFG.profile_url.replace(/0$/, encodeURIComponent(r.id));
        const avatar = kind === 'servers'
            ? `<img src="${HG.esc(r.avatar || PAGE_CFG.server_icon)}" data-fallback="${HG.esc(PAGE_CFG.server_icon)}" alt="">`
            : '';
        const value = metric === 'hours' ? `${HG.fmt(r.value, 1)} h` : HG.fmt(r.value);
        return `<li class="an-rank-item${i < 3 ? ' podium-' + (i + 1) : ''}">
            <span class="an-rank-pos">${i + 1}</span>
            ${avatar}
            <a class="an-rank-name" href="${href}">${HG.esc(r.name)}</a>
            <span class="an-rank-bar"><i style="width: ${Math.max(3, (r.value / max) * 100)}%"></i></span>
            <span class="an-rank-value">${value}</span>
        </li>`;
    }).join('') || `<li class="an-rank-empty">${T('Aucune donnée', 'No data')}</li>`;
}

function bindRankings() {
    document.querySelectorAll('[data-ranking]').forEach(card => {
        card.querySelectorAll('[data-rank-metric]').forEach(btn => {
            btn.addEventListener('click', () => {
                card.querySelectorAll('[data-rank-metric]').forEach(b => b.classList.toggle('active', b === btn));
                if (apiData) renderRanking(card, btn.dataset.rankMetric);
            });
        });
    });
}

// ---------------------------------------------------------------------------
// Lazy initialisation per tab, once the data is loaded
// ---------------------------------------------------------------------------
function initTab(tabId) {
    if (!apiData || initializedTabs.has(tabId)) return;
    initializedTabs.add(tabId);
    if (tabId === 'tab-trends') renderTrends();
    else if (tabId === 'tab-rhythm') { renderPresence(); renderHourly(); }
    else if (tabId === 'tab-community') { renderGrowth(); document.querySelectorAll('[data-ranking]').forEach(c => renderRanking(c, 'hours')); }
}

document.addEventListener('DOMContentLoaded', () => {
    Chart.defaults.color = '#a3a6b0';
    Chart.defaults.font.family = 'Arial, sans-serif';
    bindTrendControls();
    bindRankings();
    bindPresenceControls();
    bindPeakControls();

    const hash = window.location.hash.replace('#', '');
    switchGraphTab(hash || 'tab-trends');

    // Data inlined in the page when the server already had it, otherwise one request (preloaded in the page)
    const inline = document.getElementById('graphsInitialData');
    const load = inline
        ? Promise.resolve().then(() => JSON.parse(inline.textContent))
        : fetch('/api/graphs/data').then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
    load
        .then(data => {
            apiData = data;
            renderKpis(data.summary);
            initTab(currentTab);
            document.querySelectorAll('.chart-loading-overlay').forEach(el => el.classList.add('loaded'));
        })
        .catch(err => {
            console.error('Failed to load analytics:', err);
            document.querySelectorAll('.chart-spinner-text').forEach(el => {
                el.textContent = T('Erreur de chargement', 'Error loading data');
                el.style.color = '#ef4444';
            });
        });
});
