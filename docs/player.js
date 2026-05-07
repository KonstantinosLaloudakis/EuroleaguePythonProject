// player.js
const DATA_URL = 'data/current/player_career_stats.json';
const CURRENT_SEASON_CODE = 'E2025';

let careerData = null;

document.addEventListener('DOMContentLoaded', async () => {
    const code = new URLSearchParams(window.location.search).get('code');
    if (!code) { showError('No player code in URL. Try player.html?code=P123456'); return; }

    try {
        careerData = await fetch(DATA_URL).then(r => r.json());
    } catch (e) {
        showError('Could not load player data. Run the data pipeline first.'); return;
    }

    const player = careerData.players[code];
    if (!player) { showError(`Player not found: ${code}`); return; }

    document.title = `${player.name} — EL Analytics`;
    document.getElementById('bc-name').textContent = player.name;

    const el = document.getElementById('player-content');
    el.innerHTML = renderHero(player) + renderChart(player.seasons) + renderTableSection(player);
    setupTabs(player);
    setupSort(player);
    setupSearch(careerData.index);
});

// ── Hero card ──────────────────────────────────────────────────────────────────
function renderHero(player) {
    const initials = player.name.split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join('');
    const current  = player.seasons[0];
    const first    = player.seasons[player.seasons.length - 1];
    const span     = (first && current && first !== current)
        ? `${first.season.slice(0, 4)}–${current.season.slice(5)}`
        : (current ? current.season : '');
    const seasonLbl = current ? current.season : '—';
    const fmt = (v) => (v != null ? v.toFixed(1) : '—');

    return `
    <div class="hero-card">
      <div class="hero-avatar">${initials}</div>
      <div>
        <div class="hero-name">${player.name}</div>
        <div class="hero-meta">${[player.position, player.nationality].filter(Boolean).join(' · ')}</div>
        <div class="hero-tags">
          ${current ? `<span class="tag tag-team">${current.team_name || current.team_code}</span>` : ''}
          <span class="tag tag-span">${player.seasons.length} season${player.seasons.length !== 1 ? 's' : ''}${span ? ' · ' + span : ''}</span>
        </div>
      </div>
      <div>
        <div class="season-label">${seasonLbl}</div>
        <div class="hero-stats-grid">
          <div class="hero-stat"><div class="val gold">${fmt(current?.ppg)}</div><div class="lbl">PPG</div></div>
          <div class="hero-stat"><div class="val">${fmt(current?.rpg)}</div><div class="lbl">RPG</div></div>
          <div class="hero-stat"><div class="val">${fmt(current?.apg)}</div><div class="lbl">APG</div></div>
          <div class="hero-stat"><div class="val green">${fmt(current?.pir)}</div><div class="lbl">PIR</div></div>
        </div>
      </div>
    </div>`;
}

// ── PIR trend chart ────────────────────────────────────────────────────────────
function renderChart(seasons) {
    if (!seasons.length) return '';
    const pirs   = seasons.map(s => s.pir || 0);
    const maxPIR = Math.max(...pirs, 1);
    const peak   = Math.max(...pirs);
    const peakSzn = seasons.find(s => s.pir === peak);
    const H = 64, W_BAR = 18, GAP = 4;
    const totalW = seasons.length * (W_BAR + GAP);

    const bars = [...seasons].reverse().map((s, i) => {
        const h    = Math.max(2, Math.round((s.pir || 0) / maxPIR * H));
        const x    = i * (W_BAR + GAP);
        const y    = H - h;
        const isCurrent = s.season_code === CURRENT_SEASON_CODE;
        const isPeak    = s.pir === peak && peak > 0;
        const fill  = isCurrent ? '#38bdf8' : isPeak ? '#818cf8' : '#2563eb';
        const lbl   = s.season.slice(2, 4) + '-' + s.season.slice(7, 9);
        return `<rect x="${x}" y="${y}" width="${W_BAR}" height="${h}" fill="${fill}" rx="2"/>
                <text x="${x + W_BAR / 2}" y="${H + 14}" text-anchor="middle" fill="#475569" font-size="7">${lbl}</text>`;
    }).join('');

    return `
    <div class="card">
      <div class="chart-header">
        <div>
          <div class="card-title">Career PIR Trend</div>
          <div class="card-sub">Performance Index Rating per game · all Euroleague seasons</div>
        </div>
        ${peakSzn ? `<div class="chart-peak">Peak: ${peak.toFixed(1)} (${peakSzn.season})</div>` : ''}
      </div>
      <div class="pir-chart">
        <svg viewBox="0 0 ${totalW} ${H + 20}" style="width:100%;min-width:${Math.min(totalW, 300)}px;height:90px">
          ${bars}
        </svg>
      </div>
      <div class="chart-legend">
        <div class="legend-item"><div class="legend-dot" style="background:#2563eb"></div>Past</div>
        <div class="legend-item"><div class="legend-dot" style="background:#818cf8"></div>Career peak</div>
        <div class="legend-item"><div class="legend-dot" style="background:#38bdf8"></div>Current season</div>
      </div>
    </div>`;
}

// ── Stat table ─────────────────────────────────────────────────────────────────
const TABS = {
    scoring:    { label: 'Scoring',    cols: ['ppg','rpg','apg','spg','bpg','tpg','pir'] },
    shooting:   { label: 'Shooting',   cols: ['ppg','fg2_pct','fg3_pct','ft_pct'] },
    rebounding: { label: 'Rebounding', cols: ['rpg','oreb','dreb','bpg'] },
    all:        { label: 'All Stats',  cols: ['ppg','rpg','oreb','dreb','apg','spg','bpg','tpg','fg2_pct','fg3_pct','ft_pct','pir'] },
};
const COL_LABELS = {
    ppg:'PPG', rpg:'RPG', oreb:'OREB', dreb:'DREB',
    apg:'APG', spg:'SPG', bpg:'BPG', tpg:'TPG',
    fg2_pct:'2P%', fg3_pct:'3P%', ft_pct:'FT%', pir:'PIR',
};

function renderTableSection(player) {
    const tabs = Object.entries(TABS).map(([k, t]) =>
        `<button class="tab-btn${k === 'scoring' ? ' active' : ''}" data-tab="${k}">${t.label}</button>`
    ).join('');
    return `
    <div class="card" style="padding:0;margin-bottom:0">
      <div class="tab-bar">${tabs}</div>
      <div id="table-wrap" style="overflow-x:auto;padding:12px 0 0">${buildTable(player, 'scoring')}</div>
    </div>`;
}

function buildTable(player, tabKey) {
    const cols = TABS[tabKey].cols;
    const fmt  = (v) => (v != null ? v.toFixed(1) : '<span style="color:var(--text-muted)">—</span>');
    const hl   = c => c === 'ppg' ? 'val-gold' : c === 'pir' ? 'val-green' : '';

    const head = `<tr><th>Season</th><th>Team</th><th style="text-align:right">GP</th>${
        cols.map(c => `<th data-col="${c}">${COL_LABELS[c]}</th>`).join('')}</tr>`;

    const rows = player.seasons.map(s => {
        const isCur = s.season_code === CURRENT_SEASON_CODE;
        const cells = cols.map(c => `<td class="${hl(c)}">${fmt(s[c])}</td>`).join('');
        return `<tr class="${isCur ? 'current-szn' : ''}">
          <td><span class="szn-link">${s.season}</span></td>
          <td>${s.team_code}</td>
          <td style="text-align:right">${s.gp ?? '—'}</td>${cells}</tr>`;
    }).join('');

    const car = player.career;
    const carCells = cols.map(c => `<td class="${hl(c)}">${fmt(car[c])}</td>`).join('');
    const carRow = `<tr class="career-row">
      <td>Career</td><td style="color:var(--text-muted)">—</td>
      <td style="text-align:right">${car.gp}</td>${carCells}</tr>`;

    return `<table class="stat-table"><thead>${head}</thead><tbody>${rows}${carRow}</tbody></table>`;
}

function setupTabs(player) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('table-wrap').innerHTML =
                '<div style="padding:0">' + buildTable(player, btn.dataset.tab) + '</div>';
            setupSort(player);
        });
    });
}

// ── Column sort ────────────────────────────────────────────────────────────────
let _sortCol = null, _sortAsc = false;

function setupSort(player) {
    document.querySelectorAll('.stat-table thead th[data-col]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.col;
            _sortAsc = _sortCol === col ? !_sortAsc : false;
            _sortCol = col;
            const sorted = [...player.seasons].sort((a, b) => {
                const va = a[col] ?? -Infinity, vb = b[col] ?? -Infinity;
                return _sortAsc ? va - vb : vb - va;
            });
            const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'scoring';
            document.getElementById('table-wrap').innerHTML =
                '<div style="padding:0">' + buildTable({...player, seasons: sorted}, activeTab) + '</div>';
            setupSort(player);
        });
    });
}

// ── Search bar ─────────────────────────────────────────────────────────────────
function setupSearch(index) {
    const input    = document.getElementById('player-search');
    const dropdown = document.getElementById('search-dropdown');
    if (!input || !dropdown) return;

    input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        dropdown.innerHTML = '';
        if (q.length < 2) { dropdown.classList.remove('open'); return; }

        const matches = index.filter(p => p.name.toLowerCase().includes(q)).slice(0, 10);
        if (!matches.length) { dropdown.classList.remove('open'); return; }

        matches.forEach(p => {
            const item = document.createElement('div');
            item.className = 'search-item';
            item.innerHTML = `<span>${p.name}</span><span class="si-team">${p.current_team || ''}</span>`;
            item.addEventListener('click', () => {
                window.location.href = `player.html?code=${encodeURIComponent(p.code)}`;
            });
            dropdown.appendChild(item);
        });
        dropdown.classList.add('open');
    });

    document.addEventListener('click', e => {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });

    input.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const first = dropdown.querySelector('.search-item');
        if (first) first.click();
    });
}

function showError(msg) {
    const el = document.getElementById('player-content');
    if (el) el.innerHTML = `<p class="error-msg">${msg}</p>`;
}
