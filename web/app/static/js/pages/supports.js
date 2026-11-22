/* Help page (web 3.51.0): one tab per section, the address keeps the open tab (/supports#faq).
   Old anchors (#prestige, #titres, #badges) still work: they open the tab that holds them. */
function switchHelpTab(name, event, el, keepScroll) {
    const pane = document.querySelector('.help-pane[data-pane="' + name + '"]');
    if (!pane) return;
    document.querySelectorAll('.graphs-tab-btn[data-tab]').forEach(function (btn) {
        const on = btn.dataset.tab === name;
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.help-pane').forEach(function (p) {
        const on = p === pane;
        p.hidden = !on;
        p.classList.toggle('active', on);
    });
    if (!keepScroll && window.history && window.history.replaceState) {
        window.history.replaceState(null, '', '#' + name);
    }
}

function openHelpHash() {
    const hash = decodeURIComponent((window.location.hash || '').slice(1));
    if (!hash) return;
    if (document.querySelector('.help-pane[data-pane="' + CSS.escape(hash) + '"]')) {
        switchHelpTab(hash, null, null, true);
        return;
    }
    // An anchor inside a tab (#prestige, #titres): open its tab, then bring it into view
    const target = document.getElementById(hash);
    const pane = target && target.closest('.help-pane');
    if (pane) {
        switchHelpTab(pane.dataset.pane, null, null, true);
        requestAnimationFrame(function () { target.scrollIntoView({ block: 'start' }); });
    }
}

document.addEventListener('DOMContentLoaded', openHelpHash);
window.addEventListener('hashchange', openHelpHash);

// A link to another tab inside the page (href="#progression") switches tab instead of jumping
document.addEventListener('click', function (e) {
    const a = e.target.closest('a[href^="#"]');
    if (!a || !document.querySelector('.help-pane[data-pane="' + CSS.escape(a.getAttribute('href').slice(1)) + '"]')) return;
    e.preventDefault();
    switchHelpTab(a.getAttribute('href').slice(1));
    window.scrollTo({ top: 0 });
});
