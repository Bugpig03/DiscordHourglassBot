/* Key figures count up to their value when the page opens (home, server and profile tiles).
   The figure is already written in full in the page; only its number is animated, keeping its format
   (thousands separator, decimals, unit). Ranks (#6) are left alone. Off when less motion is asked. */
(() => {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const NUMBER = /\d{1,3}(?:[   ]\d{3})+(?:,\d+)?|\d+(?:,\d+)?/;
    const DURATION = 1100;

    function firstNumberNode(el) {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            const m = NUMBER.exec(node.nodeValue);
            if (!m) continue;
            if (node.nodeValue.slice(0, m.index).includes('#')) return null;
            return { node, m };
        }
        return null;
    }

    function animate(el) {
        const hit = firstNumberNode(el);
        if (!hit) return;
        const { node, m } = hit;
        const raw = m[0];
        const sep = (raw.match(/[   ]/) || [' '])[0];
        const decimals = raw.includes(',') ? raw.split(',')[1].length : 0;
        const target = parseFloat(raw.replace(/[   ]/g, '').replace(',', '.'));
        if (!isFinite(target) || target < 10) return;
        const before = node.nodeValue.slice(0, m.index);
        const after = node.nodeValue.slice(m.index + raw.length);
        const format = (v) => v.toLocaleString(HG.locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
            .replace(/[   ]/g, sep);
        const start = performance.now();
        const step = (now) => {
            const t = Math.min(1, (now - start) / DURATION);
            const eased = 1 - Math.pow(1 - t, 3);
            node.nodeValue = before + (t < 1 ? format(target * eased) : raw) + after;
            if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    const run = () => document.querySelectorAll('.dashboard-kpi-val, .home-stats-value').forEach(animate);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
    else run();
})();
