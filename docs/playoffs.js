/**
 * playoffs.js — Interactive Euroleague Playoff Bracket Simulator
 *
 * Format:
 *   Play-In:      7v10, 8v9 (single game)
 *   Quarterfinals: 1v(PI-B), 2v(PI-A), 3v6, 4v5 (best-of-5)
 *   Final Four:    SF1 vs SF2, then Final (single game, neutral venue)
 *   Champion
 */

'use strict';

const TEAM_COLORS = {
    BER:'#005CA9', IST:'#E30613', MCO:'#D4AF37', BAS:'#B50031',
    RED:'#CC0000', MIL:'#C8102E', BAR:'#004D98', MUN:'#0066B2',
    ULK:'#003366', ASV:'#222222', TEL:'#F6C300', OLY:'#E2001A',
    PAN:'#007F3D', PAR:'#333333', PRS:'#1a1a2e', MAD:'#6d4c94',
    PAM:'#EB7622', VIR:'#1a1a1a', ZAL:'#006233', DUB:'#555555',
    HTA:'#cc0000',
};

const ELO_HCA = 50;

// State
let _teams = [];
let _seeded = [];    // top 10 teams by seed
let _bracket = {};   // round → matchup index → { a, b, winner }
let _champion = null;

// ── Elo win probability ──────────────────────────────────────────────────
function eloWinProb(eloA, eloB, neutral = false) {
    const hca = neutral ? 0 : ELO_HCA;
    return 1 / (1 + Math.pow(10, (eloB - eloA - hca) / 400));
}

// Best-of-N series probability (team A wins >=ceil(n/2) games)
function seriesProb(pGame, n) {
    const need = Math.ceil(n / 2);
    let prob = 0;
    for (let wins = need; wins <= n; wins++) {
        // P(exactly `wins` wins in `wins + (need-1)` games, last game is a win)
        const games = wins + need - 1;
        // but we need at most n games, and team wins the last game
        // Use: P(win series) = sum over k=need..n of C(k-1, need-1) * p^need * (1-p)^(k-need)
        const losses = wins - need;
        const totalGames = wins + losses; // = need + losses, but wins is the loop var... let me redo
        // Actually: team needs `need` wins. Series ends when one team hits `need`.
        // P = sum_{losses=0}^{need-1} C(need-1+losses, losses) * p^need * (1-p)^losses
        // Let me recalculate properly
    }
    // Correct formula: P(A wins best-of-n) = sum_{l=0}^{need-1} C(need-1+l, l) * p^need * q^l
    const q = 1 - pGame;
    prob = 0;
    for (let l = 0; l < need; l++) {
        prob += comb(need - 1 + l, l) * Math.pow(pGame, need) * Math.pow(q, l);
    }
    return prob;
}

function comb(n, k) {
    if (k > n) return 0;
    if (k === 0 || k === n) return 1;
    let r = 1;
    for (let i = 0; i < k; i++) r = r * (n - i) / (i + 1);
    return r;
}

// ── Initialize ───────────────────────────────────────────────────────────
async function init() {
    try {
        const resp = await fetch('data/current/dashboard.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        _teams = (data.teams || []).sort((a, b) =>
            b.wins - a.wins || a.losses - b.losses || b.elo - a.elo
        );

        if (data.updated) {
            const el = document.getElementById('last-updated');
            if (el) {
                const d = new Date(data.updated);
                el.textContent = `Data as of Round ${data.round || ''} · Updated ${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`;
                el.style.display = '';
            }
        }

        // Top 10 teams seeded 1-10
        _seeded = _teams.slice(0, 10).map((t, i) => ({
            ...t,
            seed: i + 1,
        }));

        resetBracket();
    } catch (err) {
        document.getElementById('bracket').innerHTML =
            `<p style="color:var(--accent-red);padding:1rem">Failed to load data: ${err}</p>`;
    }
}

function resetBracket() {
    _bracket = {
        playin: [
            { a: null, b: null, winner: null },  // 7 vs 10
            { a: null, b: null, winner: null },   // 8 vs 9
        ],
        quarters: [
            { a: null, b: null, winner: null },   // 1 vs PI-B winner
            { a: null, b: null, winner: null },   // 2 vs PI-A winner
            { a: null, b: null, winner: null },   // 3 vs 6
            { a: null, b: null, winner: null },   // 4 vs 5
        ],
        semis: [
            { a: null, b: null, winner: null },   // QF1 winner vs QF4 winner
            { a: null, b: null, winner: null },   // QF2 winner vs QF3 winner
        ],
        final: [
            { a: null, b: null, winner: null },
        ],
    };
    _champion = null;

    // Seed play-in
    _bracket.playin[0].a = _seeded[6];  // 7
    _bracket.playin[0].b = _seeded[9];  // 10
    _bracket.playin[1].a = _seeded[7];  // 8
    _bracket.playin[1].b = _seeded[8];  // 9

    // Seed QF with known teams (1-6 go directly)
    _bracket.quarters[0].a = _seeded[0]; // 1
    _bracket.quarters[1].a = _seeded[1]; // 2
    _bracket.quarters[2].a = _seeded[2]; // 3
    _bracket.quarters[2].b = _seeded[5]; // 6
    _bracket.quarters[3].a = _seeded[3]; // 4
    _bracket.quarters[3].b = _seeded[4]; // 5

    renderBracket();
}

// ── Render ────────────────────────────────────────────────────────────────
function renderBracket() {
    const container = document.getElementById('bracket');

    container.innerHTML = `
        <div class="bracket-round">
            <div class="bracket-round-title">Play-In</div>
            ${renderMatchup('playin', 0, 1, false)}
            ${renderMatchup('playin', 1, 1, false)}
        </div>
        <div class="bracket-round">
            <div class="bracket-round-title">Quarterfinals</div>
            ${renderMatchup('quarters', 0, 5, true)}
            ${renderMatchup('quarters', 1, 5, true)}
            ${renderMatchup('quarters', 2, 5, false)}
            ${renderMatchup('quarters', 3, 5, false)}
        </div>
        <div class="bracket-round">
            <div class="bracket-round-title">Final Four — Semis</div>
            ${renderMatchup('semis', 0, 1, true)}
            ${renderMatchup('semis', 1, 1, true)}
        </div>
        <div class="bracket-round">
            <div class="bracket-round-title">Final</div>
            ${renderMatchup('final', 0, 1, true)}
        </div>
        <div>
            ${renderChampion()}
        </div>
    `;

    renderPathSummary();
}

function renderMatchup(round, idx, seriesLen, neutral) {
    const m = _bracket[round][idx];
    const teamA = m.a;
    const teamB = m.b;

    let probA = null, probB = null;
    if (teamA && teamB) {
        const pGame = eloWinProb(teamA.elo, teamB.elo, neutral);
        if (seriesLen > 1) {
            probA = seriesProb(pGame, seriesLen);
        } else {
            probA = pGame;
        }
        probB = 1 - probA;
    }

    const sideA = renderSide(teamA, probA, m.winner, round, idx, 'a');
    const sideB = renderSide(teamB, probB, m.winner, round, idx, 'b');
    const badge = seriesLen > 1 ? `<div class="series-badge">Best of ${seriesLen}</div>` : `<div class="series-badge">Single game</div>`;

    return `<div class="matchup">${sideA}${sideB}${badge}</div>`;
}

function renderSide(team, prob, winner, round, idx, side) {
    if (!team) {
        return `<div class="matchup-seed waiting locked">
            <div class="seed-num">?</div>
            <div class="seed-color" style="background:var(--border)"></div>
            <div class="seed-info"><div class="seed-name">Waiting...</div></div>
        </div>`;
    }

    const color = TEAM_COLORS[team.team] || '#555';
    const isWinner = winner && winner.team === team.team;
    const isLoser = winner && winner.team !== team.team;
    const cls = isWinner ? ' winner' : isLoser ? ' loser' : '';
    const locked = winner ? ' locked' : '';
    const check = isWinner ? '<div class="seed-check">✓</div>' : '<div class="seed-check"></div>';

    const probText = prob !== null
        ? `<div class="seed-prob" style="color:${probColor(prob)}">${(prob * 100).toFixed(0)}%</div>`
        : '';

    const onclick = winner ? '' : `onclick="pickWinner('${round}',${idx},'${side}')"`;

    return `<div class="matchup-seed${cls}${locked}" ${onclick}>
        <div class="seed-num">#${team.seed}</div>
        <div class="seed-color" style="background:${color}"></div>
        <div class="seed-info">
            <div class="seed-name">${team.name}</div>
            <div class="seed-record">${team.wins}-${team.losses} · Elo ${team.elo.toFixed(0)}</div>
        </div>
        ${probText}
        ${check}
    </div>`;
}

function probColor(p) {
    if (p >= 0.65) return '#22c55e';
    if (p >= 0.50) return '#a3e635';
    if (p >= 0.35) return '#fbbf24';
    return '#f87171';
}

function renderChampion() {
    if (!_champion) {
        return `<div class="champion-card empty">
            <div class="champion-trophy">🏆</div>
            <div class="champion-label">Champion</div>
            <div class="champion-name" style="color:var(--text-muted)">TBD</div>
        </div>`;
    }
    const color = TEAM_COLORS[_champion.team] || '#555';
    const path = computeChampionPath();
    return `<div class="champion-card">
        <div class="champion-trophy">🏆</div>
        <div class="champion-label">Champion</div>
        <div class="champion-name" style="color:${color}">${_champion.name}</div>
        <div class="champion-prob">Path probability: ${(path * 100).toFixed(1)}%</div>
    </div>`;
}

// ── Pick winner ──────────────────────────────────────────────────────────
function pickWinner(round, idx, side) {
    const m = _bracket[round][idx];
    if (!m.a || !m.b || m.winner) return;

    const winner = side === 'a' ? m.a : m.b;
    m.winner = winner;

    // Cascade: feed winner into next round
    if (round === 'playin') {
        // Play-in 0 (7v10) winner → QF slot 1 (as opponent of seed 2)
        // Play-in 1 (8v9) winner → QF slot 0 (as opponent of seed 1)
        if (idx === 0) _bracket.quarters[1].b = winner;
        if (idx === 1) _bracket.quarters[0].b = winner;
    } else if (round === 'quarters') {
        // QF0 & QF3 winners → SF0, QF1 & QF2 winners → SF1
        if (idx === 0) _bracket.semis[0].a = winner;
        if (idx === 3) _bracket.semis[0].b = winner;
        if (idx === 1) _bracket.semis[1].a = winner;
        if (idx === 2) _bracket.semis[1].b = winner;
    } else if (round === 'semis') {
        if (idx === 0) _bracket.final[0].a = winner;
        if (idx === 1) _bracket.final[0].b = winner;
    } else if (round === 'final') {
        _champion = winner;
    }

    renderBracket();
}

// ── Path probability ─────────────────────────────────────────────────────
function computeChampionPath() {
    if (!_champion) return 0;
    let prob = 1;

    // Walk backwards through the bracket to find all matchups the champion won
    const rounds = ['playin', 'quarters', 'semis', 'final'];
    const seriesLens = { playin: 1, quarters: 5, semis: 1, final: 1 };
    const neutrals = { playin: false, quarters: true, semis: true, final: true };

    for (const round of rounds) {
        for (const m of _bracket[round]) {
            if (m.winner && m.winner.team === _champion.team && m.a && m.b) {
                const pGame = eloWinProb(m.a.elo, m.b.elo, neutrals[round]);
                const len = seriesLens[round];
                const pA = len > 1 ? seriesProb(pGame, len) : pGame;
                const side = m.winner.team === m.a.team ? pA : 1 - pA;
                prob *= side;
            }
        }
    }
    return prob;
}

function renderPathSummary() {
    const container = document.getElementById('path-summary');
    if (!_seeded.length) { container.innerHTML = ''; return; }

    // Show championship probability for all top seeds based on Elo
    // Simple: for each top-6 team, compute naive path probability assuming they face expected opponents
    const chips = _seeded.slice(0, 6).map(t => {
        const color = TEAM_COLORS[t.team] || '#555';
        const pct = t.top4_pct != null ? t.top4_pct : '—';
        return `<div class="path-chip">
            <div class="path-chip-color" style="background:${color}"></div>
            <span>${t.name}</span>
            <span class="path-chip-pct">${typeof pct === 'number' ? pct.toFixed(0) + '%' : pct}</span>
            <span style="font-size:0.68rem;color:var(--text-muted)">Top 4</span>
        </div>`;
    });

    container.innerHTML = chips.join('');
}

// ── Boot ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
