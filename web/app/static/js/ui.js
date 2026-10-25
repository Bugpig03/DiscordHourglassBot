/* Site-wide UI behaviours wired through data attributes, so templates need no inline event handlers.

   - data-call="fnName" [data-arg="value"]  click calls window.fnName(arg, event, element)
   - data-tip="text"                        instant styled tooltip (hover, keyboard focus and tap)
   Image fallbacks (data-fallback) are handled earlier, by the inline script in <head> of base.html.
*/
(function () {
    const HG = (window.HG = window.HG || {});

    // Site language: code ('fr', 'pt'…) and Intl locale ('pt-BR') come from <html data-lang data-locale>
    const root = document.documentElement;
    HG.lang = root.dataset.lang || 'fr';
    HG.locale = root.dataset.locale || 'fr-FR';
    let phrases = null;
    // Translate an inline pair: French text, English text, optional {placeholders}. Other languages read
    // the translations embedded in the page (#hgI18n), keyed by the French text, and fall back to English.
    HG.tr = function (fr, en, vars) {
        let text = fr;
        if (HG.lang === 'en') text = en;
        else if (HG.lang !== 'fr') {
            if (!phrases) {
                const node = document.getElementById('hgI18n');
                try { phrases = node ? JSON.parse(node.textContent) : {}; } catch (e) { phrases = {}; }
            }
            text = phrases[fr] != null ? phrases[fr] : en;
        }
        return vars ? text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m)) : text;
    };
    // Localized weekday name, 0 = Monday ('long' or 'short')
    HG.weekday = function (index, width) {
        return new Date(Date.UTC(2024, 0, 1 + index)).toLocaleDateString(HG.locale, { weekday: width || 'long', timeZone: 'UTC' });
    };

    // Escape text before inserting it into an HTML string (server names and usernames are free text)
    HG.esc = function (value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    document.addEventListener('click', (e) => {
        const el = e.target.closest('[data-call]');
        if (!el) return;
        const fn = window[el.dataset.call];
        if (typeof fn === 'function') fn(el.dataset.arg, e, el);
    });

    /* ---------------------------------------------------------------- Tooltips */
    let tooltip = null;
    let hideTimer = null;

    function ensureTooltip() {
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = 'hg-tooltip';
            tooltip.setAttribute('role', 'tooltip');
            document.body.appendChild(tooltip);
        }
        return tooltip;
    }

    function show(el) {
        const tip = ensureTooltip();
        clearTimeout(hideTimer);
        tip.textContent = el.dataset.tip;
        tip.classList.add('visible');

        // Above the element, kept inside the viewport (flips below near the top edge)
        const r = el.getBoundingClientRect();
        const w = tip.offsetWidth;
        const h = tip.offsetHeight;
        const left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
        const top = r.top - h - 8 < 8 ? r.bottom + 8 : r.top - h - 8;
        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
    }

    function hide() {
        if (tooltip) tooltip.classList.remove('visible');
    }

    document.addEventListener('mouseover', (e) => {
        const el = e.target.closest('[data-tip]');
        if (el) show(el);
    });
    document.addEventListener('mouseout', (e) => {
        const el = e.target.closest('[data-tip]');
        if (el && !el.contains(e.relatedTarget)) hide();
    });
    document.addEventListener('focusin', (e) => {
        const el = e.target.closest('[data-tip]');
        if (el) show(el);
    });
    document.addEventListener('focusout', hide);
    // Touch screens: a tap shows the tooltip for a moment
    document.addEventListener('touchstart', (e) => {
        const el = e.target.closest('[data-tip]');
        if (!el) return hide();
        show(el);
        clearTimeout(hideTimer);
        hideTimer = setTimeout(hide, 2500);
    }, { passive: true });
    window.addEventListener('scroll', hide, { passive: true });
})();

// Tabbed pages: the tab buttons are announced as tabs
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.graphs-tabs:not(.adm-tabs) .graphs-tab-btn[data-tab]').forEach(function (tab) {
        tab.setAttribute('role', 'tab');
    });
});

// Tab bars wider than the screen (mobile): fade the right edge while sections remain hidden
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.graphs-tabs').forEach(function (bar) {
        const update = function () {
            bar.classList.toggle('has-more', bar.scrollLeft + bar.clientWidth < bar.scrollWidth - 4);
        };
        // Keep the open section visible in the bar (it may be scrolled out on a phone)
        const reveal = function () {
            const active = bar.querySelector('.graphs-tab-btn.active');
            if (!active || bar.scrollWidth <= bar.clientWidth) return;
            const left = active.offsetLeft - bar.offsetLeft;
            if (left < bar.scrollLeft || left + active.offsetWidth > bar.scrollLeft + bar.clientWidth) {
                bar.scrollLeft = Math.max(0, left - 12);  // instant: a smooth scroll is cancelled by the page scroll
                update();
            }
        };
        // Never a cut text: subtitles all or none, then scroll the bar if even a title does not fit
        const isCut = function (selector) {
            return Array.from(bar.querySelectorAll(selector)).some(function (el) {
                return el.offsetParent !== null && el.scrollWidth > el.clientWidth + 1;
            });
        };
        const fitDescs = function () {
            bar.classList.remove('no-desc', 'tabs-scroll');
            if (isCut('.tab-desc')) bar.classList.add('no-desc');
            if (isCut('.tab-title')) bar.classList.add('tabs-scroll');
        };
        bar.addEventListener('click', function () { setTimeout(reveal, 0); });
        bar.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', function () { fitDescs(); update(); });
        fitDescs();
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { fitDescs(); update(); });
        update();
        setTimeout(reveal, 0);
    });
});
