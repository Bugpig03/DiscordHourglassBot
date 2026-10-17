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
