'use strict';

const DASHBOARD_URL = 'data/current/dashboard.json';

function teamColor(code) {
  return (typeof TEAM_COLORS !== 'undefined' && TEAM_COLORS[code]) || '#6b7280';
}

function teamName(code) {
  return (typeof TEAM_NAMES !== 'undefined' && TEAM_NAMES[code]) || code;
}

function renderHero(checkpoints) {
  const latest     = checkpoints[checkpoints.length - 1];
  const prePlayoff = checkpoints[0];

  // Current leader (highest current odds)
  const [leaderCode, leaderPct] = Object.entries(latest.odds)
    .sort((a, b) => b[1] - a[1])[0];

  // Biggest gainer among alive teams (vs pre-playoff)
  const [gainerCode, gainerDelta] = Object.entries(latest.odds)
    .filter(([, v]) => v > 0)
    .map(([t, v]) => [t, v - (prePlayoff.odds[t] || 0)])
    .sort((a, b) => b[1] - a[1])[0];

  // Eliminated count
  const eliminatedCount = Object.values(latest.odds).filter(v => v === 0).length;

  const leaderColor = teamColor(leaderCode);
  const gainerColor = '#22c55e';
  const elimColor   = '#f59e0b';

  document.getElementById('chase-hero').innerHTML = `
    <div class="chase-hero-card" style="--card-accent:${leaderColor}">
      <div class="chase-hero-label">Current Leader</div>
      <div class="chase-hero-value" style="color:${leaderColor}">${leaderCode}</div>
      <div class="chase-hero-sub">${teamName(leaderCode)} · <strong style="color:var(--text-primary)">${leaderPct.toFixed(1)}%</strong></div>
    </div>
    <div class="chase-hero-card" style="--card-accent:${gainerColor}">
      <div class="chase-hero-label">Biggest Gainer</div>
      <div class="chase-hero-value" style="color:${gainerColor}">${gainerCode}</div>
      <div class="chase-hero-sub">${teamName(gainerCode)} · <strong style="color:${gainerColor}">+${gainerDelta.toFixed(1)}pp</strong> since pre-playoff</div>
    </div>
    <div class="chase-hero-card" style="--card-accent:${elimColor}">
      <div class="chase-hero-label">Eliminated</div>
      <div class="chase-hero-value" style="color:${elimColor}">${eliminatedCount}</div>
      <div class="chase-hero-sub">teams at 0% title odds</div>
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', async () => {
  let dashboard;
  try {
    dashboard = await fetch(DASHBOARD_URL).then(r => r.json());
  } catch {
    document.getElementById('chase-hero').innerHTML =
      '<p style="color:var(--text-muted);padding:40px;text-align:center">Could not load data.</p>';
    return;
  }

  const checkpoints = dashboard.championship_odds_history || [];
  if (checkpoints.length === 0) {
    document.getElementById('chase-hero').innerHTML =
      '<p style="color:var(--text-muted);padding:40px;text-align:center">No championship odds data available.</p>';
    return;
  }

  renderHero(checkpoints);
  renderChart(checkpoints);
  renderTable(checkpoints);
});

function renderChart(checkpoints) {
  const labels  = checkpoints.map(c => c.label);
  const latest  = checkpoints[checkpoints.length - 1];

  const allTeams = Object.entries(latest.odds)
    .sort((a, b) => b[1] - a[1])
    .map(([code]) => code);

  const traces = allTeams.map(code => {
    const isEliminated = latest.odds[code] === 0;
    const color        = teamColor(code);
    const yValues      = checkpoints.map(c => c.odds[code] ?? 0);

    return {
      x: labels,
      y: yValues,
      name: teamName(code),
      type: 'scatter',
      mode: 'lines+markers',
      line:   { color, width: isEliminated ? 1.5 : 2.5, dash: isEliminated ? 'dash' : 'solid' },
      marker: { color, size: isEliminated ? 3 : 5 },
      opacity: isEliminated ? 0.4 : 1.0,
      hovertemplate: `<b>${teamName(code)}</b><br>%{y:.1f}%<extra></extra>`,
    };
  });

  const firstQF = checkpoints.find(c => c.label.startsWith('QF'));
  const qfLabel = firstQF ? firstQF.label : null;

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor:  'transparent',
    font:  { color: '#9ca3af', family: 'Inter, sans-serif', size: 11 },
    xaxis: {
      ticktext:   labels,
      tickvals:   labels,
      gridcolor:  '#2d2e3a',
      tickangle:  -40,
      automargin: true,
    },
    yaxis: {
      title:      { text: 'Title Probability (%)', font: { size: 11 } },
      gridcolor:  '#2d2e3a',
      ticksuffix: '%',
      rangemode:  'tozero',
      automargin: true,
    },
    legend: {
      bgcolor:     'rgba(26,27,35,0.85)',
      bordercolor: '#2d2e3a',
      borderwidth: 1,
      font:        { size: 11 },
    },
    margin: { t: 16, r: 16, b: 80, l: 60 },
    shapes: qfLabel ? [{
      type: 'line',
      xref: 'x', yref: 'paper',
      x0: qfLabel, x1: qfLabel,
      y0: 0, y1: 1,
      line: { color: '#f59e0b', width: 1.5, dash: 'dot' },
    }] : [],
    annotations: qfLabel ? [{
      xref: 'x', yref: 'paper',
      x: qfLabel, y: 0.98,
      text: 'Quarters begin',
      showarrow: false,
      font: { color: '#f59e0b', size: 10 },
      xanchor: 'left',
      yanchor: 'top',
    }] : [],
  };

  Plotly.newPlot('chase-chart', traces, layout, { displayModeBar: false, responsive: true });
}
