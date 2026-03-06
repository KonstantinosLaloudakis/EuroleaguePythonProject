/**
 * Euroleague Win Probability Replay — Client-side app
 * Loads pre-computed game data from JSON and renders interactive Plotly charts.
 */

const DATA_BASE = 'data';

// ── State ────────────────────────────────────────────────
let seasonsData = [];
let currentGames = [];

// ── DOM Elements ─────────────────────────────────────────
const seasonSelect = document.getElementById('season-select');
const teamFilter = document.getElementById('team-filter');
const gameSelect = document.getElementById('game-select');
const chartDiv = document.getElementById('wp-chart');
const placeholder = document.getElementById('placeholder');
const keyPlaysSection = document.getElementById('key-plays');
const keyPlaysList = document.getElementById('key-plays-list');
const gameSummary = document.getElementById('game-summary');
const summaryContent = document.getElementById('summary-content');

// ── Initialize ───────────────────────────────────────────
async function init() {
    try {
        const resp = await fetch(`${DATA_BASE}/seasons.json`);
        seasonsData = await resp.json();

        seasonSelect.innerHTML = '<option value="">— Select Season —</option>';
        seasonsData.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.season;
            opt.textContent = `${s.label} (${s.count} games)`;
            seasonSelect.appendChild(opt);
        });
        seasonSelect.disabled = false;
    } catch (err) {
        seasonSelect.innerHTML = '<option value="">Error loading seasons</option>';
        console.error('Failed to load seasons:', err);
    }
}

// ── Season Changed ───────────────────────────────────────
seasonSelect.addEventListener('change', async () => {
    const season = seasonSelect.value;
    if (!season) {
        resetDownstream();
        return;
    }

    gameSelect.innerHTML = '<option value=""><span class="loading-spinner"></span>Loading games...</option>';
    gameSelect.disabled = true;
    teamFilter.disabled = true;

    try {
        const resp = await fetch(`${DATA_BASE}/${season}/games.json`);
        currentGames = await resp.json();

        // Populate team filter
        const allTeams = new Set();
        currentGames.forEach(g => { allTeams.add(g.ta); allTeams.add(g.tb); });
        const sortedTeams = [...allTeams].sort();

        teamFilter.innerHTML = '<option value="">All Teams</option>';
        sortedTeams.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t;
            opt.textContent = t;
            teamFilter.appendChild(opt);
        });
        teamFilter.disabled = false;

        populateGames();
    } catch (err) {
        gameSelect.innerHTML = '<option value="">Error loading games</option>';
        console.error('Failed to load games:', err);
    }
});

// ── Team Filter Changed ──────────────────────────────────
teamFilter.addEventListener('change', populateGames);

function populateGames() {
    const filterTeam = teamFilter.value;
    let games = currentGames;

    if (filterTeam) {
        games = games.filter(g => g.ta === filterTeam || g.tb === filterTeam);
    }

    gameSelect.innerHTML = '<option value="">— Select Game —</option>';
    games.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.gc;
        const winner = g.sa > g.sb ? g.ta : g.tb;
        const marker = winner === g.ta ? '✦' : '';
        const marker2 = winner === g.tb ? '✦' : '';
        opt.textContent = `${marker}${g.ta} ${g.sa} - ${g.sb} ${g.tb}${marker2}`;
        gameSelect.appendChild(opt);
    });
    gameSelect.disabled = false;
}

// ── Game Selected ────────────────────────────────────────
gameSelect.addEventListener('change', async () => {
    const gc = gameSelect.value;
    const season = seasonSelect.value;
    if (!gc || !season) return;

    placeholder.classList.add('hidden');

    try {
        const resp = await fetch(`${DATA_BASE}/${season}/${gc}.json`);
        const data = await resp.json();
        renderChart(data);
    } catch (err) {
        console.error('Failed to load game data:', err);
    }
});

// ── Render Chart ─────────────────────────────────────────
function renderChart(data) {
    const { ta, tb, timeline } = data;

    // Prepend tip-off
    const full = [{ e: 0, s: 2400, a: 0, b: 0, w: 0.5, p: 1, d: 'Tip-Off' }, ...timeline];

    const elapsed = full.map(p => p.e / 60);
    const wpPct = full.map(p => p.w * 100);

    // Format time remaining
    const fmtTime = (secs) => {
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    // Hover text
    const hoverText = full.map(p =>
        `<b>${p.d}</b><br>` +
        `Score: ${ta} ${p.a} - ${p.b} ${tb}<br>` +
        `WP (${ta}): ${(p.w * 100).toFixed(1)}%<br>` +
        `Q${p.p} — ${fmtTime(p.s)} remaining`
    );

    // Calculate WP shifts for key plays
    const shifts = full.map((p, i) => ({
        ...p,
        shift: i > 0 ? (p.w - full[i - 1].w) * 100 : 0,
        idx: i,
    }));

    const sorted = [...shifts].sort((a, b) => Math.abs(b.shift) - Math.abs(a.shift));
    const keyPlays = sorted.filter(p => Math.abs(p.shift) >= 3 && p.d !== 'Tip-Off').slice(0, 8);

    // Build Plotly traces
    const traces = [];

    // Fill below 50% (team B winning zone)
    traces.push({
        x: elapsed, y: wpPct,
        fill: 'tozeroy', fillcolor: 'rgba(59,130,246,0.1)',
        line: { width: 0 }, showlegend: false, hoverinfo: 'skip',
    });

    // Fill above 50% (team A winning zone)  
    traces.push({
        x: elapsed, y: wpPct,
        fill: 'tonexty', fillcolor: 'rgba(239,68,68,0.08)',
        line: { width: 0 }, showlegend: false, hoverinfo: 'skip',
        yaxis: 'y',
    });

    // Main WP line
    traces.push({
        x: elapsed, y: wpPct,
        mode: 'lines',
        line: { color: 'rgba(255,255,255,0.9)', width: 2.5 },
        text: hoverText, hoverinfo: 'text',
        showlegend: false,
    });

    // Key play markers
    keyPlays.forEach(kp => {
        const color = kp.shift > 0 ? '#22c55e' : '#ef4444';
        const playerShort = kp.d.split('(')[0].split(',')[0].trim();
        traces.push({
            x: [kp.e / 60], y: [kp.w * 100],
            mode: 'markers',
            marker: { size: 9, color, symbol: 'circle', line: { color: 'white', width: 1 } },
            showlegend: false,
            hovertext: `<b>${kp.d}</b><br>WP: ${(kp.w * 100).toFixed(1)}%<br>Shift: ${kp.shift > 0 ? '+' : ''}${kp.shift.toFixed(1)}%<br>Score: ${ta} ${kp.a} - ${kp.b} ${tb}<br>Q${kp.p} — ${fmtTime(kp.s)} remaining`,
            hoverinfo: 'text',
        });
    });

    const finalScore = full[full.length - 1];
    const winner = finalScore.a > finalScore.b ? ta : tb;

    const layout = {
        title: {
            text: `${ta} ${finalScore.a} - ${finalScore.b} ${tb}`,
            font: { size: 22, color: 'white', family: 'Outfit, sans-serif' },
            x: 0.5, xanchor: 'center',
        },
        xaxis: {
            title: { text: 'Game Time (Minutes)', font: { color: '#9ca3af' } },
            range: [0, 40],
            tickvals: [0, 5, 10, 15, 20, 25, 30, 35, 40],
            color: '#9ca3af',
            gridcolor: '#2d2e3a',
            zeroline: false,
        },
        yaxis: {
            title: { text: 'Win Probability (%)', font: { color: '#9ca3af' } },
            range: [0, 100],
            tickvals: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            color: '#9ca3af',
            gridcolor: '#2d2e3a',
            zeroline: false,
        },
        plot_bgcolor: '#0f1117',
        paper_bgcolor: '#1f2029',
        font: { color: 'white' },
        showlegend: false,
        hovermode: 'closest',
        margin: { l: 55, r: 20, t: 60, b: 50 },
        shapes: [
            // 50% line
            {
                type: 'line', x0: 0, x1: 40, y0: 50, y1: 50,
                line: { color: '#4b5563', width: 1, dash: 'dash' }
            },
            // Quarter lines
            ...[10, 20, 30].map(x => ({
                type: 'line', x0: x, x1: x, y0: 0, y1: 100,
                line: { color: '#374151', width: 1, dash: 'dot' },
            })),
        ],
        annotations: [
            {
                x: 0.5, y: 97, text: `<b>${ta}</b>`, showarrow: false,
                font: { size: 14, color: '#ef4444' }, xref: 'x', yref: 'y', xanchor: 'left'
            },
            {
                x: 0.5, y: 3, text: `<b>${tb}</b>`, showarrow: false,
                font: { size: 14, color: '#3b82f6' }, xref: 'x', yref: 'y', xanchor: 'left'
            },
            // Quarter labels
            ...[1, 2, 3, 4].map((q, i) => ({
                x: 5 + i * 10, y: 96, text: `Q${q}`, showarrow: false,
                font: { size: 10, color: '#6b7280' }, xref: 'x', yref: 'y',
            })),
        ],
    };

    Plotly.newPlot(chartDiv, traces, layout, {
        responsive: true,
        displayModeBar: false,
    });

    // ── Key Plays Panel ─────────────────────────────────
    keyPlaysList.innerHTML = '';
    const sortedByTime = [...keyPlays].sort((a, b) => a.e - b.e);
    sortedByTime.forEach(kp => {
        const card = document.createElement('div');
        const cls = kp.shift > 0 ? 'positive' : 'negative';
        card.className = `key-play-card ${cls}`;
        card.innerHTML = `
            <div class="key-play-desc">${kp.d}</div>
            <div class="key-play-meta">Q${kp.p} · ${fmtTime(kp.s)} · Score: ${ta} ${kp.a}-${kp.b} ${tb}</div>
            <div class="key-play-shift ${cls}">WP: ${(kp.w * 100).toFixed(1)}% (${kp.shift > 0 ? '+' : ''}${kp.shift.toFixed(1)}%)</div>
        `;
        keyPlaysList.appendChild(card);
    });
    keyPlaysSection.classList.remove('hidden');

    // ── Game Summary ────────────────────────────────────
    const minWP = Math.min(...wpPct);
    const maxWP = Math.max(...wpPct);
    summaryContent.innerHTML = `
        <strong>${winner} wins ${finalScore.a}-${finalScore.b}</strong> ·
        ${ta} WP range: ${minWP.toFixed(1)}% — ${maxWP.toFixed(1)}% ·
        ${full.length - 2} scoring plays
    `;
    gameSummary.classList.remove('hidden');
}

// ── Reset ────────────────────────────────────────────────
function resetDownstream() {
    currentGames = [];
    teamFilter.innerHTML = '<option value="">All Teams</option>';
    teamFilter.disabled = true;
    gameSelect.innerHTML = '<option value="">Select a season first</option>';
    gameSelect.disabled = true;
    placeholder.classList.remove('hidden');
    keyPlaysSection.classList.add('hidden');
    gameSummary.classList.add('hidden');
    Plotly.purge(chartDiv);
}

// ── Go ───────────────────────────────────────────────────
init();
