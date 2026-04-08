/* network.js — Assist / Playmaking Network */

let _data = null;       // full JSON
let _selected = null;   // current team code
let _pinned = null;     // pinned player id

// ── Boot ─────────────────────────────────────────────────────────────────────
fetchJSON('data/current/assist_network.json')
    .then(data => {
        _data = data;
        renderTeamGrid();
        renderCombosTable(data.top_combos);
        renderPlaymakersTable(data.top_playmakers);
        restoreFromURL();
    })
    .catch(err => {
        console.error('Failed to load assist network:', err);
        document.getElementById('load-error').classList.remove('hidden');
    });

// ── URL state ────────────────────────────────────────────────────────────────
function restoreFromURL() {
    const params = new URLSearchParams(location.search);
    const team = params.get('team');
    if (team && _data.teams[team]) {
        selectTeam(team);
    } else {
        // Default: first team alphabetically
        const first = Object.keys(_data.teams).sort()[0];
        if (first) selectTeam(first);
    }
}

function updateURL(teamCode) {
    const url = new URL(location);
    url.searchParams.set('team', teamCode);
    history.replaceState(null, '', url);
}

// ── Team grid ────────────────────────────────────────────────────────────────
function renderTeamGrid() {
    const grid = document.getElementById('team-grid');
    const codes = Object.keys(_data.teams).sort((a, b) => {
        const na = TEAM_NAMES[a] || a;
        const nb = TEAM_NAMES[b] || b;
        return na.localeCompare(nb);
    });
    grid.innerHTML = codes.map(code => {
        const color = TEAM_COLORS[code] || '#6b7280';
        const name = TEAM_NAMES[code] || code;
        return `<div class="team-chip" id="chip-${code}"
                     onclick="selectTeam('${code}')"
                     style="border-top:3px solid ${color}40">
            <span class="team-chip-name" style="color:${color}">${name}</span>
        </div>`;
    }).join('');
}

function selectTeam(code) {
    if (!_data || !_data.teams[code]) return;
    _selected = code;
    _pinned = null;

    // Highlight chip
    document.querySelectorAll('.team-chip').forEach(c => c.classList.remove('selected'));
    const chip = document.getElementById('chip-' + code);
    if (chip) chip.classList.add('selected');

    // Show chord card
    document.getElementById('chord-card').style.display = '';
    document.getElementById('chord-title').textContent =
        (TEAM_NAMES[code] || code) + ' — Assist Network';

    // Hide player detail
    document.getElementById('player-detail').classList.remove('visible');

    updateURL(code);
    renderChord(_data.teams[code], code);
}
