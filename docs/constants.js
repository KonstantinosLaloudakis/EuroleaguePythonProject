/**
 * constants.js — Shared constants and utilities for Euroleague Analytics
 * Single source of truth: include via <script src="constants.js"> before page JS.
 */
'use strict';

// ── Team lookup tables ───────────────────────────────────────────────────
const TEAM_COLORS = {
    BER:'#005CA9', IST:'#E30613', MCO:'#D4AF37', BAS:'#B50031',
    RED:'#CC0000', MIL:'#C8102E', BAR:'#004D98', MUN:'#0066B2',
    ULK:'#003366', ASV:'#222222', TEL:'#F6C300', OLY:'#E2001A',
    PAN:'#007F3D', PAR:'#333333', PRS:'#1a1a2e', MAD:'#6d4c94',
    PAM:'#EB7622', VIR:'#1a1a1a', ZAL:'#006233', DUB:'#555555',
    HTA:'#cc0000',
};

const TEAM_NAMES = {
    BER:'ALBA Berlin', IST:'Anadolu Efes', MCO:'AS Monaco', BAS:'Baskonia',
    RED:'Crvena Zvezda', MIL:'EA7 Milan', BAR:'FC Barcelona', MUN:'Bayern Munich',
    ULK:'Fenerbahce', ASV:'ASVEL', TEL:'Maccabi Tel Aviv', OLY:'Olympiacos',
    PAN:'Panathinaikos', PAR:'Partizan', PRS:'Paris Basketball', MAD:'Real Madrid',
    PAM:'Valencia Basket', VIR:'Virtus Bologna', ZAL:'Zalgiris', DUB:'Dubai Basketball',
    HTA:'Hapoel Tel Aviv',
};

// ── Shared tab switching ─────────────────────────────────────────────────
/**
 * switchTab(tabId, tabIds, opts)
 *   tabId  — id of the tab panel to show
 *   tabIds — ordered array of all tab panel ids in this group
 *   opts.scope    — CSS selector to scope .tab-btn search (default: document)
 *   opts.hash     — persist tabId in URL hash (default: true)
 *   opts.onSwitch — callback(tabId) after switching
 */
function switchTab(tabId, tabIds, opts = {}) {
    tabIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.toggle('hidden', id !== tabId);
            el.setAttribute('role', 'tabpanel');
        }
    });
    const scope = opts.scope ? document.querySelector(opts.scope) : document;
    const buttons = scope ? scope.querySelectorAll('.tab-btn') : [];
    const idx = tabIds.indexOf(tabId);
    buttons.forEach((btn, i) => {
        const isActive = i === idx;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('role', 'tab');
        btn.setAttribute('aria-selected', isActive);
        btn.setAttribute('tabindex', isActive ? '0' : '-1');
    });
    if (opts.hash !== false) {
        history.replaceState(null, '', '#' + tabId);
    }
    if (opts.onSwitch) opts.onSwitch(tabId);
}

// ── Keyboard navigation for tab bars ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-bar, #paint-tabs').forEach(bar => {
        bar.setAttribute('role', 'tablist');
        bar.addEventListener('keydown', e => {
            const tabs = [...bar.querySelectorAll('.tab-btn')];
            const idx = tabs.indexOf(e.target);
            if (idx === -1) return;
            let next = -1;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (idx + 1) % tabs.length;
            else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (idx - 1 + tabs.length) % tabs.length;
            if (next !== -1) {
                e.preventDefault();
                tabs[next].focus();
                tabs[next].click();
            }
        });
    });
});

// ── Shared Plotly theme ──────────────────────────────────────────────────
const PLOTLY_THEME = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#9ca3af', size: 12 },
    margin: { t: 30, r: 20, b: 40, l: 50 },
    xaxis: { gridcolor: '#2d2e3a', zerolinecolor: '#2d2e3a', color: '#9ca3af' },
    yaxis: { gridcolor: '#2d2e3a', zerolinecolor: '#2d2e3a', color: '#9ca3af' },
};

const PLOTLY_CONFIG = { displayModeBar: false, responsive: true };

// ── Safe fetch with resp.ok check ───────────────────────────────────────
function fetchJSON(url) {
    return fetch(url).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status} loading ${url}`);
        return r.json();
    });
}
