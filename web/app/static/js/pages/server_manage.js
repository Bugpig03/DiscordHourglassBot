/* Server management page: sections in tabs (kept in the address #section), dates shown in the visitor's own time,
   and the member search to choose a manager (owner only). */
(function () {
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const esc = v => HG.esc(v);

    // ---------------------------------------------------------------- tabs
    const buttons = Array.from(document.querySelectorAll('[data-sm-tab]'));
    const panes = Array.from(document.querySelectorAll('[data-sm-pane]'));
    function show(key, push) {
        if (!panes.some(p => p.dataset.smPane === key)) key = 'general';
        buttons.forEach(b => {
            const on = b.dataset.smTab === key;
            b.classList.toggle('active', on);
            b.setAttribute('aria-selected', String(on));
        });
        panes.forEach(p => { p.hidden = p.dataset.smPane !== key; });
        if (push) history.replaceState(null, '', `${location.pathname}#${key}`);
    }
    buttons.forEach(b => b.addEventListener('click', () => show(b.dataset.smTab, true)));
    const hash = location.hash.replace('#', '');
    if (hash) show(hash, false);
    // A saved form comes back with ?section=…&notice=…: keep only the section in the address
    if (location.search) {
        const active = (buttons.find(b => b.classList.contains('active')) || {}).dataset;
        history.replaceState(null, '', `${location.pathname}#${(active && active.smTab) || 'general'}`);
    }

    // ---------------------------------------------------------------- dates (stored in UTC)
    document.querySelectorAll('time[data-utc]').forEach(el => {
        const d = new Date(el.dataset.utc);
        if (isNaN(d)) return;
        el.dateTime = d.toISOString();
        el.textContent = d.toLocaleString(HG.locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    });

    // ---------------------------------------------------------------- level-up announcements: live preview
    const levels = document.getElementById('smLevels');
    if (levels) {
        const area = levels.querySelector('textarea[name="message"]');
        const preview = levels.querySelector('[data-preview]');
        const card = levels.querySelector('[data-preview-card]');
        const counter = levels.querySelector('[data-counter]');
        const toggle = levels.querySelector('[data-levels-enabled]');
        const switchLabel = levels.querySelector('.sm-switch-label');
        const body = levels.querySelector('[data-levels-body]');
        const max = Number(area.getAttribute('maxlength')) || 300;

        // Discord-like rendering of the text: **bold**, *italics*, the member as a mention or in bold
        const render = () => {
            const mention = levels.querySelector('input[name="mention"]').checked;
            const name = levels.dataset.user || T('membre', 'member');
            const template = area.value.trim() || levels.dataset.default;
            let html = esc(template)
                .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
                .replace(/\*(.+?)\*/g, '<i>$1</i>')
                .replace(/\n/g, '<br>');
            const who = mention ? `<span class="sm-mention">@${esc(name)}</span>` : `<b>${esc(name)}</b>`;
            html = html.replace(/\{(membre|member)\}/g, who).replace(/\{(niveau|level)\}/g, esc(levels.dataset.level || '12'))
                .replace(/\{(serveur|server)\}/g, esc(levels.dataset.server || ''));
            preview.innerHTML = html;
            card.hidden = !levels.querySelector('input[name="with_card"]').checked;
            counter.textContent = `${area.value.length} / ${max}`;
            switchLabel.textContent = toggle.checked ? switchLabel.dataset.on : switchLabel.dataset.off;
            body.classList.toggle('is-off', !toggle.checked);
            body.inert = !toggle.checked; // turned off: nothing to change until it is turned on (values kept)
        };
        levels.addEventListener('input', render);
        levels.addEventListener('change', render);
        // Variables inserted where the cursor is
        levels.querySelectorAll('[data-var]').forEach(btn => btn.addEventListener('click', () => {
            const v = btn.dataset.var;
            const start = area.selectionStart ?? area.value.length, end = area.selectionEnd ?? area.value.length;
            if (area.value.length - (end - start) + v.length > max) return;
            area.value = area.value.slice(0, start) + v + area.value.slice(end);
            area.focus();
            area.selectionStart = area.selectionEnd = start + v.length;
            render();
        }));
        render();
    }

    // ---------------------------------------------------------------- reports: each switch dims its card
    document.querySelectorAll('[data-report]').forEach(card => {
        const toggle = card.querySelector('[data-report-enabled]');
        const label = card.querySelector('.sm-switch-label');
        const body = card.querySelector('[data-report-body]');
        const sync = () => {
            label.textContent = toggle.checked ? label.dataset.on : label.dataset.off;
            body.classList.toggle('is-off', !toggle.checked);
            body.inert = !toggle.checked;
        };
        toggle.addEventListener('change', sync);
        sync();
    });
    // Private mode: the switch saves at once
    document.querySelectorAll('form[data-autosubmit]').forEach(f => f.addEventListener('change', () => f.submit()));

    // A test sends the saved settings: after a change, saving comes first
    const reportsForm = document.getElementById('smReports');
    if (reportsForm) {
        const dirty = () => {
            reportsForm.querySelectorAll('[data-report-test]').forEach(b => { b.disabled = true; });
            reportsForm.querySelectorAll('[data-test-hint]').forEach(h => { h.hidden = false; });
        };
        reportsForm.addEventListener('change', dirty);
        reportsForm.addEventListener('input', dirty);
    }

    // ---------------------------------------------------------------- automatic roles: rules editor
    // A rule is a progression of tiers, each tier a role and its conditions; the rule keeps the highest tier reached
    // or stacks them all. Drawn from the JSON of the page and sent back as JSON (rules_json) on save. The figure of
    // each tier counts the members who would have its role today, from their activity (no names) read like the bot.
    const rolesForm = document.getElementById('smRoles');
    if (rolesForm) {
        const data = JSON.parse(document.getElementById('smRoleData').textContent || '{}');
        const list = rolesForm.querySelector('[data-rules]');
        const empty = rolesForm.querySelector('[data-rules-empty]');
        const addRule = rolesForm.querySelector('[data-add-rule]');
        const counter = rolesForm.querySelector('[data-rule-count]');
        const ruleTpl = document.getElementById('smRuleTpl');
        const tierTpl = document.getElementById('smTierTpl');
        const condTpl = document.getElementById('smCondTpl');
        const maxRules = Number(rolesForm.dataset.maxRules) || 10;
        const maxTiers = Number(rolesForm.dataset.maxTiers) || 10;
        const maxTiersTotal = Number(rolesForm.dataset.maxTiersTotal) || 30;
        const maxConds = Number(rolesForm.dataset.maxConditions) || 3;
        const metrics = data.metrics || [];
        const grants = data.grants || {};
        const toggle = rolesForm.querySelector('[data-roles-enabled]');
        const switchLabel = toggle.closest('.sm-switch').querySelector('.sm-switch-label');

        // Index in a member's row: [voice hours, voice hours 30 d, messages, messages 30 d, level]
        const column = c => c.metric === 'level' ? 4 : (c.metric === 'voice' ? 0 : 2) + (c.scope === '30d' ? 1 : 0);
        const condMet = (c, row) => row[column(c)] >= c.min;
        const tierMet = (t, row) => t.conditions.length > 0 && (t.match === 'any' ? t.conditions.some(c => condMet(c, row)) : t.conditions.every(c => condMet(c, row)));

        const readCond = li => ({
            metric: li.querySelector('[data-cond-metric]').value,
            scope: li.querySelector('[data-cond-scope]').value,
            min: Math.max(0, Number(li.querySelector('[data-cond-min]').value) || 0),
        });
        const readTier = li => ({
            role_id: li.querySelector('[data-tier-role]').value,
            match: li.querySelector('[data-tier-match]').value,
            conditions: Array.from(li.querySelector('[data-conds]').children).map(readCond),
        });
        const readRule = li => ({
            keep_highest: li.dataset.mode !== '0',
            tiers: Array.from(li.querySelector('[data-tiers]').children).map(readTier),
        });

        function addCond(tier, cond) {
            const li = condTpl.content.firstElementChild.cloneNode(true);
            if (cond) {
                li.querySelector('[data-cond-metric]').value = cond.metric;
                li.querySelector('[data-cond-scope]').value = cond.scope || 'total';
                li.querySelector('[data-cond-min]').value = cond.min;
            }
            tier.querySelector('[data-conds]').appendChild(li);
        }

        function addTier(rule, tier) {
            const li = tierTpl.content.firstElementChild.cloneNode(true);
            const tiers = rule.querySelector('[data-tiers]');
            if (tier) {
                li.querySelector('[data-tier-role]').value = tier.role_id;
                li.querySelector('[data-tier-match]').value = tier.match || 'all';
            }
            tiers.appendChild(li);
            if (tier && tier.conditions && tier.conditions.length) {
                tier.conditions.forEach(c => addCond(li, c));
            } else {
                // A new tier starts from the previous one's criteria, a step higher: 10 h -> 50 h -> 100 h…
                const prev = li.previousElementSibling ? readTier(li.previousElementSibling) : null;
                if (prev && prev.conditions.length) {
                    li.querySelector('[data-tier-match]').value = prev.match;
                    prev.conditions.forEach(c => addCond(li, { ...c, min: Math.max(1, c.min * 2) }));
                } else {
                    addCond(li, null);
                }
            }
        }

        function addRuleItem(rule) {
            const li = ruleTpl.content.firstElementChild.cloneNode(true);
            li.dataset.mode = rule && rule.keep_highest === false ? '0' : '1';
            list.appendChild(li);
            (rule && rule.tiers && rule.tiers.length ? rule.tiers : [null]).forEach(t => addTier(li, t));
        }

        const fmt = n => new Intl.NumberFormat(HG.locale).format(n);
        const totalTiers = () => list.querySelectorAll('.sm-tier').length;
        function refresh() {
            const rules = Array.from(list.children);
            const full = totalTiers() >= maxTiersTotal;
            rules.forEach((ruleLi, i) => {
                const rule = readRule(ruleLi);
                const tierItems = Array.from(ruleLi.querySelector('[data-tiers]').children);
                // Members who would have each tier's role: with "highest only", only the last tier reached counts
                const counts = rule.tiers.map(() => 0);
                metrics.forEach(row => {
                    if (rule.keep_highest) {
                        for (let k = rule.tiers.length - 1; k >= 0; k--) if (tierMet(rule.tiers[k], row)) { counts[k]++; break; }
                    } else {
                        rule.tiers.forEach((t, k) => { if (tierMet(t, row)) counts[k]++; });
                    }
                });
                const several = tierItems.length > 1;
                ruleLi.querySelector('[data-rule-num]').textContent = T('Règle {n}', 'Rule {n}', { n: i + 1 });
                ruleLi.querySelector('[data-rule-mode]').hidden = !several;
                ruleLi.querySelectorAll('[data-rule-mode] button').forEach(b => {
                    const on = b.dataset.mode === ruleLi.dataset.mode;
                    b.classList.toggle('is-on', on);
                    b.setAttribute('aria-pressed', String(on));
                });
                ruleLi.querySelector('[data-rule-up]').disabled = i === 0;
                ruleLi.querySelector('[data-rule-down]').disabled = i === rules.length - 1;
                ruleLi.querySelector('[data-add-tier]').hidden = tierItems.length >= maxTiers || full;
                ruleLi.classList.toggle('is-ladder', several);

                tierItems.forEach((li, k) => {
                    li.querySelector('[data-tier-num]').textContent = several ? T('Palier {n}', 'Tier {n}', { n: k + 1 }) : T('Rôle', 'Role');
                    const conds = Array.from(li.querySelector('[data-conds]').children);
                    conds.forEach(c => {
                        const level = c.querySelector('[data-cond-metric]').value === 'level';
                        const scope = c.querySelector('[data-cond-scope]');
                        scope.disabled = level;
                        if (level) scope.value = 'total';
                        if (scope._hgButton) scope._hgButton.hidden = level;
                        c.querySelector('[data-cond-delete]').hidden = conds.length < 2;
                    });
                    li.querySelector('[data-tier-match-wrap]').hidden = conds.length < 2;
                    li.querySelector('[data-add-cond]').hidden = conds.length >= maxConds;
                    li.querySelector('[data-tier-up]').hidden = li.querySelector('[data-tier-down]').hidden = !several;
                    li.querySelector('[data-tier-up]').disabled = k === 0;
                    li.querySelector('[data-tier-down]').disabled = k === tierItems.length - 1;
                    li.querySelector('[data-tier-delete]').hidden = !several;
                    const role = li.querySelector('[data-tier-role]');
                    const option = role.options[role.selectedIndex];
                    li.querySelector('[data-tier-blocked]').hidden = !(option && option.dataset.blocked);
                    li.querySelector('[data-tier-danger]').hidden = !(option && option.dataset.danger);
                    const given = grants[role.value] || 0;
                    li.querySelector('[data-tier-count]').innerHTML = role.value
                        ? `<b>${fmt(counts[k])}</b> ${esc(T('membre(s)', 'member(s)'))}${given ? `<small>${esc(T('{n} déjà donnés par le bot', '{n} already given by the bot', { n: fmt(given) }))}</small>` : ''}`
                        : '';
                });
            });
            empty.hidden = rules.length > 0;
            addRule.hidden = rules.length >= maxRules || full;
            counter.textContent = `${rules.length} / ${maxRules}`;
            switchLabel.textContent = toggle.checked ? switchLabel.dataset.on : switchLabel.dataset.off;
            rolesForm.querySelectorAll('[data-roles-body]').forEach(b => { b.classList.toggle('is-off', !toggle.checked); b.inert = !toggle.checked; });
        }

        (data.rules || []).forEach(addRuleItem);
        // New selects get their Arène button just after being added (select.js): drawn again once they have it
        const refreshSoon = () => { refresh(); setTimeout(refresh, 0); };
        addRule.addEventListener('click', () => { addRuleItem(null); refreshSoon(); });
        list.addEventListener('click', e => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const rule = btn.closest('.sm-rule');
            const tier = btn.closest('.sm-tier');
            if (btn.closest('[data-rule-mode]')) rule.dataset.mode = btn.dataset.mode;
            else if (btn.matches('[data-add-tier]')) addTier(rule, null);
            else if (btn.matches('[data-add-cond]')) addCond(tier, null);
            else if (btn.matches('[data-cond-delete]')) btn.closest('.sm-cond').remove();
            else if (btn.matches('[data-tier-delete]')) tier.remove();
            else if (btn.matches('[data-tier-up]') && tier.previousElementSibling) tier.previousElementSibling.before(tier);
            else if (btn.matches('[data-tier-down]') && tier.nextElementSibling) tier.nextElementSibling.after(tier);
            else if (btn.matches('[data-rule-delete]')) rule.remove();
            else if (btn.matches('[data-rule-up]') && rule.previousElementSibling) rule.previousElementSibling.before(rule);
            else if (btn.matches('[data-rule-down]') && rule.nextElementSibling) rule.nextElementSibling.after(rule);
            else return;
            refreshSoon();
        });
        rolesForm.addEventListener('input', refresh);
        rolesForm.addEventListener('change', refresh);
        rolesForm.addEventListener('submit', () => {
            rolesForm.querySelector('input[name="rules_json"]').value = JSON.stringify(Array.from(list.children).map(readRule));
        });
        refreshSoon();
    }

    // ---------------------------------------------------------------- choose a manager
    const form = document.getElementById('smAddManager');
    if (!form) return;
    const input = form.querySelector('input[type="search"]');
    const list = form.querySelector('.tl-suggest');
    const hidden = form.querySelector('input[name="user_id"]');
    let found = [], active = -1, timer = 0, call = null;

    function close() { list.hidden = true; list.innerHTML = ''; found = []; active = -1; }
    function render() {
        if (!found.length) {
            list.innerHTML = input.value.trim() ? `<li class="tl-suggest-empty">${esc(T('Aucun membre trouvé', 'No member found'))}</li>` : '';
            list.hidden = !input.value.trim();
            return;
        }
        list.innerHTML = found.map((m, i) => `<li role="option" data-index="${i}" class="${i === active ? 'is-active' : ''}" aria-selected="${i === active}">
            <img src="${esc(m.avatar || '/static/images/base_avatar_big.png')}" alt="" width="22" height="22" loading="lazy">
            <span>@${esc(m.name)}${m.nickname ? ` <small>${esc(m.nickname)}</small>` : ''}</span></li>`).join('');
        list.hidden = false;
    }
    function pick(m) {
        if (!m) return;
        hidden.value = m.id;
        input.value = `@${m.name}`;
        close();
        form.submit();
    }
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (!q) return close();
        timer = setTimeout(async () => {
            if (call) call.abort();
            call = new AbortController();
            try {
                const res = await fetch(`${input.dataset.membersUrl}?q=${encodeURIComponent(q)}`, { signal: call.signal, credentials: 'same-origin' });
                found = (await res.json()).members || [];
                active = found.length ? 0 : -1;
                render();
            } catch (e) { /* aborted */ }
        }, 180);
    });
    input.addEventListener('keydown', e => {
        if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && found.length) {
            e.preventDefault();
            active = (active + (e.key === 'ArrowDown' ? 1 : -1) + found.length) % found.length;
            render();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (active >= 0) pick(found[active]);
        } else if (e.key === 'Escape') {
            close();
        }
    });
    list.addEventListener('mousedown', e => {
        const li = e.target.closest('[data-index]');
        if (li) { e.preventDefault(); pick(found[Number(li.dataset.index)]); }
    });
    input.addEventListener('blur', () => setTimeout(close, 120));
})();
