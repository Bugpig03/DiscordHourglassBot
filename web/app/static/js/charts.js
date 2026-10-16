/* Shared Chart.js helpers for Hourglass pages (loaded right after chart.js). */
(function () {
    const isEn = document.documentElement.lang === 'en';
    const HG = (window.HG = window.HG || {});

    HG.locale = isEn ? 'en-US' : 'fr-FR';

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

    function fade(color, alpha) {
        const hex = color.replace('#', '');
        if (!/^[0-9a-f]{6}$/i.test(hex)) return color;
        const n = parseInt(hex, 16);
        return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
    }

    // Bar dataset options: HG.partialBar('#38bdf8') -> { backgroundColor, borderColor, borderWidth }
    HG.partialBar = function (color) {
        return {
            backgroundColor: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) ? fade(color, 0.3) : color),
            borderColor: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) ? color : 'transparent'),
            borderWidth: (ctx) => (isPartialIndex(ctx.chart, ctx.dataIndex) ? 2 : 0),
        };
    };

    // Line dataset option: segment: HG.partialSegment  (dashes the segment leading to the current period)
    HG.partialSegment = {
        borderDash: (ctx) => (isPartialIndex(ctx.chart, ctx.p1DataIndex) ? [6, 5] : undefined),
    };

    // Tooltip footer shared by every chart: flags the running period
    Chart.defaults.plugins.tooltip.callbacks.footer = function (items) {
        const item = items && items[0];
        if (!item || !isPartialIndex(item.chart, item.dataIndex)) return '';
        if (item.chart.$hgPartial === 'month') {
            return isEn ? '⏳ Current month: data still coming in' : '⏳ Mois en cours : données partielles';
        }
        return isEn ? '⏳ Today: day still in progress' : '⏳ Aujourd’hui : journée en cours';
    };
    Chart.defaults.plugins.tooltip.footerColor = '#fbbf24';
    Chart.defaults.plugins.tooltip.footerFont = { weight: 'normal', size: 11 };
})();
