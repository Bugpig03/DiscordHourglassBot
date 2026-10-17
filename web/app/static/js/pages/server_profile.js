/* Page script extracted from templates/server_profile.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

const serverChartInstances = [];
let serverHoursChartInstance = null;
let serverMsgsChartInstance = null;
let serverMonthlyHoursChartInstance = null;
let serverMonthlyMsgsChartInstance = null;

let sHoursMonthlyData = null;
let sHoursDailyData = null;
let sMsgsMonthlyData = null;
let sMsgsDailyData = null;
let sMonthlyHoursBarData = null;
let sDailyHoursBarData = null;
let sMonthlyMsgsBarData = null;
let sDailyMsgsBarData = null;

let serverGranularity = PAGE_CFG.charts_default_granularity;

function switchServerGranularity(mode) {
    serverGranularity = mode;
    document.querySelectorAll('.granularity-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-granularity') === mode);
    });

    const isDay = (mode === 'day');
    const isEn = PAGE_CFG.current_lang === 'en';
    const langLocale = isEn ? 'en-US' : 'fr-FR';
    const hoursUnit = PAGE_CFG.t_top_hours_unit;
    const msgsUnit = PAGE_CFG.t_top_msgs_unit;

    // 1. Hours line chart
    if (serverHoursChartInstance && sHoursDailyData && sHoursMonthlyData) {
        const data = isDay ? sHoursDailyData : sHoursMonthlyData;
        serverHoursChartInstance.data.labels = data.labels;
        serverHoursChartInstance.data.datasets[0].data = data.hours;
        serverHoursChartInstance.options.scales.x.time.unit = isDay ? 'day' : 'month';
        serverHoursChartInstance.update();
    }

    // 2. Messages line chart
    if (serverMsgsChartInstance && sMsgsDailyData && sMsgsMonthlyData) {
        const data = isDay ? sMsgsDailyData : sMsgsMonthlyData;
        serverMsgsChartInstance.data.labels = data.labels;
        serverMsgsChartInstance.data.datasets[0].data = data.messages;
        serverMsgsChartInstance.options.scales.x.time.unit = isDay ? 'day' : 'month';
        serverMsgsChartInstance.update();
    }

    // 3. Periodic hours bar chart
    if (serverMonthlyHoursChartInstance && sDailyHoursBarData && sMonthlyHoursBarData) {
        const data = isDay ? sDailyHoursBarData : sMonthlyHoursBarData;
        const avg = isDay ? Number(PAGE_CFG.charts_avg_daily_hours) : Number(PAGE_CFG.charts_avg_hours);
        const unit = isDay ? PAGE_CFG.t_charts_unit_hours_per_day : PAGE_CFG.t_graphs_unit_hours_per_month;
        
        HG.setPartial(serverMonthlyHoursChartInstance, data.partial);
        serverMonthlyHoursChartInstance.data.labels = data.labels;
        serverMonthlyHoursChartInstance.data.datasets[0].data = data.hours;
        serverMonthlyHoursChartInstance.data.datasets[0].label = isDay ? (isEn ? 'Daily hours' : 'Heures du jour') : (isEn ? 'Monthly hours' : 'Heures du mois');
        serverMonthlyHoursChartInstance.data.datasets[1].data = Array(data.hours.length).fill(avg);
        serverMonthlyHoursChartInstance.data.datasets[1].label = (isEn ? 'Average (' : 'Moyenne (') + HG.fmt(avg, 1) + ' ' + hoursUnit + ')';
        serverMonthlyHoursChartInstance.update();

        const hTitle = document.getElementById('serverHoursBarTitle');
        if (hTitle) hTitle.textContent = isDay ? PAGE_CFG.t_charts_daily_hours_title : PAGE_CFG.t_server_profile_monthly_hours_title;
        const hDesc = document.getElementById('serverHoursBarDesc');
        if (hDesc) hDesc.textContent = isDay ? PAGE_CFG.t_charts_daily_hours_desc : PAGE_CFG.t_server_profile_monthly_hours_desc;
        const hBadge = document.getElementById('serverHoursBarBadge');
        if (hBadge) hBadge.textContent = `${isEn ? 'Average' : 'Moyenne'} : ${avg} ${unit}`;
    }

    // 4. Periodic messages bar chart
    if (serverMonthlyMsgsChartInstance && sDailyMsgsBarData && sMonthlyMsgsBarData) {
        const data = isDay ? sDailyMsgsBarData : sMonthlyMsgsBarData;
        const avg = isDay ? Number(PAGE_CFG.charts_avg_daily_msgs) : Number(PAGE_CFG.charts_avg_msgs);
        const unit = isDay ? PAGE_CFG.t_charts_unit_msgs_per_day : PAGE_CFG.t_graphs_unit_msgs_per_month;

        HG.setPartial(serverMonthlyMsgsChartInstance, data.partial);
        serverMonthlyMsgsChartInstance.data.labels = data.labels;
        serverMonthlyMsgsChartInstance.data.datasets[0].data = data.messages;
        serverMonthlyMsgsChartInstance.data.datasets[0].label = isDay ? (isEn ? 'Daily messages' : 'Messages du jour') : (isEn ? 'Monthly messages' : 'Messages du mois');
        serverMonthlyMsgsChartInstance.data.datasets[1].data = Array(data.messages.length).fill(Math.round(avg));
        serverMonthlyMsgsChartInstance.data.datasets[1].label = (isEn ? 'Average (' : 'Moyenne (') + Math.round(avg).toLocaleString(langLocale) + ' ' + msgsUnit + ')';
        serverMonthlyMsgsChartInstance.update();

        const mTitle = document.getElementById('serverMessagesBarTitle');
        if (mTitle) mTitle.textContent = isDay ? PAGE_CFG.t_charts_daily_msgs_title : PAGE_CFG.t_server_profile_monthly_msgs_title;
        const mDesc = document.getElementById('serverMessagesBarDesc');
        if (mDesc) mDesc.textContent = isDay ? PAGE_CFG.t_charts_daily_msgs_desc : PAGE_CFG.t_server_profile_monthly_msgs_desc;
        const mBadge = document.getElementById('serverMessagesBarBadge');
        if (mBadge) mBadge.textContent = `${isEn ? 'Average' : 'Moyenne'} : ${Math.round(avg).toLocaleString(langLocale)} ${unit}`;
    }
}

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
    const hoursUnit = PAGE_CFG.t_top_hours_unit;
    const msgsUnit = PAGE_CFG.t_top_msgs_unit;

    const modernPalette = [
        '#5865F2', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#a855f7', '#64748b'
    ];

    // Load data from JSON elements
    const sHoursEl = document.getElementById('serverHoursProgressionData');
    const sHoursDailyEl = document.getElementById('serverHoursDailyProgressionData');
    if (sHoursEl) sHoursMonthlyData = JSON.parse(sHoursEl.textContent);
    if (sHoursDailyEl) sHoursDailyData = JSON.parse(sHoursDailyEl.textContent);

    const sMsgsEl = document.getElementById('serverMessagesProgressionData');
    const sMsgsDailyEl = document.getElementById('serverMessagesDailyProgressionData');
    if (sMsgsEl) sMsgsMonthlyData = JSON.parse(sMsgsEl.textContent);
    if (sMsgsDailyEl) sMsgsDailyData = JSON.parse(sMsgsDailyEl.textContent);

    const sMonthlyHoursEl = document.getElementById('serverMonthlyHoursData');
    const sDailyHoursEl = document.getElementById('serverDailyHoursData');
    if (sMonthlyHoursEl) sMonthlyHoursBarData = JSON.parse(sMonthlyHoursEl.textContent);
    if (sDailyHoursEl) sDailyHoursBarData = JSON.parse(sDailyHoursEl.textContent);

    const sMonthlyMsgsEl = document.getElementById('serverMonthlyMessagesData');
    const sDailyMsgsEl = document.getElementById('serverDailyMessagesData');
    if (sMonthlyMsgsEl) sMonthlyMsgsBarData = JSON.parse(sMonthlyMsgsEl.textContent);
    if (sDailyMsgsEl) sDailyMsgsBarData = JSON.parse(sDailyMsgsEl.textContent);

    // 1. Server Hours Progression
    if (sHoursMonthlyData) {
        const ctx = document.getElementById('serverHoursChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.35)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.00)');

        serverHoursChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sHoursMonthlyData.labels,
                datasets: [{
                    label: isEn ? 'Cumulative hours' : 'Heures cumulées',
                    data: sHoursMonthlyData.hours,
                    borderColor: '#38bdf8',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#38bdf8',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { display: true, labels: { color: '#e2e8f0', font: { weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#38bdf8',
                        borderColor: 'rgba(56, 189, 248, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: function(ctx) {
                                const val = ctx.parsed.y;
                                const dataArr = ctx.dataset.data;
                                const idx = ctx.dataIndex;
                                let deltaStr = '';
                                if (idx > 0 && dataArr && dataArr.length > idx) {
                                    const prev = typeof dataArr[idx - 1] === 'number' ? dataArr[idx - 1] : (dataArr[idx - 1]?.y ?? 0);
                                    const diff = Math.round((val - prev) * 10) / 10;
                                    const diffSign = diff >= 0 ? '+' : '';
                                    const periodText = isEn
                                        ? (serverGranularity === 'day' ? 'this day' : 'this month')
                                        : (serverGranularity === 'day' ? 'ce jour' : 'ce mois');
                                    deltaStr = ` (${diffSign}${diff.toLocaleString(langLocale)} h ${periodText})`;
                                } else if (idx === 0) {
                                    deltaStr = isEn ? ' (baseline)' : ' (point de départ)';
                                }
                                return ` ${val.toLocaleString(langLocale)} ${isEn ? 'hours' : 'heures'}${deltaStr}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(val) { return val.toLocaleString(langLocale) + ' ' + hoursUnit; }
                        }
                    }
                }
            }
        });
        serverChartInstances.push(serverHoursChartInstance);
    }

    // 2. Server Messages Progression
    if (sMsgsMonthlyData) {
        const ctx = document.getElementById('serverMessagesChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, 'rgba(88, 101, 242, 0.35)');
        gradient.addColorStop(1, 'rgba(88, 101, 242, 0.00)');

        serverMsgsChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sMsgsMonthlyData.labels,
                datasets: [{
                    label: isEn ? 'Cumulative messages' : 'Messages cumulés',
                    data: sMsgsMonthlyData.messages,
                    borderColor: '#5865F2',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#5865F2',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { display: true, labels: { color: '#e2e8f0', font: { weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#a5b4fc',
                        borderColor: 'rgba(88, 101, 242, 0.4)',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: function(ctx) {
                                const val = ctx.parsed.y;
                                const dataArr = ctx.dataset.data;
                                const idx = ctx.dataIndex;
                                let deltaStr = '';
                                if (idx > 0 && dataArr && dataArr.length > idx) {
                                    const prev = typeof dataArr[idx - 1] === 'number' ? dataArr[idx - 1] : (dataArr[idx - 1]?.y ?? 0);
                                    const diff = Math.round(val - prev);
                                    const diffSign = diff >= 0 ? '+' : '';
                                    const periodText = isEn
                                        ? (serverGranularity === 'day' ? 'this day' : 'this month')
                                        : (serverGranularity === 'day' ? 'ce jour' : 'ce mois');
                                    deltaStr = ` (${diffSign}${diff.toLocaleString(langLocale)} ${periodText})`;
                                } else if (idx === 0) {
                                    deltaStr = isEn ? ' (baseline)' : ' (point de départ)';
                                }
                                return ` ${val.toLocaleString(langLocale)} messages${deltaStr}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(val) { return val.toLocaleString(langLocale) + ' ' + msgsUnit; }
                        }
                    }
                }
            }
        });
        serverChartInstances.push(serverMsgsChartInstance);
    }

    // 3. Server Monthly Hours
    if (sMonthlyHoursBarData) {
        const ctx = document.getElementById('serverMonthlyHoursChart').getContext('2d');
        const completed = sMonthlyHoursBarData.hours.length > 1 ? sMonthlyHoursBarData.hours.slice(0, -1) : sMonthlyHoursBarData.hours;
        const avg = completed.reduce((a, b) => a + b, 0) / Math.max(1, completed.length);

        serverMonthlyHoursChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sMonthlyHoursBarData.labels,
                datasets: [
                    {
                        label: isEn ? 'Monthly hours' : 'Heures du mois',
                        data: sMonthlyHoursBarData.hours,
                        ...HG.partialBar('#38bdf8'),
                        borderRadius: 6,
                        order: 2
                    },
                    {
                        label: (isEn ? 'Average (' : 'Moyenne (') + HG.fmt(avg, 1) + ' ' + hoursUnit + ')',
                        data: Array(sMonthlyHoursBarData.hours.length).fill(Number(avg.toFixed(1))),
                        type: 'line',
                        borderColor: '#fbbf24',
                        borderWidth: 2.5,
                        borderDash: [6, 6],
                        pointRadius: 0,
                        fill: false,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#e2e8f0', font: { weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        callbacks: {
                            label: function(ctx) { return ` ${ctx.parsed.y.toLocaleString(langLocale)} ${hoursUnit}`; }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', maxRotation: 45 } },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { color: '#94a3b8', callback: function(val) { return val.toLocaleString(langLocale) + ' ' + hoursUnit; } }
                    }
                }
            }
        });
        HG.setPartial(serverMonthlyHoursChartInstance, sMonthlyHoursBarData.partial);
        serverMonthlyHoursChartInstance.update();
        serverChartInstances.push(serverMonthlyHoursChartInstance);
    }

    // 4. Server Monthly Messages
    if (sMonthlyMsgsBarData) {
        const ctx = document.getElementById('serverMonthlyMessagesChart').getContext('2d');
        const completed = sMonthlyMsgsBarData.messages.length > 1 ? sMonthlyMsgsBarData.messages.slice(0, -1) : sMonthlyMsgsBarData.messages;
        const avg = completed.reduce((a, b) => a + b, 0) / Math.max(1, completed.length);

        serverMonthlyMsgsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sMonthlyMsgsBarData.labels,
                datasets: [
                    {
                        label: isEn ? 'Monthly messages' : 'Messages du mois',
                        data: sMonthlyMsgsBarData.messages,
                        ...HG.partialBar('#5865F2'),
                        borderRadius: 6,
                        order: 2
                    },
                    {
                        label: (isEn ? 'Average (' : 'Moyenne (') + Math.round(avg).toLocaleString(langLocale) + ' ' + msgsUnit + ')',
                        data: Array(sMonthlyMsgsBarData.messages.length).fill(Math.round(avg)),
                        type: 'line',
                        borderColor: '#f472b6',
                        borderWidth: 2.5,
                        borderDash: [6, 6],
                        pointRadius: 0,
                        fill: false,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#e2e8f0', font: { weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        callbacks: {
                            label: function(ctx) { return ` ${ctx.parsed.y.toLocaleString(langLocale)} messages`; }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', maxRotation: 45 } },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { color: '#94a3b8', callback: function(val) { return val.toLocaleString(langLocale) + ' ' + msgsUnit; } }
                    }
                }
            }
        });
        HG.setPartial(serverMonthlyMsgsChartInstance, sMonthlyMsgsBarData.partial);
        serverMonthlyMsgsChartInstance.update();
        serverChartInstances.push(serverMonthlyMsgsChartInstance);
    }

    // Apply default granularity if day
    if (serverGranularity === 'day') {
        switchServerGranularity('day');
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

    // 6. Server Hourly Activity (24h)
    const sHourlyEl = document.getElementById('serverHourlyActivityData');
    if (sHourlyEl) {
        const hourlyData = JSON.parse(sHourlyEl.textContent);
        const ctxH = document.getElementById('serverHourlyChart').getContext('2d');
        const gradV = ctxH.createLinearGradient(0, 0, 0, 300);
        gradV.addColorStop(0, 'rgba(56, 189, 248, 0.35)');
        gradV.addColorStop(1, 'rgba(56, 189, 248, 0.00)');

        const cH = new Chart(ctxH, {
            type: 'line',
            data: {
                labels: hourlyData.labels,
                datasets: [
                    {
                        label: isEn ? 'Avg Voice (h/day)' : 'Moyenne vocale (h/jour)',
                        data: hourlyData.voice_hours,
                        borderColor: '#38bdf8',
                        backgroundColor: gradV,
                        borderWidth: 2.5,
                        tension: 0.35,
                        fill: true,
                        yAxisID: 'y',
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#38bdf8'
                    },
                    {
                        label: isEn ? 'Avg Messages (msgs/day)' : 'Moyenne messages (msgs/jour)',
                        data: hourlyData.messages_count,
                        borderColor: '#818cf8',
                        backgroundColor: 'rgba(129, 140, 248, 0.08)',
                        borderWidth: 2,
                        tension: 0.35,
                        borderDash: [4, 4],
                        fill: false,
                        yAxisID: 'y1',
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#818cf8'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#cbd5e1', usePointStyle: true, boxWidth: 8, padding: 16 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.datasetIndex === 0) {
                                    return ` 🎙️ ${ctx.parsed.y} ${isEn ? 'h/day' : 'h/jour'}`;
                                } else {
                                    return ` 💬 ${ctx.parsed.y.toLocaleString(langLocale)} ${isEn ? 'msgs/day' : 'msgs/jour'}`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { color: '#38bdf8', callback: v => v + ' ' + (isEn ? 'h/day' : 'h/jour') }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#818cf8', callback: v => v.toLocaleString(langLocale) + ' ' + (isEn ? 'msgs/day' : 'msgs/jour') }
                    }
                }
            }
        });
        serverChartInstances.push(cH);
    }

    // 7. Server Voice Channels Doughnut
    const sVoiceChEl = document.getElementById('serverVoiceChannelsData');
    if (sVoiceChEl) {
        const vChData = JSON.parse(sVoiceChEl.textContent);
        const ctxVC = document.getElementById('serverVoiceChannelsChart').getContext('2d');
        const cVC = new Chart(ctxVC, {
            type: 'doughnut',
            data: {
                labels: vChData.labels,
                datasets: [{
                    data: vChData.hours,
                    backgroundColor: modernPalette.slice(0, vChData.labels.length),
                    borderColor: '#15202e',
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '58%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#cbd5e1', font: { size: 11 }, usePointStyle: true, padding: 10 }
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
        serverChartInstances.push(cVC);
    }

    // 8. Server Text Channels Doughnut
    const sTextChEl = document.getElementById('serverTextChannelsData');
    if (sTextChEl) {
        const tChData = JSON.parse(sTextChEl.textContent);
        const ctxTC = document.getElementById('serverTextChannelsChart').getContext('2d');
        const cTC = new Chart(ctxTC, {
            type: 'doughnut',
            data: {
                labels: tChData.labels,
                datasets: [{
                    data: tChData.messages,
                    backgroundColor: modernPalette.slice(1, tChData.labels.length + 1),
                    borderColor: '#15202e',
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '58%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#cbd5e1', font: { size: 11 }, usePointStyle: true, padding: 10 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const val = ctx.parsed;
                                const pct = total > 0 ? HG.fmt((val / total) * 100, 1) : 0;
                                return ` ${val.toLocaleString(langLocale)} ${msgsUnit} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
        serverChartInstances.push(cTC);
    }

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
