/* Site-wide UI behaviours wired through data attributes, so templates need no inline event handlers.

   - data-call="fnName" [data-arg="value"]  click calls window.fnName(arg, event, element)
   - data-tip="text"                        instant styled tooltip (hover, keyboard focus and tap)
   Image fallbacks (data-fallback) are handled earlier, by the inline script in <head> of base.html.
*/
(function () {
    const HG = (window.HG = window.HG || {});

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

// Tabbed pages: at the end of each section, buttons to the other sections (many visitors never noticed
// the tab bar). They click the real tab, so each page keeps its own switching logic, then bring the bar back in view.
document.addEventListener('DOMContentLoaded', function () {
    const bar = document.querySelector('.graphs-tabs:not(.adm-tabs)');
    if (!bar) return;
    const tabs = Array.from(bar.querySelectorAll('.graphs-tab-btn[data-tab]'));
    if (tabs.length < 2) return;
    const fr = document.documentElement.lang !== 'en';
    tabs.forEach(function (tab) {
        tab.setAttribute('role', 'tab');
        const pane = document.getElementById(tab.dataset.tab);
        if (!pane) return;
        const nav = document.createElement('nav');
        nav.className = 'tab-next';
        nav.setAttribute('aria-label', fr ? 'Autres sections' : 'Other sections');
        const label = document.createElement('span');
        label.className = 'tab-next-label';
        label.textContent = fr ? 'Autres sections' : 'Other sections';
        nav.appendChild(label);
        tabs.filter(function (other) { return other !== tab; }).forEach(function (other) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'tab-next-btn';
            const icon = other.querySelector('svg');
            if (icon) btn.appendChild(icon.cloneNode(true));
            const title = document.createElement('span');
            title.textContent = (other.querySelector('.tab-title') || other).textContent.trim();
            btn.appendChild(title);
            btn.addEventListener('click', function () {
                other.click();
                bar.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            nav.appendChild(btn);
        });
        pane.appendChild(nav);
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
        bar.addEventListener('click', function () { setTimeout(reveal, 0); });
        bar.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update);
        update();
        setTimeout(reveal, 0);
    });
});
