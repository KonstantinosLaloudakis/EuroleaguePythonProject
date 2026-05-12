'use strict';

const COMPARE_DATA_URL = 'data/current/player_career_stats.json';

const TOT_STATS = [
  { key: 'ppg',     label: 'PPG',  pct: false },
  { key: 'rpg',     label: 'RPG',  pct: false },
  { key: 'apg',     label: 'APG',  pct: false },
  { key: 'spg',     label: 'SPG',  pct: false },
  { key: 'bpg',     label: 'BPG',  pct: false },
  { key: 'pir',     label: 'PIR',  pct: false },
  { key: 'fg2_pct', label: 'FG2%', pct: true  },
  { key: 'fg3_pct', label: '3P%',  pct: true  },
  { key: 'ft_pct',  label: 'FT%',  pct: true  },
];

const TABLE_COLS = [
  { key: 'ppg',     label: 'PPG',  dec: 1 },
  { key: 'rpg',     label: 'RPG',  dec: 1 },
  { key: 'apg',     label: 'APG',  dec: 1 },
  { key: 'spg',     label: 'SPG',  dec: 1 },
  { key: 'pir',     label: 'PIR',  dec: 1 },
  { key: 'fg2_pct', label: 'FG2%', dec: 1 },
  { key: 'fg3_pct', label: '3P%',  dec: 1 },
];

let _lookup = {};   // code → player object
let _index  = [];   // [{code, name, current_team, seasons}]
let _slotA  = null; // enriched player object (with _code) or null
let _slotB  = null; // enriched player object (with _code) or null

function buildLookup(data) {
  _index = data.index || [];
  _lookup = {};
  Object.entries(data.players || {}).forEach(([code, player]) => {
    _lookup[code] = player;
  });
}

function getParams() {
  const p = new URLSearchParams(window.location.search);
  return { a: p.get('a'), b: p.get('b') };
}

function updateURL() {
  const p = new URLSearchParams();
  if (_slotA) p.set('a', _slotA._code);
  if (_slotB) p.set('b', _slotB._code);
  const qs = p.toString();
  history.replaceState(null, '', qs ? `?${qs}` : window.location.pathname);
}

function lastTeamColor(player) {
  const code = player.seasons && player.seasons[0] && player.seasons[0].team_code;
  return (code && typeof TEAM_COLORS !== 'undefined' && TEAM_COLORS[code]) || '#1d4ed8';
}

function playerInitials(player) {
  return player.name.split(/[\s,]+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('');
}

function fmt(v, dec = 1) {
  return (v != null && !isNaN(v)) ? Number(v).toFixed(dec) : '—';
}

function syncInputs() {
  document.getElementById('input-a').value = _slotA ? _slotA.name : '';
  document.getElementById('input-b').value = _slotB ? _slotB.name : '';
}

function renderAll() {
  renderHeroCards();
  renderToT();
  renderSeasonTables();
}
