/* ── shots.js — Shot Lab ─────────────────────────────────────────────────── */

const TEAM_COLORS = {
    BER:'#005CA9', IST:'#E30613', MCO:'#E30613', BAS:'#006633',
    RED:'#CC0000', MIL:'#CC0000', BAR:'#A50044', MUN:'#DC052D',
    ULK:'#003DA5', ASV:'#FFD700', TEL:'#005BAA', OLY:'#CC0000',
    PAN:'#007A33', PAR:'#000000', PRS:'#001489', MAD:'#FEBE10',
    PAM:'#FF6B00', VIR:'#003DA5', ZAL:'#006600', DUB:'#00843D',
    HTA:'#CC0000',
};

const TEAM_NAMES = {
    BER:'ALBA Berlin', IST:'Anadolu Efes', MCO:'AS Monaco', BAS:'Baskonia',
    RED:'Crvena Zvezda', MIL:'EA7 Milan', BAR:'FC Barcelona', MUN:'Bayern Munich',
    ULK:'Fenerbahce', ASV:'ASVEL', TEL:'Maccabi Tel Aviv', OLY:'Olympiacos',
    PAN:'Panathinaikos', PAR:'Partizan', PRS:'Paris Basketball', MAD:'Real Madrid',
    PAM:'Valencia Basket', VIR:'Virtus Bologna', ZAL:'Zalgiris', DUB:'Dubai Basketball',
    HTA:'Hapoel Tel Aviv',
};

let _data = null;
const ZONES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];

// ── Boot ──────────────────────────────────────────────────────────────────
fetch('data/current/shot_stats.json')
    .then(r => r.json())
    .then(data => {
        _data = data;
        populateFilters();
        restoreFromURL();
        renderAll();
    })
    .catch(err => {
        document.getElementById('court-chart').innerHTML =
            `<p style="color:var(--accent-red);padding:1rem">Failed to load shot data: ${err}</p>`;
    });

function populateFilters() {
    const teamSel = document.getElementById('shot-team');
    const teams = Object.keys(_data.teams).sort((a, b) =>
        (TEAM_NAMES[a] || a).localeCompare(TEAM_NAMES[b] || b)
    );
    teams.forEach(code => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = TEAM_NAMES[code] || code;
        teamSel.appendChild(opt);
    });
    rebuildPlayerDropdown();
}

function rebuildPlayerDropdown() {
    const playerSel = document.getElementById('shot-player');
    const teamFilter = document.getElementById('shot-team').value;
    playerSel.innerHTML = '<option value="">All Players</option>';

    const players = Object.entries(_data.players)
        .filter(([_, p]) => !teamFilter || p.team === teamFilter)
        .sort((a, b) => b[1].total_fga - a[1].total_fga);

    players.forEach(([name, p]) => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = `${name} (${p.total_fga} FGA)`;
        playerSel.appendChild(opt);
    });
}

function onFilterChange() {
    const src = event ? event.target : null;
    if (src && src.id === 'shot-team') {
        document.getElementById('shot-player').value = '';
        rebuildPlayerDropdown();
    }
    updateURL();
    renderAll();
}

function restoreFromURL() {
    const params = new URLSearchParams(location.search);
    const team = params.get('team');
    const player = params.get('player');
    if (team) {
        document.getElementById('shot-team').value = team;
        rebuildPlayerDropdown();
    }
    if (player) {
        document.getElementById('shot-player').value = player;
    }
}

function updateURL() {
    const team = document.getElementById('shot-team').value;
    const player = document.getElementById('shot-player').value;
    const params = new URLSearchParams();
    if (team) params.set('team', team);
    if (player) params.set('player', player);
    const qs = params.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
}

// ── Active data ───────────────────────────────────────────────────────────
function getActiveZoneData() {
    const player = document.getElementById('shot-player').value;
    const team   = document.getElementById('shot-team').value;

    if (player && _data.players[player]) {
        return { zones: _data.players[player].zones, label: player };
    }
    if (team && _data.teams[team]) {
        return { zones: _data.teams[team], label: TEAM_NAMES[team] || team };
    }
    return { zones: _data.league, label: 'League Average' };
}

function getActiveGridData() {
    const player = document.getElementById('shot-player').value;
    const team   = document.getElementById('shot-team').value;
    const grid   = _data.grid;
    if (!grid) return null;

    // Players don't have grid data — fall back to team or league
    if (player && team && grid.teams[team]) return grid.teams[team];
    if (team && grid.teams[team]) return grid.teams[team];
    return grid.league;
}

// ── Render all ────────────────────────────────────────────────────────────
function renderAll() {
    const { zones, label } = getActiveZoneData();
    document.getElementById('court-title').textContent = `${label} Shot Chart`;
    renderCourt(label);
    renderZoneTable(zones);
    renderDistChart(zones, label);
}

// ── Plotly Heatmap Court ──────────────────────────────────────────────────
function renderCourt(label) {
    const grid = _data.grid;
    const activeGrid = getActiveGridData();
    if (!grid || !activeGrid) {
        document.getElementById('court-chart').innerHTML =
            '<p style="color:var(--text-muted)">No heatmap data available.</p>';
        return;
    }

    const { cols, rows, x_min, x_max, y_min, y_max } = grid;
    const cellW = (x_max - x_min) / cols;
    const cellH = (y_max - y_min) / rows;

    // Build x/y axis labels (cell centers)
    const xVals = Array.from({length: cols}, (_, i) => x_min + (i + 0.5) * cellW);
    const yVals = Array.from({length: rows}, (_, i) => y_min + (i + 0.5) * cellH);

    // Court boundary check — mask cells outside playing area
    const courtHalfW = 740;
    const courtYMin = -80;
    const courtYMax = 1330;
    const arcRadius = 675;

    function isInsideCourt(cx, cy) {
        // Outside court rectangle (with margin to avoid edge bleed)
        if (Math.abs(cx) > courtHalfW - 30 || cy < courtYMin || cy > courtYMax) return false;
        // Near half-court line — too sparse
        if (cy > courtYMax - 100) return false;
        return true;
    }

    // Build the z matrix (FG%) and custom hover text
    const z = [];
    const hoverText = [];
    for (let r = 0; r < rows; r++) {
        const zRow = [];
        const hRow = [];
        for (let c = 0; c < cols; c++) {
            const cx = xVals[c];
            const cy = yVals[r];
            const fg  = activeGrid.fg_pct[r][c];
            const att = activeGrid.attempts[r][c];
            if (fg !== null && att > 0 && isInsideCourt(cx, cy)) {
                zRow.push(fg);
                hRow.push(`FG%: ${fg}%<br>${att} attempts`);
            } else {
                zRow.push(null);
                hRow.push('');
            }
        }
        z.push(zRow);
        hoverText.push(hRow);
    }

    const trace = {
        type: 'heatmap',
        x: xVals,
        y: yVals,
        z: z,
        text: hoverText,
        hovertemplate: '%{text}<extra></extra>',
        colorscale: [
            [0,    '#2563eb'],  // 0% - cold blue
            [0.25, '#5580c0'],  // 25%
            [0.45, '#6b7280'],  // 45% - neutral grey
            [0.55, '#8b6b6b'],  // 55%
            [0.75, '#ef6868'],  // 75%
            [1,    '#dc2626'],  // 100% - hot red
        ],
        zmin: 20,
        zmax: 80,
        zsmooth: 'best',
        connectgaps: false,
        showscale: true,
        colorbar: {
            title: { text: 'FG%', font: { color: '#9ca3af', size: 12 } },
            tickfont: { color: '#9ca3af', size: 11 },
            ticksuffix: '%',
            len: 0.6,
            thickness: 12,
            bgcolor: 'transparent',
            borderwidth: 0,
            x: 1.02,
        },
    };

    // Court line shapes
    const lc = 'rgba(255,255,255,0.5)';
    const lw = 1.5;

    // 3-point arc as SVG path
    const arcR = 675;
    let arcPath = '';
    for (let i = 0; i <= 50; i++) {
        const a = Math.PI + (0 - Math.PI) * (i / 50);
        const px = arcR * Math.cos(a);
        const py = arcR * Math.sin(a);
        arcPath += (i === 0 ? 'M' : 'L') + `${px},${py} `;
    }

    const shapes = [
        // Court outline
        { type:'rect', x0:-740, y0:-80, x1:740, y1:1330, line:{color:lc, width:2}, fillcolor:'transparent' },
        // Paint (5.8m deep from baseline → ~490 data units from Y=-80)
        { type:'rect', x0:-245, y0:-80, x1:245, y1:490, line:{color:lc, width:lw}, fillcolor:'transparent' },
        // FT circle (centered at FT line Y=490, radius ~60)
        { type:'circle', x0:-60, y0:430, x1:60, y1:550, line:{color:lc, width:1}, fillcolor:'transparent' },
        // 3PT arc
        { type:'path', path: arcPath, line:{color:lc, width:lw}, fillcolor:'transparent' },
        // 3PT sidelines
        { type:'line', x0:-740, y0:-80, x1:-740, y1:630, line:{color:lc, width:lw} },
        { type:'line', x0:740, y0:-80, x1:740, y1:630, line:{color:lc, width:lw} },
        // Basket
        { type:'circle', x0:-12, y0:-12, x1:12, y1:12, line:{color:'#ff6b00', width:2}, fillcolor:'#ff6b00' },
        // Backboard
        { type:'line', x0:-55, y0:-40, x1:55, y1:-40, line:{color:'rgba(255,255,255,0.6)', width:2.5} },
    ];

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: '#1a1b2e',
        height: 520,
        margin: { t: 10, r: 60, b: 10, l: 10 },
        xaxis: {
            range: [-800, 800],
            scaleanchor: 'y',
            scaleratio: 1,
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            fixedrange: true,
        },
        yaxis: {
            range: [-120, 1400],
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            fixedrange: true,
        },
        shapes: shapes,
        font: { family: 'Inter, sans-serif' },
    };

    document.getElementById('court-chart').innerHTML = '';
    Plotly.newPlot('court-chart', [trace], layout, {
        displayModeBar: false,
        responsive: true,
    });
}

// ── Zone table ────────────────────────────────────────────────────────────
function renderZoneTable(zones) {
    const league = _data.league;
    let totalAtt = 0, totalMakes = 0;

    const groups = [
        { name: 'At Rim',     keys: ['A'] },
        { name: 'Paint',      keys: ['B', 'C'] },
        { name: 'Mid-Range',  keys: ['D', 'E'] },
        { name: 'Extended',   keys: ['F', 'G'] },
        { name: '3-Point',    keys: ['H', 'I'] },
        { name: 'Deep 3PT',   keys: ['J'] },
    ];

    const rows = groups.map(g => {
        const att   = g.keys.reduce((s, z) => s + (zones[z]?.attempts || 0), 0);
        const makes = g.keys.reduce((s, z) => s + (zones[z]?.makes || 0), 0);
        const pts   = g.keys.reduce((s, z) => s + (zones[z]?.pps || 0) * (zones[z]?.attempts || 0), 0);
        const lAtt  = g.keys.reduce((s, z) => s + (league[z]?.attempts || 0), 0);
        const lMakes= g.keys.reduce((s, z) => s + (league[z]?.makes || 0), 0);
        totalAtt += att;
        totalMakes += makes;

        if (att === 0) {
            return `<tr>
                <td class="zone-name-cell">${g.name}</td>
                <td>0</td><td>0</td><td>–</td><td>–</td>
                <td><span class="vs-avg vs-avg-neutral">–</span></td>
            </tr>`;
        }

        const fg  = +(makes / att * 100).toFixed(1);
        const pps = +(pts / att).toFixed(2);
        const lFg = lAtt > 0 ? lMakes / lAtt * 100 : 0;
        const diff = (fg - lFg).toFixed(1);

        let vsClass = 'vs-avg-neutral';
        let vsText  = '–';
        if (att >= 5) {
            vsText = diff;
            if (diff > 2)  { vsClass = 'vs-avg-hot';  vsText = '+' + diff; }
            if (diff < -2) { vsClass = 'vs-avg-cold'; }
        }

        return `<tr>
            <td class="zone-name-cell">${g.name}</td>
            <td>${att}</td>
            <td>${makes}</td>
            <td>${fg}%</td>
            <td>${pps}</td>
            <td><span class="vs-avg ${vsClass}">${vsText}${vsText !== '–' ? '%' : ''}</span></td>
        </tr>`;
    }).join('');

    const totalFg = totalAtt > 0 ? (totalMakes / totalAtt * 100).toFixed(1) : '0.0';
    const footer = `<tr style="font-weight:700;border-top:2px solid var(--border)">
        <td>Total</td><td>${totalAtt}</td><td>${totalMakes}</td>
        <td>${totalFg}%</td><td colspan="2"></td>
    </tr>`;

    document.getElementById('zone-table-body').innerHTML = rows + footer;
}

// ── Distribution chart ────────────────────────────────────────────────────
function renderDistChart(zones, label) {
    const league = _data.league;

    // Combine symmetric zones into logical groups
    const groups = [
        { name: 'At Rim',     keys: ['A'] },
        { name: 'Paint',      keys: ['B', 'C'] },
        { name: 'Mid-Range',  keys: ['D', 'E'] },
        { name: 'Extended',   keys: ['F', 'G'] },
        { name: '3-Point',    keys: ['H', 'I'] },
        { name: 'Deep 3PT',   keys: ['J'] },
    ];
    const names = groups.map(g => g.name);

    const leagueTotal = ZONES.reduce((s, z) => s + (league[z]?.attempts || 0), 0);
    const activeTotal = ZONES.reduce((s, z) => s + (zones[z]?.attempts || 0), 0);

    const leaguePcts = groups.map(g => {
        const att = g.keys.reduce((s, z) => s + (league[z]?.attempts || 0), 0);
        return leagueTotal > 0 ? +(att / leagueTotal * 100).toFixed(1) : 0;
    });
    const activePcts = groups.map(g => {
        const att = g.keys.reduce((s, z) => s + (zones[z]?.attempts || 0), 0);
        return activeTotal > 0 ? +(att / activeTotal * 100).toFixed(1) : 0;
    });

    const isLeague = label === 'League Average';

    const traces = [
        {
            type: 'bar',
            y: names,
            x: activePcts,
            orientation: 'h',
            name: isLeague ? 'League' : label,
            marker: { color: '#a855f7' },
            hovertemplate: '%{y}: %{x}%<extra></extra>',
        },
    ];

    if (!isLeague) {
        traces.push({
            type: 'bar',
            y: names,
            x: leaguePcts,
            orientation: 'h',
            name: 'League Avg',
            marker: { color: '#374151' },
            hovertemplate: '%{y}: %{x}%<extra></extra>',
        });
    }

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        height: 260,
        margin: { t: 10, r: 20, b: 40, l: 90 },
        barmode: 'group',
        xaxis: {
            title: { text: '% of Total Shots', font: { color: '#6b7280', size: 11 } },
            tickfont: { color: '#6b7280', size: 11 },
            gridcolor: '#2d2e3a',
            ticksuffix: '%',
        },
        yaxis: {
            tickfont: { color: '#9ca3af', size: 12 },
            autorange: 'reversed',
        },
        legend: {
            font: { color: '#9ca3af', size: 11 },
            bgcolor: 'transparent',
            orientation: 'h',
            x: 0.5, xanchor: 'center', y: -0.15,
        },
        font: { family: 'Inter, sans-serif' },
    };

    document.getElementById('dist-chart').innerHTML = '';
    Plotly.newPlot('dist-chart', traces, layout, { displayModeBar: false, responsive: true });
}
