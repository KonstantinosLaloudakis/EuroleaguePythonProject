const VALID_SLOTS = ['qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'];

function getSlotId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

function teamName(code) {
  return (typeof TEAM_NAMES !== 'undefined' && TEAM_NAMES[code]) || code;
}
function logoUrl(code) { return `logos/${code}.png`; }

function renderError(root, msg) {
  root.innerHTML = `<div class="series-error"><h1>Series not found</h1><p>${msg}</p></div>`;
}

function renderIndex(root, series) {
  const items = VALID_SLOTS.map(id => {
    const s = series[id] || {};
    const teams = s.high_seed && s.low_seed
      ? `${s.high_seed.team} vs ${s.low_seed.team}`
      : 'TBD';
    return `<li><a href="series.html?id=${id}">${s.label || id} — ${teams}</a></li>`;
  }).join('');
  root.innerHTML = `<h1>All series</h1><ul class="series-index">${items}</ul>`;
}

async function main() {
  const root = document.getElementById('series-root');
  const slotId = getSlotId();

  let dashboard;
  try {
    const res = await fetch('data/current/dashboard.json');
    dashboard = await res.json();
  } catch (err) {
    renderError(root, 'Could not load dashboard data.');
    return;
  }

  const series = dashboard.series || {};
  if (!slotId) {
    renderIndex(root, series);
    return;
  }
  if (!VALID_SLOTS.includes(slotId)) {
    renderError(root, `Invalid series id: "${slotId}". Valid ids: ${VALID_SLOTS.join(', ')}.`);
    return;
  }

  const entry = series[slotId];
  if (!entry) {
    renderError(root, `No data available for "${slotId}".`);
    return;
  }

  renderSeries(root, entry, dashboard);
}

function renderSeries(root, entry, dashboard) {
  root.innerHTML = `
    <section id="series-hero" class="series-section"></section>
    <section id="series-timeline" class="series-section"></section>
    <section id="series-h2h" class="series-section"></section>
    <section id="series-recaps" class="series-section"></section>
  `;
  renderHero(document.getElementById('series-hero'), entry);
  renderTimeline(document.getElementById('series-timeline'), entry);
  renderH2H(document.getElementById('series-h2h'), entry);
  renderRecaps(document.getElementById('series-recaps'), entry, dashboard);
}

// ── Hero ────────────────────────────────────────────────────────────────

function renderHero(container, entry) {
  const { high_seed, low_seed, wins, status, winner, series_win_prob, label, format } = entry;

  const seedLabel = (s) => {
    if (!s) return '<span class="series-team-name">TBD</span>';
    const seedSuffix = s.seed != null ? ` (${s.seed})` : '';
    return `<img class="series-logo" src="${logoUrl(s.team)}" alt="${s.team}" onerror="this.style.display='none'"><span class="series-team-name">${teamName(s.team)}${seedSuffix}</span>`;
  };

  const scoreLine = () => {
    if (status === 'awaiting_teams') return 'Matchup pending — awaiting play-in / prior series';
    if (status === 'not_started') return 'Best-of-5 · Series not started';
    if (status === 'completed') return `Series complete · Winner: ${teamName(winner)}`;
    const leaderCode = wins.high > wins.low ? (high_seed && high_seed.team) : (low_seed && low_seed.team);
    return `Series: ${Math.max(wins.high, wins.low)}-${Math.min(wins.high, wins.low)} ${leaderCode || ''}`.trim();
  };

  const fmtLine = () => {
    if (format === 'best_of_5') return 'Best-of-5 · 2-2-1 home pattern';
    return format;
  };

  const probBar = () => {
    if (status === 'completed' || status === 'awaiting_teams') return '';
    const h = (series_win_prob && series_win_prob.high) || 0;
    const l = (series_win_prob && series_win_prob.low) || 0;
    const highTeam = high_seed ? high_seed.team : 'HIGH';
    const lowTeam = low_seed ? low_seed.team : 'LOW';
    return `
      <div class="series-prob-bar">
        <div class="series-prob-fill series-prob-high" style="width: ${h}%"></div>
        <div class="series-prob-fill series-prob-low" style="width: ${l}%"></div>
      </div>
      <div class="series-prob-labels">
        <span>${highTeam} ${h.toFixed(1)}%</span>
        <span>${lowTeam} ${l.toFixed(1)}%</span>
      </div>
    `;
  };

  container.innerHTML = `
    <div class="series-hero">
      <h1 class="series-title">${label}</h1>
      <div class="series-teams">
        <div class="series-team series-team-high">${seedLabel(high_seed)}</div>
        <div class="series-vs">vs</div>
        <div class="series-team series-team-low">${seedLabel(low_seed)}</div>
      </div>
      <div class="series-state">${scoreLine()}</div>
      <div class="series-format">${fmtLine()}</div>
      ${probBar()}
    </div>
  `;
}

// ── Timeline ────────────────────────────────────────────────────────────

function renderTimeline(container, entry) {
  const games = entry.games || [];
  const visible = games.filter(g => g.status !== 'unnecessary');
  if (visible.length === 0) {
    container.innerHTML = '';
    return;
  }
  const boxes = visible.map(g => renderGameBox(g)).join('');
  container.innerHTML = `
    <h2 class="series-section-title">Game-by-game</h2>
    <div class="series-timeline">${boxes}</div>
  `;
}

function renderGameBox(g) {
  const num = `G${g.game_num}`;
  if (g.status === 'completed') {
    const winnerCls = g.winner === g.home ? 'home-win' : 'away-win';
    const link = g.gamecode
      ? `replay.html?season=2025&gamecode=${g.gamecode}`
      : null;
    const inner = `
      <div class="series-game-num">${num}</div>
      <div class="series-game-score ${winnerCls}">
        <span class="${g.winner === g.home ? 'winner' : ''}">${g.home} ${g.home_score}</span>
        <span class="${g.winner === g.away ? 'winner' : ''}">${g.away} ${g.away_score}</span>
      </div>
      <div class="series-game-date">${formatDate(g.date)}</div>
      <div class="series-game-status">Final</div>
    `;
    return link
      ? `<a class="series-game-box completed" href="${link}">${inner}</a>`
      : `<div class="series-game-box completed">${inner}</div>`;
  }

  const homeWp = g.pregame_wp && g.pregame_wp.home;
  const awayWp = g.pregame_wp && g.pregame_wp.away;
  const venue = g.home ? `@ ${g.home}` : 'TBD';
  return `
    <div class="series-game-box upcoming">
      <div class="series-game-num">${num}</div>
      <div class="series-game-venue">${venue}</div>
      <div class="series-game-date">${formatDate(g.date) || 'TBD'}</div>
      ${homeWp != null ? `<div class="series-game-wp">${g.home} ${homeWp.toFixed(0)}% / ${g.away} ${awayWp.toFixed(0)}%</div>` : ''}
    </div>
  `;
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ── Regular-Season H2H ──────────────────────────────────────────────────

function renderH2H(container, entry) {
  const meetings = entry.rs_h2h || [];
  const highTeam = entry.high_seed && entry.high_seed.team;
  const lowTeam = entry.low_seed && entry.low_seed.team;

  if (!highTeam || !lowTeam) {
    container.innerHTML = `
      <h2 class="series-section-title">Regular-season H2H</h2>
      <p class="series-empty">Waiting for both teams to be determined.</p>
    `;
    return;
  }

  if (meetings.length === 0) {
    container.innerHTML = `
      <h2 class="series-section-title">Regular-season H2H</h2>
      <p class="series-empty">No regular-season meetings.</p>
    `;
    return;
  }

  const cards = meetings.map(m => {
    const hostedBy = `${m.home} home`;
    return `
      <div class="series-h2h-card">
        <div class="series-h2h-round">Round ${m.round} · ${hostedBy}</div>
        <div class="series-h2h-score">
          <span class="${m.winner === m.home ? 'winner' : ''}">${m.home} ${m.home_score}</span>
          <span> – </span>
          <span class="${m.winner === m.away ? 'winner' : ''}">${m.away} ${m.away_score}</span>
        </div>
      </div>
    `;
  }).join('');

  let highWins = 0, lowWins = 0, highPts = 0, lowPts = 0;
  meetings.forEach(m => {
    const highIsHome = m.home === highTeam;
    const hs = highIsHome ? m.home_score : m.away_score;
    const ls = highIsHome ? m.away_score : m.home_score;
    highPts += hs;
    lowPts += ls;
    if (m.winner === highTeam) highWins += 1;
    else lowWins += 1;
  });
  const margin = highPts - lowPts;
  const marginLeader = margin > 0 ? highTeam : (margin < 0 ? lowTeam : 'even');
  const marginStr = margin === 0 ? 'Combined margin: even' : `Combined margin: ${marginLeader} +${Math.abs(margin)}`;

  container.innerHTML = `
    <h2 class="series-section-title">Regular-season H2H</h2>
    <div class="series-h2h-cards">${cards}</div>
    <div class="series-h2h-summary">Season split: ${highTeam} ${highWins}-${lowWins} ${lowTeam} · ${marginStr}</div>
  `;
}

// ── Recaps ──────────────────────────────────────────────────────────────

function renderRecaps(container, entry, dashboard) {
  const highTeam = entry.high_seed && entry.high_seed.team;
  const lowTeam = entry.low_seed && entry.low_seed.team;
  if (!highTeam || !lowTeam) {
    container.innerHTML = '';
    return;
  }

  const allRecaps = (dashboard && dashboard.playoff_recaps) || [];
  const pair = new Set([highTeam, lowTeam]);
  const matching = allRecaps.filter(r =>
    pair.has(r.home) && pair.has(r.away)
  );

  if (matching.length === 0) {
    container.innerHTML = '';
    return;
  }

  const cards = matching.map(r => renderRecapCard(r)).join('');
  container.innerHTML = `
    <h2 class="series-section-title">Game recaps</h2>
    <div class="series-recaps">${cards}</div>
  `;
}

function renderRecapCard(r) {
  const score = `${r.home} ${r.home_score} – ${r.away} ${r.away_score}`;
  const pre = r.pre_game_win_prob != null ? `Pre-game ${r.winner} win prob: ${r.pre_game_win_prob}%` : '';
  const upset = r.is_upset ? '<span class="recap-upset">Upset</span>' : '';
  const title = r.series_label || r.round || '';
  return `
    <div class="series-recap-card">
      <div class="recap-title">${title} ${upset}</div>
      <div class="recap-score ${r.winner === r.home ? 'home-win' : 'away-win'}">${score}</div>
      <div class="recap-pre">${pre}</div>
    </div>
  `;
}

main();
