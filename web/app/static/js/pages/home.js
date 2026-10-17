/* Page script extracted from templates/home.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

document.addEventListener('DOMContentLoaded', function() {
    const rawDataEl = document.getElementById('homeDailyChartData');
    if (!rawDataEl) return;
    try {
        const chartData = JSON.parse(rawDataEl.textContent);
        const ctx = document.getElementById('homeActivityChart').getContext('2d');
        
        const isEn = PAGE_CFG.current_lang === 'en';
        const hoursLabel = isEn ? 'Voice hours' : 'Heures en vocal';
        const msgsLabel = 'Messages';

        // Different marks for different units: bars for voice hours (left axis), a line for messages (right axis)
        const homeChart = new Chart(ctx, {
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        type: 'bar',
                        label: hoursLabel,
                        data: chartData.hours,
                        ...HG.partialBar('#38bdf8'),
                        borderRadius: 4,
                        maxBarThickness: 18,
                        yAxisID: 'y',
                        order: 2
                    },
                    {
                        type: 'line',
                        label: msgsLabel,
                        data: chartData.messages,
                        borderColor: '#10b981',
                        backgroundColor: '#10b981',
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
                        labels: { color: '#94a3b8', font: { size: 12, weight: '600' }, boxWidth: 12, usePointStyle: true, sort: (a, b) => a.datasetIndex - b.datasetIndex }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        borderColor: 'rgba(255, 255, 255, 0.12)',
                        borderWidth: 1,
                        padding: 10,
                        titleColor: '#ffffff',
                        bodyColor: '#cbd5e1',
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
                        ticks: { color: '#8b9bb0', font: { size: 11 }, maxTicksLimit: 8, maxRotation: 0 }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        title: { display: true, text: isEn ? 'Hours' : 'Heures', color: '#38bdf8', font: { size: 11, weight: '600' } },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#38bdf8', font: { size: 11 }, callback: (v) => HG.fmt(v) }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        title: { display: true, text: 'Messages', color: '#10b981', font: { size: 11, weight: '600' } },
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#10b981', font: { size: 11 }, callback: (v) => HG.fmt(v) }
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
