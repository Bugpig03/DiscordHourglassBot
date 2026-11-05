/* Shared Chart.js helpers for Hourglass pages (loaded right after chart.js). */
(function () {
    const HG = (window.HG = window.HG || {});

    // Locale-aware number formatting, consistent with the server-side `num` Jinja filter
    HG.fmt = function (value, decimals = 0) {
        return Number(value || 0).toLocaleString(HG.locale, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    };

    /* ----------------------------------------------------------------------
       Dense time series (30 days, 30+ months, 24 hours): keep ~8 horizontal
       labels instead of every rotated date, and show points only on hover.
       ---------------------------------------------------------------------- */
    const DENSE_THRESHOLD = 14;
    Chart.register({
        id: 'hgDenseSeries',
        beforeInit(chart) {
            const cfg = chart.config;
            const labels = (cfg.data && cfg.data.labels) || [];
            const x = cfg.options && cfg.options.scales && cfg.options.scales.x;
            // A chart that sets ticks.autoSkip: false picks its own labels (e.g. one per day on 7 days of hours)
            if (!x || labels.length <= DENSE_THRESHOLD || (x.ticks && x.ticks.autoSkip === false)) return;

            x.ticks = Object.assign({}, x.ticks, { autoSkip: true, maxTicksLimit: 8, maxRotation: 0, minRotation: 0 });
            (cfg.data.datasets || []).forEach((ds) => {
                const type = ds.type || cfg.type;
                if (type === 'line') {
                    ds.pointRadius = 0;
                    ds.pointHoverRadius = ds.pointHoverRadius || 5;
                    ds.pointHitRadius = 12;
                }
            });
        },
    });

    /* ----------------------------------------------------------------------
       Current (unfinished) period: the last month / today is drawn faded or
       dashed so it never reads as a sudden drop next to complete periods.
       A chart opts in with HG.setPartial(chart, 'month' | 'day' | null).
       ---------------------------------------------------------------------- */
    HG.setPartial = function (chart, kind) {
        chart.$hgPartial = kind || null;
    };

    function isPartialIndex(chart, index) {
        return !!chart.$hgPartial && index === chart.data.labels.length - 1;
    }

    /* Estimated months: before October 2024 the old bot only kept totals, spread over the months they
       cover. The first n bars are drawn hatched-faded. A chart opts in with HG.setEstimated(chart, n). */
    HG.setEstimated = function (chart, count) {
        chart.$hgEstimated = count || 0;
    };

    function isEstimatedIndex(chart, index) {
        return index < (chart.$hgEstimated || 0);
    }

    // Values of the complete, measured periods only (average of the per-period charts)
    HG.measuredValues = function (values, series) {
        const end = series.partial && values.length > 1 ? values.length - 1 : values.length;
        const start = Math.min(series.estimated || 0, end);
        const measured = values.slice(start, end);
        return measured.length ? measured : values.slice(0, end);
    };

    function fade(color, alpha) {
        const hex = color.replace('#', '');
        if (!/^[0-9a-f]{6}$/i.test(hex)) return color;
        const n = parseInt(hex, 16);
        return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
    }

    // Bar dataset options: HG.partialBar('#717cf8') -> { backgroundColor, borderColor, borderWidth }
    HG.partialBar = function (color) {
        return {
            backgroundColor: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) ? fade(color, 0.3)
                : isEstimatedIndex(ctx.chart, ctx.dataIndex) ? fade(color, 0.35) : color),
            borderColor: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) || isEstimatedIndex(ctx.chart, ctx.dataIndex) ? color : 'transparent'),
            borderWidth: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) ? 2 : isEstimatedIndex(ctx.chart, ctx.dataIndex) ? 1 : 0),
        };
    };

    // Line dataset option: segment: HG.partialSegment  (dashes the segment leading to the current period)
    HG.partialSegment = {
        borderDash: (ctx) => (isPartialIndex(ctx.chart, ctx.p1DataIndex) ? [6, 5] : undefined),
    };

    // Tooltip footer shared by every chart: flags the running period
    Chart.defaults.plugins.tooltip.callbacks.footer = function (items) {
        const item = items && items[0];
        if (item && isEstimatedIndex(item.chart, item.dataIndex)) {
            return HG.tr('Estimation : avant octobre 2024, le bot ne gardait que les totaux', 'Estimate: before October 2024, the bot only kept totals');
        }
        if (!item || !isPartialIndex(item.chart, item.dataIndex)) return '';
        if (item.chart.$hgPartial === 'month') {
            return HG.tr('Mois en cours : données partielles', 'Current month: data still coming in');
        }
        return HG.tr('Aujourd’hui : journée en cours', 'Today: day still in progress');
    };
    Chart.defaults.plugins.tooltip.footerColor = '#fbbf24';
    Chart.defaults.plugins.tooltip.footerFont = { weight: 'normal', size: 11 };
})();
