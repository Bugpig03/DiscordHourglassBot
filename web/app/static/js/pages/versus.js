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
    const isEn = document.documentElement.lang === 'en' || PAGE_CFG.current_lang === 'en';

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
                    const emptyLabel = isEn
                        ? `No ${type} found for "${HG.esc(q)}"`
                        : `Aucun ${type === 'users' ? 'utilisateur' : 'serveur'} trouvé pour « ${HG.esc(q)} »`;
                    resultsContainer.innerHTML = `
                        <div class="search-empty-state" style="padding: 22px 14px;">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/><line x1="8" x2="14" y1="11" y2="11"/></svg>
                            <span>${emptyLabel}</span>
                        </div>
                    `;
                    return;
                }

                const groupTitle = type === 'users'
                    ? (isEn ? `Users (${currentResults.length})` : `Utilisateurs (${currentResults.length})`)
                    : (isEn ? `Servers (${currentResults.length})` : `Serveurs (${currentResults.length})`);

                let html = `<div class="search-group-title">${groupTitle}</div>`;
                currentResults.forEach((item, i) => {
                    const avatar = item.avatar || (type === 'users' ? '/static/images/base_avatar_big.png' : '/static/icons/server.png');
                    const name = type === 'users' ? item.username : item.servername;
                    const sub = type === 'users'
                        ? (isEn ? 'User Profile' : 'Profil Utilisateur')
                        : `ID: ${HG.esc(item.server_id)}`;
                    const badge = isEn ? 'Select' : 'Choisir';
                    const lvl = (type === 'users' && item.level)
                        ? `<span class="user-level-tag">${isEn ? 'Lv.' : 'Nv.'} ${HG.esc(item.level)}</span>`
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

    // Initialize Chart.js
    const rawDataElem = document.getElementById('versusChartData');
    if (!rawDataElem) return;
    let chartData = null;
    try {
        chartData = JSON.parse(rawDataElem.textContent);
    } catch(e) {
        return;
    }
    if (!chartData || !chartData.name1) return;

    const ctx = document.getElementById('versusChart');
    if (!ctx) return;

    const hoursUnit = PAGE_CFG.t_top_hours_unit;

    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: chartData.name1,
                    data: chartData.data1,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.12)',
                    fill: true,
                    tension: 0.32,
                    pointBackgroundColor: '#38bdf8',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    borderWidth: 2.8,
                },
                {
                    label: chartData.name2,
                    data: chartData.data2,
                    borderColor: '#f43f5e',
                    backgroundColor: 'rgba(244, 63, 94, 0.12)',
                    fill: true,
                    tension: 0.32,
                    pointBackgroundColor: '#f43f5e',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    borderWidth: 2.8,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#cbd5e1',
                        font: { size: 13, weight: 'bold' },
                        usePointStyle: true,
                        padding: 16
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.94)',
                    titleColor: '#ffffff',
                    bodyColor: '#e2e8f0',
                    borderColor: 'rgba(255, 255, 255, 0.12)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return ' ' + context.dataset.label + ': ' + context.parsed.y + ' ' + hoursUnit;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'month' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 0,
                        maxTicksLimit: 6,
                        autoSkip: true
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false },
                    ticks: {
                        color: '#94a3b8',
                        maxTicksLimit: 6,
                        callback: function(val) { return val + ' ' + hoursUnit; }
                    }
                }
            }
        }
    });
});
