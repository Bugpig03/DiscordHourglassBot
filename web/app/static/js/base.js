/* Site-wide script (navbar, global search, Discord login popup) extracted from templates/base.html; Jinja values come from #hgBaseConfig. */
const BASE_CFG = JSON.parse(document.getElementById('hgBaseConfig').textContent);

        document.addEventListener('DOMContentLoaded', () => {
            const toggle = document.getElementById('mobileNavToggle');
            const menu = document.getElementById('appNavMenu');
            if (toggle && menu) {
                // Phone menu: the page behind is dimmed and locked (body.nav-open); closes on an outside tap,
                // on Escape, on a link, and when the screen becomes wide enough for the full navbar
                const setMenu = (isOpen) => {
                    menu.classList.toggle('open', isOpen);
                    toggle.classList.toggle('open', isOpen);
                    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                    document.body.classList.toggle('nav-open', isOpen);
                };
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    setMenu(!menu.classList.contains('open'));
                });

                document.addEventListener('click', (e) => {
                    if (menu.classList.contains('open') && !menu.contains(e.target) && !toggle.contains(e.target)) {
                        setMenu(false);
                    }
                });
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape' && menu.classList.contains('open')) setMenu(false);
                });
                menu.addEventListener('click', (e) => {
                    if (e.target.closest('a[href]') || e.target.closest('#quickSearchBtn')) setMenu(false);
                });
                window.matchMedia('(min-width: 1025px)').addEventListener('change', (e) => {
                    if (e.matches) setMenu(false);
                });

                // Dropdown hover buffer & mouseleave grace period
                document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
                    let hoverTimer;
                    dropdown.addEventListener('mouseenter', () => {
                        clearTimeout(hoverTimer);
                        dropdown.classList.add('is-hovered');
                    });
                    dropdown.addEventListener('mouseleave', () => {
                        hoverTimer = setTimeout(() => {
                            dropdown.classList.remove('is-hovered');
                        }, 220);
                    });
                });

                // Dropdown click toggle (touch & mobile friendly)
                document.querySelectorAll('.nav-dropdown-toggle').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const parent = btn.closest('.nav-dropdown');
                        if (parent) {
                            const wasOpen = parent.classList.contains('open');
                            document.querySelectorAll('.nav-dropdown.open').forEach(d => {
                                if (d !== parent) d.classList.remove('open');
                            });
                            parent.classList.toggle('open', !wasOpen);
                        }
                    });
                });

                document.addEventListener('click', (e) => {
                    if (!e.target.closest('.nav-dropdown')) {
                        document.querySelectorAll('.nav-dropdown.open').forEach(d => d.classList.remove('open'));
                    }
                });
            }

            // Global Search Input Event Listener
            const searchInput = document.getElementById('globalSearchInput');
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    const q = this.value.trim();
                    clearTimeout(searchDebounceTimer);
                    if (!q) {
                        renderInitialSearchHint();
                        return;
                    }
                    searchDebounceTimer = setTimeout(() => {
                        performGlobalSearch(q);
                    }, 180);
                });

                searchInput.addEventListener('keydown', function(e) {
                    const items = document.querySelectorAll('.search-result-item');
                    if (items.length === 0) return;

                    if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        currentSelectedIndex = (currentSelectedIndex + 1) % items.length;
                        updateSearchHighlight(items);
                    } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        currentSelectedIndex = (currentSelectedIndex - 1 + items.length) % items.length;
                        updateSearchHighlight(items);
                    } else if (e.key === 'Enter') {
                        e.preventDefault();
                        if (currentSelectedIndex >= 0 && currentSelectedIndex < items.length) {
                            items[currentSelectedIndex].click();
                        } else if (items.length > 0) {
                            items[0].click();
                        }
                    }
                });
            }
        });

        // Discord OAuth2 Popup Authentication
        // data-call="startDiscordLogin" on the Discord login links (navbar and /login)
        window.startDiscordLogin = function(_, event, link) {
            // Phones and tablets: same tab, no popup. A window opened by script is never handed to the
            // Discord app, a plain navigation can be (when the system links discord.com to the app).
            if (window.matchMedia('(pointer: coarse)').matches || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                if (event) event.preventDefault();
                window.location.href = link.href.replace(/([?&])popup=1(&|$)/, '$1popup=0$2');
                return;
            }
            openDiscordAuthPopup(event, link.href);
        };

        function openDiscordAuthPopup(event, authUrl) {
            if (event) event.preventDefault();
            const url = authUrl || BASE_CFG.oauth_popup_url;
            const width = 500;
            const height = 750;
            const left = window.screenX + Math.max(0, Math.floor((window.outerWidth - width) / 2));
            const top = window.screenY + Math.max(0, Math.floor((window.outerHeight - height) / 2));
            const separator = url.includes('?') ? '&' : '?';
            const finalUrl = url.includes('popup=') ? url : (url + separator + 'popup=1');

            const popup = window.open(
                finalUrl,
                'discord_oauth_popup',
                `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no`
            );

            if (popup && !popup.closed) {
                popup.focus();
            } else {
                window.location.href = finalUrl;
            }
        }

        window.addEventListener('message', function(event) {
            if (event.origin === window.location.origin && event.data && event.data.type === 'DISCORD_AUTH_SUCCESS') {
                window.location.reload();
            }
        });

        // Global Search Functions
        let searchDebounceTimer = null;
        let currentSelectedIndex = -1;

        // Pager: ← / → change page when the keyboard is not busy with a field or the search modal
        document.addEventListener('keydown', function(e) {
            if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
            const tag = (document.activeElement && document.activeElement.tagName) || '';
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || document.activeElement.isContentEditable) return;
            const modal = document.getElementById('globalSearchModal');
            if (modal && modal.style.display === 'flex') return;
            const pager = document.querySelector('.pager');
            const target = pager && pager.dataset[e.key === 'ArrowLeft' ? 'prev' : 'next'];
            if (!target) return;
            if (window.HG && HG.hasLiveRegion && HG.hasLiveRegion()) HG.liveLoad(target, { scroll: true });
            else window.location.href = target;
        });

        function openGlobalSearch() {
            const modal = document.getElementById('globalSearchModal');
            const input = document.getElementById('globalSearchInput');
            if (modal && input) {
                modal.style.display = 'flex';
                input.value = '';
                currentSelectedIndex = -1;
                renderInitialSearchHint();
                document.body.style.overflow = 'hidden';
                // Focus synchronously: the modal is already displayed, and a delay drops the first keystrokes
                input.focus();
            }
        }

        function closeGlobalSearch() {
            const modal = document.getElementById('globalSearchModal');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = '';
            }
        }

        // Called by data-call (arg, event, element): only a click on the backdrop itself closes the modal
        function closeGlobalSearchOnBackdrop(_, e) {
            if (e.target && e.target.id === 'globalSearchModal') {
                closeGlobalSearch();
            }
        }

        // Global Keyboard Shortcut (Ctrl+K or Cmd+K)
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                const modal = document.getElementById('globalSearchModal');
                if (modal && modal.style.display === 'flex') {
                    closeGlobalSearch();
                } else {
                    openGlobalSearch();
                }
            } else if (e.key === 'Escape') {
                closeGlobalSearch();
            }
        });

        function renderInitialSearchHint() {
            const container = document.getElementById('globalSearchResults');
            if (!container) return;
            const isEn = BASE_CFG.current_lang === 'en';
            container.innerHTML = `
                <div class="search-initial-hint">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.7;"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>
                    <span>${isEn ? 'Type a member or server name to search...' : 'Tapez le nom d\'un membre ou d\'un serveur...'}</span>
                </div>
            `;
        }

        function performGlobalSearch(q) {
            const container = document.getElementById('globalSearchResults');
            if (!container) return;
            const isEn = BASE_CFG.current_lang === 'en';

            fetch(`/api/search?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    currentSelectedIndex = -1;
                    const users = data.users || [];
                    const servers = data.servers || [];

                    if (users.length === 0 && servers.length === 0) {
                        container.innerHTML = `
                            <div class="search-empty-state">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/><line x1="8" x2="14" y1="11" y2="11"/></svg>
                                <span>${isEn ? `No results found for "${HG.esc(q)}"` : `Aucun résultat trouvé pour « ${HG.esc(q)} »`}</span>
                            </div>
                        `;
                        return;
                    }

                    let html = '';
                    if (users.length > 0) {
                        html += `<div class="search-group-title"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 6px;"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>${isEn ? 'Users' : 'Utilisateurs'} (${users.length})</div>`;
                        users.forEach(u => {
                            html += `
                                <a href="${HG.esc(u.url)}" class="search-result-item">
                                    <img src="${HG.esc(u.avatar)}" class="search-item-avatar" alt="${HG.esc(u.username)}">
                                    <div class="search-item-info">
                                        <span class="search-item-name" style="display: inline-flex; align-items: center; gap: 6px;">
                                            <span>${HG.esc(u.username)}</span>
                                            ${u.level ? `<span class="user-level-tag">${isEn ? 'Lv.' : 'Nv.'} ${HG.esc(u.level)}</span>` : ''}
                                        </span>
                                        <span class="search-item-sub">${isEn ? 'User Profile' : 'Profil Utilisateur'}</span>
                                    </div>
                                    <span class="search-item-badge">Voir</span>
                                </a>
                            `;
                        });
                    }

                    if (servers.length > 0) {
                        html += `<div class="search-group-title" style="margin-top: 14px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 6px;"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>${isEn ? 'Servers' : 'Serveurs'} (${servers.length})</div>`;
                        servers.forEach(s => {
                            html += `
                                <a href="${HG.esc(s.url)}" class="search-result-item">
                                    <img src="${HG.esc(s.avatar)}" class="search-item-avatar border-server" alt="${HG.esc(s.servername)}" data-fallback="/static/icons/server.png">
                                    <div class="search-item-info">
                                        <span class="search-item-name">${HG.esc(s.servername)}</span>
                                        <span class="search-item-sub">ID: ${HG.esc(s.server_id)}</span>
                                    </div>
                                    <span class="search-item-badge">Voir</span>
                                </a>
                            `;
                        });
                    }

                    container.innerHTML = html;
                })
                .catch(err => {
                    container.innerHTML = `<div class="search-empty-state">Erreur lors de la recherche.</div>`;
                });
        }

        function updateSearchHighlight(items) {
            items.forEach((item, index) => {
                if (index === currentSelectedIndex) {
                    item.classList.add('selected');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('selected');
                }
            });
        }
    
