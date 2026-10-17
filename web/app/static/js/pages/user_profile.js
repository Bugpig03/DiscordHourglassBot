/* Page script extracted from templates/user_profile.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);
// Voice series follow the member's profile color (sky blue by default)
const ACCENT = PAGE_CFG.accent_hex || '#38bdf8';
const ACCENT_RGB = PAGE_CFG.accent_rgb || '56, 189, 248';

const userChartInstances = [];
let userHoursChartInstance = null;
let userMsgsChartInstance = null;
let userMonthlyHoursChartInstance = null;
let userMonthlyMsgsChartInstance = null;

let uHoursMonthlyData = null;
let uHoursDailyData = null;
let uMsgsMonthlyData = null;
let uMsgsDailyData = null;
let uMonthlyHoursBarData = null;
let uDailyHoursBarData = null;
let uMonthlyMsgsBarData = null;
let uDailyMsgsBarData = null;

let userGranularity = PAGE_CFG.charts_default_granularity;

function switchUserGranularity(mode) {
    userGranularity = mode;
    document.querySelectorAll('.granularity-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-granularity') === mode);
    });

    const isDay = (mode === 'day');
    const isEn = PAGE_CFG.current_lang === 'en';
    const langLocale = isEn ? 'en-US' : 'fr-FR';
    const hoursUnit = PAGE_CFG.t_top_hours_unit;
    const msgsUnit = PAGE_CFG.t_top_msgs_unit;

    // 1. Hours line chart
    if (userHoursChartInstance && uHoursDailyData && uHoursMonthlyData) {
        const data = isDay ? uHoursDailyData : uHoursMonthlyData;
        userHoursChartInstance.data.labels = data.labels;
        userHoursChartInstance.data.datasets[0].data = data.hours;
        userHoursChartInstance.options.scales.x.time.unit = isDay ? 'day' : 'month';
        userHoursChartInstance.update();
    }

    // 2. Messages line chart
    if (userMsgsChartInstance && uMsgsDailyData && uMsgsMonthlyData) {
        const data = isDay ? uMsgsDailyData : uMsgsMonthlyData;
        userMsgsChartInstance.data.labels = data.labels;
        userMsgsChartInstance.data.datasets[0].data = data.messages;
        userMsgsChartInstance.options.scales.x.time.unit = isDay ? 'day' : 'month';
        userMsgsChartInstance.update();
    }

    // 3. Periodic hours bar chart
    if (userMonthlyHoursChartInstance && uDailyHoursBarData && uMonthlyHoursBarData) {
        const data = isDay ? uDailyHoursBarData : uMonthlyHoursBarData;
        const avg = isDay ? Number(PAGE_CFG.charts_avg_daily_hours) : Number(PAGE_CFG.charts_avg_hours);
        const unit = isDay ? PAGE_CFG.t_charts_unit_hours_per_day : PAGE_CFG.t_graphs_unit_hours_per_month;

        HG.setPartial(userMonthlyHoursChartInstance, data.partial);
        userMonthlyHoursChartInstance.data.labels = data.labels;
        userMonthlyHoursChartInstance.data.datasets[0].data = data.hours;
        userMonthlyHoursChartInstance.data.datasets[0].label = isDay ? (isEn ? 'Daily hours' : 'Heures du jour') : (isEn ? 'Monthly hours' : 'Heures du mois');
        userMonthlyHoursChartInstance.data.datasets[1].data = Array(data.hours.length).fill(avg);
        userMonthlyHoursChartInstance.data.datasets[1].label = (isEn ? 'Average (' : 'Moyenne (') + HG.fmt(avg, 1) + ' ' + hoursUnit + ')';
        userMonthlyHoursChartInstance.update();

        const hTitle = document.getElementById('userHoursBarTitle');
        if (hTitle) hTitle.textContent = isDay ? PAGE_CFG.t_charts_daily_hours_title : PAGE_CFG.t_user_profile_monthly_hours_title;
        const hDesc = document.getElementById('userHoursBarDesc');
        if (hDesc) hDesc.textContent = isDay ? PAGE_CFG.t_charts_daily_hours_desc : PAGE_CFG.t_user_profile_monthly_hours_desc;
        const hBadge = document.getElementById('userHoursBarBadge');
        if (hBadge) hBadge.textContent = `${isEn ? 'Average' : 'Moyenne'} : ${avg} ${unit}`;
    }

    // 4. Periodic messages bar chart
    if (userMonthlyMsgsChartInstance && uDailyMsgsBarData && uMonthlyMsgsBarData) {
        const data = isDay ? uDailyMsgsBarData : uMonthlyMsgsBarData;
        const avg = isDay ? Number(PAGE_CFG.charts_avg_daily_msgs) : Number(PAGE_CFG.charts_avg_msgs);
        const unit = isDay ? PAGE_CFG.t_charts_unit_msgs_per_day : PAGE_CFG.t_graphs_unit_msgs_per_month;

        HG.setPartial(userMonthlyMsgsChartInstance, data.partial);
        userMonthlyMsgsChartInstance.data.labels = data.labels;
        userMonthlyMsgsChartInstance.data.datasets[0].data = data.messages;
        userMonthlyMsgsChartInstance.data.datasets[0].label = isDay ? (isEn ? 'Daily messages' : 'Messages du jour') : (isEn ? 'Monthly messages' : 'Messages du mois');
        userMonthlyMsgsChartInstance.data.datasets[1].data = Array(data.messages.length).fill(Math.round(avg));
        userMonthlyMsgsChartInstance.data.datasets[1].label = (isEn ? 'Average (' : 'Moyenne (') + Math.round(avg).toLocaleString(langLocale) + ' ' + msgsUnit + ')';
        userMonthlyMsgsChartInstance.update();

        const mTitle = document.getElementById('userMessagesBarTitle');
        if (mTitle) mTitle.textContent = isDay ? PAGE_CFG.t_charts_daily_msgs_title : PAGE_CFG.t_user_profile_monthly_msgs_title;
        const mDesc = document.getElementById('userMessagesBarDesc');
        if (mDesc) mDesc.textContent = isDay ? PAGE_CFG.t_charts_daily_msgs_desc : PAGE_CFG.t_user_profile_monthly_msgs_desc;
        const mBadge = document.getElementById('userMessagesBarBadge');
        if (mBadge) mBadge.textContent = `${isEn ? 'Average' : 'Moyenne'} : ${Math.round(avg).toLocaleString(langLocale)} ${unit}`;
    }
}

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
    const uHoursEl = document.getElementById('userHoursProgressionData');
    const uHoursDailyEl = document.getElementById('userHoursDailyProgressionData');
    if (uHoursEl) uHoursMonthlyData = JSON.parse(uHoursEl.textContent);
    if (uHoursDailyEl) uHoursDailyData = JSON.parse(uHoursDailyEl.textContent);

    const uMsgsEl = document.getElementById('userMessagesProgressionData');
    const uMsgsDailyEl = document.getElementById('userMessagesDailyProgressionData');
    if (uMsgsEl) uMsgsMonthlyData = JSON.parse(uMsgsEl.textContent);
    if (uMsgsDailyEl) uMsgsDailyData = JSON.parse(uMsgsDailyEl.textContent);

    const uMonthlyHoursEl = document.getElementById('userMonthlyHoursData');
    const uDailyHoursEl = document.getElementById('userDailyHoursData');
    if (uMonthlyHoursEl) uMonthlyHoursBarData = JSON.parse(uMonthlyHoursEl.textContent);
    if (uDailyHoursEl) uDailyHoursBarData = JSON.parse(uDailyHoursEl.textContent);

    const uMonthlyMsgsEl = document.getElementById('userMonthlyMessagesData');
    const uDailyMsgsEl = document.getElementById('userDailyMessagesData');
    if (uMonthlyMsgsEl) uMonthlyMsgsBarData = JSON.parse(uMonthlyMsgsEl.textContent);
    if (uDailyMsgsEl) uDailyMsgsBarData = JSON.parse(uDailyMsgsEl.textContent);

    // 1. User Hours Progression
    if (uHoursMonthlyData) {
        const ctx = document.getElementById('userHoursChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, `rgba(${ACCENT_RGB}, 0.35)`);
        gradient.addColorStop(1, `rgba(${ACCENT_RGB}, 0.00)`);

        userHoursChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: uHoursMonthlyData.labels,
                datasets: [{
                    label: isEn ? 'Cumulative hours' : 'Heures cumulées',
                    data: uHoursMonthlyData.hours,
                    borderColor: ACCENT,
                    backgroundColor: gradient,
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: ACCENT,
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
                                        ? (userGranularity === 'day' ? 'this day' : 'this month')
                                        : (userGranularity === 'day' ? 'ce jour' : 'ce mois');
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
        userChartInstances.push(userHoursChartInstance);
    }

    // 2. User Messages Progression
    if (uMsgsMonthlyData) {
        const ctx = document.getElementById('userMessagesChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, 'rgba(88, 101, 242, 0.35)');
        gradient.addColorStop(1, 'rgba(88, 101, 242, 0.00)');

        userMsgsChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: uMsgsMonthlyData.labels,
                datasets: [{
                    label: isEn ? 'Cumulative messages' : 'Messages cumulés',
                    data: uMsgsMonthlyData.messages,
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
                                        ? (userGranularity === 'day' ? 'this day' : 'this month')
                                        : (userGranularity === 'day' ? 'ce jour' : 'ce mois');
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
        userChartInstances.push(userMsgsChartInstance);
    }

    // 3. User Monthly Hours
    if (uMonthlyHoursBarData) {
        const ctx = document.getElementById('userMonthlyHoursChart').getContext('2d');
        const completed = uMonthlyHoursBarData.hours.length > 1 ? uMonthlyHoursBarData.hours.slice(0, -1) : uMonthlyHoursBarData.hours;
        const avg = completed.reduce((a, b) => a + b, 0) / Math.max(1, completed.length);

        userMonthlyHoursChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: uMonthlyHoursBarData.labels,
                datasets: [
                    {
                        label: isEn ? 'Monthly hours' : 'Heures du mois',
                        data: uMonthlyHoursBarData.hours,
                        ...HG.partialBar(ACCENT),
                        borderRadius: 6,
                        order: 2
                    },
                    {
                        label: (isEn ? 'Average (' : 'Moyenne (') + HG.fmt(avg, 1) + ' ' + hoursUnit + ')',
                        data: Array(uMonthlyHoursBarData.hours.length).fill(Number(avg.toFixed(1))),
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
        HG.setPartial(userMonthlyHoursChartInstance, uMonthlyHoursBarData.partial);
        userMonthlyHoursChartInstance.update();
        userChartInstances.push(userMonthlyHoursChartInstance);
    }

    // 4. User Monthly Messages
    if (uMonthlyMsgsBarData) {
        const ctx = document.getElementById('userMonthlyMessagesChart').getContext('2d');
        const completed = uMonthlyMsgsBarData.messages.length > 1 ? uMonthlyMsgsBarData.messages.slice(0, -1) : uMonthlyMsgsBarData.messages;
        const avg = completed.reduce((a, b) => a + b, 0) / Math.max(1, completed.length);

        userMonthlyMsgsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: uMonthlyMsgsBarData.labels,
                datasets: [
                    {
                        label: isEn ? 'Monthly messages' : 'Messages du mois',
                        data: uMonthlyMsgsBarData.messages,
                        ...HG.partialBar('#5865F2'),
                        borderRadius: 6,
                        order: 2
                    },
                    {
                        label: (isEn ? 'Average (' : 'Moyenne (') + Math.round(avg).toLocaleString(langLocale) + ' ' + msgsUnit + ')',
                        data: Array(uMonthlyMsgsBarData.messages.length).fill(Math.round(avg)),
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
        HG.setPartial(userMonthlyMsgsChartInstance, uMonthlyMsgsBarData.partial);
        userMonthlyMsgsChartInstance.update();
        userChartInstances.push(userMonthlyMsgsChartInstance);
    }

    // Apply default granularity if day
    if (userGranularity === 'day') {
        switchUserGranularity('day');
    }

    // 5. User Servers Donut
    const uServersPieEl = document.getElementById('userServersPieData');
    if (uServersPieEl) {
        const pieData = JSON.parse(uServersPieEl.textContent);
        const ctx = document.getElementById('userServersPieChart').getContext('2d');

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
        userChartInstances.push(c5);
    }

    // 6. User Hourly Activity (24h)
    const uHourlyEl = document.getElementById('userHourlyActivityData');
    if (uHourlyEl) {
        const hourlyData = JSON.parse(uHourlyEl.textContent);
        const ctxH = document.getElementById('userHourlyChart').getContext('2d');
        const gradV = ctxH.createLinearGradient(0, 0, 0, 300);
        gradV.addColorStop(0, `rgba(${ACCENT_RGB}, 0.35)`);
        gradV.addColorStop(1, `rgba(${ACCENT_RGB}, 0.00)`);

        const cH = new Chart(ctxH, {
            type: 'line',
            data: {
                labels: hourlyData.labels,
                datasets: [
                    {
                        label: isEn ? 'Avg Voice (h/day)' : 'Moyenne vocale (h/jour)',
                        data: hourlyData.voice_hours,
                        borderColor: ACCENT,
                        backgroundColor: gradV,
                        borderWidth: 2.5,
                        tension: 0.35,
                        fill: true,
                        yAxisID: 'y',
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        pointBackgroundColor: ACCENT
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
                        ticks: { color: ACCENT, callback: v => v + ' ' + (isEn ? 'h/day' : 'h/jour') }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#818cf8', callback: v => v.toLocaleString(langLocale) }
                    }
                }
            }
        });
        userChartInstances.push(cH);
    }

    // 7. User Favorite Channels Doughnut
    const uFavChEl = document.getElementById('userFavoriteChannelsData');
    if (uFavChEl) {
        const favChData = JSON.parse(uFavChEl.textContent);
        const ctxFC = document.getElementById('userFavoriteChannelsChart').getContext('2d');
        const cFC = new Chart(ctxFC, {
            type: 'doughnut',
            data: {
                labels: favChData.labels,
                datasets: [{
                    data: favChData.hours,
                    backgroundColor: modernPalette.slice(0, favChData.labels.length),
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
        userChartInstances.push(cFC);
    }

    // Check URL Hash
    const validTabs = ['tab-activity', 'tab-charts', 'tab-servers', 'tab-badges'];
    const currentHash = window.location.hash ? window.location.hash.replace('#', '') : '';
    if (validTabs.includes(currentHash)) {
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
