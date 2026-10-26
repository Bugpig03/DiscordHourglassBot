/* Cut-corner outlines (Arène theme): a box cut with clip-path loses its border on the two cut corners.
   This draws the missing diagonal with the box's own border (::before top-left, ::after bottom-right, see
   arene.css "cut-corner outlines"), so the colored line runs all around without a gap.
   Boxes are found from their computed style, including the ones added later (live lists, tabs, admin). */
(() => {
    const CUT_POLYGON = /^polygon\((\d+(?:\.\d+)?)px 0px, 100% 0px, 100% calc\(100% - \1px\), calc\(100% - \1px\) 100%, 0px 100%, 0px \1px\)$/;
    const SKIP = 'svg, svg *, script, style, img, canvas, input, select, textarea, option';
    // Panels that light up in their own color on hover (arene.css "motion"): their diagonals are drawn even
    // without a border, transparent at rest and colored on hover like the inset outline
    const GLOW = '.an-card, .dashboard-chart-box, .dashboard-podium-card, .dashboard-kpi-card, .home-stats-box, .profile-record, '
        + '.legal-card, .versus-metrics-container, .adm-tile, .xp-guide-item, .companion-card, .heatmap-month-card';

    const visible = (cs, side) => parseFloat(cs[`border${side}Width`]) > 0
        && cs[`border${side}Style`] !== 'none'
        && !/^rgba\(\d+, \d+, \d+, 0\)$/.test(cs[`border${side}Color`]) && cs[`border${side}Color`] !== 'transparent';
    const freePseudo = (el, which) => {
        const c = getComputedStyle(el, which).content;
        return c === 'none' || c === 'normal';
    };

    function mark(el) {
        if (el.matches(SKIP) || el.classList.contains('ar-cut')) return;
        const cs = getComputedStyle(el);
        const m = CUT_POLYGON.exec(cs.clipPath);
        if (!m) return;
        const top = visible(cs, 'Top'), left = visible(cs, 'Left'), bottom = visible(cs, 'Bottom'), right = visible(cs, 'Right');
        const glow = el.matches(GLOW);
        const tl = (top || left || glow) && freePseudo(el, '::before');
        const br = (bottom || right || glow) && freePseudo(el, '::after');
        if (!tl && !br) return;
        const s = el.style;
        s.setProperty('--cut', `${m[1]}px`);
        s.setProperty('--cut-bt', cs.borderTopWidth);
        s.setProperty('--cut-bl', cs.borderLeftWidth);
        s.setProperty('--cut-bb', cs.borderBottomWidth);
        s.setProperty('--cut-br', cs.borderRightWidth);
        // The diagonal continues the top line (or the left one when the box has no top border), and the
        // bottom line (or the right one): "inherit" keeps hover color changes, the fallback is a snapshot
        if (tl) el.dataset.cutTl = top ? 'top' : left ? 'left' : 'glow';
        if (!top && left) { s.setProperty('--cut-tlw', cs.borderLeftWidth); s.setProperty('--cut-tlc', cs.borderLeftColor); }
        if (br) el.dataset.cutBr = bottom ? 'bottom' : right ? 'right' : 'glow';
        if (!bottom && right) { s.setProperty('--cut-brw', cs.borderRightWidth); s.setProperty('--cut-brc', cs.borderRightColor); }
        // A faint grey border (alpha 0.3 or less) takes the hover color; a colored one keeps its own
        const alpha = (side) => { const m2 = /rgba\([^)]*, ([\d.]+)\)$/.exec(cs[`border${side}Color`]); return m2 ? parseFloat(m2[1]) : 1; };
        if (glow && tl && top && alpha('Top') <= 0.3) el.dataset.cutTlSoft = '';
        if (glow && br && bottom && alpha('Bottom') <= 0.3) el.dataset.cutBrSoft = '';
        if (cs.position === 'static') el.classList.add('ar-cut-pos');
        el.classList.add('ar-cut');
    }

    function scan(root) {
        if (root.nodeType !== 1) return;
        mark(root);
        root.querySelectorAll('*').forEach(mark);
    }

    let pending = [];
    let queued = false;
    const flush = () => {
        queued = false;
        const roots = pending;
        pending = [];
        roots.forEach((n) => n.isConnected && scan(n));
    };
    const start = () => {
        scan(document.body);
        new MutationObserver((records) => {
            records.forEach((r) => r.addedNodes.forEach((n) => n.nodeType === 1 && pending.push(n)));
            if (pending.length && !queued) {
                queued = true;
                requestAnimationFrame(flush);
            }
        }).observe(document.body, { childList: true, subtree: true });
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})();
