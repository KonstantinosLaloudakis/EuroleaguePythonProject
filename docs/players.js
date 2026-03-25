/* ── players.js — Player Stats Hub ─────────────────────────────────────── */

const TEAM_NAMES = {
    BER:'ALBA Berlin', IST:'Anadolu Efes', MCO:'AS Monaco', BAS:'Baskonia',
    RED:'Crvena Zvezda', MIL:'EA7 Milan', BAR:'FC Barcelona', MUN:'Bayern Munich',
    ULK:'Fenerbahce', ASV:'ASVEL', TEL:'Maccabi Tel Aviv', OLY:'Olympiacos',
    PAN:'Panathinaikos', PAR:'Partizan', PRS:'Paris Basketball', MAD:'Real Madrid',
    PAM:'Valencia Basket', VIR:'Virtus Bologna', ZAL:'Zalgiris', DUB:'Dubai Basketball',
    HTA:'Hapoel Tel Aviv',
};

const TEAM_COLORS = {
    BER:'#005CA9', IST:'#E30613', MCO:'#E30613', BAS:'#006633',
    RED:'#CC0000', MIL:'#CC0000', BAR:'#A50044', MUN:'#DC052D',
    ULK:'#003DA5', ASV:'#FFD700', TEL:'#005BAA', OLY:'#CC0000',
    PAN:'#007A33', PAR:'#000000', PRS:'#001489', MAD:'#FEBE10',
    PAM:'#FF6B00', VIR:'#003DA5', ZAL:'#006600', DUB:'#00843D',
    HTA:'#CC0000',
};

// ── State ─────────────────────────────────────────────────────────────────
let _players = [];
let _mvpList  = [];
let _lbSort    = { key: 'avg_pir', dir: 'desc' };
let _posFilter = '';
let _lbShowAll = false;

// ── Tab switching ─────────────────────────────────────────────────────────
function switchTab(id) {
    document.querySelectorAll('[id^="tab-"]').forEach(el => el.style.display = 'none');
    document.getElementById(id).style.display = '';
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const idx = ['tab-leaderboards','tab-mvp'].indexOf(id);
    document.querySelectorAll('.tab-btn')[idx]?.classList.add('active');
    history.replaceState(null, '', '#' + id);
}

// ── Boot ──────────────────────────────────────────────────────────────────
fetch('data/current/dashboard.json')
    .then(r => r.json())
    .then(data => {
        _players = data.player_stats || [];
        _mvpList  = data.mvp || [];

        // Last-updated stamp
        if (data.updated) {
            const el = document.getElementById('last-updated');
            const d  = new Date(data.updated);
            el.textContent = `Updated ${d.toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'})} ${d.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})} UTC`;
            el.style.display = '';
        }

        // Populate team dropdown
        const teams = [...new Set(_players.map(p => p.team))].sort();
        const sel   = document.getElementById('lb-team');
        teams.forEach(t => {
            const o = document.createElement('option');
            o.value = t; o.textContent = t;
            sel.appendChild(o);
        });

        _renderLeaderboard();
        renderMvpRace(_mvpList, _players);

        // Restore tab from hash
        const hash = location.hash.replace('#','');
        if (hash && document.getElementById(hash)) switchTab(hash);
    })
    .catch(err => {
        document.getElementById('leaderboard-table').innerHTML =
            `<p style="color:var(--accent-red);padding:1rem">Failed to load data: ${err}</p>`;
    });

// ── Leaderboard ───────────────────────────────────────────────────────────
const LB_COLS = [
    { key: 'avg_pts',  label: 'PTS',  title: 'Points per game' },
    { key: 'avg_reb',  label: 'REB',  title: 'Rebounds per game' },
    { key: 'avg_ast',  label: 'AST',  title: 'Assists per game' },
    { key: 'avg_stl',  label: 'STL',  title: 'Steals per game' },
    { key: 'avg_blk',  label: 'BLK',  title: 'Blocks per game' },
    { key: 'avg_to',   label: 'TO',   title: 'Turnovers per game' },
    { key: 'avg_pir',  label: 'PIR',  title: 'Performance Index Rating per game' },
    { key: 'fg_pct',   label: 'FG%',  title: 'Field goal percentage' },
    { key: 'fg3_pct',  label: '3P%',  title: 'Three-point percentage' },
    { key: 'ft_pct',   label: 'FT%',  title: 'Free throw percentage' },
    { key: 'gp',       label: 'GP',   title: 'Games played' },
];

function _setPosFilter(btn, pos) {
    document.querySelectorAll('.pos-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _posFilter = pos;
    _lbShowAll = false;
    _renderLeaderboard();
}

function _renderLeaderboard() {
    const search  = (document.getElementById('lb-search')?.value || '').toLowerCase();
    const team    = document.getElementById('lb-team')?.value || '';
    const minGP   = parseInt(document.getElementById('lb-mingp')?.value || '5', 10);

    let rows = _players.filter(p =>
        p.gp >= minGP &&
        (!team || p.team === team) &&
        (!_posFilter || (p.position || '').startsWith(_posFilter)) &&
        (!search || p.name.toLowerCase().includes(search))
    );

    // Sort
    rows.sort((a, b) => {
        const av = a[_lbSort.key] ?? 0;
        const bv = b[_lbSort.key] ?? 0;
        return _lbSort.dir === 'desc' ? bv - av : av - bv;
    });

    const container = document.getElementById('leaderboard-table');
    if (!rows.length) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem">No players match your filters.</p>';
        return;
    }

    const headerCols = LB_COLS.map(c => {
        let cls = '';
        if (_lbSort.key === c.key) cls = _lbSort.dir === 'desc' ? 'lb-sort-desc' : 'lb-sort-asc';
        return `<th class="${cls}" title="${c.title}" onclick="_lbSetSort('${c.key}')">${c.label}</th>`;
    }).join('');

    const displayed = _lbShowAll ? rows : rows.slice(0, 30);
    const sortColIdx = LB_COLS.findIndex(c => c.key === _lbSort.key); // 0-based among stat cols

    const bodyRows = displayed.map((p, i) => {
        const color = TEAM_COLORS[p.team] || '#6b7280';
        const badge = `<span class="lb-team-badge" title="${TEAM_NAMES[p.team] || p.team}" style="color:${color};border-color:${color}30;background:${color}15">${p.team}</span>`;
        const statCells = LB_COLS.map((c, ci) => {
            const isActive = ci === sortColIdx;
            const style = isActive ? ' style="background:rgba(59,130,246,0.08);color:var(--text-primary);font-weight:600"' : '';
            let val = p[c.key];
            if (c.key === 'fg_pct' || c.key === 'fg3_pct' || c.key === 'ft_pct') val = val + '%';
            return `<td${style}>${val}</td>`;
        }).join('');
        return `<tr>
            <td class="lb-rank">${i + 1}</td>
            <td class="lb-player-cell">
                <span class="lb-player-name">${p.name}</span>
                <span class="lb-player-meta">${badge}${p.position || ''}</span>
            </td>
            ${statCells}
        </tr>`;
    }).join('');

    const showAllBtn = rows.length > 30
        ? `<button class="forecast-toggle-btn" onclick="_lbToggleShowAll()">${_lbShowAll ? 'Show Top 30' : `Show All ${rows.length}`}</button>`
        : '';

    container.innerHTML = `
        <div style="overflow-x:auto">
        <table class="leaderboard-tbl">
            <thead><tr>
                <th></th>
                <th style="text-align:left">Player</th>
                ${LB_COLS.map((c, ci) => {
                    const isActive = ci === sortColIdx;
                    let cls = '';
                    if (isActive) cls = _lbSort.dir === 'desc' ? 'lb-sort-desc' : 'lb-sort-asc';
                    const style = isActive ? 'background:rgba(59,130,246,0.12)' : '';
                    return `<th class="${cls}" title="${c.title}" style="${style}" onclick="_lbSetSort('${c.key}')">${c.label}</th>`;
                }).join('')}
            </tr></thead>
            <tbody>${bodyRows}</tbody>
        </table>
        </div>
        <div class="lb-footer" style="display:flex;justify-content:space-between;align-items:center">
            <span>${_lbShowAll ? displayed.length : Math.min(30, rows.length)} of ${rows.length} players · sorted by ${_lbSort.key.replace('avg_','').toUpperCase()} ${_lbSort.dir === 'desc' ? '↓' : '↑'}</span>
            ${showAllBtn}
        </div>`;
}

function _lbSetSort(key) {
    if (_lbSort.key === key) {
        _lbSort.dir = _lbSort.dir === 'desc' ? 'asc' : 'desc';
    } else {
        _lbSort.key = key;
        // Default: stats desc, TO asc
        _lbSort.dir = key === 'avg_to' ? 'asc' : 'desc';
    }
    _renderLeaderboard();
}

function _lbToggleShowAll() {
    _lbShowAll = !_lbShowAll;
    _renderLeaderboard();
}

// ── MVP Race ──────────────────────────────────────────────────────────────
function renderMvpRace(mvpList, playerStats) {
    // Enrich mvp entries with full stats from player_stats
    const statsLookup = {};
    playerStats.forEach(p => { statsLookup[p.name] = p; });

    const enriched = mvpList.map(m => ({
        ...m,
        ...(statsLookup[m.player] || {}),
    }));

    const maxScore = enriched[0]?.mvp_score || enriched[0]?.mvp_score || 100;

    // Podium (top 3)
    const medals = ['🥇','🥈','🥉'];
    const podiumHtml = enriched.slice(0, 3).map((m, i) => {
        const color   = TEAM_COLORS[m.team] || '#6b7280';
        const pct     = Math.round((m.mvp_score / maxScore) * 100);
        const avgPir  = m.avg_pir ?? m.avg_pir ?? '—';
        const avgPts  = m.avg_pts ?? '—';
        const avgAst  = m.avg_ast ?? '—';
        return `<div class="mvp-card rank-${i+1}">
            <div class="mvp-medal">${medals[i]}</div>
            <div class="mvp-card-name">${m.player}</div>
            <div class="mvp-card-team">
                <span class="lb-team-badge" title="${TEAM_NAMES[m.team] || m.team}" style="color:${color};border-color:${color}30;background:${color}15">${m.team}</span>
                ${m.gp} GP
            </div>
            <div class="mvp-score-bar-wrap"><div class="mvp-score-bar" style="width:${pct}%"></div></div>
            <div class="mvp-score-label">MVP Score: ${m.mvp_score}</div>
            <div class="mvp-card-stats">
                <div class="mvp-stat"><span class="mvp-stat-val">${avgPts}</span><span class="mvp-stat-lbl">PTS</span></div>
                <div class="mvp-stat"><span class="mvp-stat-val">${avgPir}</span><span class="mvp-stat-lbl">PIR</span></div>
                <div class="mvp-stat"><span class="mvp-stat-val">${avgAst}</span><span class="mvp-stat-lbl">AST</span></div>
                <div class="mvp-stat"><span class="mvp-stat-val">${(m.wpa||0).toFixed(0)}</span><span class="mvp-stat-lbl">WPA</span></div>
            </div>
        </div>`;
    }).join('');
    document.getElementById('mvp-podium').innerHTML = `<div class="mvp-podium">${podiumHtml}</div>`;

    // Full rankings table
    const tableRows = enriched.map((m, i) => {
        const color = TEAM_COLORS[m.team] || '#6b7280';
        const badge = `<span class="lb-team-badge" title="${TEAM_NAMES[m.team] || m.team}" style="color:${color};border-color:${color}30;background:${color}15">${m.team}</span>`;
        const avgPir  = m.avg_pir ?? '—';
        const avgPts  = m.avg_pts ?? '—';
        const consist = m.consistency ? (m.consistency * 100).toFixed(0) + '%' : '—';
        const clutch  = m.clutch_eff  ? m.clutch_eff.toFixed(2) : '—';
        return `<tr>
            <td style="color:var(--text-muted);font-weight:700">${i+1}</td>
            <td>
                <span style="font-weight:600;color:var(--text-primary)">${m.player}</span><br>
                <span style="font-size:0.75rem">${badge}${m.position || ''}</span>
            </td>
            <td><span class="mvp-score-pill">${m.mvp_score}</span></td>
            <td>${avgPir}</td>
            <td>${avgPts}</td>
            <td>${(m.wpa||0).toFixed(0)}</td>
            <td>${consist}</td>
            <td>${clutch}</td>
            <td style="color:var(--text-muted)">${m.gp}</td>
        </tr>`;
    }).join('');

    document.getElementById('mvp-race-table').innerHTML = `
        <div style="overflow-x:auto">
        <table class="mvp-race-tbl">
            <thead><tr>
                <th></th>
                <th>Player</th>
                <th title="Composite MVP Score">Score</th>
                <th title="Avg Performance Index Rating">PIR</th>
                <th title="Avg Points">PTS</th>
                <th title="Win Probability Added">WPA</th>
                <th title="Consistency (inverse CV)">Consist.</th>
                <th title="Clutch Efficiency (points-per-clutch-game × true shooting %)">Clutch</th>
                <th>GP</th>
            </tr></thead>
            <tbody>${tableRows}</tbody>
        </table>
        </div>`;
}
