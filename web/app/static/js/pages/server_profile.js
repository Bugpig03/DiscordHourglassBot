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

    const langLocale = HG.locale;
    const hoursUnit = 'h';

    // Shares and rankings: the Arène colors of the site, toned down, gray for "others"
    const modernPalette = HG.RANK_COLORS;
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
            month: { labels: hm.labels, hours: hm.hours, messages: mm.messages, partial: hm.partial, estimated: hm.estimated },
            day: { labels: hd.labels, hours: hd.hours, messages: md.messages, partial: hd.partial },
            month_cumul: { labels: hc.labels, hours: hc.hours, messages: mc.messages },
            day_cumul: { labels: hcd.labels, hours: hcd.hours, messages: mcd.messages },
        }, { colors: { hours: '#717cf8', messages: '#3fd1a0' }, period: PAGE_CFG.charts_default_granularity });
    }

    // Top members: share of the voice hours of the 10 most active members (and the others)
    const sMembersPieEl = document.getElementById('serverTopMembersPieData');
    if (sMembersPieEl) {
        const pieData = JSON.parse(sMembersPieEl.textContent);
        const narrow = window.innerWidth < 768;
        serverChartInstances.push(HG.draw('serverTopMembersChart', HG.donutOption({
            labels: pieData.labels, values: pieData.hours, colors: modernPalette,
            format: v => `${HG.fmt(v, 1)} ${hoursUnit}`,
            legend: narrow ? { top: 'auto', bottom: 0, left: 'center' } : { orient: 'vertical', top: 'middle', left: '64%', right: 8 },
        })));
    }

    // Peak hours (voice or messages) + day x hour grid
    HG.peakCard(document.getElementById('serverPeakCard'), readJson('serverHourlyActivityData'), readJson('serverPunchcardData'));

    // Most active channels: voice hours or messages
    const voice = readJson('serverVoiceChannelsData') || { labels: [], hours: [] };
    const text = readJson('serverTextChannelsData') || { labels: [], messages: [] };
    HG.splitCard(document.getElementById('serverChannelsCard'), {
        voice: { labels: voice.labels, values: voice.hours, metric: 'hours', desc:HG.tr('Heures en vocal par salon vocal.', 'Voice hours per voice channel.')},
        text: { labels: text.labels, values: text.messages, metric: 'messages', desc:HG.tr('Messages par salon textuel.', 'Messages per text channel.')},
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

