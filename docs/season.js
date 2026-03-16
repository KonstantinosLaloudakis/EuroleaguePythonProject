/**
 * season.js — Euroleague Season Hub
 * Renders standings, power scatter, MVP race, playoff grid,
 * oracle predictions, player forecasts, and accuracy stats.
 */

'use strict';

// ── Team color lookup ─────────────────────────────────────────────────────
const TEAM_COLORS = {
    'OLY': '#E2001A', 'ULK': '#003366', 'PAN': '#007F3D', 'MAD': '#6d4c94',
    'BAR': '#004D98', 'MCO': '#D4AF37', 'ZAL': '#006233', 'DUB': '#555555',
    'IST': '#003366', 'HTA': '#cc0000', 'PAR': '#333333', 'RED': '#CC0000',
    'TEL': '#F6C300', 'BAS': '#B50031', 'MUN': '#0066B2', 'VIR': '#1a1a1a',
    'PAM': '#EB7622', 'ASV': '#222222', 'PRS': '#1a1a2e', 'BER': '#005CA9',
    'MIL': '#C8102E',
};

// ── Sort state ────────────────────────────────────────────────────────────
let sortState = { col: 'wins', asc: false };

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
    try {
        const resp = await fetch('data/current/dashboard.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        renderStandings(data.teams || []);
        renderPowerScatter(data.teams || []);
        renderMVPRace(data.mvp || []);
        renderPlayoffGrid(data.teams || []);
        renderOracleHeader(data);
        renderOracleCards(data.oracle);
        renderPlayerForecasts(
            (data.oracle && data.oracle.player_forecasts) ? data.oracle.player_forecasts : []
        );
        renderAccuracyStats(data.accuracy);

    } catch (err) {
        console.error('Dashboard load error:', err);
        document.getElementById('load-error').classList.remove('hidden');
        // Hide loading placeholders
        document.querySelectorAll('.loading-placeholder').forEach(el => {
            el.textContent = 'Failed to load data.';
        });
    }
}

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(tabId) {
    const tabs = ['tab-standings', 'tab-oracle'];
    tabs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', id !== tabId);
    });

    document.querySelectorAll('.tab-btn').forEach((btn, i) => {
        btn.classList.toggle('active', tabs[i] === tabId);
    });

    // Trigger Plotly resize so charts fill their containers correctly
    if (tabId === 'tab-oracle') {
        setTimeout(() => {
            const calibEl = document.getElementById('calibration-chart');
            if (calibEl && calibEl._plotly) Plotly.Plots.resize(calibEl);
        }, 50);
    }
}

// ── Standings table ───────────────────────────────────────────────────────
function renderStandings(teams) {
    const container = document.getElementById('standings-table');
    if (!teams.length) {
        container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:1rem;">No standings data available.</p>';
        return;
    }

    const cols = [
        { key: '#',        label: '#',        sortKey: null,       align: 'center' },
        { key: 'name',     label: 'Team',     sortKey: 'name',     align: 'left' },
        { key: 'wl',       label: 'W-L',      sortKey: 'wins',     align: 'center' },
        { key: 'elo',      label: 'Elo',      sortKey: 'elo',      align: 'right' },
        { key: 'adj_net',  label: 'Adj Net',  sortKey: 'adj_net',  align: 'right' },
        { key: 'adj_off',  label: 'Adj Off',  sortKey: 'adj_off',  align: 'right' },
        { key: 'adj_def',  label: 'Adj Def',  sortKey: 'adj_def',  align: 'right' },
        { key: 'avg_wins', label: 'xWins',    sortKey: 'avg_wins', align: 'right' },
        { key: 'top4_pct', label: 'Top 4%',   sortKey: 'top4_pct', align: 'right' },
        { key: 'top6_pct', label: 'Top 6%',   sortKey: 'top6_pct', align: 'right' },
        { key: 'top10_pct',label: 'Top 10%',  sortKey: 'top10_pct',align: 'right' },
    ];

    function buildTable(sorted) {
        let html = '<div class="standings-table-wrap"><table class="standings-tbl"><thead><tr>';
        cols.forEach(c => {
            const sortable = c.sortKey ? 'sortable' : '';
            const active = sortState.col === c.sortKey ? 'sort-active' : '';
            const arrow = sortState.col === c.sortKey ? (sortState.asc ? ' ▲' : ' ▼') : '';
            const onclick = c.sortKey ? `onclick="sortStandings('${c.sortKey}')"` : '';
            html += `<th class="${sortable} ${active}" ${onclick} style="text-align:${c.align}">${c.label}${arrow}</th>`;
        });
        html += '</tr></thead><tbody>';

        sorted.forEach((t, i) => {
            const badgeColor = TEAM_COLORS[t.team] || '#555';
            const badge = `<span class="team-badge" style="background:${badgeColor}">${t.team.substring(0,3)}</span>`;
            const netColor = t.adj_net >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            const netStr = (t.adj_net >= 0 ? '+' : '') + t.adj_net.toFixed(2);

            html += `<tr>
                <td style="text-align:center;color:var(--text-muted);font-size:0.8rem">${i + 1}</td>
                <td style="text-align:left">${badge} <span style="font-weight:600">${t.name}</span></td>
                <td style="text-align:center;font-weight:700">${t.wins}-${t.losses}</td>
                <td style="text-align:right">${t.elo.toFixed(0)}</td>
                <td style="text-align:right;color:${netColor};font-weight:700">${netStr}</td>
                <td style="text-align:right">${t.adj_off.toFixed(1)}</td>
                <td style="text-align:right">${t.adj_def.toFixed(1)}</td>
                <td style="text-align:right">${t.avg_wins.toFixed(1)}</td>
                <td style="text-align:right">${pctCell(t.top4_pct, '#a855f7')}</td>
                <td style="text-align:right">${pctCell(t.top6_pct, '#22c55e')}</td>
                <td style="text-align:right">${pctCell(t.top10_pct, '#3b82f6')}</td>
            </tr>`;
        });

        html += '</tbody></table></div>';
        return html;
    }

    function pctCell(val, color) {
        const opacity = Math.min(val / 100, 1) * 0.6;
        const bg = hexToRgba(color, opacity);
        const textColor = opacity > 0.3 ? '#fff' : 'var(--text-primary)';
        return `<span class="pct-cell" style="background:${bg};color:${textColor}">${val.toFixed(1)}%</span>`;
    }

    function getSorted() {
        return [...teams].sort((a, b) => {
            let va = a[sortState.col], vb = b[sortState.col];
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            if (va < vb) return sortState.asc ? -1 : 1;
            if (va > vb) return sortState.asc ? 1 : -1;
            return 0;
        });
    }

    window.sortStandings = function (col) {
        if (sortState.col === col) {
            sortState.asc = !sortState.asc;
        } else {
            sortState.col = col;
            sortState.asc = false;
        }
        container.innerHTML = buildTable(getSorted());
    };

    container.innerHTML = buildTable(getSorted());
}

// ── Power Scatter ─────────────────────────────────────────────────────────
function renderPowerScatter(teams) {
    if (!teams.length) return;

    const meanOff = teams.reduce((s, t) => s + t.adj_off, 0) / teams.length;
    const meanDef = teams.reduce((s, t) => s + t.adj_def, 0) / teams.length;

    const x = teams.map(t => t.adj_off);
    const y = teams.map(t => t.adj_def);
    const text = teams.map(t => t.team);
    const colors = teams.map(t => t.adj_net);
    const hoverText = teams.map(t =>
        `<b>${t.name} (${t.team})</b><br>Adj Off: ${t.adj_off.toFixed(1)}<br>Adj Def: ${t.adj_def.toFixed(1)}<br>Adj Net: ${t.adj_net >= 0 ? '+' : ''}${t.adj_net.toFixed(2)}`
    );

    const xMin = Math.min(...x) - 2, xMax = Math.max(...x) + 2;
    const yMin = Math.min(...y) - 2, yMax = Math.max(...y) + 2;

    // Quadrant label positions
    const quadrants = [
        { x: xMax - 0.5, y: yMin + 0.5, text: 'Elite', xanchor: 'right', yanchor: 'bottom' },
        { x: xMin + 0.5, y: yMin + 0.5, text: 'Offensive', xanchor: 'left', yanchor: 'bottom' },
        { x: xMax - 0.5, y: yMax - 0.5, text: 'Defensive', xanchor: 'right', yanchor: 'top' },
        { x: xMin + 0.5, y: yMax - 0.5, text: 'Weak', xanchor: 'left', yanchor: 'top' },
    ];

    const annotations = quadrants.map(q => ({
        x: q.x, y: q.y,
        text: q.text,
        xanchor: q.xanchor,
        yanchor: q.yanchor,
        showarrow: false,
        font: { color: 'rgba(156,163,175,0.35)', size: 13, family: 'Outfit' },
    }));

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: '#0f1117',
        font: { color: '#9ca3af', family: 'Inter' },
        margin: { t: 10, b: 50, l: 55, r: 10 },
        xaxis: {
            title: 'Adj. Offensive Rating',
            gridcolor: '#2d2e3a',
            zerolinecolor: '#2d2e3a',
            tickfont: { size: 11 },
        },
        yaxis: {
            title: 'Adj. Defensive Rating',
            autorange: 'reversed',
            gridcolor: '#2d2e3a',
            zerolinecolor: '#2d2e3a',
            tickfont: { size: 11 },
        },
        shapes: [
            // Vertical mean line
            { type: 'line', x0: meanOff, x1: meanOff, y0: yMin, y1: yMax,
              line: { color: 'rgba(156,163,175,0.3)', width: 1, dash: 'dot' } },
            // Horizontal mean line
            { type: 'line', x0: xMin, x1: xMax, y0: meanDef, y1: meanDef,
              line: { color: 'rgba(156,163,175,0.3)', width: 1, dash: 'dot' } },
        ],
        annotations,
        showlegend: false,
        coloraxis: { showscale: false },
        hovermode: 'closest',
    };

    const trace = {
        type: 'scatter',
        mode: 'markers+text',
        x, y,
        text,
        hovertext: hoverText,
        hoverinfo: 'text',
        textposition: 'top center',
        textfont: { color: '#f0f0f5', size: 10, family: 'Inter' },
        marker: {
            size: 14,
            color: colors,
            colorscale: [
                [0, '#ef4444'],
                [0.5, '#f59e0b'],
                [1, '#22c55e'],
            ],
            cmin: Math.min(...colors),
            cmax: Math.max(...colors),
            line: { color: '#1f2029', width: 1.5 },
        },
    };

    Plotly.newPlot('power-scatter', [trace], layout, { displayModeBar: false, responsive: true });
}

// ── MVP Race bar chart ────────────────────────────────────────────────────
function renderMVPRace(mvp) {
    if (!mvp.length) return;

    const top10 = mvp.slice(0, 10);
    // Last name only
    const names = top10.map(p => {
        const parts = p.player.split(',');
        return parts.length > 1 ? parts[0].trim() : p.player;
    });
    const scores = top10.map(p => p.mvp_score);
    const barColors = top10.map(p => TEAM_COLORS[p.team] || '#555');
    const hoverText = top10.map(p =>
        `<b>${p.player}</b><br>Team: ${p.team}<br>MVP Score: ${p.mvp_score.toFixed(1)}<br>Avg PIR: ${p.avg_pir.toFixed(1)}<br>GP: ${p.gp}`
    );

    const trace = {
        type: 'bar',
        orientation: 'h',
        x: scores,
        y: names,
        text: scores.map(s => s.toFixed(1)),
        textposition: 'inside',
        insidetextanchor: 'end',
        textfont: { color: '#fff', size: 11 },
        hovertext: hoverText,
        hoverinfo: 'text',
        marker: {
            color: barColors,
            line: { color: '#1f2029', width: 1 },
        },
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: '#0f1117',
        font: { color: '#9ca3af', family: 'Inter' },
        margin: { t: 10, b: 40, l: 110, r: 10 },
        xaxis: {
            title: 'MVP Score',
            gridcolor: '#2d2e3a',
            zerolinecolor: '#2d2e3a',
            tickfont: { size: 11 },
        },
        yaxis: {
            autorange: 'reversed',
            gridcolor: '#2d2e3a',
            tickfont: { size: 12, color: '#f0f0f5' },
        },
        showlegend: false,
        hovermode: 'closest',
    };

    Plotly.newPlot('mvp-chart', [trace], layout, { displayModeBar: false, responsive: true });
}

// ── Playoff probability grid ──────────────────────────────────────────────
function renderPlayoffGrid(teams) {
    const container = document.getElementById('playoff-grid');
    if (!teams.length) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem">No playoff data available.</p>';
        return;
    }

    const sorted = [...teams].sort((a, b) => b.top6_pct - a.top6_pct);

    let html = '<div class="playoff-grid-inner">';
    html += `<div class="playoff-header-row">
        <div class="ph-team">Team</div>
        <div class="ph-xwins">xWins</div>
        <div class="ph-tile" style="color:#a855f7">Top 4</div>
        <div class="ph-tile" style="color:#22c55e">Top 6</div>
        <div class="ph-tile" style="color:#3b82f6">Top 10</div>
    </div>`;

    sorted.forEach(t => {
        const badgeColor = TEAM_COLORS[t.team] || '#555';
        const badge = `<span class="team-badge" style="background:${badgeColor}">${t.team.substring(0,3)}</span>`;
        html += `<div class="playoff-row">
            <div class="pr-team">${badge} <span class="pr-name">${t.name}</span></div>
            <div class="pr-xwins">${t.avg_wins.toFixed(1)}</div>
            <div class="pr-tile">${playoffTile(t.top4_pct, '#a855f7')}</div>
            <div class="pr-tile">${playoffTile(t.top6_pct, '#22c55e')}</div>
            <div class="pr-tile">${playoffTile(t.top10_pct, '#3b82f6')}</div>
        </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}

function playoffTile(val, color) {
    const opacity = Math.min(val / 100, 1) * 0.75;
    const bg = hexToRgba(color, opacity);
    const textColor = opacity > 0.25 ? '#fff' : 'var(--text-muted)';
    return `<div class="playoff-tile" style="background:${bg};color:${textColor}">${val.toFixed(1)}%</div>`;
}

// ── Oracle header ─────────────────────────────────────────────────────────
function renderOracleHeader(data) {
    const el = document.getElementById('oracle-header');
    const round = data.oracle ? data.oracle.round : null;
    const acc = data.accuracy ? data.accuracy.accuracy : null;

    let html = '<div class="oracle-header-content">';
    html += `<div class="oracle-round-badge">Round ${round || data.round || '?'} Forecast</div>`;
    if (acc !== null) {
        html += `<div class="oracle-acc-badge">Model Accuracy: <strong>${acc.toFixed(1)}%</strong></div>`;
    }
    html += '</div>';
    el.innerHTML = html;
}

// ── Oracle game cards ─────────────────────────────────────────────────────
function renderOracleCards(oracle) {
    const container = document.getElementById('oracle-cards');
    if (!oracle || !oracle.predictions || !oracle.predictions.length) {
        container.innerHTML = '<div class="oracle-placeholder"><p>No oracle predictions available for the next round.</p></div>';
        return;
    }

    const preds = oracle.predictions;
    let html = '<div class="oracle-cards-grid">';

    preds.forEach(p => {
        const homeWP = p.HomeWinProb || 50;
        const awayWP = 100 - homeWP;
        const isHomeWinner = p.Winner === p.Local;
        const margin = p.Margin ? Math.abs(p.Margin).toFixed(1) : '?';
        const conf = p.Conf ? p.Conf.toFixed(1) : '?';
        const homeGlow = isHomeWinner ? ' winner-glow' : '';
        const awayGlow = !isHomeWinner ? ' winner-glow' : '';
        const homeColor = TEAM_COLORS[p.Local] || '#ef4444';
        const awayColor = TEAM_COLORS[p.Road] || '#3b82f6';

        // Truncate insight to 100 chars
        let insight = '';
        if (p.Insight) {
            const clean = p.Insight.replace(/[\u2600-\u27BF\uD800-\uDFFF]/gu, '').trim();
            insight = clean.length > 100 ? clean.substring(0, 97) + '…' : clean;
        }

        const confBadgeClass = conf >= 75 ? 'conf-high' : conf >= 60 ? 'conf-med' : 'conf-low';

        html += `<div class="oracle-card">
            <div class="oracle-matchup">
                <div class="oracle-team home-team${homeGlow}">
                    <span class="team-badge" style="background:${homeColor}">${(p.Local||'').substring(0,3)}</span>
                    <span class="oracle-team-name">${p.LocalName || p.Local}</span>
                    <span class="ha-badge ha-home">H</span>
                </div>
                <div class="oracle-vs">vs</div>
                <div class="oracle-team away-team${awayGlow}">
                    <span class="ha-badge ha-away">A</span>
                    <span class="oracle-team-name">${p.RoadName || p.Road}</span>
                    <span class="team-badge" style="background:${awayColor}">${(p.Road||'').substring(0,3)}</span>
                </div>
            </div>
            <div class="wp-bar-wrap">
                <div class="wp-bar wp-home" style="width:${homeWP}%;background:${homeColor}80">
                    ${homeWP.toFixed(0)}%
                </div>
                <div class="wp-bar wp-away" style="width:${awayWP}%;background:${awayColor}80">
                    ${awayWP.toFixed(0)}%
                </div>
            </div>
            <div class="oracle-footer">
                <span class="oracle-margin">±${margin} pts</span>
                <span class="oracle-conf ${confBadgeClass}">${conf}% conf</span>
            </div>
            ${insight ? `<div class="oracle-insight">${insight}</div>` : ''}
        </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}

// ── Player forecasts table ────────────────────────────────────────────────
function renderPlayerForecasts(forecasts) {
    const container = document.getElementById('player-forecast-table');
    if (!forecasts || !forecasts.length) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem">No player forecast data available.</p>';
        return;
    }

    const top15 = forecasts.slice(0, 15);
    let html = '<div style="overflow-x:auto"><table class="forecast-tbl">';
    html += `<thead><tr>
        <th>#</th>
        <th style="text-align:left">Player</th>
        <th>Tm</th>
        <th>vs</th>
        <th>H/A</th>
        <th>AvgPIR</th>
        <th>Form</th>
        <th>Def</th>
        <th>WinP%</th>
        <th>PredPIR</th>
        <th>PredPTS</th>
    </tr></thead><tbody>`;

    top15.forEach((p, i) => {
        const rowBg = i % 2 === 0 ? 'background:rgba(255,255,255,0.02)' : '';
        const pirHighlight = p.PredictedPIR >= 20 ? 'color:var(--accent-gold);font-weight:700' : '';
        const ha = p.IsHome ? 'H' : 'A';
        const haColor = p.IsHome ? 'var(--accent-green)' : 'var(--accent-blue)';
        const teamColor = TEAM_COLORS[p.Team] || '#555';
        const lastName = (p.Player || '').split(',')[0].trim();
        const formPct = p.FormFactor ? ((p.FormFactor - 1) * 100).toFixed(0) : '0';
        const formColor = p.FormFactor >= 1 ? 'var(--accent-green)' : 'var(--accent-red)';
        const formStr = (p.FormFactor >= 1 ? '+' : '') + formPct + '%';
        const defFactor = p.DefFactor ? p.DefFactor.toFixed(2) : '1.00';

        html += `<tr style="${rowBg}">
            <td style="color:var(--text-muted);text-align:center">${i + 1}</td>
            <td style="text-align:left;font-weight:600">${lastName}</td>
            <td><span class="team-badge sm" style="background:${teamColor}">${p.Team}</span></td>
            <td style="color:var(--text-muted)">${p.Opponent || ''}</td>
            <td style="color:${haColor};font-weight:700;text-align:center">${ha}</td>
            <td style="text-align:right">${(p.AvgPIR || 0).toFixed(1)}</td>
            <td style="text-align:right;color:${formColor}">${formStr}</td>
            <td style="text-align:right">${defFactor}</td>
            <td style="text-align:right">${(p.WinProb || 0).toFixed(0)}%</td>
            <td style="text-align:right;${pirHighlight}">${(p.PredictedPIR || 0).toFixed(1)}</td>
            <td style="text-align:right">${(p.PredictedPTS || 0).toFixed(1)}</td>
        </tr>`;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// ── Accuracy stats ────────────────────────────────────────────────────────
function renderAccuracyStats(accuracy) {
    const container = document.getElementById('accuracy-stats');
    if (!accuracy) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem">No accuracy data available.</p>';
        return;
    }

    const acc = accuracy.accuracy || 0;
    const brier = accuracy.brier_score || 0;
    const logloss = accuracy.log_loss || 0;
    const n = accuracy.n_games || 0;
    const calibration = accuracy.calibration || [];

    let html = `<div class="accuracy-stat-row">
        <div class="acc-stat-box">
            <div class="acc-val" style="color:var(--accent-green)">${acc.toFixed(1)}%</div>
            <div class="acc-label">Accuracy</div>
        </div>
        <div class="acc-stat-box">
            <div class="acc-val">${brier.toFixed(4)}</div>
            <div class="acc-label">Brier Score</div>
        </div>
        <div class="acc-stat-box">
            <div class="acc-val">${logloss.toFixed(4)}</div>
            <div class="acc-label">Log-Loss</div>
        </div>
        <div class="acc-stat-box">
            <div class="acc-val">${n}</div>
            <div class="acc-label">Games</div>
        </div>
    </div>`;

    container.innerHTML = html;

    // Calibration chart
    if (calibration.length) {
        const calibDiv = document.createElement('div');
        calibDiv.id = 'calibration-chart';
        calibDiv.style.height = '220px';
        calibDiv.style.marginTop = '1rem';
        container.appendChild(calibDiv);

        const buckets = calibration.map(c => c.Bucket);
        const accVals = calibration.map(c => c.Accuracy);
        const confVals = calibration.map(c => c.AvgConfidence);

        const traces = [
            {
                type: 'bar',
                name: 'Actual Accuracy %',
                x: buckets,
                y: accVals,
                marker: { color: '#22c55e', opacity: 0.8 },
                hovertemplate: '%{x}: %{y:.1f}%<extra>Actual</extra>',
            },
            {
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Avg Confidence %',
                x: buckets,
                y: confVals,
                line: { color: '#a855f7', width: 2 },
                marker: { color: '#a855f7', size: 8 },
                hovertemplate: '%{x}: %{y:.1f}%<extra>Confidence</extra>',
            },
        ];

        const layout = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: '#0f1117',
            font: { color: '#9ca3af', family: 'Inter', size: 10 },
            margin: { t: 5, b: 45, l: 40, r: 10 },
            xaxis: { gridcolor: '#2d2e3a', tickfont: { size: 10 } },
            yaxis: { gridcolor: '#2d2e3a', tickfont: { size: 10 }, title: '%' },
            legend: { font: { size: 10 }, bgcolor: 'transparent', x: 0, y: 1.1, orientation: 'h' },
            showlegend: true,
        };

        Plotly.newPlot('calibration-chart', traces, layout, { displayModeBar: false, responsive: true });
    }
}

// ── Utility: hex to rgba ──────────────────────────────────────────────────
function hexToRgba(hex, alpha) {
    const h = hex.replace('#', '');
    const len = h.length === 3 ? 1 : 2;
    const r = parseInt(h.substring(0, len).padEnd(2, h[0]), 16);
    const g = parseInt(h.substring(len, len * 2).padEnd(2, h[len]), 16);
    const b = parseInt(h.substring(len * 2, len * 3).padEnd(2, h[len * 2]), 16);
    return `rgba(${r},${g},${b},${alpha.toFixed(3)})`;
}

// ── Boot ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
