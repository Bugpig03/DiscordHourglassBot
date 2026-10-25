/* Page script extracted from templates/home.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

document.addEventListener('DOMContentLoaded', function() {
    const rawDataEl = document.getElementById('homeDailyChartData');
    if (!rawDataEl) return;
    try {
        const chartData = JSON.parse(rawDataEl.textContent);
        const ctx = document.getElementById('homeActivityChart').getContext('2d');
        
        const hoursLabel = HG.tr('Heures en vocal', 'Voice hours');
        const msgsLabel = HG.tr('Messages', 'Messages');

        // Different marks for different units: bars for voice hours (left axis), a line for messages (right axis)
        const homeChart = new Chart(ctx, {
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        type: 'bar',
                        label: hoursLabel,
                        data: chartData.hours,
                        ...HG.partialBar('#717cf8'),
                        borderRadius: 4,
                        maxBarThickness: 18,
                        yAxisID: 'y',
                        order: 2
                    },
                    {
                        type: 'line',
                        label: msgsLabel,
                        data: chartData.messages,
                        borderColor: '#3fd1a0',
                        backgroundColor: '#3fd1a0',
                        borderWidth: 2.4,
                        tension: 0.35,
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        yAxisID: 'y1',
                        segment: HG.partialSegment,
                        order: 1
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
                        labels: { color: '#a3a6b0', font: { size: 12, weight: '600' }, boxWidth: 12, usePointStyle: true, sort: (a, b) => a.datasetIndex - b.datasetIndex }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(24, 25, 29, 0.95)',
                        borderColor: 'rgba(255, 255, 255, 0.12)',
                        borderWidth: 1,
                        padding: 10,
                        titleColor: '#ffffff',
                        bodyColor: '#d0d2d8',
                        callbacks: {
                            label: function(item) {
                                return item.dataset.yAxisID === 'y'
                                    ? ` ${hoursLabel} : ${HG.fmt(item.parsed.y, 1)} h`
                                    : ` ${msgsLabel} : ${HG.fmt(item.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#9a9da7', font: { size: 11 }, maxTicksLimit: 8, maxRotation: 0 }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        title: { display: true, text:HG.tr('Heures', 'Hours'), color: '#717cf8', font: { size: 11, weight: '600' } },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#717cf8', font: { size: 11 }, callback: (v) => HG.fmt(v) }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        title: { display: true, text: HG.tr('Messages', 'Messages'), color: '#3fd1a0', font: { size: 11, weight: '600' } },
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#3fd1a0', font: { size: 11 }, callback: (v) => HG.fmt(v) }
                    }
                }
            }
        });
        HG.setPartial(homeChart, chartData.partial);
        homeChart.update();
    } catch(e) {
        console.error('Error rendering home activity chart:', e);
    }
});
