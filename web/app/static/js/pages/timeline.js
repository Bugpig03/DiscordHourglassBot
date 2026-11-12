/* Timeline (Outils menu): a leaderboard race built by the visitor.
   Every setting lives in the address (srv, metric, top, users, from, to, mode, speed), so a copied link opens the
   same race. Needs charts.js (HG, ECharts). */
(function () {
    const HG = window.HG = window.HG || {};
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const esc = v => HG.esc(v);
    const $ = id => document.getElementById(id);
    const cfg = JSON.parse(($('tlConfig') || {}).textContent || '{}');
    const PALETTE = HG.RANK_COLORS;
    const MAX_PICKS = cfg.max_picks || 20;
    const DEFAULTS = { srv: '', metric: 'voice', who: 'top', top: cfg.default_top || 20, from: '', to: '', view: 'race', speed: 1, curve: 'cumul' };
    const SPEEDS = [0.5, 1, 2, 4];

    const stage = $('tlStage');
    const builder = $('tlBuilder');
    let state = readUrl();
    let data = null;
    let request = null;
    let rangeKey = '';
    let linesChart = null;
    let filling = false;  // the period lists are being refilled: their "change" events are not the visitor's

    /* ------------------------------------------------------------ address */
    function readUrl() {
        const q = new URLSearchParams(location.search);
        const s = Object.assign({}, DEFAULTS, { picks: [] });
        if (q.get('srv') && cfg.servers.some(x => x.id === q.get('srv'))) s.srv = q.get('srv');
        if (q.get('metric') === 'messages') s.metric = 'messages';
        const top = Number(q.get('top'));
        if (cfg.tops.includes(top)) s.top = top;
        const ids = (q.get('users') || '').split(',').filter(id => /^\d{1,20}$/.test(id));
        s.picks = [...new Set(ids)].slice(0, MAX_PICKS).map(id => ({ id, name: '', avatar: null }));
        if (s.picks.length || q.get('who') === 'picks') s.who = 'picks';
        if (/^\d{4}-\d{2}$/.test(q.get('from') || '')) s.from = q.get('from');
        if (/^\d{4}-\d{2}$/.test(q.get('to') || '')) s.to = q.get('to');
        if (q.get('mode') === 'lines') s.view = 'lines';
        if (SPEEDS.includes(Number(q.get('speed')))) s.speed = Number(q.get('speed'));
        return s;
    }

    function params(forApi) {
        const q = new URLSearchParams();
        if (state.srv) q.set('srv', state.srv);
        if (state.metric !== DEFAULTS.metric) q.set('metric', state.metric);
        if (state.who === 'picks') {
            if (state.picks.length) q.set('users', state.picks.map(p => p.id).join(','));
            else if (!forApi) q.set('who', 'picks');
        } else if (state.top !== DEFAULTS.top) q.set('top', state.top);
        if (state.from) q.set('from', state.from);
        if (state.to) q.set('to', state.to);
        if (!forApi) {
            if (state.view !== DEFAULTS.view) q.set('mode', state.view);
            if (state.speed !== DEFAULTS.speed) q.set('speed', state.speed);
        }
        return q;
    }

    function writeUrl() {
        const q = params(false).toString();
        history.replaceState(null, '', location.pathname + (q ? `?${q}` : ''));
    }

    /* ------------------------------------------------------------ controls */
    function setGroup(name, value) {
        builder.parentElement.querySelectorAll(`[data-tl-group="${name}"] [data-value]`).forEach(b => {
            const on = b.dataset.value === String(value);
            b.classList.toggle('active', on);
            b.setAttribute('aria-pressed', String(on));
        });
    }

    function syncControls() {
        setGroup('metric', state.metric);
        setGroup('who', state.who);
        setGroup('top', state.top);
        setGroup('view', state.view);
        setGroup('speed', state.speed);
        setGroup('curve', state.curve);
        const scope = $('tlScope');
        if (scope.value !== state.srv) { scope.value = state.srv; scope.dispatchEvent(new Event('change')); }
        builder.querySelectorAll('[data-tl-show]').forEach(el => { el.hidden = el.dataset.tlShow !== state.who; });
        stage.querySelectorAll('[data-tl-show-view]').forEach(el => { el.hidden = el.dataset.tlShowView !== state.view; });
        renderChips();
    }

    function bindGroup(name, apply) {
        builder.parentElement.querySelectorAll(`[data-tl-group="${name}"] [data-value]`).forEach(b => {
            b.addEventListener('click', () => { apply(b.dataset.value); setGroup(name, b.dataset.value); });
        });
    }

    function change(patch, refetch = true) {
        Object.assign(state, patch);
        syncControls();
        writeUrl();
        if (refetch) load(); else render();
    }

    bindGroup('metric', v => change({ metric: v }));
    bindGroup('who', v => change({ who: v }));
    bindGroup('top', v => change({ top: Number(v) }));
    bindGroup('view', v => change({ view: v }, false));
    bindGroup('curve', v => change({ curve: v }, false));
    bindGroup('speed', v => { state.speed = Number(v); writeUrl(); });

    $('tlScope').addEventListener('change', e => {
        if (e.target.value !== state.srv) change({ srv: e.target.value });
    });

    function monthLabel(ym) {
        const [y, m] = ym.split('-').map(Number);
        return new Date(y, m - 1, 1).toLocaleDateString(HG.locale, { month: 'short', year: 'numeric' });
    }
    function monthsBetween(a, b) {
        const out = [];
        let [y, m] = a.split('-').map(Number);
        const [y2, m2] = b.split('-').map(Number);
        while (y < y2 || (y === y2 && m <= m2)) {
            out.push(`${y}-${String(m).padStart(2, '0')}`);
            m += 1;
            if (m > 12) { m = 1; y += 1; }
        }
        return out;
    }
    function shiftMonth(ym, delta) {
        const [y, m] = ym.split('-').map(Number);
        const d = new Date(y, m - 1 + delta, 1);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    }

    // Start and end lists, filled from the months that hold data in this scope
    function fillPeriod() {
        const from = $('tlFrom'), to = $('tlTo');
        const range = data && data.range;
        const key = range ? `${range.min}|${range.max}` : '';
        if (key !== rangeKey) {
            rangeKey = key;
            const months = range ? monthsBetween(range.min, range.max) : [];
            const html = months.map(ym => `<option value="${ym}">${esc(monthLabel(ym))}</option>`).join('');
            from.innerHTML = html;
            to.innerHTML = months.slice().reverse().map(ym => `<option value="${ym}">${esc(monthLabel(ym))}</option>`).join('');
        }
        const period = data && data.period;
        if (period) {
            from.value = period.from;
            to.value = period.to;
        }
        filling = true;
        [from, to].forEach(sel => { sel.disabled = !period; sel.dispatchEvent(new Event('change')); });
        filling = false;
        markPreset();
    }
    function periodChanged() {
        if (filling || !data || !data.range) return;
        let a = $('tlFrom').value, b = $('tlTo').value;
        if (a > b) [a, b] = [b, a];
        const from = a === data.range.min ? '' : a;
        const to = b === data.range.max ? '' : b;
        if (from !== state.from || to !== state.to) change({ from, to });
    }
    $('tlFrom').addEventListener('change', periodChanged);
    $('tlTo').addEventListener('change', periodChanged);

    function presetPeriod(kind) {
        const max = (data && data.range && data.range.max) || new Date().toISOString().slice(0, 7);
        if (kind === 'all') return { from: '', to: '' };
        if (kind === '12') return { from: shiftMonth(max, -11), to: '' };
        return { from: `${max.slice(0, 4)}-01`, to: '' };
    }
    function markPreset() {
        builder.querySelectorAll('[data-preset]').forEach(b => {
            const p = presetPeriod(b.dataset.preset);
            const min = data && data.range && data.range.min;
            const from = p.from && min && p.from <= min ? '' : p.from;
            b.classList.toggle('active', from === state.from && p.to === state.to);
        });
    }
    builder.querySelectorAll('[data-preset]').forEach(b => b.addEventListener('click', () => {
        const p = presetPeriod(b.dataset.preset);
        const min = data && data.range && data.range.min;
        change({ from: p.from && min && p.from <= min ? '' : p.from, to: p.to });
    }));

    /* ------------------------------------------------------------ hand-picked members */
    const search = $('tlSearch');
    const suggest = $('tlSuggest');
    let found = [], active = -1, searchTimer = 0, searchCall = null;

    function renderChips() {
        const list = $('tlChips');
        list.innerHTML = state.picks.map((p, k) => {
            const missing = data && data.skipped && data.skipped.find(s => s.id === p.id);
            const color = PALETTE[k % (PALETTE.length - 1)];
            const name = p.name || (missing ? T('Membre indisponible', 'Member unavailable') : '…');
            return `<li class="tl-chip${missing ? ' is-missing' : ''}" style="--chip: ${color}">
                ${p.avatar ? `<img src="${esc(p.avatar.split('?')[0])}?size=32" alt="" width="20" height="20" loading="lazy" data-fallback="hide">` : '<i></i>'}
                <span>${esc(name)}</span>
                <button type="button" data-remove="${esc(p.id)}" aria-label="${esc(T('Retirer {name}', 'Remove {name}', { name }))}">×</button>
            </li>`;
        }).join('');
        $('tlPickCount').textContent = `${state.picks.length} / ${MAX_PICKS}`;
        const full = state.picks.length >= MAX_PICKS;
        search.disabled = full;
        search.placeholder = full ? T('Maximum atteint', 'Maximum reached') : T('Ajouter un membre…', 'Add a member…');
        const me = $('tlMe');
        if (me) me.hidden = full || state.picks.some(p => p.id === me.dataset.id);
    }
    $('tlChips').addEventListener('click', e => {
        const btn = e.target.closest('[data-remove]');
        if (btn) change({ picks: state.picks.filter(p => p.id !== btn.dataset.remove) });
    });

    function addPick(member) {
        if (!member || state.picks.length >= MAX_PICKS || state.picks.some(p => p.id === member.id)) return;
        search.value = '';
        closeSuggest();
        change({ picks: state.picks.concat([{ id: member.id, name: member.name, avatar: member.avatar || null }]) });
        search.focus();
    }
    const meBtn = $('tlMe');
    if (meBtn) meBtn.addEventListener('click', () => addPick({ id: meBtn.dataset.id, name: meBtn.dataset.name, avatar: meBtn.dataset.avatar }));

    function closeSuggest() {
        suggest.hidden = true;
        suggest.innerHTML = '';
        found = [];
        active = -1;
        search.removeAttribute('aria-activedescendant');
    }
    function showSuggest() {
        const q = search.value.trim();
        if (!found.length) {
            suggest.innerHTML = q ? `<li class="tl-suggest-empty">${esc(T('Aucun membre trouvé', 'No member found'))}</li>` : '';
            suggest.hidden = !q;
            return;
        }
        suggest.innerHTML = found.map((m, i) => `<li role="option" id="tlOpt${i}" data-index="${i}" class="${i === active ? 'is-active' : ''}" aria-selected="${i === active}">
            <img src="${esc((m.avatar || '/static/images/base_avatar_big.png').split('?')[0])}${m.avatar ? '?size=32' : ''}" alt="" width="22" height="22" loading="lazy">
            <span>${esc(m.name)}</span></li>`).join('');
        suggest.hidden = false;
        if (active >= 0) search.setAttribute('aria-activedescendant', `tlOpt${active}`);
    }
    search.addEventListener('input', () => {
        clearTimeout(searchTimer);
        const q = search.value.trim();
        if (!q) return closeSuggest();
        searchTimer = setTimeout(async () => {
            if (searchCall) searchCall.abort();
            searchCall = new AbortController();
            try {
                const url = `${cfg.members_api}?${new URLSearchParams(Object.assign({ q }, state.srv ? { srv: state.srv } : {}))}`;
                const res = await fetch(url, { signal: searchCall.signal });
                const json = await res.json();
                found = (json.members || []).filter(m => !state.picks.some(p => p.id === m.id));
                active = found.length ? 0 : -1;
                showSuggest();
            } catch (err) { /* aborted or offline: the list stays as it was */ }
        }, 180);
    });
    search.addEventListener('keydown', e => {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            if (!found.length) return;
            e.preventDefault();
            active = (active + (e.key === 'ArrowDown' ? 1 : -1) + found.length) % found.length;
            showSuggest();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (active >= 0) addPick(found[active]);
        } else if (e.key === 'Escape') {
            closeSuggest();
        }
    });
    suggest.addEventListener('mousedown', e => {
        const li = e.target.closest('[data-index]');
        if (li) { e.preventDefault(); addPick(found[Number(li.dataset.index)]); }
    });
    search.addEventListener('blur', () => setTimeout(closeSuggest, 120));

    /* ------------------------------------------------------------ share and reset */
    $('tlShare').addEventListener('click', async () => {
        const btn = $('tlShare');
        const label = btn.querySelector('span');
        const before = label.textContent;
        try {
            await navigator.clipboard.writeText(location.href);
            label.textContent = T('Lien copié !', 'Link copied!');
        } catch (err) {
            window.prompt(T('Copie ce lien :', 'Copy this link:'), location.href);
        }
        btn.classList.add('is-done');
        setTimeout(() => { label.textContent = before; btn.classList.remove('is-done'); }, 1800);
    });
    $('tlReset').addEventListener('click', () => change(Object.assign({}, DEFAULTS, { picks: [] })));

    /* ------------------------------------------------------------ data */
    function setLoading(on) {
        $('tlLoading').hidden = !on;
        stage.classList.toggle('is-loading', on);
    }

    async function load() {
        if (request) request.abort();
        if (state.who === 'picks' && !state.picks.length) {
            data = null;
            setLoading(false);
            render();
            return;
        }
        request = new AbortController();
        setLoading(true);
        try {
            const res = await fetch(`${cfg.api}?${params(true)}`, { signal: request.signal });
            if (!res.ok) throw new Error(String(res.status));
            data = await res.json();
            // Names and avatars of the hand-picked members (a shared link only carries their ids)
            (data.members || []).forEach(m => {
                const p = state.picks.find(x => x.id === m.id);
                if (p) Object.assign(p, { name: m.name, avatar: m.avatar });
            });
        } catch (err) {
            if (err.name === 'AbortError') return;
            data = { error: true };
        }
        setLoading(false);
        render();
    }

    /* ------------------------------------------------------------ drawing */
    const unitText = v => (state.metric === 'voice' ? `${HG.fmt(v, 1)} h` : T('{n} messages', '{n} messages', { n: HG.fmt(v) }));

    function describe() {
        const scope = state.srv ? (cfg.servers.find(s => s.id === state.srv) || {}).name : T('Tous les serveurs', 'All servers');
        const metric = state.metric === 'voice' ? T('heures de vocal', 'voice hours') : T('messages', 'messages');
        const title = state.who === 'picks'
            ? T('{n} membres au choix', '{n} hand-picked members', { n: state.picks.length })
            : T('Top {n}', 'Top {n}', { n: state.top });
        $('tlTitle').textContent = `${title} · ${state.metric === 'voice' ? T('Vocal', 'Voice') : T('Messages', 'Messages')}`;
        const period = data && data.period ? `${monthLabel(data.period.from)} → ${monthLabel(data.period.to)}` : '';
        $('tlDesc').textContent = [scope, period, T('{m} cumulés depuis le début de la période', '{m} added up from the start of the period', { m: metric })]
            .filter(Boolean).join(' · ');
    }

    function notice() {
        const box = $('tlNotice');
        const skipped = (data && data.skipped) || [];
        const hidden = skipped.filter(s => s.reason === 'hidden').length;
        const unknown = skipped.filter(s => s.reason === 'unknown').length;
        const parts = [];
        if (hidden) parts.push(T('{n} membre(s) retiré(s) : profil privé ou bot', '{n} member(s) left out: private profile or bot', { n: hidden }));
        if (unknown) parts.push(T('{n} membre(s) introuvable(s)', '{n} member(s) not found', { n: unknown }));
        box.textContent = parts.join(' · ');
        box.hidden = !parts.length;
    }

    function empty(text) {
        const box = $('tlEmpty');
        box.textContent = text || '';
        box.hidden = !text;
        stage.classList.toggle('is-empty', !!text);
    }

    function render() {
        describe();
        fillPeriod();
        renderChips();
        notice();
        if (state.who === 'picks' && !state.picks.length) return empty(T('Ajoute des membres pour lancer la course.', 'Add members to start the race.'));
        if (!data) return;
        if (data.error) return empty(T('La timeline n’a pas pu être chargée. Réessaie dans un instant.', 'The timeline could not be loaded. Try again in a moment.'));
        if (!data.members || !data.members.length || !data.frames || !data.frames.length) {
            return empty(T('Pas d’activité à montrer pour ces réglages.', 'No activity to show for these settings.'));
        }
        empty('');
        if (state.view === 'race') drawRace(); else drawLines();
    }

    function drawRace() {
        const shown = state.who === 'picks' ? data.members.length : state.top;
        const rows = Math.min(shown, data.members.length);
        $('tlRaceChart').style.height = `${Math.max(240, rows * (rows > 15 ? 27 : 40) + 50)}px`;
        HG.memberRace(stage, data, PALETTE, {
            shown: rows,
            unit: state.metric === 'voice' ? 'h' : 'msg',
            stepMs: () => 1100 / state.speed,
            hideZero: state.who === 'top',
        });
    }

    function drawLines() {
        if (stage._race) stage._race.stop();
        const cumul = state.curve === 'cumul';
        const last = data.frames[data.frames.length - 1];
        // Top mode: the final top N (the race also sends the members who left it on the way)
        let order = data.members.map((m, k) => k);
        if (state.who === 'top') order = order.sort((a, b) => last.values[b] - last.values[a]).slice(0, state.top);
        const colors = PALETTE.slice(0, -1);
        const labels = data.frames.map(f => f.label);
        const box = $('tlLinesChart');
        box.style.height = `${order.length > 15 ? 560 : 480}px`;
        linesChart = HG.draw(box, {
            legend: HG.legend({ data: order.map(k => data.members[k].name) }),
            grid: HG.grid({ top: 40, right: 18 }),
            xAxis: HG.categoryAxis(labels, { boundaryGap: false }),
            yAxis: HG.valueAxis({ axisLabel: { formatter: v => (state.metric === 'voice' ? `${HG.fmt(v)} h` : HG.fmt(v)) } }),
            tooltip: HG.tooltip({
                formatter: ps => {
                    const rows = HG.sortedRows(ps, v => unitText(v));
                    const f = data.frames[ps[0] ? ps[0].dataIndex : 0];
                    const extra = rows.length > 12 ? rows.length - 12 : 0;
                    return HG.tipHtml(f.label, rows.slice(0, 12), {
                        notes: [extra ? T('+ {n} autres', '+ {n} more', { n: extra }) : '',
                            f.partial ? T('Mois en cours : données partielles', 'Current month: data still coming in') : ''],
                    });
                },
            }),
            series: order.map(k => ({
                type: 'line', name: data.members[k].name, smooth: 0.15, showSymbol: data.frames.length < 25, symbolSize: 5,
                data: data.frames.map(f => (cumul ? f.values[k] : f.gains[k])),
                itemStyle: { color: colors[k % colors.length] },
                lineStyle: { width: 2 },
                emphasis: { focus: 'series', lineStyle: { width: 3 } },
            })),
        });
    }

    // Charts drawn while their block was hidden: resize them when shown
    function resizeVisible() {
        if (state.view === 'lines' && linesChart) linesChart.resize();
        if (state.view === 'race' && stage._race) stage._race.chart.resize();
    }
    window.addEventListener('resize', resizeVisible);

    function start() {
        syncControls();
        writeUrl();
        load();
    }
    if (window.echarts && HG.chart) start();
    else window.addEventListener('load', start, { once: true });
})();
