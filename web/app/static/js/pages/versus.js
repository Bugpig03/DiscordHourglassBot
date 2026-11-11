/* Page script extracted from templates/versus.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

function swapVersusInputs() {
    const i1 = document.getElementById('inputEntity1');
    const i2 = document.getElementById('inputEntity2');
    if (i1 && i2) {
        const tmp = i1.value;
        i1.value = i2.value;
        i2.value = tmp;
        document.getElementById('versusForm').submit();
    }
}

function setupVersusAutocomplete(inputId, dropdownId, resultsId, clearBtnId, groupId, type) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    const resultsContainer = document.getElementById(resultsId);
    const clearBtn = document.getElementById(clearBtnId);
    const group = document.getElementById(groupId);
    const form = document.getElementById('versusForm');

    if (!input || !dropdown || !resultsContainer) return;

    let searchTimer = null;
    let selectedIndex = -1;
    let currentResults = [];

    function updateClearBtn() {
        if (clearBtn) {
            clearBtn.style.display = input.value.trim().length > 0 ? 'inline-flex' : 'none';
        }
    }

    updateClearBtn();

    if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            input.value = '';
            updateClearBtn();
            closeDropdown();
            input.focus();
        });
    }

    function openDropdown() {
        document.querySelectorAll('.page-search-dropdown').forEach(d => {
            if (d !== dropdown) d.style.display = 'none';
        });
        document.querySelectorAll('.versus-input-group').forEach(g => {
            g.style.zIndex = '1';
        });
        if (group) group.style.zIndex = '105';
        dropdown.style.display = 'block';
    }

    function closeDropdown() {
        dropdown.style.display = 'none';
        selectedIndex = -1;
        if (group) group.style.zIndex = '1';
    }

    function updateHighlight() {
        const items = resultsContainer.querySelectorAll('.search-result-item');
        items.forEach((item, idx) => {
            if (idx === selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    function selectItem(itemData) {
        if (type === 'users') {
            input.value = itemData.username;
        } else {
            input.value = itemData.servername || itemData.server_id;
        }
        updateClearBtn();
        closeDropdown();

        // Check if the other input is already filled
        const otherId = inputId === 'inputEntity1' ? 'inputEntity2' : 'inputEntity1';
        const otherInput = document.getElementById(otherId);
        if (otherInput && otherInput.value.trim().length > 0) {
            form.submit();
        } else if (otherInput) {
            otherInput.focus();
        }
    }

    function performSearch(q) {
        if (!q) {
            closeDropdown();
            return;
        }

        fetch(`/api/search?q=${encodeURIComponent(q)}&type=${type}&limit=8`)
            .then(res => res.json())
            .then(data => {
                currentResults = type === 'users' ? (data.users || []) : (data.servers || []);
                selectedIndex = -1;
                openDropdown();

                if (currentResults.length === 0) {
                    const emptyLabel = type === 'users'
                        ? HG.tr('Aucun utilisateur trouvé pour « {q} »', 'No user found for "{q}"', { q: HG.esc(q) })
                        : HG.tr('Aucun serveur trouvé pour « {q} »', 'No server found for "{q}"', { q: HG.esc(q) });
                    resultsContainer.innerHTML = `
                        <div class="search-empty-state" style="padding: 22px 14px;">
                            <svg width="22" height="22" style="color: #72767d;" aria-hidden="true" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" data-px="search"><path d="M2 0h3v1h-3zM1 1h1v1h-1zM5 1h1v1h-1zM0 2h1v1h-1zM6 2h1v1h-1zM0 3h1v1h-1zM6 3h1v1h-1zM0 4h1v1h-1zM6 4h1v1h-1zM1 5h1v1h-1zM5 5h1v1h-1zM2 6h3v1h-3zM6 6h1v1h-1zM6 7h2v1h-2zM7 8h2v1h-2z"/><path d="M2 1h3v1h-3zM1 2h5v1h-5zM1 3h5v1h-5zM1 4h5v1h-5zM2 5h3v1h-3z" opacity="0.3"/></svg>
                            <span>${emptyLabel}</span>
                        </div>
                    `;
                    return;
                }

                const groupTitle = type === 'users'
                    ? HG.tr('Utilisateurs ({n})', 'Users ({n})', { n: currentResults.length })
                    : HG.tr('Serveurs ({n})', 'Servers ({n})', { n: currentResults.length });

                let html = `<div class="search-group-title">${groupTitle}</div>`;
                currentResults.forEach((item, i) => {
                    const avatar = item.avatar || (type === 'users' ? '/static/images/base_avatar_big.png' : '/static/icons/server.png');
                    const name = type === 'users' ? item.username : item.servername;
                    const sub = type === 'users'
                        ? HG.tr('Profil Utilisateur', 'User Profile')
                        : `ID: ${HG.esc(item.server_id)}`;
                    const badge = HG.tr('Choisir', 'Select');
                    const lvl = (type === 'users' && item.level)
                        ? `<span class="user-level-tag">${HG.tr('Nv.', 'Lv.')} ${HG.esc(item.level)}</span>`
                        : '';

                    html += `
                        <div class="search-result-item" data-index="${i}" style="cursor: pointer;">
                            <img src="${HG.esc(avatar)}" class="search-item-avatar" alt="${HG.esc(name)}" data-fallback="${type === 'users' ? '/static/images/base_avatar_big.png' : '/static/icons/server.png'}">
                            <div class="search-item-info">
                                <span class="search-item-name" style="display: inline-flex; align-items: center; gap: 6px;">
                                    <span>${HG.esc(name)}</span>
                                    ${lvl}
                                </span>
                                <span class="search-item-sub">${sub}</span>
                            </div>
                            <span class="search-item-badge">${badge}</span>
                        </div>
                    `;
                });
                resultsContainer.innerHTML = html;

                const renderedItems = resultsContainer.querySelectorAll('.search-result-item');
                renderedItems.forEach((rendered, idx) => {
                    rendered.addEventListener('mouseenter', () => {
                        selectedIndex = idx;
                        updateHighlight();
                    });
                    rendered.addEventListener('click', () => {
                        selectItem(currentResults[idx]);
                    });
                });
            })
            .catch(() => {
                resultsContainer.innerHTML = `<div class="search-empty-state" style="padding: 20px 14px;">Erreur de recherche.</div>`;
            });
    }

    input.addEventListener('input', function() {
        updateClearBtn();
        clearTimeout(searchTimer);
        const q = this.value.trim();
        if (q.length === 0) {
            closeDropdown();
            return;
        }
        searchTimer = setTimeout(() => performSearch(q), 180);
    });

    input.addEventListener('focus', function() {
        if (this.value.trim().length > 0) {
            if (currentResults.length > 0) {
                openDropdown();
            } else {
                performSearch(this.value.trim());
            }
        }
    });

    input.addEventListener('keydown', function(e) {
        const items = resultsContainer.querySelectorAll('.search-result-item');
        const count = items.length;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (dropdown.style.display === 'none') {
                openDropdown();
                return;
            }
            if (count > 0) {
                selectedIndex = (selectedIndex + 1) % count;
                updateHighlight();
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (count > 0) {
                selectedIndex = selectedIndex <= 0 ? count - 1 : selectedIndex - 1;
                updateHighlight();
            }
        } else if (e.key === 'Enter') {
            if (dropdown.style.display !== 'none' && selectedIndex >= 0 && currentResults[selectedIndex]) {
                e.preventDefault();
                selectItem(currentResults[selectedIndex]);
            }
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            closeDropdown();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const searchType = PAGE_CFG.tab;
    setupVersusAutocomplete('inputEntity1', 'dropdownEntity1', 'resultsEntity1', 'clearEntity1', 'groupEntity1', searchType);
    setupVersusAutocomplete('inputEntity2', 'dropdownEntity2', 'resultsEntity2', 'clearEntity2', 'groupEntity2', searchType);

    // The duel at a glance: each category as the share each side holds
    const radarEl = document.getElementById('versusRadarData');
    if (radarEl && document.getElementById('versusRadar')) {
        try {
            const r = JSON.parse(radarEl.textContent);
            if (r.axes && r.axes.length >= 3) drawVersusRadar(r);
        } catch (e) {
            console.error('Versus radar:', e);
        }
    }

    // Both curves over a shared timeline (cumulative voice hours, month by month)
    const rawDataElem = document.getElementById('versusChartData');
    if (!rawDataElem) return;
    let chartData = null;
    try {
        chartData = JSON.parse(rawDataElem.textContent);
    } catch(e) {
        return;
    }
    if (!chartData || !chartData.name1) return;
    if (!document.getElementById('versusChart')) return;

    const hoursUnit = PAGE_CFG.t_top_hours_unit;
    const points = list => (list || []).map(p => [new Date(p.x).getTime(), p.y]);
    const sides = [
        { name: chartData.name1, data: points(chartData.data1), color: '#717cf8' },
        { name: chartData.name2, data: points(chartData.data2), color: '#f43f5e' },
    ];
    const count = Math.max(sides[0].data.length, sides[1].data.length);
    const zoom = HG.zoom(count, { min: 30, compact: true, label: v => new Date(v).toLocaleDateString(HG.locale, { month: 'short', year: 'numeric' }) });
    const monthTitle = t => new Date(t).toLocaleDateString(HG.locale, { month: 'long', year: 'numeric' });
    HG.draw('versusChart', {
        grid: HG.grid({ top: 40, bottom: zoom.bottom }),
        legend: HG.legend({ textStyle: { color: '#d0d2d8', fontWeight: 'bold', fontSize: 13 } }),
        tooltip: HG.tooltip({
            formatter: ps => {
                const rows = HG.sortedRows(ps, v => `${HG.fmt(v, 1)} ${hoursUnit}`);
                const gap = rows.length === 2 ? rows[0].raw - rows[1].raw : null;
                return HG.tipHtml(monthTitle(ps[0].value[0]), rows, {
                    sub: gap != null && gap > 0 ? HG.tr('Écart : {n}', 'Gap: {n}', { n: `${HG.fmt(gap, 1)} ${hoursUnit}` }) : null,
                });
            },
        }),
        xAxis: HG.timeAxis({ splitNumber: 5, axisLabel: { color: HG.chartColors.muted, hideOverlap: true,
            formatter: v => new Date(v).toLocaleDateString(HG.locale, { month: 'short', year: '2-digit' }) } }),
        // The scale follows the period chosen with the slider (cumulative hours: a zoomed period sits far above zero)
        yAxis: HG.valueAxis({ min: HG.fitMin, axisLabel: { formatter: v => `${HG.fmt(v)} ${hoursUnit}` } }),
        dataZoom: zoom.dataZoom,
        series: sides.map(s => ({
            name: s.name, type: 'line', data: s.data, smooth: 0.32, showSymbol: false, symbolSize: 8,
            lineStyle: { width: 2.8, color: s.color }, itemStyle: { color: s.color, borderColor: '#fff', borderWidth: 2 },
            areaStyle: { color: HG.areaFill(s.color, 0.22) },
            emphasis: { focus: 'series', lineStyle: { width: 3.4 } },
            blur: { lineStyle: { opacity: 0.25 }, areaStyle: { opacity: 0.05 } },
        })),
    });
});


// Short branch names: the radar sits between the two sides, where the full category titles do not fit
const RADAR_SHORT = {
    hours: () => HG.tr('Vocal', 'Voice'),
    messages: () => HG.tr('Messages', 'Messages'),
    level: () => HG.tr('Niveau', 'Level'),
    activity_30d: () => HG.tr('30 jours', '30 days'),
    rank: () => HG.tr('Rang', 'Rank'),
    badges: () => HG.tr('Badges', 'Badges'),
    servers: () => HG.tr('Serveurs', 'Servers'),
    members: () => HG.tr('Membres', 'Members'),
};

function drawVersusRadar(r) {
    const C = HG.chartColors;
    const sides = [
        { name: r.name1, color: '#717cf8', values: r.axes.map(a => a.pct1), text: a => a.v1, side: '1' },
        { name: r.name2, color: '#f43f5e', values: r.axes.map(a => Math.round((100 - a.pct1) * 10) / 10), text: a => a.v2, side: '2' },
    ];
    const chart = HG.draw('versusRadar', {
        animationDuration: 900,
        // Our own tooltip (below): the stat of the branch under the pointer only
        tooltip: { show: false },
        radar: {
            indicator: r.axes.map(a => ({ name: RADAR_SHORT[a.key] ? RADAR_SHORT[a.key]() : a.label, max: 100 })),
            shape: 'polygon',
            radius: '66%',
            center: ['50%', '52%'],
            splitNumber: 4,
            axisName: { color: '#c9ccd3', fontWeight: 600, fontSize: 11 },
            axisNameGap: 8,
            splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
            splitArea: { areaStyle: { color: ['rgba(255, 255, 255, 0.015)', 'rgba(255, 255, 255, 0.035)'] } },
            axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        },
        series: [{
            type: 'radar',
            symbolSize: 6,
            // Hovering keeps both shapes in full: they are compared, not singled out
            emphasis: { focus: 'none', lineStyle: { width: 2.6 } },
            data: sides.map(s => ({
                name: s.name, value: s.values,
                lineStyle: { color: s.color, width: 2.2 }, itemStyle: { color: s.color },
                areaStyle: { color: HG.rgba(s.color, 0.25) },
            })),
        }],
    });
    bindRadarBranches(chart, r, sides);
}

/* The branch under the pointer (or the finger): its name lights up and a tooltip gives that one stat for both
   sides, the winning value in its side's color. Branches go anticlockwise from the top, like ECharts draws them. */
function bindRadarBranches(chart, r, sides) {
    if (!chart) return;
    const box = chart.getDom();
    const tip = document.createElement('div');
    tip.className = 'vs-radar-tip';
    tip.hidden = true;
    box.appendChild(tip);
    const names = r.axes.map(a => (RADAR_SHORT[a.key] ? RADAR_SHORT[a.key]() : a.label));
    let current = -1;

    function highlight(i) {
        if (i === current) return;
        current = i;
        chart.setOption({ radar: { indicator: r.axes.map((a, k) => ({
            name: names[k], max: 100, color: k === i ? '#ffffff' : '#c9ccd3',
        })) } });
    }

    function branchAt(x, y) {
        const radar = chart.getModel().getComponent('radar');
        const cs = radar && radar.coordinateSystem;
        if (!cs) return -1;
        const dx = x - cs.cx, dy = cs.cy - y;
        if (Math.hypot(dx, dy) > cs.r * 1.35) return -1;
        const n = r.axes.length;
        const angle = (Math.atan2(dy, dx) * 180 / Math.PI - 90 + 720) % 360;  // 0 at the top, anticlockwise
        return Math.round(angle / (360 / n)) % n;
    }

    function show(x, y) {
        const i = branchAt(x, y);
        if (i < 0) return hide();
        highlight(i);
        const a = r.axes[i];
        const lead = a.winner === 'tie' ? HG.tr('Égalité', 'Tie')
            : HG.tr('Avantage {name}', 'Edge to {name}', { name: a.winner === '1' ? sides[0].name : sides[1].name });
        tip.innerHTML = HG.tipHtml(a.label, [
            { color: sides[0].color, name: sides[0].name, value: a.v1, dim: a.winner === '2' },
            { color: sides[1].color, name: sides[1].name, value: a.v2, dim: a.winner === '1' },
        ], { sub: lead });
        tip.hidden = false;
        const w = tip.offsetWidth, h = tip.offsetHeight;
        const left = Math.min(Math.max(4, x + 14), box.clientWidth - w - 4);
        const top = Math.min(Math.max(4, y - h - 10), box.clientHeight - h - 4);
        tip.style.left = `${x + 14 + w > box.clientWidth ? Math.max(4, x - w - 14) : left}px`;
        tip.style.top = `${top}px`;
    }

    function hide() {
        tip.hidden = true;
        highlight(-1);
    }

    chart.getZr().on('mousemove', e => show(e.offsetX, e.offsetY));
    chart.getZr().on('click', e => show(e.offsetX, e.offsetY));
    chart.getZr().on('globalout', hide);
}
