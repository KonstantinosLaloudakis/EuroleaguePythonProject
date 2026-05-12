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
