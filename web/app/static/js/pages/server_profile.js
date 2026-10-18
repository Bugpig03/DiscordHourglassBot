/* Page script extracted from templates/server_profile.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

const serverChartInstances = HG.cardCharts || [];

function switchServerProfileTab(tabId) {
    if (tabId === 'tab-channels') tabId = 'tab-activity';
    document.querySelectorAll('.graphs-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });

    document.querySelectorAll('.graphs-tab-pane').forEach(pane => {
        if (pane.id === tabId) {
            pane.style.display = 'block';
            pane.classList.add('active');
        } else {
            pane.style.display = 'none';
            pane.classList.remove('active');
        }
    });

    requestAnimationFrame(() => {
        serverChartInstances.forEach(c => {
            try { c.resize(); } catch(e) {}
        });
        window.dispatchEvent(new Event('resize'));
    });

    if (window.history && window.history.replaceState) {
        window.history.replaceState(null, null, '#' + tabId);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "Arial, sans-serif";

    const isEn = PAGE_CFG.current_lang === 'en';
    const langLocale = isEn ? 'en-US' : 'fr-FR';
    const hoursUnit = 'h';

    const modernPalette = [
        '#5865F2', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#a855f7', '#64748b'
    ];
    const readJson = id => {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : null;
    };

    // Activity over time: one chart (voice / messages, monthly / 30 days, per period / cumulative)
    const trendCard = document.getElementById('serverTrendCard');
    if (trendCard) {
        const hm = readJson('serverMonthlyHoursData') || {}, mm = readJson('serverMonthlyMessagesData') || {};
        const hd = readJson('serverDailyHoursData') || {}, md = readJson('serverDailyMessagesData') || {};
        const hc = readJson('serverHoursProgressionData') || {}, mc = readJson('serverMessagesProgressionData') || {};
        const hcd = readJson('serverHoursDailyProgressionData') || {}, mcd = readJson('serverMessagesDailyProgressionData') || {};
        HG.trendCard(trendCard, {
            month: { labels: hm.labels, hours: hm.hours, messages: mm.messages, partial: hm.partial },
            day: { labels: hd.labels, hours: hd.hours, messages: md.messages, partial: hd.partial },
            month_cumul: { labels: hc.labels, hours: hc.hours, messages: mc.messages },
            day_cumul: { labels: hcd.labels, hours: hcd.hours, messages: mcd.messages },
        }, { colors: { hours: '#38bdf8', messages: '#818cf8' }, period: PAGE_CFG.charts_default_granularity });
    }

    // 5. Server Top Members Donut
    const sMembersPieEl = document.getElementById('serverTopMembersPieData');
    if (sMembersPieEl) {
        const pieData = JSON.parse(sMembersPieEl.textContent);
        const ctx = document.getElementById('serverTopMembersChart').getContext('2d');

        const c5 = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: pieData.labels,
                datasets: [{
                    data: pieData.hours,
                    backgroundColor: modernPalette.slice(0, pieData.labels.length),
                    borderColor: '#15202e',
                    borderWidth: 2,
                    hoverOffset: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '55%',
                layout: { padding: 10 },
                plugins: {
                    legend: {
                        position: window.innerWidth < 768 ? 'bottom' : 'right',
                        labels: {
                            color: '#cbd5e1',
                            padding: 12,
                            font: { size: 11, weight: '500' },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const val = ctx.parsed;
                                const pct = total > 0 ? HG.fmt((val / total) * 100, 1) : 0;
                                return ` ${val.toLocaleString(langLocale)} ${hoursUnit} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
        serverChartInstances.push(c5);
    }

    // Peak hours (voice or messages) + day x hour grid
    HG.peakCard(document.getElementById('serverPeakCard'), readJson('serverHourlyActivityData'), readJson('serverPunchcardData'));

    // Most active channels: voice hours or messages
    const voice = readJson('serverVoiceChannelsData') || { labels: [], hours: [] };
    const text = readJson('serverTextChannelsData') || { labels: [], messages: [] };
    HG.splitCard(document.getElementById('serverChannelsCard'), {
        voice: { labels: voice.labels, values: voice.hours, metric: 'hours', desc: isEn ? 'Voice hours per voice channel.' : 'Heures en vocal par salon vocal.' },
        text: { labels: text.labels, values: text.messages, metric: 'messages', desc: isEn ? 'Messages per text channel.' : 'Messages par salon textuel.' },
    }, 'voice');

    // Check URL Hash
    const validTabs = ['tab-activity', 'tab-charts', 'tab-members'];
    let currentHash = window.location.hash ? window.location.hash.replace('#', '') : '';
    if (currentHash === 'tab-channels') currentHash = 'tab-activity';
    if (validTabs.includes(currentHash)) {
        switchServerProfileTab(currentHash);
    }
});

// "Voir plus": append the next slice of members without reloading (the link still works without JS)
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', async function(e) {
        const btn = e.target.closest('#loadMoreMembers');
        const list = document.getElementById('serverMembersList');
        if (!btn || !list) return;
        e.preventDefault();
        if (btn.dataset.loading) return;
        btn.dataset.loading = '1';
        btn.style.opacity = '0.6';
        try {
            const url = new URL(btn.dataset.url, window.location.origin);
            url.searchParams.set('offset', btn.dataset.offset);
            const res = await fetch(url, { credentials: 'same-origin' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            list.insertAdjacentHTML('beforeend', await res.text());

            const remaining = parseInt(res.headers.get('X-Remaining') || '0', 10);
            btn.dataset.offset = String(parseInt(btn.dataset.offset, 10) + PAGE_CFG.members_page_size);
            const counter = document.getElementById('loadMoreMembersCount');
            if (counter) counter.textContent = remaining;
            if (remaining <= 0) btn.parentElement.remove();
        } catch (err) {
            // Fall back to the full list page
            window.location.href = btn.href;
        } finally {
            delete btn.dataset.loading;
            btn.style.opacity = '';
        }
    });
});
