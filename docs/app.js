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

        // Populate team filter with full names but keep codes as values
        const teamMap = new Map();
        currentGames.forEach(g => {
            teamMap.set(g.ta, g.ta_name);
            teamMap.set(g.tb, g.tb_name);
        });

        // Sort by full name
        const sortedTeams = Array.from(teamMap.keys()).sort((a, b) => teamMap.get(a).localeCompare(teamMap.get(b)));

        teamFilter.innerHTML = '<option value="">All Teams</option>';
        sortedTeams.forEach(code => {
            const opt = document.createElement('option');
            opt.value = code;
            opt.textContent = `${teamMap.get(code)} (${code})`;
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
        opt.dataset.taName = g.ta_name;
        opt.dataset.tbName = g.tb_name;
        const winner = g.sa > g.sb ? g.ta : g.tb;
        const marker = winner === g.ta ? '✦ ' : '';
        const marker2 = winner === g.tb ? ' ✦' : '';

        let roundStr = g.rnd;
        if (typeof roundStr === 'number') roundStr = `Round ${roundStr}`;

        opt.textContent = `[${roundStr}] ${marker}${g.ta_name} ${g.sa} - ${g.sb} ${g.tb_name}${marker2}`;
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
        const option = gameSelect.options[gameSelect.selectedIndex];
        renderChart(data, option.dataset.taName, option.dataset.tbName);
    } catch (err) {
        console.error('Failed to load game data:', err);
    }
});

// ── Render Chart ─────────────────────────────────────────
function renderChart(data, taName, tbName) {
    const { ta, tb, timeline } = data;

    // Fallback if full names aren't provided
    taName = taName || ta;
    tbName = tbName || tb;

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
        `Score: ${taName} ${p.a} - ${p.b} ${tbName}<br>` +
        `WP (${taName}): ${(p.w * 100).toFixed(1)}%<br>` +
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
            hovertext: `<b>${kp.d}</b><br>WP: ${(kp.w * 100).toFixed(1)}%<br>Shift: ${kp.shift > 0 ? '+' : ''}${kp.shift.toFixed(1)}%<br>Score: ${taName} ${kp.a} - ${kp.b} ${tbName}<br>Q${kp.p} — ${fmtTime(kp.s)} remaining`,
            hoverinfo: 'text',
        });
    });

    const finalScore = full[full.length - 1];
    const winnerName = finalScore.a > finalScore.b ? taName : tbName;
    const minWP = Math.min(...wpPct);
    const maxWP = Math.max(...wpPct);
    summaryContent.innerHTML = `
        <strong>${winnerName} wins ${finalScore.a}-${finalScore.b}</strong> ·
        ${taName} WP range: ${minWP.toFixed(1)}% — ${maxWP.toFixed(1)}% ·
        ${full.length - 2} scoring plays
    `;

    const layout = {
        title: {
            text: `${taName} ${finalScore.a} - ${finalScore.b} ${tbName}`,
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
            <div class="key-play-meta">Q${kp.p} · ${fmtTime(kp.s)} · Score: ${taName} ${kp.a}-${kp.b} ${tbName}</div>
            <div class="key-play-shift ${cls}">WP: ${(kp.w * 100).toFixed(1)}% (${kp.shift > 0 ? '+' : ''}${kp.shift.toFixed(1)}%)</div>
        `;
        keyPlaysList.appendChild(card);
    });
    keyPlaysSection.classList.remove('hidden');


    gameSummary.classList.remove('hidden');

    // ── Advanced Stats Panel ─────────────────────────────
    const advStatsSection = document.getElementById('adv-stats');
    if (data.adv && Object.keys(data.adv).length > 0) {
        advStatsSection.classList.remove('hidden');

        // 1. Quarter Margins (Bar Chart)
        if (data.adv.q && data.adv.q.length > 0) {
            const periods = data.adv.q.map(q => q.p <= 4 ? `Q${q.p}` : `OT${q.p - 4}`);
            const margins = data.adv.q.map(q => q.a - q.b);
            const colors = margins.map(m => m >= 0 ? '#ef4444' : '#3b82f6');

            const qTrace = {
                x: periods,
                y: margins,
                type: 'bar',
                marker: { color: colors },
                text: margins.map(m => m > 0 ? `+${m}` : m),
                textposition: 'auto',
                hoverinfo: 'none'
            };

            const qLayout = {
                margin: { l: 30, r: 10, t: 10, b: 30 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#9ca3af' },
                xaxis: { fixedrange: true },
                yaxis: { fixedrange: true, zerolinecolor: '#4b5563' }
            };
            Plotly.newPlot('q-margin-chart', [qTrace], qLayout, { displayModeBar: false });
        }

        // 2. Player Impact (Scatter Plot)
        if (data.adv.i && data.adv.i.length > 0) {
            const teamA_players = data.adv.i.filter(p => p.t === ta);
            const teamB_players = data.adv.i.filter(p => p.t === tb);

            const impactTraces = [
                {
                    x: teamA_players.map(p => p.p),
                    y: teamA_players.map(p => p.h),
                    mode: 'markers+text',
                    type: 'scatter',
                    name: taName,
                    text: teamA_players.map(p => p.n),
                    textposition: 'top center',
                    marker: { size: 12, color: '#ef4444', line: { color: 'white', width: 1 } },
                    hoverinfo: 'text',
                    hovertext: teamA_players.map(p => `<b>${p.n}</b><br>Points: ${p.p}<br>Hustle (REB+AST+STL): ${p.h}`)
                },
                {
                    x: teamB_players.map(p => p.p),
                    y: teamB_players.map(p => p.h),
                    mode: 'markers+text',
                    type: 'scatter',
                    name: tbName,
                    text: teamB_players.map(p => p.n),
                    textposition: 'top center',
                    marker: { size: 12, color: '#3b82f6', line: { color: 'white', width: 1 } },
                    hoverinfo: 'text',
                    hovertext: teamB_players.map(p => `<b>${p.n}</b><br>Points: ${p.p}<br>Hustle (REB+AST+STL): ${p.h}`)
                }
            ];

            const impactLayout = {
                margin: { l: 40, r: 20, t: 20, b: 40 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#9ca3af' },
                xaxis: { title: 'Offensive Production (Points)', gridcolor: '#2d2e3a' },
                yaxis: { title: 'Playmaking & Hustle', gridcolor: '#2d2e3a' },
                legend: { orientation: 'h', y: 1.1, x: 0.5, xanchor: 'center' },
                annotations: [
                    { x: 1, y: 1, xref: 'paper', yref: 'paper', text: 'High Volume / High Hustle', showarrow: false, font: { color: '#10b981', size: 10 }, xanchor: 'right', yanchor: 'top', opacity: 0.5 },
                    { x: 1, y: 0, xref: 'paper', yref: 'paper', text: 'Scoring Specialists', showarrow: false, font: { color: '#f59e0b', size: 10 }, xanchor: 'right', yanchor: 'bottom', opacity: 0.5 },
                    { x: 0, y: 1, xref: 'paper', yref: 'paper', text: 'Role Players / Glue', showarrow: false, font: { color: '#f59e0b', size: 10 }, xanchor: 'left', yanchor: 'top', opacity: 0.5 }
                ]
            };
            Plotly.newPlot('impact-chart', impactTraces, impactLayout, { displayModeBar: false });
        }

        // 3. Major Scoring Runs
        const runsList = document.getElementById('runs-list');
        runsList.innerHTML = '';
        if (data.adv.r && data.adv.r.length > 0) {
            data.adv.r.forEach(run => {
                const isTeamA = run.t === ta;
                const teamName = isTeamA ? taName : tbName;
                const cls = isTeamA ? 'team-a' : 'team-b';

                const item = document.createElement('div');
                item.className = `run-item ${cls}`;
                item.innerHTML = `
                    <div class="run-score ${cls}">${run.p} - 0</div>
                    <div class="run-meta">
                        <strong>${teamName}</strong><br>
                        ${fmtTime(2400 - run.en)} to ${fmtTime(2400 - run.st)} remaining
                    </div>
                `;
                runsList.appendChild(item);
            });
        } else {
            runsList.innerHTML = '<div style="color:var(--text-muted); font-size: 0.9rem; padding: 1rem 0;">No major runs (8+ pts) detected.</div>';
        }

        // 4. Four Factors Radar
        if (data.adv.f && data.adv.f.length > 0) {
            const get_team_factors = (teamCode) => {
                const fa = data.adv.f.find(f => f.t === teamCode) || { eFG: 0, TOV: 0, ORB: 0, FTR: 0 };
                return [fa.eFG, fa.TOV, fa.ORB, fa.FTR, fa.eFG];
            };

            const rCategories = ['eFG%', 'TOV% (Lower=Better)', 'ORB%', 'FT Rate', 'eFG%'];

            const rTraces = [
                {
                    type: 'scatterpolar',
                    r: get_team_factors(ta),
                    theta: rCategories,
                    fill: 'toself',
                    name: taName,
                    line: { color: '#ef4444' },
                    fillcolor: 'rgba(239, 68, 68, 0.2)'
                },
                {
                    type: 'scatterpolar',
                    r: get_team_factors(tb),
                    theta: rCategories,
                    fill: 'toself',
                    name: tbName,
                    line: { color: '#3b82f6' },
                    fillcolor: 'rgba(59, 130, 246, 0.2)'
                }
            ];

            const rLayout = {
                polar: {
                    radialaxis: { visible: true, range: [0, 80], color: '#4b5563', gridcolor: '#334155' },
                    angularaxis: { color: '#9ca3af', gridcolor: '#334155' },
                    bgcolor: 'transparent'
                },
                showlegend: true,
                legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center', font: { color: '#9ca3af' } },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                margin: { l: 65, r: 65, t: 40, b: 50 }
            };

            Plotly.newPlot('radar-chart', rTraces, rLayout, { displayModeBar: false });
        }

        // 5. Top Lineups
        const lineupsList = document.getElementById('lineups-list');
        lineupsList.innerHTML = '';
        if (data.adv.l && data.adv.l.length > 0) {
            data.adv.l.forEach(lu => {
                const isTeamA = lu.t === ta;
                const teamName = isTeamA ? taName : tbName;
                const cls = isTeamA ? 'team-a' : 'team-b';

                const item = document.createElement('div');
                item.className = `lineup-item ${cls}`;

                const scoreClass = lu.n > 0 ? 'positive' : (lu.n < 0 ? 'negative' : '');
                const scorePrefix = lu.n > 0 ? '+' : '';

                item.innerHTML = `
                    <div class="lineup-meta">
                        <strong>${teamName}</strong>
                        <div class="lineup-score ${scoreClass}">${scorePrefix}${lu.n}</div>
                    </div>
                    <div class="lineup-names">${lu.l}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 5px;">Played: ${lu.d} mins</div>
                `;
                lineupsList.appendChild(item);
            });
        } else {
            lineupsList.innerHTML = '<div style="color:var(--text-muted); font-size: 0.9rem; padding: 1rem 0;">No significant 5-man lineups tracked for this game.</div>';
        }

        // 6. Spatial Gravity Map (Interactive Shot Chart)
        if (data.adv.s && data.adv.s.length > 0) {
            const shotData = data.adv.s;
            let currentShotTeam = ta;

            function getCourtShapes() {
                const c = '#555';
                const w = 1.5;
                // Generate arc path as SVG
                function arcPath(cx, cy, rx, ry, startDeg, endDeg, steps = 60) {
                    let path = '';
                    for (let i = 0; i <= steps; i++) {
                        const angle = (startDeg + (endDeg - startDeg) * i / steps) * Math.PI / 180;
                        const x = cx + rx * Math.cos(angle);
                        const y = cy + ry * Math.sin(angle);
                        path += (i === 0 ? 'M ' : 'L ') + x + ',' + y + ' ';
                    }
                    return path;
                }
                const cornerX = 660;
                const arcR = 675;
                const interY = Math.sqrt(arcR * arcR - cornerX * cornerX);

                return [
                    // Baseline
                    { type: 'line', x0: -750, y0: -157.5, x1: 750, y1: -157.5, line: { color: c, width: w } },
                    // Backboard
                    { type: 'line', x0: -90, y0: -37.5, x1: 90, y1: -37.5, line: { color: c, width: w } },
                    // Paint left
                    { type: 'line', x0: -245, y0: -157.5, x1: -245, y1: 422.5, line: { color: c, width: w } },
                    // Paint right
                    { type: 'line', x0: 245, y0: -157.5, x1: 245, y1: 422.5, line: { color: c, width: w } },
                    // Paint top
                    { type: 'line', x0: -245, y0: 422.5, x1: 245, y1: 422.5, line: { color: c, width: w } },
                    // Restricted area arc
                    { type: 'path', path: arcPath(0, 0, 125, 125, 0, 180), line: { color: c, width: w }, fillcolor: 'rgba(0,0,0,0)' },
                    // Basket rim
                    { type: 'circle', x0: -22.5, y0: -22.5, x1: 22.5, y1: 22.5, line: { color: '#ef4444', width: 2 }, fillcolor: 'rgba(0,0,0,0)' },
                    // 3PT left corner
                    { type: 'line', x0: cornerX, y0: -157.5, x1: cornerX, y1: interY, line: { color: c, width: w } },
                    // 3PT right corner
                    { type: 'line', x0: -cornerX, y0: -157.5, x1: -cornerX, y1: interY, line: { color: c, width: w } },
                    // 3PT arc
                    {
                        type: 'path', path: arcPath(0, 0, arcR, arcR,
                            Math.atan2(interY, cornerX) * 180 / Math.PI,
                            180 - Math.atan2(interY, cornerX) * 180 / Math.PI),
                        line: { color: c, width: w }, fillcolor: 'rgba(0,0,0,0)'
                    }
                ];
            }

            function renderShotChart(teamCode) {
                const teamShots = shotData.filter(s => s.t === teamCode);
                const isTeamA = teamCode === ta;
                const teamName = isTeamA ? taName : tbName;

                const makes = teamShots.filter(s => s.m === 1);
                const misses = teamShots.filter(s => s.m === 0);
                const fgPct = teamShots.length > 0 ? (makes.length / teamShots.length * 100).toFixed(1) : 0;

                const traces = [
                    {
                        x: makes.map(s => s.x), y: makes.map(s => s.y),
                        mode: 'markers', type: 'scatter', name: 'Made',
                        marker: { size: 10, color: '#10b981', symbol: 'circle', line: { color: 'white', width: 1 }, opacity: 0.85 },
                        hoverinfo: 'text',
                        hovertext: makes.map(s => `<b>${s.n}</b><br>Made (Q${s.q})`)
                    },
                    {
                        x: misses.map(s => s.x), y: misses.map(s => s.y),
                        mode: 'markers', type: 'scatter', name: 'Missed',
                        marker: { size: 8, color: '#ef4444', symbol: 'x', line: { width: 1.5 }, opacity: 0.6 },
                        hoverinfo: 'text',
                        hovertext: misses.map(s => `<b>${s.n}</b><br>Missed (Q${s.q})`)
                    }
                ];

                const layout = {
                    shapes: getCourtShapes(),
                    xaxis: { range: [-800, 800], showgrid: false, zeroline: false, showticklabels: false, fixedrange: true, scaleanchor: 'y' },
                    yaxis: { range: [-200, 1000], showgrid: false, zeroline: false, showticklabels: false, fixedrange: true },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: '#0E1117',
                    margin: { l: 10, r: 10, t: 35, b: 10 },
                    legend: { orientation: 'h', y: 1.05, x: 0.5, xanchor: 'center', font: { color: '#9ca3af' } },
                    title: { text: `${teamName} — ${teamShots.length} Attempts | ${fgPct}% FG`, font: { color: '#9ca3af', size: 14 }, x: 0.5 },
                    dragmode: false
                };

                Plotly.newPlot('shot-chart', traces, layout, { displayModeBar: false, staticPlot: false });
            }

            // Initial render
            renderShotChart(ta);

            // Toggle buttons
            const btnTa = document.getElementById('btn-shots-ta');
            const btnTb = document.getElementById('btn-shots-tb');
            btnTa.textContent = taName;
            btnTb.textContent = tbName;

            btnTa.onclick = () => {
                btnTa.classList.add('active'); btnTb.classList.remove('active');
                currentShotTeam = ta; renderShotChart(ta);
            };
            btnTb.onclick = () => {
                btnTb.classList.add('active'); btnTa.classList.remove('active');
                currentShotTeam = tb; renderShotChart(tb);
            };
        }

    } else {
        advStatsSection.classList.add('hidden');
    }
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
    document.getElementById('adv-stats').classList.add('hidden');
    Plotly.purge(chartDiv);
}

// ── Go ───────────────────────────────────────────────────
init();
