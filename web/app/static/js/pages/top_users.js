/* Page script extracted from templates/top_users.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('top-filter-form');
    if (!form) return;

    // Period and Sort auto-submit
    form.querySelectorAll('select').forEach(function(select) {
        select.addEventListener('change', function() {
            form.requestSubmit();
        });
    });

    // Server Autocomplete Search
    const input = document.getElementById('topServerSearchInput');
    const hiddenId = document.getElementById('topFilterServerId');
    const clearBtn = document.getElementById('topServerClearBtn');
    const dropdown = document.getElementById('topServerDropdown');
    const resultsContainer = document.getElementById('topServerDropdownResults');
    const isEn = document.documentElement.lang === 'en' || PAGE_CFG.current_lang === 'en';

    if (!input || !hiddenId || !dropdown || !resultsContainer) return;

    const serverDataset = JSON.parse(document.getElementById('topServerDataset').textContent);

    let currentList = [];
    let selectedIndex = -1;

    function updateClearBtn() {
        if (clearBtn) {
            const hasVal = input.value.trim().length > 0 || (hiddenId.value && hiddenId.value !== 'all');
            clearBtn.style.display = hasVal ? 'inline-flex' : 'none';
        }
    }

    // Results were refreshed in place (live filters): the synced fields may have changed
    document.addEventListener('hg:live-updated', updateClearBtn);

    function openDropdown() {
        renderResults(input.value.trim());
        dropdown.style.display = 'block';
    }

    function closeDropdown() {
        dropdown.style.display = 'none';
        selectedIndex = -1;
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

    function selectServer(serverItem) {
        if (!serverItem || serverItem.id === 'all') {
            hiddenId.value = 'all';
            input.value = '';
        } else {
            hiddenId.value = serverItem.id;
            input.value = serverItem.name;
        }
        updateClearBtn();
        closeDropdown();
        form.requestSubmit();
    }

    function renderResults(q) {
        const query = q.toLowerCase();
        currentList = [];

        let html = '';

        // "All Servers" option (always present if query is empty or matches)
        const allLabel = isEn ? 'All servers' : 'Tous les serveurs';
        const allSub = isEn ? 'Global leaderboard across all servers' : 'Classement global tous serveurs';
        if (!query || allLabel.toLowerCase().includes(query) || 'global'.includes(query)) {
            currentList.push({ id: 'all', name: allLabel });
            html += `
                <div class="search-result-item" data-index="0" style="cursor: pointer;">
                    <div class="all-servers-icon-wrap">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                        </svg>
                    </div>
                    <div class="search-item-info">
                        <span class="search-item-name">${allLabel}</span>
                        <span class="search-item-sub">${allSub}</span>
                    </div>
                    <span class="search-item-badge">${isEn ? 'Select' : 'Choisir'}</span>
                </div>
            `;
        }

        // Filter server dataset
        let matched = [];
        if (!query) {
            matched = serverDataset.slice(0, 15);
        } else {
            matched = serverDataset.filter(s => 
                (s.name && s.name.toLowerCase().includes(query)) ||
                (s.id && s.id.includes(query))
            );
        }

        if (matched.length > 0) {
            const groupTitle = isEn ? `Servers (${matched.length})` : `Serveurs (${matched.length})`;
            html += `<div class="search-group-title">${groupTitle}</div>`;

            matched.forEach(s => {
                const idx = currentList.length;
                currentList.push(s);
                html += `
                    <div class="search-result-item" data-index="${idx}" style="cursor: pointer;">
                        <img src="${HG.esc(s.avatar)}" class="search-item-avatar border-server" alt="${HG.esc(s.name)}" data-fallback="/static/icons/server.png">
                        <div class="search-item-info">
                            <span class="search-item-name">${HG.esc(s.name)}</span>
                            <span class="search-item-sub">ID: ${HG.esc(s.id)}</span>
                        </div>
                        <span class="search-item-badge">${isEn ? 'Select' : 'Choisir'}</span>
                    </div>
                `;
            });
        }

        if (currentList.length === 0) {
            const emptyLabel = isEn
                ? `No server found for "${HG.esc(q)}"`
                : `Aucun serveur trouvé pour « ${HG.esc(q)} »`;
            html = `
                <div class="search-empty-state" style="padding: 22px 14px;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/><line x1="8" x2="14" y1="11" y2="11"/></svg>
                    <span>${emptyLabel}</span>
                </div>
            `;
        }

        resultsContainer.innerHTML = html;
        selectedIndex = -1;

        // Attach item events
        const renderedItems = resultsContainer.querySelectorAll('.search-result-item');
        renderedItems.forEach((elem) => {
            const itemIdx = parseInt(elem.getAttribute('data-index'), 10);
            elem.addEventListener('mouseenter', () => {
                selectedIndex = itemIdx;
                updateHighlight();
            });
            elem.addEventListener('click', (e) => {
                e.stopPropagation();
                selectServer(currentList[itemIdx]);
            });
        });
    }

    input.addEventListener('input', function() {
        updateClearBtn();
        renderResults(this.value.trim());
        dropdown.style.display = 'block';
    });

    input.addEventListener('focus', function() {
        openDropdown();
    });

    if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            hiddenId.value = 'all';
            input.value = '';
            updateClearBtn();
            closeDropdown();
            form.requestSubmit();
        });
    }

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
            if (dropdown.style.display !== 'none' && selectedIndex >= 0 && currentList[selectedIndex]) {
                e.preventDefault();
                selectServer(currentList[selectedIndex]);
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
});
