/* Shared chart cards of the member and server profiles (same rules as the Analytics page):
   - HG.trendCard: one chart, voice or messages, monthly or 30 days, per period or cumulative;
   - HG.peakCard: average activity per hour (one metric at a time) + day x hour grid;
   - HG.splitCard: one doughnut + ranked list, switched between several breakdowns.
   Each card is driven by data-* attributes inside its root element. Needs charts.js (HG, ECharts). */
(function () {
    const HG = window.HG = window.HG || {};
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const PALETTE = HG.RANK_COLORS;  // Arène colors, toned down; the last (gray) for the rest

    // Charts of the cards, resized when a profile tab is shown (ECharts instances)
    HG.cardCharts = HG.cardCharts || [];
    function keep(chart) {
        if (chart && !HG.cardCharts.includes(chart)) HG.cardCharts.push(chart);
        return chart;
    }

    function bindToggle(root, attr, onChange) {
        const buttons = root.querySelectorAll(`[${attr}]`);
        buttons.forEach(btn => btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.toggle('active', b === btn));
            onChange(btn.getAttribute(attr));
        }));
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
        const box = HG.chartBox(root.querySelector('[data-trend-canvas]'));
        const summary = root.querySelector('[data-trend-summary]');

        root.querySelectorAll('[data-trend-period]').forEach(b => b.classList.toggle('active', b.dataset.trendPeriod === state.period));

        function render() {
            const cumul = state.mode === 'cumul';
            const series = sources[state.period + (cumul ? '_cumul' : '')] || { labels: [] };
            const metric = state.metric;
            const values = series[metric] || [];
            const labels = (series.labels || []).map(l => dateLabel(l, state.period));
            const per = state.period === 'month' ? T('mois', 'month') : T('jour', 'day');
            if (summary) {
                if (cumul) {
                    summary.textContent = `${T('Total', 'Total')} : ${HG.metricText(metric, values[values.length - 1] || 0)}`;
                } else {
                    const complete = HG.measuredValues(values, series);
                    const avg = complete.reduce((a, b) => a + b, 0) / Math.max(1, complete.length);
                    const total = values.reduce((a, b) => a + b, 0);
                    const span = state.period === 'month' ? T('Total sur la période', 'Total over the period') : T('Total sur 30 jours', 'Total over 30 days');
                    summary.textContent = `${span} : ${HG.metricText(metric, total)} · ${T('moyenne', 'average')} ${HG.metricText(metric, avg)} / ${per}`;
                }
            }
            keep(HG.draw(box, HG.trendOption({ labels, values, series, metric, cumul, color: opts.colors[metric], perLabel: per })));
        }

        bindToggle(root, 'data-trend-metric', v => { state.metric = v; render(); });
        bindToggle(root, 'data-trend-period', v => { state.period = v; render(); });
        bindToggle(root, 'data-trend-mode', v => { state.mode = v; render(); });
        render();
    };

    const hourLabel = h => (HG.lang === 'fr' ? `${h}h` : `${h}:00`);

    /* hourly: {voice_hours[24], messages_count[24]}; punchcard: {days: [{day_name, day_index, hours: [{hour, voice_hours, messages}]}]} */
    HG.peakCard = function (root, hourly, punchcard) {
        if (!root || !hourly) return;
        const box = HG.chartBox(root.querySelector('[data-peak-canvas]'));
        const badge = root.querySelector('[data-peak-badge]');
        const desc = root.querySelector('[data-peak-desc]');
        const punch = root.querySelector('[data-punch]');
        const punchTitle = root.querySelector('[data-punch-title]');
        let metric = 'hours';

        function renderPunch() {
            if (!punch || !punchcard || !punchcard.days) return;
            const isVoice = metric === 'hours';
            if (punchTitle) punchTitle.textContent = isVoice
                ? T('Détail par jour de la semaine (vocal)', 'Detail per day of the week (voice)')
                : T('Détail par jour de la semaine (messages)', 'Detail per day of the week (messages)');
            const chart = keep(HG.draw(punch, HG.punchOption(punchcard.days, metric)));
            HG.punchFilter(chart, root.querySelector('.hg-punch-head') || punch.parentElement, metric);
        }

        function render() {
            const isVoice = metric === 'hours';
            const values = (isVoice ? hourly.voice_hours : hourly.messages_count) || [];
            const max = Math.max(0, ...values);
            const peak = max > 0 ? values.indexOf(max) : -1;
            if (badge) badge.textContent = peak >= 0
                ? `${T('Pic', 'Peak')} : ${hourLabel(peak)} – ${hourLabel((peak + 1) % 24)}`
                : `${T('Pic', 'Peak')} : --`;
            if (desc) desc.textContent = isVoice
                ? T('Nombre moyen de membres en vocal à chaque heure de la journée.', 'Average number of members in voice at each hour of the day.')
                : T('Nombre moyen de messages envoyés à chaque heure de la journée.', 'Average number of messages sent at each hour of the day.');
            keep(HG.draw(box, HG.hourlyOption(values, metric)));
            renderPunch();
        }

        bindToggle(root, 'data-peak', v => { metric = v; render(); });
        render();
    };

    /* sets: {key: {labels, values, metric: 'hours' | 'messages', desc}} switched by [data-split="key"]
       Hovering a line of the list brings its slice out, and the other way round. */
    HG.splitCard = function (root, sets, first) {
        if (!root) return;
        const box = HG.chartBox(root.querySelector('[data-split-canvas]'));
        const list = root.querySelector('[data-split-list]');
        const desc = root.querySelector('[data-split-desc]');
        const empty = root.querySelector('[data-split-empty]');
        let chart = null;

        function render(key) {
            const set = sets[key] || { labels: [], values: [] };
            const total = set.values.reduce((a, b) => a + b, 0);
            if (desc) desc.textContent = set.desc || '';
            const hasData = total > 0;
            const holder = box.parentElement;
            holder.hidden = !hasData;
            if (empty) empty.hidden = hasData;
            if (list) list.innerHTML = hasData ? set.labels.map((l, i) => `
                <li class="hg-split-item" data-split-index="${i}">
                    <i style="background: ${PALETTE[i % PALETTE.length]};"></i>
                    <span class="hg-split-name">${HG.esc(l)}</span>
                    <span class="hg-split-value">${HG.metricText(set.metric, set.values[i])}</span>
                    <span class="hg-split-pct">${HG.fmt((set.values[i] / total) * 100, 1)} %</span>
                </li>`).join('') : '';
            if (!hasData) return;
            chart = keep(HG.draw(box, HG.donutOption({
                labels: set.labels, values: set.values, colors: PALETTE, format: v => HG.metricText(set.metric, v),
            })));
            if (list) {
                list.querySelectorAll('[data-split-index]').forEach(li => {
                    const dataIndex = Number(li.dataset.splitIndex);
                    li.addEventListener('mouseenter', () => {
                        chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex });
                        chart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex });
                    });
                    li.addEventListener('mouseleave', () => {
                        chart.dispatchAction({ type: 'downplay', seriesIndex: 0, dataIndex });
                        chart.dispatchAction({ type: 'hideTip' });
                    });
                });
                chart.off('mouseover');
                chart.off('mouseout');
                chart.on('mouseover', e => list.querySelectorAll('[data-split-index]').forEach(li => li.classList.toggle('is-hover', Number(li.dataset.splitIndex) === e.dataIndex)));
                chart.on('mouseout', () => list.querySelectorAll('.is-hover').forEach(li => li.classList.remove('is-hover')));
            }
        }

        bindToggle(root, 'data-split', render);
        render(first);
    };
})();
