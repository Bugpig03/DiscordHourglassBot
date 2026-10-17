/* Live lists: filters, searches and pagination update the results in place instead of reloading the page.

   Markup contract (everything keeps working as plain links/forms without JavaScript):
   - [data-live-region]   block(s) replaced after each navigation (results, pager, counters); several
                          regions on one page are matched by their attribute value (data-live-region="count")
   - form[data-live-form] GET form whose submission is intercepted; its fields are re-synced from the response
   - [data-live-search]   text input inside a live form, submitted automatically while typing
   - a[data-live-link], .pager a   links loaded in place
*/
(function () {
    const HG = (window.HG = window.HG || {});
    const SEARCH_DEBOUNCE_MS = 300;
    let controller = null;

    function region() {
        return document.querySelector('[data-live-region]');
    }

    function regions() {
        return [...document.querySelectorAll('[data-live-region]')];
    }

    // Copy field values from the freshly rendered forms, so selects / hidden inputs match the new URL
    function syncForms(doc) {
        doc.querySelectorAll('form[data-live-form] [id]').forEach((fresh) => {
            const current = document.getElementById(fresh.id);
            if (!current || current === document.activeElement) return;
            if ('value' in fresh) current.value = fresh.value;
            if (fresh.placeholder !== undefined && current.placeholder !== undefined) current.placeholder = fresh.placeholder;
        });
    }

    async function load(url, { push = true, scroll = false } = {}) {
        const targets = regions();
        if (!targets.length) {
            window.location.href = url;
            return;
        }
        if (controller) controller.abort();
        controller = new AbortController();
        targets.forEach((t) => {
            t.setAttribute('aria-busy', 'true');
            t.classList.add('is-live-loading');
        });

        try {
            const res = await fetch(url, { signal: controller.signal, credentials: 'same-origin' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
            const pairs = targets.map((t) => [t, doc.querySelector(`[data-live-region="${t.dataset.liveRegion}"]`)]);
            if (pairs.some(([, fresh]) => !fresh)) throw new Error('missing live region');

            pairs.forEach(([t, fresh]) => t.replaceWith(document.adoptNode(fresh)));
            const fresh = pairs[0][1];
            syncForms(doc);
            document.title = doc.title;
            if (push) {
                const next = new URL(url, window.location.origin);
                next.hash = window.location.hash;
                history.pushState({ hgLive: true }, '', next);
            }
            if (scroll) {
                const top = fresh.getBoundingClientRect().top;
                if (top < 0) window.scrollTo({ top: window.scrollY + top - 90, behavior: 'smooth' });
            }
            document.dispatchEvent(new CustomEvent('hg:live-updated', { detail: { region: fresh } }));
        } catch (err) {
            if (err.name === 'AbortError') return;
            window.location.href = url; // Graceful fallback: classic navigation
        } finally {
            regions().forEach((current) => {
                current.removeAttribute('aria-busy');
                current.classList.remove('is-live-loading');
            });
        }
    }

    function formUrl(form) {
        const url = new URL(form.getAttribute('action') || window.location.pathname, window.location.origin);
        const params = new URLSearchParams();
        new FormData(form).forEach((value, key) => {
            if (String(value).trim() !== '') params.append(key, value);
        });
        url.search = params.toString();
        return url.toString();
    }

    HG.liveLoad = load;
    HG.hasLiveRegion = () => !!region();

    document.addEventListener('submit', (e) => {
        const form = e.target.closest('form[data-live-form]');
        if (!form || !region()) return;
        e.preventDefault();
        load(formUrl(form));
    });

    document.addEventListener('click', (e) => {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

        // Clear button of a live search field: empty the field and refresh the results
        const clear = e.target.closest('form[data-live-form] .page-search-clear');
        if (clear) {
            const input = clear.closest('form').querySelector('[data-live-search]');
            if (input && region()) {
                e.preventDefault();
                input.value = '';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                clear.closest('form').requestSubmit();
                return;
            }
        }

        const link = e.target.closest('a[data-live-link], .pager a');
        if (!link || !region() || link.origin !== window.location.origin) return;
        e.preventDefault();
        load(link.href, { scroll: !!link.closest('.pager') });
    });

    // Search fields: refresh while typing (debounced); Enter still submits immediately
    document.addEventListener('input', (e) => {
        const input = e.target.closest('[data-live-search]');
        if (!input) return;
        const form = input.closest('form');
        form.classList.toggle('has-value', input.value.trim() !== '');
        clearTimeout(input._hgTimer);
        input._hgTimer = setTimeout(() => form.requestSubmit(), SEARCH_DEBOUNCE_MS);
    });

    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.hgLive) load(window.location.href, { push: false });
    });

    if (region()) history.replaceState({ hgLive: true }, '', window.location.href);
})();
