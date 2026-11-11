/* Analytics page: three tabs (Évolution, Horaires, Communauté) fed by /api/graphs/data (cached 5 min server side). */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
const T = (fr, en, vars) => HG.tr(fr, en, vars);

const charts = {};
const initializedTabs = new Set();
let apiData = null;
let currentTab = 'tab-trends';

function switchGraphTab(tabId, initial) {
    if (!document.getElementById(tabId)) tabId = 'tab-trends';
    currentTab = tabId;
    document.querySelectorAll('.graphs-tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tabId));
    document.querySelectorAll('.graphs-tab-pane').forEach(pane => pane.classList.toggle('active', pane.id === tabId));
    initTab(tabId);
    requestAnimationFrame(() => Object.values(charts).forEach(c => { try { c.resize(); } catch (e) {} }));
    // The address only gets a #tab once the visitor switches: a #fragment present when the page finishes loading
    // makes the browser jump down to that section, past the header card
    if (!initial && window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + tabId);
}

const COLORS = { hours: '#717cf8', messages: '#3fd1a0' };
const RACE_PALETTE = HG.RANK_COLORS;

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
    const cumul = trendState.mode === 'cumul';
    const per = trendState.period === 'month' ? T('mois', 'month') : T('jour', 'day');

    const summary = document.getElementById('trendsSummary');
    if (cumul) {
        summary.textContent = `${T('Total', 'Total')} : ${fmtValue(metric, values[values.length - 1] || 0)}`;
    } else {
        const complete = HG.measuredValues(values, series);
        const avg = complete.reduce((a, b) => a + b, 0) / Math.max(1, complete.length);
        const total = values.reduce((a, b) => a + b, 0);
        summary.textContent = `${T('Total sur la période', 'Total over the period')} : ${fmtValue(metric, total)} · ${T('moyenne', 'average')} ${fmtValue(metric, avg)} / ${per}`;
    }
    charts.trends = HG.draw('trendsChart', HG.trendOption({
        labels: series.labels, values, series, metric, cumul, color: COLORS[metric], perLabel: per,
    }));
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
function hourLabel(h) {
    return HG.lang === 'fr' ? `${h}h` : `${h}:00`;
}

function renderHourly() {
    const d = apiData.hourly;
    const isVoice = peakMetric === 'hours';
    const values = (isVoice ? d.voice_hours : d.messages_count) || [];
    const max = Math.max(0, ...values);
    const peak = max > 0 ? values.indexOf(max) : -1;
    document.getElementById('badgePeak').textContent = peak >= 0
        ? `${T('Pic', 'Peak')} : ${hourLabel(peak)} – ${hourLabel((peak + 1) % 24)}`
        : `${T('Pic', 'Peak')} : --`;
    document.getElementById('peakDesc').textContent = isVoice
        ? T('Nombre moyen de membres en vocal à chaque heure de la journée.', 'Average number of members in voice at each hour of the day.')
        : T('Nombre moyen de messages envoyés à chaque heure de la journée.', 'Average number of messages sent at each hour of the day.');
    charts.hourly = HG.draw('hourlyChart', HG.hourlyOption(values, peakMetric));
    renderPunchcard(apiData.punchcard);
}

function renderPunchcard(data) {
    const container = document.getElementById('punchcardContent');
    if (!container || !data || !data.days) return;
    const isVoice = peakMetric === 'hours';
    document.getElementById('punchTitle').textContent = isVoice
        ? T('Détail par jour de la semaine (vocal)', 'Detail per day of the week (voice)')
        : T('Détail par jour de la semaine (messages)', 'Detail per day of the week (messages)');
    charts.punch = HG.draw(container, HG.punchOption(data.days, peakMetric));
    HG.punchFilter(charts.punch, document.querySelector('.an-punch-head'), peakMetric);
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

// Points of a time series: [local time, value] on a time axis (zoom keeps sensible ticks), or the labels sent by
// the server when the data was computed before the times were added
function timePoints(p, values) {
    return p.times ? values.map((v, i) => [new Date(p.times[i]).getTime(), v]) : values;
}
function timeX(p) {
    return p.times ? HG.timeAxis() : HG.categoryAxis(p.labels, { boundaryGap: false });
}

function renderPresence() {
    const p = apiData.presence[presenceRange];
    const label = presenceRange === '7d' ? T('sur 7 jours', 'over 7 days') : T('sur 48 h', 'over 48 h');
    document.getElementById('badgePresence').textContent = `${T('Connectés en moyenne', 'Online on average')} ${label} : ${HG.fmt(p.avg_ratio || 0, 1)} %`;
    const empty = !p.labels || !p.labels.length;
    document.getElementById('presenceEmpty').hidden = !empty;
    document.getElementById('presenceChart').hidden = empty;
    if (empty) {
        document.getElementById('badgePresence').textContent = `${T('Connectés en moyenne', 'Online on average')} ${label} : --`;
        if (charts.presence) charts.presence.clear();
        return;
    }
    const SERIES = [
        { key: 'online', name: T('En ligne', 'Online'), color: '#22c55e' },
        { key: 'idle', name: T('Absent', 'Idle'), color: '#f59e0b' },
        { key: 'dnd', name: T('Ne pas déranger', 'Do not disturb'), color: '#ef4444' },
        { key: 'offline', name: T('Hors ligne', 'Offline'), color: '#8b8e98' },
    ];
    const zoom = HG.zoom(p.labels.length, { min: 60, minSpan: p.times ? 6 * 3600 * 1000 : 6 });
    charts.presence = HG.draw('presenceChart', {
        grid: HG.grid({ top: 40, bottom: zoom.bottom }),
        // Offline members dwarf the other curves: hidden by default, one click on the legend shows them
        legend: HG.legend({ selected: { [SERIES[3].name]: false } }),
        tooltip: HG.tooltip({
            formatter: ps => {
                const rows = HG.sortedRows(ps, v => HG.fmt(v));
                const sum = rows.reduce((a, r) => a + r.raw, 0);
                rows.forEach(r => { r.pct = sum ? `${Math.round(r.raw / sum * 100)} %` : ''; });
                return HG.tipHtml(p.labels[ps[0].dataIndex], rows, { total: rows.length > 1 ? HG.fmt(sum) : null, pctColumn: true });
            },
        }),
        xAxis: timeX(p),
        yAxis: HG.valueAxis({ min: HG.fitMin }),
        dataZoom: zoom.dataZoom,
        series: SERIES.map(s => ({
            name: s.name, type: 'line', data: timePoints(p, p[s.key]),
            showSymbol: false, smooth: 0.3, symbolSize: 6,
            lineStyle: { width: 1.6, color: s.color }, itemStyle: { color: s.color },
            // Each curve at its own value (not stacked): a light fill under it, fading out
            areaStyle: { color: HG.areaFill(s.color, 0.16, 0) },
            emphasis: { focus: 'series', lineStyle: { width: 2.6 } },
            blur: { lineStyle: { opacity: 0.2 }, areaStyle: { opacity: 0.05 } },
        })),
    });
    syncRhythm();
}

// Presence and members in voice share their timeline: hovering or zooming one moves the other
function syncRhythm() {
    const p = apiData.presence[presenceRange], v = apiData.voice_live && apiData.voice_live[voiceLiveRange];
    if (p && p.times && v && v.times) HG.syncTime([charts.presence, charts.voiceLive]);
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

let voiceLiveRange = '7d';

// Members in voice every 15 min (rebuilt from the voice sessions), over 48 h or 7 days
function renderVoiceLive() {
    const p = apiData.voice_live && apiData.voice_live[voiceLiveRange];
    const badge = document.getElementById('badgeVoiceLive');
    const empty = !p || !p.has_data;
    document.getElementById('voiceLiveEmpty').hidden = !empty;
    document.getElementById('voiceLiveChart').hidden = empty;
    const label = voiceLiveRange === '7d' ? T('sur 7 jours', 'over 7 days') : T('sur 48 h', 'over 48 h');
    badge.textContent = `${T('Pic', 'Peak')} ${label} : ${empty ? '--' : HG.fmt(Math.max(...p.voice))}`;
    const rec = apiData.voice_live && apiData.voice_live.record;
    const recBadge = document.getElementById('badgeVoiceRecord');
    recBadge.hidden = !rec;
    if (rec) {
        const when = new Date(rec.at).toLocaleString(HG.lang, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        recBadge.textContent = `${T('Record absolu', 'All-time record')} : ${HG.fmt(rec.count)} · ${when}`;
    }
    if (empty) {
        if (charts.voiceLive) charts.voiceLive.clear();
        return;
    }
    const zoom = HG.zoom(p.voice.length, { min: 60, minSpan: p.times ? 3 * 3600 * 1000 : 12 });
    charts.voiceLive = HG.draw('voiceLiveChart', {
        grid: HG.grid({ top: 30, bottom: zoom.bottom }),
        tooltip: HG.tooltip({
            formatter: ps => {
                const i = ps[0].dataIndex;
                // The live point comes after the 15-minute snapshots
                if (i >= p.labels.length) return HG.tipHtml(T('Maintenant', 'Right now'), [{ color: '#b1a8f5', name: T('en vocal', 'in voice'), value: HG.fmt(liveNow ? liveNow.v : 0) }]);
                return HG.tipHtml(p.labels[i], [{ color: '#8b80ea', name: T('en vocal', 'in voice'), value: HG.fmt(p.voice[i]) }]);
            },
        }),
        xAxis: timeX(p),
        yAxis: HG.valueAxis({ minInterval: 1, min: HG.fitMin }),
        dataZoom: zoom.dataZoom,
        series: [{
            id: 'voice', name: T('En vocal', 'In voice'), type: 'line', data: timePoints(p, p.voice),
            showSymbol: false, smooth: 0.3, sampling: 'lttb', symbolSize: 7,
            lineStyle: { width: 2, color: '#8b80ea' }, itemStyle: { color: '#8b80ea' },
            areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(177, 168, 245, 0.45)' }, { offset: 1, color: 'rgba(61, 53, 145, 0.04)' },
            ]) },
            // The peak of the period, in gold like the record badge
            markPoint: {
                symbol: 'pin', symbolSize: 40, itemStyle: { color: '#fbbf3c' },
                label: { color: '#15161a', fontWeight: 700, fontSize: 11 },
                data: [{ type: 'max', name: T('Pic', 'Peak') }],
            },
        }, {
            // Right now: a pulsing dot at the end of the curve, moved every minute
            id: 'live', type: 'effectScatter', data: [], symbolSize: 9, z: 5,
            rippleEffect: { scale: 3.2, brushType: 'stroke', period: 2.4 },
            itemStyle: { color: '#b1a8f5', shadowBlur: 10, shadowColor: 'rgba(177, 168, 245, 0.8)' },
            tooltip: { show: false },
        }],
    });
    paintLive();
    syncRhythm();
    startLive();
}

// ---------------------------------------------------------------------------
// Live count of members in voice (/api/live/voice), every minute while the Horaires tab is open
// ---------------------------------------------------------------------------
let liveNow = null;
let liveTimer = null;

function paintLive() {
    const p = apiData && apiData.voice_live && apiData.voice_live[voiceLiveRange];
    let badge = document.getElementById('badgeVoiceNow');
    if (!badge) {
        badge = document.createElement('span');
        badge.id = 'badgeVoiceNow';
        badge.className = 'an-badge an-badge-live';
        badge.hidden = true;
        document.getElementById('badgeVoiceLive').before(badge);
    }
    if (!liveNow) return;
    badge.hidden = false;
    badge.innerHTML = `<i aria-hidden="true"></i>${HG.esc(T('{n} en vocal maintenant', '{n} in voice right now', { n: HG.fmt(liveNow.v) }))}`;
    if (!charts.voiceLive || !p || !p.times || !p.has_data) return;
    const point = [liveNow.t, liveNow.v];
    charts.voiceLive.setOption({ series: [{ id: 'voice', data: timePoints(p, p.voice).concat([point]) }, { id: 'live', data: [point] }] });
}

function liveTick() {
    if (document.hidden || currentTab !== 'tab-rhythm') return;
    fetch('/api/live/voice', { credentials: 'same-origin' })
        .then(r => (r.ok ? r.json() : null))
        .then(d => {
            if (!d || d.in_voice == null) return;
            liveNow = { t: Date.now(), v: d.in_voice };
            paintLive();
        })
        .catch(() => {});
}

function startLive() {
    if (liveTimer) return;
    liveTick();
    liveTimer = setInterval(liveTick, 60000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) liveTick(); });
}

function bindVoiceLiveControls() {
    document.querySelectorAll('[data-voicelive]').forEach(btn => {
        btn.addEventListener('click', () => {
            voiceLiveRange = btn.dataset.voicelive;
            document.querySelectorAll('[data-voicelive]').forEach(b => b.classList.toggle('active', b === btn));
            if (apiData && initializedTabs.has('tab-rhythm')) renderVoiceLive();
        });
    });
}

// ---------------------------------------------------------------------------
// Communauté: growth + compact rankings with links to the full pages
// ---------------------------------------------------------------------------
function renderGrowth() {
    const g = apiData.growth;
    const servers = g.new_servers || [];
    const zoom = HG.zoom(g.labels.length, { min: 40, compact: true, label: v => v });
    charts.growth = HG.draw('growthChart', {
        grid: HG.grid({ top: 40, bottom: zoom.bottom }),
        legend: HG.legend({ left: 'center' }),
        tooltip: HG.tooltip({
            axisPointer: HG.barPointer,
            formatter: ps => {
                const i = ps[0].dataIndex;
                return HG.tipHtml(ps[0].axisValueLabel || ps[0].name, [
                    { color: '#b07cff', name: T('nouveaux membres', 'new members'), value: HG.fmt(g.new_users[i]) },
                    { color: '#ff6b5e', name: T('nouveaux serveurs', 'new servers'), value: HG.fmt(servers[i] || 0) },
                ]);
            },
        }),
        xAxis: HG.categoryAxis(g.labels),
        yAxis: [
            HG.valueAxis({ minInterval: 1, axisLabel: { color: '#b07cff' } }),
            HG.valueAxis({ minInterval: 1, splitLine: { show: false }, axisLabel: { color: '#ff6b5e' } }),
        ],
        dataZoom: zoom.dataZoom,
        series: [{
            type: 'bar', name: T('Nouveaux membres', 'New members'), data: g.new_users, barMaxWidth: 34, yAxisIndex: 0, barGap: '12%',
            itemStyle: { color: '#b07cff' },
            emphasis: { itemStyle: { color: '#c9a3ff' } },
        }, {
            // Second column of each month, on its own axis (a few servers a month against dozens of members)
            type: 'bar', name: T('Nouveaux serveurs', 'New servers'), data: servers, barMaxWidth: 34, yAxisIndex: 1,
            itemStyle: { color: '#ff6b5e' },
            emphasis: { itemStyle: { color: '#ff9289' } },
        }],
    });
}

// What moved lately: biggest rises in voice (30 days against the 30 before) and newcomers of the last 30 days
function renderMovers(card, kind) {
    const list = card.querySelector('[data-rank-list]');
    const what = card.dataset.movers;
    const data = apiData.movers && apiData.movers[what] && apiData.movers[what][kind];
    const rows = data || [];
    const max = Math.max(1, ...rows.map(r => r.value));
    const day = d => (d ? new Date(d + 'T12:00').toLocaleDateString(HG.locale, { day: 'numeric', month: 'short' }) : '');
    list.innerHTML = rows.map((r, i) => {
        const href = kind === 'servers'
            ? PAGE_CFG.server_url.replace(/0$/, encodeURIComponent(r.id))
            : PAGE_CFG.profile_url.replace(/0$/, encodeURIComponent(r.id));
        const fallback = kind === 'servers' ? PAGE_CFG.server_icon : PAGE_CFG.user_icon;
        const avatar = `<img src="${HG.esc(r.avatar || fallback)}" data-fallback="${HG.esc(fallback)}" alt=""${kind === 'members' ? ' class="is-member"' : ''}>`;
        const value = what === 'progress' ? `+${HG.fmt(r.value, 1)} h` : `${HG.fmt(r.value, 1)} h`;
        const tip = what === 'progress'
            ? T('{a} h ces 30 jours, contre {b} h les 30 jours d’avant', '{a} h these 30 days, against {b} h the 30 days before', { a: HG.fmt(r.current, 1), b: HG.fmt(r.previous, 1) })
            : T('Arrivé le {d}', 'Arrived on {d}', { d: day(r.since) });
        const sub = what === 'progress'
            ? T('{a} h · avant {b} h', '{a} h · before {b} h', { a: HG.fmt(r.current, 1), b: HG.fmt(r.previous, 1) })
            : T('depuis le {d}', 'since {d}', { d: day(r.since) });
        return `<li class="an-rank-item${i < 3 ? ' podium-' + (i + 1) : ''}" data-tip="${HG.esc(tip)}">
            <span class="an-rank-pos">${i + 1}</span>
            ${avatar}
            <span class="an-rank-who"><a class="an-rank-name" href="${href}">${HG.esc(r.name)}</a><small class="an-rank-sub">${HG.esc(sub)}</small></span>
            <span class="an-rank-bar"><i style="width: ${Math.max(3, (r.value / max) * 100)}%"></i></span>
            <span class="an-rank-value${what === 'progress' ? ' is-up' : ''}">${value}</span>
        </li>`;
    }).join('') || `<li class="an-rank-empty">${what === 'progress'
        ? T('Personne n’a progressé ces 30 derniers jours.', 'Nobody rose over the last 30 days.')
        : T('Aucune arrivée ces 30 derniers jours.', 'No arrival in the last 30 days.')}</li>`;
}

function bindMovers() {
    document.querySelectorAll('[data-movers]').forEach(card => {
        card.querySelectorAll('[data-movers-kind]').forEach(btn => {
            btn.addEventListener('click', () => {
                card.querySelectorAll('[data-movers-kind]').forEach(b => b.classList.toggle('active', b === btn));
                if (apiData) renderMovers(card, btn.dataset.moversKind);
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
    else if (tabId === 'tab-rhythm') { renderPresence(); renderVoiceLive(); renderHourly(); }
    else if (tabId === 'tab-community') { renderGrowth(); HG.memberRace(document.getElementById('globalRaceCard'), apiData.race, RACE_PALETTE); document.querySelectorAll('[data-movers]').forEach(c => renderMovers(c, 'members')); }
}

document.addEventListener('DOMContentLoaded', () => {
    bindTrendControls();
    bindMovers();
    bindPresenceControls();
    bindVoiceLiveControls();
    bindPeakControls();

    const hash = window.location.hash.replace('#', '');
    switchGraphTab(hash || 'tab-trends', true);

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
