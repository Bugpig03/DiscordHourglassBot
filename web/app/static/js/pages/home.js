/* Page script extracted from templates/home.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

document.addEventListener('DOMContentLoaded', function() {
    const rawDataEl = document.getElementById('homeDailyChartData');
    if (!rawDataEl) return;
    try {
        const d = JSON.parse(rawDataEl.textContent);
        const hoursLabel = HG.tr('Heures en vocal', 'Voice hours');
        const msgsLabel = HG.tr('Messages', 'Messages');
        const dayTicks = d.ticks || [];
        const weekend = d.weekend || [];
        const lastDay = d.labels.length - 1;
        const C = HG.chartColors;
        const chart = HG.chart('homeActivityChart');

        // Different marks for different units: bars for voice hours (left axis), a line for messages (right axis).
        // Today is still running: its bar is faded and the end of the messages line is dashed.
        const msgs = d.messages || [];
        const solid = d.partial ? msgs.map((v, i) => (i < lastDay ? v : null)) : msgs;
        const dashed = d.partial ? msgs.map((v, i) => (i >= lastDay - 1 ? v : null)) : [];
        const series = {
            note: i => (d.partial && i === lastDay ? HG.tr('Aujourd’hui : journée en cours', 'Today: day still in progress') : ''),
        };

        // Every day: its number, with the month underneath at the start and on each 1st; a faint line marks the
        // change of month. Weekends are dimmer, today is white. With less than 20 px per day (phones), one number
        // out of 2 or 3 is shown, counted back from today; the months stay.
        const step = () => Math.max(1, Math.ceil(20 / Math.max(1, (chart.getWidth() - 90) / Math.max(1, d.labels.length))));
        HG.draw(chart, {
            grid: HG.grid({ top: 40, left: 6, right: 6, bottom: 4 }),
            legend: HG.legend({ data: [hoursLabel, msgsLabel], left: 'center' }),
            tooltip: HG.tooltip({
                axisPointer: HG.barPointer,
                formatter: ps => {
                    const i = ps[0].dataIndex;
                    return HG.tipHtml(d.labels[i], [
                        { color: '#717cf8', name: hoursLabel, value: `${HG.fmt(d.hours[i], 1)} h` },
                        { color: '#3fd1a0', name: msgsLabel, value: HG.fmt(msgs[i]) },
                    ], { notes: [series.note(i)] });
                },
            }),
            xAxis: HG.categoryAxis(d.labels, {
                axisLabel: {
                    interval: 0,
                    lineHeight: 14,
                    fontFamily: "'Chakra Petch', sans-serif",
                    fontWeight: 600,
                    fontSize: 11,
                    formatter: (value, i) => {
                        const tick = dayTicks[i];
                        if (!tick) return value;
                        const day = (lastDay - i) % step() !== 0 ? '' : tick[0];
                        const style = i === lastDay ? 't' : weekend[i] ? 'w' : 'd';
                        return (day ? `{${style}|${day}}` : ' ') + (tick[1] ? `\n{m|${tick[1]}}` : '');
                    },
                    rich: { d: { color: C.muted }, w: { color: C.faint }, t: { color: '#f2f3f5' }, m: { color: C.muted, fontSize: 10 } },
                },
                splitLine: { show: true, interval: i => i > 0 && !!(dayTicks[i] && dayTicks[i][1]), lineStyle: { color: 'rgba(255, 255, 255, 0.09)' } },
            }),
            yAxis: [
                HG.valueAxis({ name: HG.tr('Heures', 'Hours'), nameTextStyle: { color: '#717cf8', fontWeight: 600, align: 'left' },
                    axisLabel: { color: '#717cf8', formatter: v => HG.fmt(v) } }),
                HG.valueAxis({ name: HG.tr('Messages', 'Messages'), nameTextStyle: { color: '#3fd1a0', fontWeight: 600, align: 'right' },
                    axisLabel: { color: '#3fd1a0', formatter: v => HG.fmt(v) }, splitLine: { show: false } }),
            ],
            series: [
                {
                    type: 'bar', name: hoursLabel, yAxisIndex: 0, barMaxWidth: 18,
                    data: HG.periodBars(d.hours, '#717cf8', { partial: d.partial }),
                    itemStyle: { color: '#717cf8' },
                    emphasis: { itemStyle: { color: '#8b93fa' } },
                },
                {
                    type: 'line', name: msgsLabel, yAxisIndex: 1, data: solid, smooth: 0.35, showSymbol: false, symbolSize: 7,
                    lineStyle: { width: 2.4, color: '#3fd1a0' }, itemStyle: { color: '#3fd1a0' }, z: 3,
                },
                {
                    id: 'hg-hidden-today', type: 'line', name: msgsLabel, yAxisIndex: 1, data: dashed, smooth: 0.35, showSymbol: false,
                    lineStyle: { width: 2.4, color: '#3fd1a0', type: 'dashed' }, itemStyle: { color: '#3fd1a0' }, z: 3,
                    tooltip: { show: false }, silent: true,
                },
            ],
        });
    } catch(e) {
        console.error('Error rendering home activity chart:', e);
    }
});
