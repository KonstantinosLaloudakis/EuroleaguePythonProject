const VALID_SLOTS = ['qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final'];

function getSlotId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

function teamName(code) {
  return (typeof TEAM_NAMES !== 'undefined' && TEAM_NAMES[code]) || code;
}

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
    <section id="series-tale" class="series-section"></section>
    <section id="series-momentum" class="series-section"></section>
    <section id="series-timeline" class="series-section"></section>
    <section id="series-h2h" class="series-section"></section>
    <section id="series-recaps" class="series-section"></section>
  `;
  renderHero(document.getElementById('series-hero'), entry);
  renderTaleOfTheTape(document.getElementById('series-tale'), entry);
  renderMomentum(document.getElementById('series-momentum'), entry);
  renderTimeline(document.getElementById('series-timeline'), entry);
  renderH2H(document.getElementById('series-h2h'), entry);
  renderRecaps(document.getElementById('series-recaps'), entry, dashboard);
}

// ── Hero ────────────────────────────────────────────────────────────────

function teamColor(code) {
  return (typeof TEAM_COLORS !== 'undefined' && TEAM_COLORS[code]) || '#6b7280';
}

function renderHero(container, entry) {
  const { high_seed, low_seed, wins, status, winner, series_win_prob, label, format } = entry;
  const isAwaiting = status === 'awaiting_teams';
  const isCompleted = status === 'completed';
  const isNotStarted = status === 'not_started';

  const teamPanel = (s, side) => {
    if (!s) {
      return `<div class="series-team-panel series-team-pending">
        <div class="series-team-logo-wrap"><div class="series-team-logo-placeholder">?</div></div>
        <div class="series-team-info">
          <div class="series-team-seed">TBD</div>
          <div class="series-team-name">Awaiting opponent</div>
        </div>
      </div>`;
    }
    const color = teamColor(s.team);
    const seed = s.seed != null ? `Seed #${s.seed}` : '';
    const prob = series_win_prob && series_win_prob[side] != null ? series_win_prob[side] : null;
    const showProb = !isAwaiting && !isCompleted && prob != null;
    const isWinner = isCompleted && winner === s.team;
    return `<div class="series-team-panel${isWinner ? ' series-team-panel-winner' : ''}" style="--team-color:${color}">
      <div class="series-team-logo-wrap">
        <img class="series-team-logo" src="logos/${s.team}.png" alt="${s.team}" onerror="this.style.display='none'">
      </div>
      <div class="series-team-info">
        <div class="series-team-seed">${seed}</div>
        <div class="series-team-name">${teamName(s.team)}</div>
        ${showProb ? `<div class="series-team-prob">${prob.toFixed(1)}%</div>` : ''}
        ${isWinner ? '<div class="series-team-winner-tag">🏆 Winner</div>' : ''}
      </div>
    </div>`;
  };

  const statusChip = () => {
    if (isAwaiting) return '<span class="series-status-chip awaiting">Matchup pending</span>';
    if (isNotStarted) return '<span class="series-status-chip not-started">Series not started</span>';
    if (isCompleted) return `<span class="series-status-chip completed">Final · ${teamName(winner)}</span>`;
    const leaderCode = wins.high > wins.low ? (high_seed && high_seed.team) : (low_seed && low_seed.team);
    return `<span class="series-status-chip live">Live · ${Math.max(wins.high, wins.low)}-${Math.min(wins.high, wins.low)} ${leaderCode || ''}</span>`;
  };

  const fmtLine = () => {
    if (format === 'best_of_5') return 'Best-of-5 · 2-2-1 home pattern';
    if (format === 'single_game') return 'Final Four · Single game, neutral venue';
    return format;
  };

  const probBar = () => {
    if (isCompleted || isAwaiting) return '';
    const h = (series_win_prob && series_win_prob.high) || 0;
    const l = (series_win_prob && series_win_prob.low) || 0;
    const hColor = teamColor(high_seed && high_seed.team);
    const lColor = teamColor(low_seed && low_seed.team);
    return `
      <div class="series-prob-bar">
        <div class="series-prob-fill" style="width:${h}%;background:${hColor}"></div>
        <div class="series-prob-fill" style="width:${l}%;background:${lColor}"></div>
      </div>
    `;
  };

  container.innerHTML = `
    <div class="series-hero">
      <div class="series-hero-top">
        <h1 class="series-title">${label}</h1>
        <div class="series-hero-meta">
          ${statusChip()}
          <span class="series-format-chip">${fmtLine()}</span>
        </div>
      </div>
      <div class="series-teams">
        ${teamPanel(high_seed, 'high')}
        <div class="series-vs">VS</div>
        ${teamPanel(low_seed, 'low')}
      </div>
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
  const title = entry.format === 'single_game' ? 'Game' : 'Game-by-game';
  const boxes = visible.map(g => renderGameBox(g, entry)).join('');
  container.innerHTML = `
    <h2 class="series-section-title">${title}</h2>
    <div class="series-timeline">${boxes}</div>
  `;
}

function renderGameBox(g, entry) {
  const isSingle = entry && entry.format === 'single_game';
  const num = isSingle ? 'Final Four' : `G${g.game_num}`;
  const homeColor = g.home ? teamColor(g.home) : '#6b7280';
  const neutralStyle = 'style="--home-color:#9fb7d9"';
  const homeStyle = `style="--home-color:${homeColor}"`;

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
      ? `<a class="series-game-box completed" ${homeStyle} href="${link}">${inner}</a>`
      : `<div class="series-game-box completed" ${homeStyle}>${inner}</div>`;
  }

  if (g.neutral || isSingle) {
    const highTeam = entry && entry.high_seed && entry.high_seed.team;
    const lowTeam = entry && entry.low_seed && entry.low_seed.team;
    const highWp = g.pregame_wp && g.pregame_wp.high;
    const lowWp = g.pregame_wp && g.pregame_wp.low;
    const wpLine = (highTeam && lowTeam && highWp != null)
      ? `<div class="series-game-wp">${highTeam} ${highWp.toFixed(0)}% / ${lowTeam} ${lowWp.toFixed(0)}%</div>`
      : '';
    return `
      <div class="series-game-box upcoming" ${neutralStyle}>
        <div class="series-game-num">${num}</div>
        <div class="series-game-venue">Neutral venue</div>
        <div class="series-game-date">${formatDate(g.date) || 'TBD'}</div>
        ${wpLine}
      </div>
    `;
  }

  const homeWp = g.pregame_wp && g.pregame_wp.home;
  const awayWp = g.pregame_wp && g.pregame_wp.away;
  const venue = g.home ? `@ ${g.home}` : 'TBD';
  return `
    <div class="series-game-box upcoming" ${homeStyle}>
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
    const winnerColor = teamColor(m.winner);
    const homeIsWinner = m.winner === m.home;
    const awayIsWinner = m.winner === m.away;
    return `
      <div class="series-h2h-card" style="--winner-color:${winnerColor}">
        <div class="series-h2h-round">Round ${m.round} · ${m.home} home</div>
        <div class="series-h2h-teams">
          <div class="series-h2h-side${homeIsWinner ? ' winner' : ''}">
            <img class="series-h2h-logo" src="logos/${m.home}.png" alt="${m.home}" onerror="this.style.display='none'">
            <span class="series-h2h-team">${m.home}</span>
            <span class="series-h2h-score-val">${m.home_score}</span>
          </div>
          <div class="series-h2h-dash">–</div>
          <div class="series-h2h-side${awayIsWinner ? ' winner' : ''}">
            <span class="series-h2h-score-val">${m.away_score}</span>
            <span class="series-h2h-team">${m.away}</span>
            <img class="series-h2h-logo" src="logos/${m.away}.png" alt="${m.away}" onerror="this.style.display='none'">
          </div>
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

// ── Tale of the Tape ────────────────────────────────────────────────────

function _formatTotValue(metric, value) {
  if (value == null || isNaN(value)) return '—';
  if (metric === 'ft_rate') return Number(value).toFixed(2);
  if (metric === 'pace') return Number(value).toFixed(1);
  return Number(value).toFixed(1);
}

function _suffixForMetric(metric) {
  if (metric === 'pace') return '';
  if (metric === 'ft_rate') return '';
  if (['three_pct', 'paint_pct', 'bench_share'].includes(metric)) return '%';
  return '';
}

function renderTaleOfTheTape(container, entry) {
  if (!container) return;
  const tot = entry && entry.tale_of_the_tape;
  if (!tot || !Array.isArray(tot.rows) || tot.rows.length === 0) {
    container.innerHTML = '';
    return;
  }

  const high = entry.high_seed && entry.high_seed.team;
  const low = entry.low_seed && entry.low_seed.team;
  const colorH = teamColor(high);
  const colorL = teamColor(low);

  const rowsHtml = tot.rows.map(r => {
    const lowerBetter = !!r.lower_is_better;
    // "Winner" (visually emphasized) is the side with the better stat.
    const hWins = lowerBetter ? r.high <= r.low : r.high >= r.low;
    const lWins = !hWins;

    // Bar widths: proportional split, floor at 15% so the loser is still visible.
    const total = (Number(r.high) || 0) + (Number(r.low) || 0);
    let hPct = 50, lPct = 50;
    if (total > 0) {
      hPct = Math.max(15, Math.min(85, Math.round((r.high / total) * 100)));
      lPct = 100 - hPct;
    }

    return `
      <div class="tot-row-block">
        <div class="tot-row-label">${r.label}</div>
        <div class="tot-row">
          <div class="tot-value high ${lWins ? 'dim' : ''}">${_formatTotValue(r.metric, r.high)}${_suffixForMetric(r.metric)}</div>
          <div class="tot-bar-wrap">
            <div class="tot-bar-half high ${lWins ? 'dim' : ''}"
                 style="width:${hPct}%; background:${colorH || 'var(--accent-blue)'}"></div>
            <div class="tot-bar-half low ${hWins ? 'dim' : ''}"
                 style="width:${lPct}%; background:${colorL || 'var(--accent-red)'}"></div>
          </div>
          <div class="tot-value low ${hWins ? 'dim' : ''}">${_formatTotValue(r.metric, r.low)}${_suffixForMetric(r.metric)}</div>
        </div>
      </div>
    `;
  }).join('');

  const edgesHtml = (tot.edges || []).map(e => {
    let dotColor = 'var(--text-muted)';
    if (e.favor === 'high') dotColor = colorH || 'var(--accent-blue)';
    if (e.favor === 'low') dotColor = colorL || 'var(--accent-red)';
    return `
      <div class="tot-edge">
        <span class="tot-edge-dot" style="background:${dotColor}"></span>
        <span>${e.text}</span>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="stat-card">
      <h3>Tale of the Tape</h3>
      <div class="tot-rows">${rowsHtml}</div>
      ${edgesHtml ? `
        <div class="tot-edges">
          <div class="tot-edges-title">Edges</div>
          ${edgesHtml}
        </div>` : ''}
    </div>
  `;
}

// ── Momentum ─────────────────────────────────────────────────────────────

function renderMomentum(container, entry) {
  if (!container) return;
  const m = entry && entry.momentum;
  if (!m || !Array.isArray(m.checkpoints) || m.checkpoints.length < 2) {
    container.innerHTML = '';
    return;
  }
  if (typeof Plotly === 'undefined') {
    container.innerHTML = '<div class="stat-card"><h3>Series Momentum</h3><p>Plotly failed to load.</p></div>';
    return;
  }

  const high = entry.high_seed && entry.high_seed.team;
  const low = entry.low_seed && entry.low_seed.team;
  const colorH = teamColor(high) || '#60a5fa';
  const colorL = teamColor(low) || '#f87171';

  container.innerHTML = `
    <div class="stat-card">
      <h3>Series Momentum</h3>
      <div id="momentum-chart" style="width:100%;height:280px"></div>
      ${_renderMomentumCallout(m.biggest_swing)}
    </div>
  `;

  const labels = m.checkpoints.map(c => c.label);
  const highVals = m.checkpoints.map(c => c.high_wp);
  const lowVals = m.checkpoints.map(c => c.low_wp);

  const traces = [
    {
      x: labels, y: highVals, mode: 'lines+markers',
      name: high || 'Higher seed',
      line: { color: colorH, width: 3 },
      marker: { size: 8, color: colorH },
    },
    {
      x: labels, y: lowVals, mode: 'lines+markers',
      name: low || 'Lower seed',
      line: { color: colorL, width: 3 },
      marker: { size: 8, color: colorL },
    },
  ];

  const layout = {
    margin: { l: 40, r: 16, t: 8, b: 36 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: {
      family: 'Inter, sans-serif',
      color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary') || '#cbd5e1',
      size: 12,
    },
    xaxis: { gridcolor: 'rgba(255,255,255,0.06)', tickfont: { size: 11 } },
    yaxis: {
      title: { text: 'Series WP %', font: { size: 11 } },
      range: [0, 100], gridcolor: 'rgba(255,255,255,0.06)',
      ticksuffix: '%',
    },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' },
    hovermode: 'x unified',
  };

  Plotly.newPlot('momentum-chart', traces, layout, {
    displayModeBar: false, responsive: true,
  });
}

function _renderMomentumCallout(swing) {
  if (!swing) return '';
  const winner = swing.winner_team || (swing.shifted_to === 'high' ? 'higher seed' : 'lower seed');
  return `
    <div class="momentum-callout">
      <strong>Biggest swing:</strong>
      G${swing.game_num} — ${winner} win shifted series WP +${swing.delta_pct}%
    </div>
  `;
}

main();
