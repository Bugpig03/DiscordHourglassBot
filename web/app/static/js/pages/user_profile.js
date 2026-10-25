/* Page script extracted from templates/user_profile.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
// Voice series follow the member's profile color (blurple by default, like the site)
const ACCENT = PAGE_CFG.accent_hex || '#717cf8';
const ACCENT_RGB = PAGE_CFG.accent_rgb || '113, 124, 248';

const userChartInstances = HG.cardCharts || [];

function switchUserProfileTab(tabId) {
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
        userChartInstances.forEach(c => {
            try { c.resize(); } catch(e) {}
        });
        window.dispatchEvent(new Event('resize'));
    });

    if (window.history && window.history.replaceState) {
        window.history.replaceState(null, null, '#' + tabId);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#a3a6b0';
    Chart.defaults.font.family = "Arial, sans-serif";


    const readJson = id => {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : null;
    };

    // Activity over time: one chart (voice / messages, monthly / 30 days, per period / cumulative)
    const trendCard = document.getElementById('userTrendCard');
    if (trendCard) {
        const hm = readJson('userMonthlyHoursData') || {}, mm = readJson('userMonthlyMessagesData') || {};
        const hd = readJson('userDailyHoursData') || {}, md = readJson('userDailyMessagesData') || {};
        const hc = readJson('userHoursProgressionData') || {}, mc = readJson('userMessagesProgressionData') || {};
        const hcd = readJson('userHoursDailyProgressionData') || {}, mcd = readJson('userMessagesDailyProgressionData') || {};
        HG.trendCard(trendCard, {
            month: { labels: hm.labels, hours: hm.hours, messages: mm.messages, partial: hm.partial },
            day: { labels: hd.labels, hours: hd.hours, messages: md.messages, partial: hd.partial },
            month_cumul: { labels: hc.labels, hours: hc.hours, messages: mc.messages },
            day_cumul: { labels: hcd.labels, hours: hcd.hours, messages: mcd.messages },
        }, { colors: { hours: ACCENT, messages: '#3fd1a0' }, period: PAGE_CFG.charts_default_granularity });
    }

    // Voice time split by server or by channel
    const splitCard = document.getElementById('userSplitCard');
    if (splitCard) {
        const servers = readJson('userServersPieData') || { labels: [], hours: [] };
        const channels = readJson('userFavoriteChannelsData') || { labels: [], hours: [] };
        HG.splitCard(splitCard, {
            servers: { labels: servers.labels, values: servers.hours, metric: 'hours', desc:HG.tr('Heures en vocal par serveur (top 10).', 'Voice hours per server (top 10).')},
            channels: { labels: channels.labels, values: channels.hours, metric: 'hours', desc:HG.tr('Salons vocaux favoris, tous serveurs confondus.', 'Favorite voice channels, all servers combined.')},
        }, 'servers');
    }

    // Check URL Hash
    const validTabs = ['tab-activity', 'tab-charts', 'tab-servers', 'tab-badges'];
    const currentHash = window.location.hash ? window.location.hash.replace('#', '') : '';
    // A tab hidden by the member is not rendered: ignore a stale #hash pointing to it
    if (validTabs.includes(currentHash) && document.getElementById(currentHash)) {
        switchUserProfileTab(currentHash);
    }
});



function toggleHeatmapView(mode) {
    const annualCont = document.getElementById('heatmapAnnualContainer');
    const monthlyCont = document.getElementById('heatmapMonthlyContainer');
    const btnAnn = document.getElementById('btnHeatmapAnnual');
    const btnMon = document.getElementById('btnHeatmapMonthly');

    if (mode === 'monthly') {
        if (annualCont) annualCont.style.display = 'none';
        if (monthlyCont) monthlyCont.style.display = 'block';
        if (btnAnn) btnAnn.classList.remove('active');
        if (btnMon) btnMon.classList.add('active');
    } else {
        if (annualCont) annualCont.style.display = 'block';
        if (monthlyCont) monthlyCont.style.display = 'none';
        if (btnAnn) btnAnn.classList.add('active');
        if (btnMon) btnMon.classList.remove('active');
    }
}

// Badges tab filter: all / unlocked / to unlock (hides tiers, then families left empty)
(function () {
    const buttons = document.querySelectorAll('[data-badge-filter]');
    if (!buttons.length) return;
    buttons.forEach(btn => btn.addEventListener('click', () => {
        const mode = btn.dataset.badgeFilter;
        buttons.forEach(b => b.classList.toggle('active', b === btn));
        let visibleFamilies = 0;
        document.querySelectorAll('.bd-family').forEach(fam => {
            let visible = 0;
            fam.querySelectorAll('.bd-tier').forEach(tier => {
                const unlocked = tier.dataset.state === 'unlocked';
                const show = mode === 'all' || (mode === 'unlocked' ? unlocked : !unlocked);
                tier.hidden = !show;
                if (show) visible++;
            });
            fam.hidden = visible === 0;
            if (visible) visibleFamilies++;
        });
        const empty = document.getElementById('badgesEmpty');
        if (empty) empty.hidden = visibleFamilies > 0;
    }));
})();
