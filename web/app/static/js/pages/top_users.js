/* Page script extracted from templates/top_users.html; values rendered by Jinja come from #hgPageConfig. */
const PAGE_CFG = JSON.parse(document.getElementById('hgPageConfig').textContent);

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('top-filter-form');
    if (!form) return;

    // Period, Sort and "Show bots" auto-submit
    form.querySelectorAll('select, input[type="checkbox"]').forEach(function(select) {
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
        const allLabel = HG.tr('Tous les serveurs', 'All servers');
        const allSub = HG.tr('Classement global tous serveurs', 'Global leaderboard across all servers');
        if (!query || allLabel.toLowerCase().includes(query) || 'global'.includes(query)) {
            currentList.push({ id: 'all', name: allLabel });
            html += `
                <div class="search-result-item" data-index="0" style="cursor: pointer;">
                    <div class="all-servers-icon-wrap">
                        <svg width="18" height="18" style="color: #717cf8;" aria-hidden="true" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" data-px="globe"><path d="M2 0h5v1h-5zM1 1h1v1h-1zM3 1h1v1h-1zM5 1h1v1h-1zM7 1h1v1h-1zM0 2h1v1h-1zM3 2h1v1h-1zM5 2h1v1h-1zM8 2h1v1h-1zM0 3h9v1h-9zM0 4h1v1h-1zM3 4h1v1h-1zM5 4h1v1h-1zM8 4h1v1h-1zM0 5h9v1h-9zM0 6h1v1h-1zM3 6h1v1h-1zM5 6h1v1h-1zM8 6h1v1h-1zM1 7h1v1h-1zM3 7h1v1h-1zM5 7h1v1h-1zM7 7h1v1h-1zM2 8h5v1h-5z"/></svg>
                    </div>
                    <div class="search-item-info">
                        <span class="search-item-name">${allLabel}</span>
                        <span class="search-item-sub">${allSub}</span>
                    </div>
                    <span class="search-item-badge">${HG.tr('Choisir', 'Select')}</span>
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
            const groupTitle = HG.tr('Serveurs ({n})', 'Servers ({n})', { n: matched.length });
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
                        <span class="search-item-badge">${HG.tr('Choisir', 'Select')}</span>
                    </div>
                `;
            });
        }

        if (currentList.length === 0) {
            const emptyLabel = HG.tr('Aucun serveur trouvé pour « {q} »', 'No server found for "{q}"', { q: HG.esc(q) });
            html = `
                <div class="search-empty-state" style="padding: 22px 14px;">
                    <svg width="22" height="22" style="color: #72767d;" aria-hidden="true" viewBox="0 0 9 9" fill="currentColor" shape-rendering="crispEdges" data-px="search"><path d="M2 0h3v1h-3zM1 1h1v1h-1zM5 1h1v1h-1zM0 2h1v1h-1zM6 2h1v1h-1zM0 3h1v1h-1zM6 3h1v1h-1zM0 4h1v1h-1zM6 4h1v1h-1zM1 5h1v1h-1zM5 5h1v1h-1zM2 6h3v1h-3zM6 6h1v1h-1zM6 7h2v1h-2zM7 8h2v1h-2z"/><path d="M2 1h3v1h-3zM1 2h5v1h-5zM1 3h5v1h-5zM1 4h5v1h-5zM2 5h3v1h-3z" opacity="0.3"/></svg>
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
