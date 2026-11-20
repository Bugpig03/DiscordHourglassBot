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

/* Podiums (members, servers, voters, in voice now): shown by pages, two cards side by side on a computer, one on a
   phone. The pages turn by themselves every 6 s, always forward (after the last one comes the first again); one dot
   per page, the current one filling up like a progress bar until the next turn. Clicking a dot goes to its page;
   hovering, focusing, touching or a hidden tab pauses; visitors who prefer less motion get no automatic turn. */
document.addEventListener('DOMContentLoaded', function () {
    const root = document.getElementById('podiumCarousel');
    if (!root) return;
    const track = root.querySelector('.podium-track');
    const dotsBox = root.querySelector('.podium-dots');
    const cards = Array.from(track.children);
    const DELAY = 6000;
    const calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    root.style.setProperty('--podium-delay', `${DELAY}ms`);

    // Copies of the cards at the end: going from the last page to the first keeps moving forward
    cards.forEach(card => {
        const copy = card.cloneNode(true);
        copy.setAttribute('aria-hidden', 'true');
        copy.setAttribute('inert', '');
        copy.classList.add('is-copy');
        track.appendChild(copy);
    });

    let perView = 0, pages = 0, page = 0, timer = 0, paused = false, dots = [];
    const wide = () => (window.matchMedia('(min-width: 900px)').matches ? 2 : 1);

    function buildDots() {
        perView = wide();
        pages = Math.ceil(cards.length / perView);
        dotsBox.innerHTML = '';
        dots = Array.from({ length: pages }, (_, i) => {
            const names = cards.slice(i * perView, i * perView + perView)
                .map(c => (c.querySelector('.podium-card-title') || {}).textContent || '').map(t => t.trim()).join(' · ');
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'podium-dot';
            dot.setAttribute('role', 'tab');
            dot.setAttribute('aria-label', names);
            dot.title = names;
            dot.innerHTML = '<i></i>';
            dot.addEventListener('click', () => { go(i); restart(); });
            dotsBox.appendChild(dot);
            return dot;
        });
    }

    function place(animate) {
        if (!animate) track.style.transition = 'none';
        track.style.transform = `translateX(calc(${-page} * (100% + var(--podium-gap))))`;
        if (!animate) { void track.offsetWidth; track.style.transition = ''; }
        const current = page % pages;
        dots.forEach((d, i) => {
            d.classList.toggle('active', i === current);
            d.setAttribute('aria-selected', String(i === current));
        });
        cards.forEach((card, i) => card.toggleAttribute('inert', Math.floor(i / perView) !== current));
    }
    function go(i, animate = true) { page = i; place(animate); }
    track.addEventListener('transitionend', e => {
        if (e.target === track && page >= pages) go(page - pages, false);
    });

    // The progress bar of the current dot restarts with each page (CSS animation over --podium-delay)
    function restartBar() {
        root.classList.remove('is-running');
        void root.offsetWidth;
        if (!calm && pages > 1) root.classList.add('is-running');
    }
    function restart() {
        clearInterval(timer);
        restartBar();
        if (calm || pages < 2) return;
        timer = setInterval(() => { if (!paused && !document.hidden) { go(page + 1); restartBar(); } }, DELAY);
    }
    function setPaused(on) {
        paused = on;
        root.classList.toggle('is-paused', on);
        if (!on) restart();  // a fresh full turn after a pause, rather than a jump right away
    }
    root.addEventListener('mouseenter', () => setPaused(true));
    root.addEventListener('mouseleave', () => setPaused(false));
    root.addEventListener('focusin', () => setPaused(true));
    root.addEventListener('focusout', e => { if (!root.contains(e.relatedTarget)) setPaused(false); });

    // Swipe on phones
    let startX = null;
    root.addEventListener('touchstart', e => { startX = e.touches[0].clientX; setPaused(true); }, { passive: true });
    root.addEventListener('touchend', e => {
        if (startX !== null) {
            const dx = e.changedTouches[0].clientX - startX;
            if (Math.abs(dx) > 40) go(dx < 0 ? page % pages + 1 : (page % pages + pages - 1) % pages);
        }
        startX = null;
        setPaused(false);
    });

    let lastWide = wide();
    window.addEventListener('resize', () => {
        if (wide() !== lastWide) {  // computer <-> phone: the page count changes
            lastWide = wide();
            const firstCard = (page % pages) * perView;
            buildDots();
            page = Math.floor(firstCard / perView);
            restart();
        }
        place(false);
    });
    buildDots();
    place(false);
    restart();
});
