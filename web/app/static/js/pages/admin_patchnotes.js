/* Admin > Patch notes: the official server and channel where the bot posts each new version, tests, latest posts.
   Loaded when the section is first opened, saved with fetch (CSRF token of the form). */
(function () {
    const form = document.getElementById('pnForm');
    if (!form) return;
    const T = (fr, en, vars) => HG.tr(fr, en, vars);
    const esc = v => HG.esc(v);
    const $ = id => document.getElementById(id);
    const server = $('pnServer'), channel = $('pnChannel'), role = $('pnRole'), scope = $('pnScope');
    const enabled = $('pnEnabled'), enabledLabel = $('pnEnabledLabel'), status = $('pnStatus'), hint = $('pnChannelHint');
    const grid = form.querySelector('.adm-pn-grid');
    let loaded = false, channels = [];

    const errors = {
        server: T('Ce serveur n’est pas (ou plus) un serveur du bot.', 'This server is not (or no longer) one of the bot’s.'),
        channel: T('Choisis un serveur et un salon pour activer les patch notes.', 'Choose a server and a channel to turn the patch notes on.'),
        settings: T('Enregistre d’abord un serveur et un salon.', 'Save a server and a channel first.'),
        wait: T('Un test vient d’être demandé : attends une minute.', 'A test was just asked: wait a minute.'),
        none: T('Aucune version connue pour l’instant.', 'No version known yet.'),
        error: T('L’enregistrement a échoué.', 'Saving failed.'),
    };
    const say = (text, ok) => { status.textContent = text; status.className = `adm-pn-status ${ok ? 'is-ok' : 'is-ko'}`; };
    const when = iso => (iso ? new Date(iso + 'Z').toLocaleString(HG.locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—');

    function fillGuild(data, chosenChannel, chosenRole) {
        channels = data.channels || [];
        channel.innerHTML = `<option value="">${esc(T('Choisir un salon…', 'Choose a channel…'))}</option>` + channels.map(c =>
            `<option value="${esc(c.id)}">${c.kind === 'announcement' ? '📢 ' : '#'}${esc(c.name)}${c.can_send ? '' : ' · ' + esc(T('le bot ne peut pas y écrire', 'the bot cannot write there'))}</option>`).join('');
        channel.value = chosenChannel || '';
        role.innerHTML = `<option value="">${esc(T('Personne', 'Nobody'))}</option>` + (data.roles || []).map(r => `<option value="${esc(r.id)}">@${esc(r.name)}</option>`).join('');
        role.value = chosenRole || '';
        sync();
    }

    function sync() {
        enabledLabel.textContent = enabled.checked ? T('Activées', 'On') : T('Désactivées', 'Off');
        grid.inert = !enabled.checked; // turned off: nothing to change until turned on (values kept)
        const c = channels.find(x => x.id === channel.value);
        hint.hidden = !c || (c.can_send && c.kind === 'announcement');
        if (c && !c.can_send) hint.textContent = T('Le bot ne peut pas écrire dans ce salon (ou y mettre des liens) : donne-lui « Envoyer des messages » et « Intégrer des liens ».', 'The bot cannot write in this channel (or embed links there): give it “Send messages” and “Embed links”.');
        else if (c) hint.textContent = T('Salon texte normal : les messages n’y seront pas publiés pour d’autres serveurs. Un salon d’annonces (📢) permet aux autres serveurs de le suivre.', 'Regular text channel: the messages will not be published to other servers. An announcement channel (📢) lets other servers follow it.');
    }

    function renderHistory(rows) {
        const label = { web: T('Site', 'Website'), bot: 'Bot' };
        $('pnHistory').querySelector('tbody').innerHTML = rows.map(r => {
            const tag = r.ok === true ? `<span class="adm-pn-tag is-ok">${esc(T('Posté', 'Posted'))}</span>`
                : r.ok === false ? `<span class="adm-pn-tag is-ko">${esc(T('Échec', 'Failed'))}</span>`
                : `<span class="adm-pn-tag is-wait">${esc(T('En attente du bot', 'Waiting for the bot'))}</span>`;
            return `<tr><td class="adm-muted">${esc(when(r.posted_at || r.requested_at || r.created_at))}</td><td>${esc(label[r.component] || r.component)} v${esc(r.version)}${r.requested ? ' · ' + esc(T('test', 'test')) : ''}</td>
                <td>${esc(r.title)}</td><td>${tag}</td><td class="adm-muted">${esc(r.detail)}</td></tr>`;
        }).join('') || `<tr><td>${esc(T('Rien pour l’instant.', 'Nothing yet.'))}</td></tr>`;
    }

    async function load() {
        const res = await fetch('/admin/patchnotes', { credentials: 'same-origin' });
        const data = await res.json();
        const s = data.settings;
        server.innerHTML = `<option value="">${esc(T('Choisir un serveur…', 'Choose a server…'))}</option>` +
            data.servers.map(x => `<option value="${esc(x.server_id)}">${esc(x.name)}</option>`).join('');
        server.value = s.server_id || '';
        scope.value = s.scope || 'both';
        enabled.checked = !!s.enabled;
        fillGuild(data, s.channel_id, s.mention_role_id);
        document.querySelectorAll('[data-pn-latest]').forEach(el => {
            const v = (data.latest || {})[el.dataset.pnLatest];
            el.textContent = v ? `(v${v.version})` : '';
        });
        renderHistory(data.history || []);
        loaded = true;
    }

    server.addEventListener('change', async () => {
        const res = await fetch(`/admin/patchnotes/guild?server=${encodeURIComponent(server.value)}`, { credentials: 'same-origin' });
        fillGuild(await res.json(), '', '');
    });
    form.addEventListener('change', sync);
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const res = await fetch('/admin/patchnotes', { method: 'POST', body: new FormData(form), credentials: 'same-origin' });
        const data = res.ok ? await res.json() : { ok: false, error: 'error' };
        say(data.ok ? T('Enregistré : le bot applique les réglages dans la minute.', 'Saved: the bot applies the settings within a minute.') : errors[data.error] || errors.error, data.ok);
        if (data.ok) load();
    });
    document.querySelectorAll('[data-pn-test]').forEach(btn => btn.addEventListener('click', async () => {
        btn.disabled = true;
        const body = new FormData();
        body.append('csrf_token', form.querySelector('[name="csrf_token"]').value);
        body.append('component', btn.dataset.pnTest);
        const res = await fetch('/admin/patchnotes/test', { method: 'POST', body, credentials: 'same-origin' });
        const data = res.ok ? await res.json() : { ok: false, error: 'error' };
        say(data.ok ? T('Demandé : le bot poste dans la minute.', 'Asked: the bot posts within a minute.') : errors[data.error] || errors.error, data.ok);
        btn.disabled = false;
        load();
    }));

    // Loaded the first time the section is opened
    const open = () => { if (!loaded && document.getElementById('tab-patchnotes').classList.contains('active')) load(); };
    new MutationObserver(open).observe(document.getElementById('tab-patchnotes'), { attributes: true, attributeFilter: ['class'] });
    open();
})();
