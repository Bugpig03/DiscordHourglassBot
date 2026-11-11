/* Shared ECharts helpers for every Hourglass chart (loaded right after echarts.min.js).

   One look everywhere: the Arène tooltip (values sorted, colored chips, total, notes on unfinished periods),
   a dashed aiming line that follows the pointer, the hovered series in front and the others faded, a zoom
   slider under long time series (and Ctrl + wheel to zoom, drag to move once zoomed), and charts that resize
   with their box (tabs shown later, phone rotation). */
(function () {
    const HG = (window.HG = window.HG || {});
    const esc = v => (HG.esc ? HG.esc(v) : String(v ?? ''));
    const T = (fr, en, vars) => HG.tr(fr, en, vars);

    // Locale-aware number formatting, consistent with the server-side `num` Jinja filter
    HG.fmt = function (value, decimals = 0) {
        return Number(value || 0).toLocaleString(HG.locale, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    };

    // Values of the complete, measured periods only (average of the per-period charts)
    HG.measuredValues = function (values, series) {
        const end = series.partial && values.length > 1 ? values.length - 1 : values.length;
        const start = Math.min(series.estimated || 0, end);
        const measured = values.slice(start, end);
        return measured.length ? measured : values.slice(0, end);
    };

    const C = {
        text: '#e3e5e8',
        muted: '#a3a6b0',
        faint: '#6b6f78',
        grid: 'rgba(255, 255, 255, 0.06)',
        axis: 'rgba(255, 255, 255, 0.12)',
        gold: '#fbbf3c',
        panel: '#22242b',
    };
    HG.chartColors = C;
    const DISPLAY = "'Chakra Petch', sans-serif";
    const bodyFont = () => getComputedStyle(document.body).fontFamily || 'sans-serif';

    // Heat scales, from quiet to busiest: the site's violet (voice) or green (messages), dark to light
    // Saturated from the first step (no gray-black for the quiet hours), electric at the top
    HG.HEAT = {
        hours: ['#2e2a8c', '#3c33b3', '#4c3fd6', '#5e4ef0', '#7462ff', '#8f74ff', '#ae86ff', '#d39bff'],
        messages: ['#0b4d3a', '#0d6b4f', '#0f8a63', '#13a877', '#1fc78b', '#3fe0a0', '#6ef0bb', '#a8fcd8'],
    };
    // Position of v between the smallest and the largest non-zero value: the scale spans the real spread
    HG.heatColor = function (metric, v, lo, hi) {
        const scale = HG.HEAT[metric] || HG.HEAT.hours;
        if (!(v > 0)) return 'rgba(255, 255, 255, 0.06)';
        const r = hi > lo ? (v - lo) / (hi - lo) : 1;
        return scale[Math.max(0, Math.min(scale.length - 1, Math.floor(r * scale.length - 1e-9)))];
    };

    /* Shares and rankings (doughnuts, leaderboard race): the Arène colors of the site (blurple, mint, amethyst, gold,
       coral…), toned down a little so they stay calm next to each other; the last one, gray, is for "others" */
    HG.RANK_COLORS = ['#717cf8', '#3bb38c', '#9d7ae0', '#d9a043', '#e0675d', '#4aa3cf', '#c76b9f', '#8fae4c', '#d9814a', '#3fa89a', '#6b6f78'];

    HG.rgba = function (hex, alpha) {
        const h = String(hex).replace('#', '');
        if (!/^[0-9a-f]{6}$/i.test(h)) return hex;
        const n = parseInt(h, 16);
        return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
    };

    // Vertical fill under a line: the color at the top fading out at the bottom
    HG.areaFill = function (color, top = 0.4, bottom = 0.02) {
        return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: HG.rgba(color, top) },
            { offset: 1, color: HG.rgba(color, bottom) },
        ]);
    };

    /* ----------------------------------------------------------------------
       Instances: a <canvas> left by the templates becomes a <div> (ECharts draws in its own canvas), one
       instance per element, resized whenever its box changes size.
       ---------------------------------------------------------------------- */
    HG.allCharts = HG.allCharts || [];

    HG.chartBox = function (target) {
        let el = typeof target === 'string' ? document.getElementById(target) : target;
        if (!el) return null;
        if (el.tagName === 'CANVAS') {
            const div = document.createElement('div');
            for (const a of Array.from(el.attributes)) {
                if (a.name === 'id' || a.name.startsWith('data-') || a.name.startsWith('aria-')) div.setAttribute(a.name, a.value);
            }
            div.className = ((el.getAttribute('class') || '') + ' hg-ec').trim();
            div.hidden = el.hidden;
            div.style.width = '100%';
            div.style.height = '100%';
            el.replaceWith(div);
            el = div;
        }
        return el;
    };

    HG.chart = function (target) {
        const el = HG.chartBox(target);
        if (!el) return null;
        let chart = echarts.getInstanceByDom(el);
        if (!chart) {
            chart = echarts.init(el, null, { renderer: 'canvas' });
            if (window.ResizeObserver) {
                let frame = 0;
                new ResizeObserver(() => {
                    cancelAnimationFrame(frame);
                    frame = requestAnimationFrame(() => { if (!chart.isDisposed()) chart.resize(); });
                }).observe(el);
            }
            HG.allCharts.push(chart);
        }
        return chart;
    };

    /* ----------------------------------------------------------------------
       Arène shapes (the site's style: square, corners cut on the slant)
       - vertical bars become square columns with the top right corner cut, like the cards and buttons;
       - points of the curves are diamonds rather than dots.
       Stacked bars and the horizontal race bars stay plain squares.
       ---------------------------------------------------------------------- */
    const CUT = 7;

    function cutBarSeries(s, index, count) {
        const maxWidth = s.barMaxWidth || 34;
        const data = (s.data || []).map((d, i) => (d && typeof d === 'object' && !Array.isArray(d)
            ? Object.assign({}, d, { value: [i, d.value] })
            : { value: [i, d] }));
        const hover = s.emphasis && s.emphasis.itemStyle && s.emphasis.itemStyle.color;
        return {
            type: 'custom',
            name: s.name,
            id: s.id,
            yAxisIndex: s.yAxisIndex || 0,
            xAxisIndex: s.xAxisIndex || 0,
            data,
            encode: { x: 0, y: 1, tooltip: 1 },
            itemStyle: Object.assign({}, s.itemStyle, { borderRadius: 0 }),
            markLine: s.markLine,
            tooltip: s.tooltip,
            z: s.z,
            clip: true,
            renderItem(params, api) {
                const v = api.value(1);
                if (v == null || isNaN(v) || v <= 0) return null;
                const base = api.coord([api.value(0), 0]);
                const top = api.coord([api.value(0), v]);
                const band = api.size([1, 0])[0];
                const gap = count > 1 ? 4 : 0;
                const width = Math.max(2, Math.min(maxWidth, (band * 0.72 - gap * (count - 1)) / count));
                const center = base[0] + (index - (count - 1) / 2) * (width + gap);
                const left = center - width / 2, right = center + width / 2;
                const bottom = base[1], high = Math.min(top[1], bottom);
                const cut = Math.min(CUT, width * 0.45, bottom - high);
                const style = api.style();
                return {
                    type: 'polygon',
                    shape: { points: [[left, bottom], [left, high], [right - cut, high], [right, high + cut], [right, bottom]] },
                    style,
                    emphasis: { style: hover ? { fill: hover } : { shadowBlur: 14, shadowColor: 'rgba(255, 255, 255, 0.25)' } },
                };
            },
        };
    }

    function areneShapes(option) {
        const series = option.series;
        if (!Array.isArray(series)) return option;
        const isVertical = !option.yAxis || (Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis).type !== 'category';
        const plain = series.filter(s => s && s.type === 'bar' && !s.stack && !s.realtimeSort && isVertical);
        option.series = series.map(s => {
            if (!s) return s;
            if (s.type === 'bar') {
                if (plain.includes(s)) return cutBarSeries(s, plain.indexOf(s), plain.length);
                return Object.assign({}, s, { itemStyle: Object.assign({}, s.itemStyle, { borderRadius: 0 }) });
            }
            if (s.type === 'line' && !s.symbol) return Object.assign({ symbol: 'diamond' }, s, { symbolSize: (s.symbolSize || 7) + 2 });
            return s;
        });
        return option;
    }

    // Draw (or redraw from scratch) a chart: the shared look is added to the page's option
    HG.draw = function (target, option) {
        const chart = target && typeof target.setOption === 'function' ? target : HG.chart(target);
        if (!chart) return null;
        option = areneShapes(option);
        chart.setOption(Object.assign({
            animationDuration: 500,
            animationEasing: 'cubicOut',
            // A chart with a zoom slider redraws at every move of the handles: animating each redraw made the curves
            // lag behind the slider and jump around (the first drawing keeps its animation)
            animationDurationUpdate: option.dataZoom && option.dataZoom.length ? 0 : 300,
            textStyle: { fontFamily: bodyFont(), color: C.muted },
        }, option), true);
        return chart;
    };

    /* ----------------------------------------------------------------------
       Axes, grid, legend, zoom
       ---------------------------------------------------------------------- */
    HG.grid = function (extra) {
        return Object.assign({ left: 8, right: 14, top: 24, bottom: 8, containLabel: true }, extra);
    };

    HG.categoryAxis = function (labels, extra) {
        return Object.assign({
            type: 'category',
            data: labels,
            boundaryGap: true,
            axisLine: { lineStyle: { color: C.axis } },
            axisTick: { show: false },
            axisLabel: { color: C.muted, hideOverlap: true },
            splitLine: { show: false },
        }, extra);
    };

    HG.valueAxis = function (extra) {
        const axis = Object.assign({
            type: 'value',
            min: 0,
            axisLabel: { color: C.muted, formatter: v => HG.fmt(v) },
            splitLine: { lineStyle: { color: C.grid } },
            axisLine: { show: false },
            splitNumber: 5,
        }, extra);
        if (extra && extra.axisLabel) axis.axisLabel = Object.assign({ color: C.muted, formatter: v => HG.fmt(v) }, extra.axisLabel);
        return axis;
    };

    /* Lower bound of a value axis fitted to what is shown (zoomed period included): a little under the lowest visible
       value, never below zero. For curves; bars keep their zero base. */
    HG.fitMin = function (value) {
        const span = value.max - value.min;
        if (!(value.min > 0) || !(span > 0)) return 0;
        const lowered = value.min - span * 0.12;
        if (lowered <= 0) return 0;
        const step = Math.pow(10, Math.floor(Math.log10(lowered)));
        return Math.floor(lowered / step) * step;
    };

    // Time axis: "21h" within a day, the date at midnight (ECharts puts its ticks on round hours and days)
    HG.timeAxis = function (extra) {
        return Object.assign({
            type: 'time',
            boundaryGap: false,
            axisLine: { lineStyle: { color: C.axis } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: {
                color: C.muted,
                hideOverlap: true,
                formatter: v => {
                    const d = new Date(v);
                    if (d.getHours() === 0 && d.getMinutes() === 0) {
                        return `{day|${d.toLocaleDateString(HG.locale, { weekday: 'short', day: 'numeric' })}}`;
                    }
                    return HG.lang === 'fr' ? `${d.getHours()}h${d.getMinutes() ? String(d.getMinutes()).padStart(2, '0') : ''}`
                        : d.toLocaleTimeString(HG.locale, { hour: 'numeric', minute: d.getMinutes() ? '2-digit' : undefined });
                },
                rich: { day: { color: C.text, fontWeight: 600 } },
            },
        }, extra);
    };

    HG.legend = function (extra) {
        // One line, scrolled with arrows when it does not fit (phones), so it never runs into the chart
        return Object.assign({
            type: 'scroll',
            pageIconColor: C.text,
            pageIconInactiveColor: '#55585f',
            pageIconSize: 10,
            pageTextStyle: { color: C.muted },
            top: 0,
            left: 0,
            icon: 'path://M3,0 L12,0 L9,10 L0,10 Z',
            itemWidth: 12,
            itemHeight: 10,
            itemGap: 14,
            textStyle: { color: C.text, fontFamily: bodyFont(), fontSize: 12 },
            inactiveColor: '#55585f',
        }, extra);
    };

    /* Zoom for long series: a slider under the chart showing the whole curve; its handles pick the period and
       dragging its middle moves it. No zoom on the chart itself: it took the mouse wheel (the page stopped
       scrolling over the chart) and, on phones, the finger. Returns { dataZoom, bottom } (room left for the slider). */
    HG.zoom = function (count, opts = {}) {
        if (count < (opts.min || 40)) return { dataZoom: [], bottom: 8 };
        const fmt = opts.label || (v => (typeof v === 'number' ? new Date(v).toLocaleString(HG.locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : v));
        return {
            bottom: 44,
            dataZoom: [
                { type: 'slider', filterMode: 'filter', height: 20, bottom: 6, borderColor: 'transparent', backgroundColor: C.panel,
                    fillerColor: 'rgba(113, 124, 248, 0.18)', showDetail: !opts.compact,
                    dataBackground: { lineStyle: { color: '#8b80ea', opacity: 0.5 }, areaStyle: { color: 'rgba(139, 128, 234, 0.15)' } },
                    selectedDataBackground: { lineStyle: { color: '#8b80ea' }, areaStyle: { color: 'rgba(139, 128, 234, 0.3)' } },
                    handleIcon: 'path://M3,0 L10,0 L7,24 L0,24 Z', handleSize: '100%',
                    handleStyle: { color: '#717cf8', borderColor: '#717cf8' }, moveHandleStyle: { color: '#717cf8' },
                    emphasis: { handleStyle: { color: '#b1a8f5' } },
                    textStyle: { color: C.muted, fontSize: 11 }, labelFormatter: v => fmt(v), brushSelect: false,
                    minValueSpan: opts.minSpan },
            ],
        };
    };

    /* ----------------------------------------------------------------------
       Tooltip: one Arène look; tipHtml builds its content
       ---------------------------------------------------------------------- */
    HG.tooltip = function (extra) {
        return Object.assign({
            trigger: 'axis',
            confine: true,
            enterable: false,
            transitionDuration: 0.15,
            backgroundColor: 'rgba(20, 21, 26, 0.97)',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            padding: [10, 12],
            textStyle: { color: C.text, fontFamily: bodyFont(), fontSize: 12.5 },
            extraCssText: 'box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45); border-radius: 0; min-width: 170px; '
                + 'clip-path: polygon(9px 0, 100% 0, 100% calc(100% - 9px), calc(100% - 9px) 100%, 0 100%, 0 9px);',
            axisPointer: { type: 'line', lineStyle: { color: 'rgba(255, 255, 255, 0.35)', type: 'dashed' } },
        }, extra);
    };

    // Bars: a soft band behind the hovered category rather than a line
    HG.barPointer = { type: 'shadow', shadowStyle: { color: 'rgba(255, 255, 255, 0.04)' } };

    /* rows: [{color, name, value (text), pct?, big?, dim?}]; opts: {total (text), notes: [text]} */
    HG.tipHtml = function (title, rows, opts = {}) {
        const big = rows.length === 1 && rows[0].big !== false;
        let html = title ? `<div style="font:700 11.5px ${DISPLAY};letter-spacing:.06em;text-transform:uppercase;color:${C.muted};margin-bottom:6px">${esc(title)}</div>` : '';
        html += rows.map(r => big
            ? `<div style="display:flex;align-items:baseline;gap:8px"><i style="width:10px;height:9px;background:${r.color};align-self:center;transform:skewX(-14deg)"></i>`
              + `<span style="font:700 22px ${DISPLAY};color:#fff">${esc(r.value)}</span><span style="color:${C.muted}">${esc(r.name)}</span></div>`
            : `<div style="display:flex;align-items:center;gap:8px;padding:2px 0;${r.dim ? 'opacity:.55;' : ''}">`
              + `<i style="width:10px;height:9px;flex:none;background:${r.color};transform:skewX(-14deg)"></i>`
              + `<span style="color:#c9ccd3;max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.name)}</span>`
              + `<b style="margin-left:auto;padding-left:14px;font:600 13px ${DISPLAY};color:#fff">${esc(r.value)}</b>`
              + (r.pct != null ? `<span style="color:${C.muted};font-size:11px;width:40px;text-align:right">${esc(r.pct)}</span>` : '')
              + '</div>').join('');
        if (opts.sub) html += `<div style="margin-top:4px;color:${C.muted};font-size:11.5px">${esc(opts.sub)}</div>`;
        if (opts.total != null) {
            html += `<div style="display:flex;border-top:1px solid rgba(255,255,255,.08);margin-top:6px;padding-top:6px;color:#c9ccd3">`
                + `${esc(T('Total', 'Total'))}<b style="margin-left:auto;font:600 13px ${DISPLAY};color:#fff">${esc(opts.total)}</b>`
                + (opts.pctColumn ? '<span style="width:40px"></span>' : '') + '</div>';
        }
        (opts.notes || []).filter(Boolean).forEach(n => {
            html += `<div style="margin-top:6px;color:#fbbf24;font-size:11.5px;max-width:240px;white-space:normal">${esc(n)}</div>`;
        });
        return html;
    };

    // Rows of an axis tooltip, highest first (series of a stack read best that way)
    HG.sortedRows = function (params, format) {
        return params
            .filter(p => p.value != null && !(Array.isArray(p.value) && p.value[1] == null) && !p.seriesId?.startsWith('hg-hidden'))
            .map(p => ({ color: p.color && p.color.colorStops ? p.color.colorStops[0].color : p.color, name: p.seriesName, raw: Array.isArray(p.value) ? p.value[1] : p.value, p }))
            .sort((a, b) => b.raw - a.raw)
            .map(r => ({ color: r.color, name: r.name, value: format(r.raw, r.p), raw: r.raw }));
    };

    /* ----------------------------------------------------------------------
       Unfinished and estimated periods
       - the last bar of a running month / today: faded with a dashed outline;
       - estimated months (before October 2024 the old bot only kept totals): faded and hatched.
       ---------------------------------------------------------------------- */
    HG.periodBars = function (values, color, series = {}) {
        const last = values.length - 1;
        const estimated = series.estimated || 0;
        return values.map((v, i) => {
            if (series.partial && i === last) {
                return { value: v, itemStyle: { color: HG.rgba(color, 0.3), borderColor: color, borderWidth: 1.5, borderType: 'dashed' } };
            }
            if (i < estimated) {
                return { value: v, itemStyle: { color: HG.rgba(color, 0.35), borderColor: HG.rgba(color, 0.6), borderWidth: 1,
                    decal: { symbol: 'rect', symbolSize: 1, dashArrayX: [1, 0], dashArrayY: [2, 5], rotation: Math.PI / 4, color: HG.rgba(color, 0.35) } } };
            }
            return v;
        });
    };

    HG.periodNote = function (series, index, total) {
        if (index < (series.estimated || 0)) return T('Estimation : avant octobre 2024, le bot ne gardait que les totaux', 'Estimate: before October 2024, the bot only kept totals');
        if (!series.partial || index !== total - 1) return '';
        return series.partial === 'month'
            ? T('Mois en cours : données partielles', 'Current month: data still coming in')
            : T('Aujourd’hui : journée en cours', 'Today: day still in progress');
    };

    /* ----------------------------------------------------------------------
       Shared charts
       ---------------------------------------------------------------------- */
    const metricText = (metric, v) => (metric === 'hours' ? `${HG.fmt(v, 1)} h` : T('{n} messages', '{n} messages', { n: HG.fmt(v) }));
    HG.metricText = metricText;

    /* Activity over time (Analytics page and profiles).
       series: {labels, partial?, estimated?}; values: numbers; mode 'period' (bars + average) or 'cumul' (area) */
    HG.trendOption = function ({ labels, values, series = {}, metric, cumul, color, perLabel }) {
        const zoom = HG.zoom(labels.length, { min: 40, compact: true, label: v => v });
        const axisY = HG.valueAxis({ axisLabel: { formatter: v => (metric === 'hours' ? `${HG.fmt(v)} h` : HG.fmt(v)) } });
        const base = {
            grid: HG.grid({ top: 28, bottom: zoom.bottom }),
            xAxis: HG.categoryAxis(labels, { boundaryGap: !cumul }),
            yAxis: axisY,
            dataZoom: zoom.dataZoom,
        };
        if (cumul) {
            return Object.assign(base, {
                tooltip: HG.tooltip({ formatter: ps => HG.tipHtml(ps[0].name, [{ color, name: T('au total', 'in total'), value: metricText(metric, ps[0].value) }]) }),
                series: [{
                    type: 'line', name: T('Total cumulé', 'Running total'), data: values, smooth: 0.3, showSymbol: false, symbolSize: 7,
                    lineStyle: { width: 2.5, color }, itemStyle: { color }, areaStyle: { color: HG.areaFill(color, 0.35) },
                }],
            });
        }
        const complete = HG.measuredValues(values, series);
        const avg = complete.reduce((a, b) => a + b, 0) / Math.max(1, complete.length);
        return Object.assign(base, {
            tooltip: HG.tooltip({
                axisPointer: HG.barPointer,
                formatter: ps => {
                    const p = ps[0];
                    const value = values[p.dataIndex] || 0;
                    const delta = avg ? (value - avg) / avg * 100 : 0;
                    const vs = avg ? `${delta >= 0 ? '+' : ''}${HG.fmt(delta, Math.abs(delta) < 10 ? 1 : 0)} % ${T('vs moyenne', 'vs average')}` : null;
                    return HG.tipHtml(p.axisValueLabel || p.name, [
                        { color, name: metric === 'hours' ? T('en vocal', 'in voice') : '', value: metricText(metric, value) },
                    ], { notes: [HG.periodNote(series, p.dataIndex, values.length)], sub: vs });
                },
            }),
            series: [{
                type: 'bar', name: metric === 'hours' ? T('Heures en vocal', 'Voice hours') : T('Messages', 'Messages'),
                data: HG.periodBars(values, color, series), barMaxWidth: 34, itemStyle: { color },
                emphasis: { itemStyle: { color: HG.rgba(color, 0.85) } },
                markLine: avg ? {
                    silent: true, symbol: 'none',
                    lineStyle: { color: '#fbbf24', type: 'dashed', width: 1.5 },
                    label: { position: 'insideStartTop', color: '#fbbf24', fontFamily: DISPLAY, fontWeight: 700,
                        backgroundColor: 'rgba(20, 21, 26, 0.85)', padding: [2, 6],
                        formatter: () => `${T('Moyenne', 'Average')} ${metricText(metric, avg)}${perLabel ? ' / ' + perLabel : ''}` },
                    data: [{ yAxis: Math.round(avg * 10) / 10 }],
                } : undefined,
            }],
        });
    };

    /* Average activity per hour of the day: bars in the heat scale, the busiest hour outlined */
    HG.hourlyOption = function (values, metric) {
        const isVoice = metric === 'hours';
        const max = Math.max(0, ...values);
        const nonZero = values.filter(v => v > 0);
        const lo = nonZero.length ? Math.min(...nonZero) : 0;
        const peak = max > 0 ? values.indexOf(max) : -1;
        const hourLabel = h => (HG.lang === 'fr' ? `${h}h` : `${h}:00`);
        return {
            grid: HG.grid({ top: 16 }),
            xAxis: HG.categoryAxis(values.map((_, h) => hourLabel(h))),
            yAxis: HG.valueAxis({ splitNumber: 4, axisLabel: { formatter: v => HG.fmt(v, Number.isInteger(v) ? 0 : 1) } }),
            tooltip: HG.tooltip({
                axisPointer: HG.barPointer,
                formatter: ps => {
                    const i = ps[0].dataIndex, v = values[i];
                    const pctOfPeak = max ? Math.round(v / max * 100) : 0;
                    return HG.tipHtml(`${hourLabel(i)} – ${hourLabel((i + 1) % 24)}`, [{
                        color: HG.heatColor(metric, v, lo, max),
                        name: isVoice ? T('membre(s) en vocal en moyenne', 'member(s) in voice on average') : T('messages en moyenne', 'messages on average'),
                        value: HG.fmt(v, 1),
                    }], { sub: i === peak ? T('Heure de pointe', 'Peak hour') : (max ? T('{n} % du pic', '{n} % of the peak', { n: pctOfPeak }) : null) });
                },
            }),
            series: [{
                type: 'bar', barCategoryGap: '22%',
                data: values.map((v, i) => ({
                    value: v,
                    itemStyle: { color: HG.heatColor(metric, v, lo, max),
                        borderColor: i === peak ? '#ffffff' : 'transparent', borderWidth: i === peak ? 1.5 : 0 },
                })),
                emphasis: { itemStyle: { shadowBlur: 12, shadowColor: 'rgba(139, 128, 234, 0.5)' } },
            }],
        };
    };

    /* Doughnut: values with their share; hovering a slice brings it out */
    HG.donutOption = function ({ labels, values, colors, format, legend }) {
        const total = values.reduce((a, b) => a + b, 0);
        return {
            tooltip: HG.tooltip({
                trigger: 'item',
                axisPointer: undefined,
                formatter: p => HG.tipHtml(p.name, [{ color: p.color, name: `${HG.fmt(total ? p.value / total * 100 : 0, 1)} %`, value: format(p.value) }]),
            }),
            legend: legend ? HG.legend(legend) : undefined,
            series: [{
                type: 'pie',
                radius: ['56%', '82%'],
                center: legend && legend.orient === 'vertical' ? ['32%', '50%'] : ['50%', legend ? '45%' : '50%'],
                avoidLabelOverlap: true,
                padAngle: 1.5,
                itemStyle: { borderColor: '#1b1c21', borderWidth: 2 },
                label: { show: false },
                labelLine: { show: false },
                emphasis: {
                    scale: true, scaleSize: 8,
                    label: { show: true, position: 'center', color: '#fff', fontFamily: DISPLAY, fontWeight: 700, fontSize: 15, lineHeight: 20,
                        formatter: p => `${HG.fmt(total ? p.value / total * 100 : 0, 1)} %\n{n|${String(p.name).slice(0, 18)}}`,
                        rich: { n: { color: C.muted, fontSize: 11, fontFamily: bodyFont(), fontWeight: 400 } } },
                },
                data: labels.map((l, i) => ({ name: l, value: values[i], itemStyle: { color: colors[i % colors.length] } })),
            }],
        };
    };

    /* ----------------------------------------------------------------------
       Charts over the same timeline move together: hovering one shows the same moment on the others, and
       zooming one zooms the others. Each chart must draw [time, value] points on a time axis.
       ---------------------------------------------------------------------- */
    function nearestIndex(chart, t) {
        const data = ((chart.getOption().series || [])[0] || {}).data || [];
        if (!data.length || !Array.isArray(data[0])) return -1;
        let lo = 0, hi = data.length - 1;
        if (t < data[0][0] - 3600e3 || t > data[hi][0] + 3600e3) return -1;
        while (hi - lo > 1) {
            const mid = (lo + hi) >> 1;
            if (data[mid][0] <= t) lo = mid; else hi = mid;
        }
        return Math.abs(data[lo][0] - t) <= Math.abs(data[hi][0] - t) ? lo : hi;
    }

    HG.syncTime = function (list) {
        const charts = list.filter(c => c && !c.isDisposed());
        if (charts.length < 2) return;
        let busy = false;
        charts.forEach(src => {
            src.off('updateAxisPointer');
            src.off('globalout');
            src.off('datazoom');
            src.on('updateAxisPointer', e => {
                const info = e.axesInfo && e.axesInfo[0];
                if (busy || !info || typeof info.value !== 'number') return;
                busy = true;
                charts.forEach(dst => {
                    if (dst === src) return;
                    const i = nearestIndex(dst, info.value);
                    dst.dispatchAction(i >= 0 ? { type: 'showTip', seriesIndex: 0, dataIndex: i } : { type: 'hideTip' });
                });
                busy = false;
            });
            src.on('globalout', () => {
                if (busy) return;
                charts.forEach(dst => dst !== src && dst.dispatchAction({ type: 'hideTip' }));
            });
            src.on('datazoom', () => {
                if (busy) return;
                const axis = src.getModel().getComponent('xAxis', 0).axis;
                const [startValue, endValue] = axis.scale.getExtent();
                busy = true;
                charts.forEach(dst => dst !== src && dst.dispatchAction({ type: 'dataZoom', startValue, endValue }));
                busy = false;
            });
        });
    };

    /* ----------------------------------------------------------------------
       Day x hour heat map. The color bar on the right filters: drag its handles to keep only the busy slots.
       days: [{day_name, day_index, hours: [{hour, voice_hours, messages}]}]
       ---------------------------------------------------------------------- */
    HG.punchOption = function (days, metric) {
        const isVoice = metric === 'hours';
        const val = c => (isVoice ? c.voice_hours : c.messages) || 0;
        const names = days.map(r => (HG.lang === 'fr' ? r.day_name : HG.weekday(r.day_index)));
        const data = [];
        days.forEach((r, d) => (r.hours || []).forEach(c => data.push([c.hour, d, val(c)])));
        const nonZero = data.map(x => x[2]).filter(v => v > 0);
        const lo = nonZero.length ? Math.min(...nonZero) : 0;
        const hi = nonZero.length ? Math.max(...nonZero) : 1;
        return {
            animationDuration: 600,
            grid: { left: 4, right: 8, top: 10, bottom: 4, containLabel: true },
            tooltip: HG.tooltip({
                trigger: 'item',
                axisPointer: undefined,
                formatter: p => {
                    const [h, d, v] = p.value;
                    const hour = x => (HG.lang === 'fr' ? `${x}h` : `${x}:00`);
                    return HG.tipHtml(`${names[d]} · ${hour(h)} – ${hour((h + 1) % 24)}`, [{
                        color: v > 0 ? p.color : '#3a3d46',
                        name: isVoice ? T('de vocal au total', 'of voice in total') : T('messages au total', 'messages in total'),
                        value: isVoice ? `${HG.fmt(v, 1)} h` : HG.fmt(v),
                    }], { sub: v > 0 && hi ? T('{n} % du créneau le plus actif', '{n} % of the busiest slot', { n: Math.round(v / hi * 100) }) : null });
                },
            }),
            xAxis: {
                type: 'category', data: Array.from({ length: 24 }, (_, h) => (h < 10 ? '0' + h : h) + 'h'), position: 'top',
                splitArea: { show: false }, axisLine: { show: false }, axisTick: { show: false },
                axisLabel: { color: C.muted, interval: 2, fontSize: 11, fontWeight: 600 },
            },
            yAxis: {
                type: 'category', data: names, inverse: true, axisLine: { show: false }, axisTick: { show: false },
                axisLabel: { color: C.muted, fontWeight: 600, fontSize: 12 },
            },
            visualMap: {
                // Drawn by HG.punchFilter in HTML (a slider in the site's style): hidden here
                type: 'continuous', min: lo, max: hi, show: false,
                inRange: { color: HG.HEAT[metric] || HG.HEAT.hours },
                outOfRange: { color: 'rgba(255, 255, 255, 0.04)' },
            },
            series: [{
                type: 'heatmap', data,
                itemStyle: { borderColor: '#1b1c21', borderWidth: 3 },
                emphasis: { itemStyle: { borderColor: '#ffffff', borderWidth: 1.5 } },
            }],
        };
    };

    /* The color bar of a heat map, drawn in HTML above the grid (its handles filter the slots); returns the element */
    HG.punchFilter = function (chart, holder, metric) {
        let bar = holder.querySelector('.hg-heat-filter');
        if (!bar) {
            bar = document.createElement('div');
            bar.className = 'hg-heat-filter';
            bar.innerHTML = `<span>${esc(T('Calme', 'Quiet'))}</span><div class="hg-heat-range"><i class="hg-heat-bar"></i>`
                + '<input type="range" min="0" max="100" value="0" step="1" aria-label="' + esc(T('Afficher les créneaux à partir de', 'Show slots from')) + '">'
                + `</div><span>${esc(T('Très actif', 'Busiest'))}</span><output></output>`;
            holder.append(bar);
        }
        const scale = HG.HEAT[metric] || HG.HEAT.hours;
        bar.querySelector('.hg-heat-bar').style.background = `linear-gradient(90deg, ${scale.join(', ')})`;
        const input = bar.querySelector('input');
        const out = bar.querySelector('output');
        const vm = chart.getOption().visualMap[0];
        const apply = () => {
            const pct = Number(input.value);
            const from = vm.min + (vm.max - vm.min) * pct / 100;
            chart.dispatchAction({ type: 'selectDataRange', selected: [from, vm.max] });
            out.textContent = pct ? T('à partir de {n} % du pic', 'from {n} % of the peak', { n: pct }) : '';
        };
        input.value = 0;
        input.oninput = apply;
        apply();
        return bar;
    };

    /* ----------------------------------------------------------------------
       Leaderboard race: the 10 best members by cumulative voice hours, one month per step. It starts on its own
       the first time the card is seen (final standings straight away for visitors who prefer less motion); the
       button pauses, resumes or replays it, and the slider under it picks a month.
       card: [data-race-canvas], [data-race-month], [data-race-play], [data-race-seek]; race: {members, frames}
       ---------------------------------------------------------------------- */
    const ICON = {
        play: '<path d="M2 0h2v9h-2zM4 1h1v7h-1zM5 2h1v5h-1zM6 3h1v3h-1zM7 4h1v1h-1z"/>',
        pause: '<path d="M1 1h3v7h-3zM5 1h3v7h-3z"/>',
        replay: '<path d="M3 0h3v1h-3zM1 1h2v1h-2zM6 1h1v1h-1zM8 1h1v1h-1zM1 2h1v1h-1zM7 2h2v1h-2zM0 3h1v1h-1zM6 3h3v1h-3zM0 4h1v1h-1zM0 5h1v1h-1zM8 5h1v1h-1zM1 6h1v1h-1zM7 6h1v1h-1zM1 7h2v1h-2zM6 7h2v1h-2zM3 8h3v1h-3z"/>',
    };
    const pixelIcon = name => `<svg width="13" height="13" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" aria-hidden="true">${ICON[name]}</svg>`;

    HG.memberRace = function (card, race, palette) {
        if (!card || !race || !race.frames || race.frames.length < 2) {
            if (card) card.hidden = true;
            return null;
        }
        card.hidden = false;
        const box = HG.chartBox(card.querySelector('[data-race-canvas]'));
        const monthEl = card.querySelector('[data-race-month]');
        const playBtn = card.querySelector('[data-race-play]');
        const seek = card.querySelector('[data-race-seek]');
        const STEP_MS = 1100;
        const last = race.frames.length - 1;
        const names = race.members.map((m, i) => `${i}`);  // one category per member (two members may share a name)
        const shortName = n => (n.length > 16 ? n.slice(0, 15) + '…' : n);
        const rich = { name: { color: '#e3e5e8', fontWeight: 600, fontSize: 12, padding: [0, 0, 0, 6] } };
        race.members.forEach((m, i) => {
            if (m.avatar) rich['a' + i] = { width: 22, height: 22, borderRadius: 11, backgroundColor: { image: m.avatar.split('?')[0] + '?size=64' } };
        });
        const chart = HG.chart(box);
        let frame = 0, timer = null;

        // Each member keeps one color for the whole race (easy to follow when they overtake someone)
        const colors = (palette || HG.RANK_COLORS).slice(0, -1);
        const seriesData = i => race.frames[i].values.map((v, k) => ({
            value: v, name: race.members[k].name,
            itemStyle: { color: colors[k % colors.length] },
        }));
        const monthMark = i => [{
            type: 'text', right: 24, bottom: 28, z: 0, silent: true,
            style: { text: race.frames[i].label, font: "italic 700 40px 'Chakra Petch', sans-serif", fill: 'rgba(255, 255, 255, 0.13)' },
        }];

        HG.draw(chart, {
            animationDuration: 0,
            animationDurationUpdate: STEP_MS - 100,
            animationEasing: 'linear',
            animationEasingUpdate: 'linear',
            grid: { left: 8, right: 76, top: 8, bottom: 8, containLabel: true },
            xAxis: { type: 'value', max: 'dataMax', splitNumber: 4, axisLabel: { color: C.muted, formatter: v => `${HG.fmt(v)} h` },
                splitLine: { lineStyle: { color: C.grid } } },
            yAxis: {
                type: 'category', data: names, inverse: true, max: 9,
                animationDuration: 300, animationDurationUpdate: 300,
                axisLine: { show: false }, axisTick: { show: false },
                axisLabel: { formatter: v => (rich['a' + v] ? `{a${v}|}` : '') + `{name|${shortName(race.members[Number(v)].name)}}`, rich },
            },
            tooltip: HG.tooltip({
                trigger: 'item', axisPointer: undefined,
                formatter: p => HG.tipHtml(race.frames[frame].label, [{ color: p.color, name: p.name, value: `${HG.fmt(p.value, 1)} h` }]),
            }),
            series: [{
                type: 'bar', realtimeSort: true, barCategoryGap: '26%', data: seriesData(0),
                label: { show: true, position: 'right', valueAnimation: true, color: '#fff', fontFamily: DISPLAY, fontWeight: 700,
                    formatter: p => `${HG.fmt(p.value, 1)} h` },
            }],
            graphic: monthMark(0),
        });

        seek.max = String(last);
        function show(i) {
            frame = i;
            seek.value = String(i);
            seek.style.setProperty('--seek', `${last ? (i / last) * 100 : 0}%`);
            monthEl.textContent = race.frames[i].label;
            chart.setOption({ series: [{ data: seriesData(i) }], graphic: monthMark(i) });
        }
        function setButton() {
            const state = timer ? 'pause' : frame >= last ? 'replay' : 'play';
            const label = { pause: T('Pause', 'Pause'), replay: T('Rejouer', 'Replay'), play: T('Lecture', 'Play') }[state];
            playBtn.innerHTML = `${pixelIcon(state)}<span>${esc(label)}</span>`;
            playBtn.setAttribute('aria-label', label);
            playBtn.classList.toggle('is-playing', !!timer);
        }
        function stop() { clearInterval(timer); timer = null; setButton(); }
        function play() {
            if (frame >= last) show(0);
            timer = setInterval(() => {
                if (frame >= last) return stop();
                show(frame + 1);
            }, STEP_MS);
            setButton();
        }
        playBtn.onclick = () => (timer ? stop() : play());
        seek.oninput = () => { stop(); show(Number(seek.value)); };

        const calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        show(calm ? last : 0);
        setButton();
        if (!calm && 'IntersectionObserver' in window) {
            const seen = new IntersectionObserver(entries => {
                if (entries.some(e => e.isIntersecting)) {
                    seen.disconnect();
                    if (!timer && frame === 0) play();
                }
            }, { threshold: 0.4 });
            seen.observe(card);
        }
        return chart;
    };
})();
