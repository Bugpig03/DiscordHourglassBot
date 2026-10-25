/* Shared chart cards of the member and server profiles (same rules as the Analytics page):
   - HG.trendCard: one chart, voice or messages, monthly or 30 days, per period or cumulative;
   - HG.peakCard: average activity per hour (one metric at a time) + day x hour grid;
   - HG.splitCard: one doughnut + ranked list, switched between several breakdowns.
   Each card is driven by data-* attributes inside its root element. Needs charts.js (HG). */
(function () {
    const HG = window.HG = window.HG || {};
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
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
    const PALETTE = ['#5865F2', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#a855f7', '#72767d'];

    HG.cardCharts = HG.cardCharts || [];

    function fmtMetric(metric, v) {
        return metric === 'hours' ? `${HG.fmt(v, 1)} h` : T('{n} messages', '{n} messages', { n: HG.fmt(v) });
    }

    function bindToggle(root, attr, onChange) {
        const buttons = root.querySelectorAll(`[${attr}]`);
        buttons.forEach(btn => btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.toggle('active', b === btn));
            onChange(btn.getAttribute(attr));
        }));
    }

    // The previous chart of a card must be destroyed before a new one takes its canvas
    function keepChart(old, build) {
        const i = HG.cardCharts.indexOf(old);
        if (i >= 0) HG.cardCharts.splice(i, 1);
        if (old) old.destroy();
        const chart = build();
        HG.cardCharts.push(chart);
        return chart;
    }

    // "2026-10-01" -> "oct. 2026" (month) or "1 oct." (day); other labels are kept
    function dateLabel(label, period) {
        const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(label || '');
        if (!m) return label;
        const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
        return period === 'month'
            ? d.toLocaleDateString(HG.locale, { month: 'short', year: 'numeric' })
            : d.toLocaleDateString(HG.locale, { day: 'numeric', month: 'short' });
    }

    /* sources: {month, day, month_cumul, day_cumul}, each {labels, hours, messages, partial?}
       opts: {colors: {hours, messages}, period: 'month' | 'day'} */
    HG.trendCard = function (root, sources, opts) {
        if (!root) return;
        const state = { metric: 'hours', period: opts.period || 'month', mode: 'period' };
        const canvas = root.querySelector('[data-trend-canvas]');
        const summary = root.querySelector('[data-trend-summary]');
        let chart = null;

        root.querySelectorAll('[data-trend-period]').forEach(b => b.classList.toggle('active', b.dataset.trendPeriod === state.period));

        function render() {
            const cumul = state.mode === 'cumul';
            const series = sources[state.period + (cumul ? '_cumul' : '')] || { labels: [] };
            const metric = state.metric;
            const values = series[metric] || [];
            const labels = (series.labels || []).map(l => dateLabel(l, state.period));
            const color = opts.colors[metric];
            let datasets;
            if (cumul) {
                const gradient = canvas.getContext('2d').createLinearGradient(0, 0, 0, 360);
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
                if (summary) summary.textContent = `${T('Total', 'Total')} : ${fmtMetric(metric, values[values.length - 1] || 0)}`;
            } else {
                const complete = series.partial && values.length > 1 ? values.slice(0, -1) : values;
                const avg = complete.reduce((a, b) => a + b, 0) / Math.max(1, complete.length);
                const total = values.reduce((a, b) => a + b, 0);
                const per = state.period === 'month' ? T('mois', 'month') : T('jour', 'day');
                datasets = [
                    {
                        label: metric === 'hours' ? T('Heures en vocal', 'Voice hours') : 'Messages',
                        data: values,
                        ...HG.partialBar(color),
                        borderRadius: 6,
                        borderSkipped: false,
                        order: 2,
                    },
                    {
                        label: `${T('Moyenne', 'Average')} (${fmtMetric(metric, avg)} / ${per})`,
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
                if (summary) {
                    const span = state.period === 'month' ? T('Total sur la période', 'Total over the period') : T('Total sur 30 jours', 'Total over 30 days');
                    summary.textContent = `${span} : ${fmtMetric(metric, total)} · ${T('moyenne', 'average')} ${fmtMetric(metric, avg)} / ${per}`;
                }
            }
            chart = keepChart(chart, () => new Chart(canvas, {
                type: cumul ? 'line' : 'bar',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: !cumul, labels: { color: '#e3e5e8', font: { weight: 'bold' } } },
                        tooltip: { ...TOOLTIP, callbacks: { label: c => ` ${c.dataset.label.split(' (')[0]} : ${fmtMetric(metric, c.parsed.y)}` } },
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#a3a6b0', maxRotation: 45, autoSkip: true, maxTicksLimit: 16 } },
                        y: { beginAtZero: true, grid: GRID, ticks: { color: '#a3a6b0', callback: v => (metric === 'hours' ? `${HG.fmt(v)} h` : HG.fmt(v)) } },
                    },
                },
            }));
            if (!cumul) {
                HG.setPartial(chart, series.partial);
                chart.update();
            }
        }

        bindToggle(root, 'data-trend-metric', v => { state.metric = v; render(); });
        bindToggle(root, 'data-trend-period', v => { state.period = v; render(); });
        bindToggle(root, 'data-trend-mode', v => { state.mode = v; render(); });
        render();
    };

    const PUNCH_SHADES = {
        hours: ['rgba(113, 124, 248, 0.18)', 'rgba(113, 124, 248, 0.38)', 'rgba(113, 124, 248, 0.6)', 'rgba(113, 124, 248, 0.82)', '#717cf8'],
        messages: ['rgba(63, 209, 160, 0.18)', 'rgba(63, 209, 160, 0.38)', 'rgba(63, 209, 160, 0.6)', 'rgba(63, 209, 160, 0.82)', '#3fd1a0'],
    };
    const hourLabel = h => (HG.lang === 'fr' ? `${h}h` : `${h}:00`);

    /* hourly: {voice_hours[24], messages_count[24]}; punchcard: {days: [{day_name, day_index, hours: [{hour, voice_hours, messages}]}]} */
    HG.peakCard = function (root, hourly, punchcard) {
        if (!root || !hourly) return;
        const canvas = root.querySelector('[data-peak-canvas]');
        const badge = root.querySelector('[data-peak-badge]');
        const desc = root.querySelector('[data-peak-desc]');
        const punch = root.querySelector('[data-punch]');
        const punchTitle = root.querySelector('[data-punch-title]');
        const colors = { hours: '#717cf8', messages: '#3fd1a0' };
        let metric = 'hours';
        let chart = null;

        function renderPunch() {
            if (!punch || !punchcard || !punchcard.days) return;
            const isVoice = metric === 'hours';
            const shades = PUNCH_SHADES[metric];
            root.querySelectorAll('[data-punch-legend]').forEach(el => { el.style.background = shades[Number(el.dataset.punchLegend) - 1]; });
            if (punchTitle) punchTitle.textContent = isVoice
                ? T('Détail par jour de la semaine (vocal)', 'Detail per day of the week (voice)')
                : T('Détail par jour de la semaine (messages)', 'Detail per day of the week (messages)');
            const val = c => (isVoice ? c.voice_hours : c.messages) || 0;
            const max = Math.max(0, ...punchcard.days.flatMap(r => (r.hours || []).map(val)));
            let html = '<div class="hg-punch-grid"><div></div>';
            for (let h = 0; h < 24; h++) html += `<div class="hg-punch-hour">${h % 3 === 0 ? (h < 10 ? '0' + h : h) + 'h' : ''}</div>`;
            punchcard.days.forEach(row => {
                const day = HG.lang === 'fr' ? row.day_name : HG.weekday(row.day_index);
                html += `<div class="hg-punch-day">${HG.esc(day)}</div>`;
                (row.hours || []).forEach(c => {
                    const ratio = max > 0 ? val(c) / max : 0;
                    const bg = ratio > 0 ? shades[Math.min(4, Math.floor(ratio * 5 - 1e-9))] : 'rgba(255, 255, 255, 0.04)';
                    const what = isVoice
                        ? T('{n} h de vocal au total', '{n} h of voice in total', { n: HG.fmt(c.voice_hours, 1) })
                        : T('{n} messages au total', '{n} messages in total', { n: HG.fmt(c.messages) });
                    const tip = `${day} ${hourLabel(c.hour)} · ${what}`;
                    html += `<div class="punch-cell" style="background: ${bg};" data-tip="${HG.esc(tip)}" aria-label="${HG.esc(tip)}"></div>`;
                });
            });
            punch.innerHTML = html + '</div>';
        }

        function render() {
            const isVoice = metric === 'hours';
            const values = (isVoice ? hourly.voice_hours : hourly.messages_count) || [];
            const max = Math.max(0, ...values);
            const peak = max > 0 ? values.indexOf(max) : -1;
            const color = colors[metric];
            if (badge) badge.textContent = peak >= 0
                ? `${T('Pic', 'Peak')} : ${hourLabel(peak)} – ${hourLabel((peak + 1) % 24)}`
                : `${T('Pic', 'Peak')} : --`;
            if (desc) desc.textContent = isVoice
                ? T('Nombre moyen de membres en vocal à chaque heure de la journée.', 'Average number of members in voice at each hour of the day.')
                : T('Nombre moyen de messages envoyés à chaque heure de la journée.', 'Average number of messages sent at each hour of the day.');
            const fmtVal = v => isVoice
                ? `${HG.fmt(v, 1)} ${T('membre(s) en vocal en moyenne', 'member(s) in voice on average')}`
                : `${HG.fmt(v, 1)} ${T('messages en moyenne', 'messages on average')}`;
            chart = keepChart(chart, () => new Chart(canvas, {
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
            }));
            renderPunch();
        }

        bindToggle(root, 'data-peak', v => { metric = v; render(); });
        render();
    };

    /* sets: {key: {labels, values, metric: 'hours' | 'messages', desc}} switched by [data-split="key"] */
    HG.splitCard = function (root, sets, first) {
        if (!root) return;
        const canvas = root.querySelector('[data-split-canvas]');
        const list = root.querySelector('[data-split-list]');
        const desc = root.querySelector('[data-split-desc]');
        const empty = root.querySelector('[data-split-empty]');
        let chart = null;

        function render(key) {
            const set = sets[key] || { labels: [], values: [] };
            const total = set.values.reduce((a, b) => a + b, 0);
            if (desc) desc.textContent = set.desc || '';
            const hasData = total > 0;
            canvas.parentElement.hidden = !hasData;
            if (empty) empty.hidden = hasData;
            if (list) list.innerHTML = hasData ? set.labels.map((l, i) => `
                <li class="hg-split-item">
                    <i style="background: ${PALETTE[i % PALETTE.length]};"></i>
                    <span class="hg-split-name">${HG.esc(l)}</span>
                    <span class="hg-split-value">${fmtMetric(set.metric, set.values[i])}</span>
                    <span class="hg-split-pct">${HG.fmt((set.values[i] / total) * 100, 1)} %</span>
                </li>`).join('') : '';
            if (!hasData) return;
            chart = keepChart(chart, () => new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: set.labels,
                    datasets: [{ data: set.values, backgroundColor: PALETTE.slice(0, set.labels.length), borderColor: '#212329', borderWidth: 2, hoverOffset: 8 }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '62%',
                    plugins: {
                        legend: { display: false },
                        tooltip: { ...TOOLTIP, callbacks: { label: c => ` ${fmtMetric(set.metric, c.parsed)} (${HG.fmt((c.parsed / total) * 100, 1)} %)` } },
                    },
                },
            }));
        }

        bindToggle(root, 'data-split', render);
        render(first);
    };
})();
