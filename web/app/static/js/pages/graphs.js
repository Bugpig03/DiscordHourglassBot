/* Analytics page: three tabs (Tendances, Rythme, Communauté) fed by /api/graphs/data (cached 5 min server side). */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const IS_EN = PAGE_CFG.current_lang === 'en';
const T = (fr, en) => (IS_EN ? en : fr);

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
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    titleColor: '#ffffff',
    bodyColor: '#e2e8f0',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    borderWidth: 1,
    padding: 12,
    boxPadding: 6,
};
const GRID = { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false };
const COLORS = { hours: '#38bdf8', messages: '#818cf8' };

function unit(metric) {
    return metric === 'hours' ? 'h' : (IS_EN ? 'msgs' : 'msgs');
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
                legend: { display: trendState.mode !== 'cumul', labels: { color: '#e2e8f0', font: { weight: 'bold' } } },
                tooltip: {
                    ...TOOLTIP,
                    callbacks: { label: c => ` ${c.dataset.label.split(' (')[0]} : ${fmtValue(metric, c.parsed.y)}` },
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8', maxRotation: 45, autoSkip: true, maxTicksLimit: 16 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: '#94a3b8', callback: v => `${HG.fmt(v)} ${unit(metric)}` } },
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
// Rythme: 24 h curve + day x hour punchcard, presence over 48 h
// ---------------------------------------------------------------------------
function renderHourly() {
    const d = apiData.hourly;
    document.getElementById('badgeVoicePeak').textContent = `${T('Pic vocal', 'Voice peak')} : ${d.peak_voice_hour || '--'}`;
    document.getElementById('badgeMessagesPeak').textContent = `${T('Pic messages', 'Messages peak')} : ${d.peak_messages_hour || '--'}`;
    charts.hourly = new Chart(document.getElementById('hourlyChart'), {
        type: 'line',
        data: {
            labels: d.labels,
            datasets: [
                {
                    label: T('Vocal (h / jour)', 'Voice (h / day)'),
                    data: d.voice_hours,
                    borderColor: COLORS.hours,
                    backgroundColor: 'rgba(56, 189, 248, 0.15)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 0,
                    yAxisID: 'y',
                },
                {
                    label: T('Messages (par jour)', 'Messages (per day)'),
                    data: d.messages_count,
                    borderColor: COLORS.messages,
                    borderDash: [5, 4],
                    fill: false,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#e2e8f0', usePointStyle: true, pointStyle: 'circle' } },
                tooltip: TOOLTIP,
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 12 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: COLORS.hours, maxTicksLimit: 6, callback: v => `${HG.fmt(v, Number.isInteger(v * 10) ? 1 : 2)} h` } },
                y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { color: COLORS.messages } },
            },
        },
    });
}

function renderPunchcard(data) {
    const container = document.getElementById('punchcardContent');
    if (!container || !data || !data.days) return;
    const dayNamesEn = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    let html = '<div class="an-punch-grid"><div></div>';
    for (let h = 0; h < 24; h++) html += `<div class="an-punch-hour">${h % 3 === 0 ? (h < 10 ? '0' + h : h) + 'h' : ''}</div>`;
    data.days.forEach(row => {
        const day = IS_EN ? (dayNamesEn[row.day_index] || row.day_name) : row.day_name;
        html += `<div class="an-punch-day">${HG.esc(day)}</div>`;
        (row.hours || []).forEach(c => {
            let bg = 'rgba(255, 255, 255, 0.04)';
            if (c.intensity > 0.75) bg = '#f43f5e';
            else if (c.intensity > 0.5) bg = 'rgba(129, 140, 248, 0.85)';
            else if (c.intensity > 0.25) bg = 'rgba(56, 189, 248, 0.6)';
            else if (c.intensity > 0) bg = 'rgba(56, 189, 248, 0.3)';
            const tip = IS_EN
                ? `${day} ${c.hour}:00 · ${HG.fmt(c.voice_hours, 1)} h voice · ${HG.fmt(c.messages)} messages`
                : `${day} ${c.hour}h · ${HG.fmt(c.voice_hours, 1)} h de vocal · ${HG.fmt(c.messages)} messages`;
            html += `<div class="punch-cell" style="background: ${bg};" data-tip="${HG.esc(tip)}" aria-label="${HG.esc(tip)}"></div>`;
        });
    });
    container.innerHTML = html + '</div>';
}

let presenceRange = '7d';

function dayTick(labels, i) {
    const day = l => (l || '').split(' ').slice(0, IS_EN ? 2 : 1).join(' ');
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
                { ...area(T('Hors ligne', 'Offline'), p.offline, '#64748b'), hidden: true },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#e2e8f0', usePointStyle: true, pointStyle: 'circle' } },
                tooltip: { ...TOOLTIP, callbacks: { label: c => ` ${c.dataset.label} : ${HG.fmt(c.parsed.y)} ${T('membres', 'members')}` } },
            },
            scales: {
                // 7 days = 168 hourly points: one tick per day, on the first hour of each new date
                // (labels look like "dd/mm HHh" in French, "Mon DD HHAM" in English)
                x: {
                    grid: { display: false },
                    ticks: presenceRange === '7d'
                        ? { color: '#94a3b8', autoSkip: false, maxRotation: 0, callback: (v, i) => dayTick(p.labels, i) }
                        : { color: '#94a3b8', maxTicksLimit: 12, maxRotation: 0 },
                },
                y: { stacked: true, beginAtZero: true, grid: GRID, ticks: { color: '#94a3b8' } },
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
                x: { grid: { display: false }, ticks: { color: '#94a3b8', maxRotation: 45, autoSkip: true, maxTicksLimit: 16 } },
                y: { beginAtZero: true, grid: GRID, ticks: { color: '#94a3b8', precision: 0 } },
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
    else if (tabId === 'tab-rhythm') { renderHourly(); renderPunchcard(apiData.punchcard); renderPresence(); }
    else if (tabId === 'tab-community') { renderGrowth(); document.querySelectorAll('[data-ranking]').forEach(c => renderRanking(c, 'hours')); }
}

document.addEventListener('DOMContentLoaded', () => {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = 'Arial, sans-serif';
    bindTrendControls();
    bindRankings();
    bindPresenceControls();

    const hash = window.location.hash.replace('#', '');
    switchGraphTab(hash || 'tab-trends');

    fetch('/api/graphs/data')
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
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
