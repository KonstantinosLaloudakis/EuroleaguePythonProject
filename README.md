# 🏀 EuroleaguePythonProject

A comprehensive Euroleague basketball analytics suite built in Python. This project analyzes 19 seasons (2007–2025) of play-by-play and shot data to produce advanced metrics, custom visualizations, and data-driven narratives.

---

## 📊 Analytics Modules

### The Gravity Map (`the_gravity_map.py`)
Shot chart heatmaps using hexbin density plots on an accurate Euroleague half-court diagram.

- **Team Heatmaps** — Per-team shot distribution with FG%, shot count, and zone breakdown (Paint / Mid-Range / 3PT)
- **Head-to-Head Comparisons** — Side-by-side shot maps for any two teams
- **League-Wide Heatmap** — Aggregated shooting patterns across all teams
- **Multi-Season Support** — Dynamic team code resolution via `TEAM_NAME_OVERRIDES` for teams whose codes change across seasons (e.g. Panathinaikos: `PAN` / `PAM`)
- Uses `PowerNorm(gamma=0.5)` for high-contrast colormaps

**Output examples:** `gravity_map_OLY_2025.png`, `gravity_map_PAN_vs_OLY_2024.png`, `gravity_map_league_2025.png`

---

### The Lineup Analyzer (`the_lineup_analyzer.py`)
Advanced lineup analysis from play-by-play data with per-possession efficiency metrics.

- **Death Lineups (5-Man)** — Identifies the best and worst 5-player combinations by Net Rating (per 100 possessions)
- **Dynamic Duos (2-Man)** — Best two-player pairings by shared court time and impact
- **The Anchor (On/Off)** — Player impact measured by team performance with vs. without them on court
- **Configurable thresholds** — `MIN_MINUTES_5MAN`, `MIN_MINUTES_2MAN`, `MIN_MINUTES_ANCHOR`
- Scatter plots of Offensive vs Defensive Rating for each lineup type

**Output examples:** `death_lineups_2025.png`, `dynamic_duos_100_2025.png`, `the_anchor_2024.png`

---

### Streaks & Bursts (`streaks_and_bursts.py`)
Identifies explosive individual scoring performances.

- **The Heat Check** — Most consecutive points scored by a single player (team-relative streak). Tracks sequences where one player accounts for all of their team's scoring.
- **Quarter Master** — Most points scored in a single quarter by one player
- Configurable minimum thresholds (default: 8 points)
- Multi-season support with caching

**Output examples:** `microwave.png`, `zone_master.png`

---

### The Teeter-Totter (`teeter_totter.py`)
Game volatility analysis — finds the most dramatic, back-and-forth games.

- Tracks lead changes and tie events throughout each game
- Ranks games by volatility across all seasons
- Includes team name resolution and final scores

**Output:** `teeter_totter.png`, `teeter_totter.json`

---

### Comeback Kings (`comeback_kings.py`)
Identifies the largest comebacks in Euroleague history.

- Detects the maximum deficit overcome by the winning team in each game
- Tracks the exact moment of maximum deficit and the final margin
- Ranks all games by comeback size

**Output:** `comeback_kings.png`, `comeback_kings.json`

---

### The Silencer (`the_silencer.py`)
Finds players who silence the opposition with clutch performances when the game is on the line.

**Output:** `silencer.png`

---

### The Architect (`the_architect.py`)
Assist and playmaking analysis — identifies the most creative facilitators.

**Output:** `the_architect.png`, `the_architect.json`

---

### The Atlas (`the_atlas.py`)
Workload and usage analysis — which players carry the heaviest loads for their teams.

**Output:** `atlas.png`, `atlas.json`

---

### The Microwave (`the_microwave.py`)
Quick-scoring analysis — identifies players who heat up the fastest off the bench or in short bursts.

**Output:** `microwave.png`

---

### The Gauntlet (`the_gauntlet.py`)
Margin of Victory and Strength of Schedule visualization.
- **Season Stripes** — Detailed heatmap of every game result for every team
- **The Steamrollers** — Tracking dominant wins (15+ points)
- **The Grinders** — Identifying teams that play the most close games (≤ 5 points)
- **The Mountain** — Cumulative Point Differential over the season
- **The Fortress** — Home vs. Away Point Differential scatter plot

**Output:** 
- `the_gauntlet_{year}.png`
- `the_mountain_{year}.png`
- `the_fortress_{year}.png`

---

### The Zone Master (`the_zone_master.py`)
Quarter-by-quarter dominance analysis — finds players who own specific periods of the game.

**Output:** `zone_master.png`

---

### Clutch Analysis Suite
A collection of scripts for analyzing clutch-time performance (final 5 minutes, margin ≤ 5 points).

| Script | Purpose |
|--------|---------|
| `clutchStats.py` | Core clutch statistics engine |
| `euroleague_clutch_analysis.py` | Multi-season clutch performance analysis |
| `create_clutch_rankings.py` | Aggregated clutch player rankings |
| `create_clutch_visualizations.py` | Shot charts and visual breakdowns for top clutch players |
| `analyze_clutch_facts.py` | Narrative-style clutch facts and insights |
| `create_all_seasons_rankings.py` | All-time clutch rankings across all seasons |

**Output examples:** `clutch_rankings.json`, `clutch_rankings_all_seasons.json`

---

### Coach Tactics (`coachatoPlays.py`, `coachesTop5.py`, `coachestop5Part2.py`)
After-timeout play analysis — what coaches draw up when it matters most.

**Output:** `coach_tactics_final.csv`, `coach_tactics_final2025.csv`

---

### Game Flow Visualization
Real-time score differential charts showing the ebb and flow of individual games.

**Output example:** `game_flow_2025_268.png`

---

## 🇬🇷 Greek Derby Historical Analysis

### Olympiacos (2007–2025)
Full 19-season shot data analysis tracking the evolution of Olympiacos' playing style.

| Chart | Description |
|-------|-------------|
| `oly_evolution_2007_2025.png` | 3-panel overview: shot distribution, 3PT trend, volume |
| `oly_paint_vs_3pt.png` | Paint vs Three closing gap (38pp → 25pp) |
| `oly_era_radar.png` | DNA profile by era (Pre-Analytics → Modern) |
| `oly_shot_leaders.png` | Timeline of top shooters (Spanoulis' 8-year reign) |
| `oly_efficiency_vs_volume.png` | FG% vs shot attempts scatter by season |
| `gravity_map_OLY_{year}.png` | Gravity maps for 2007, 2010, 2013, 2016, 2020, 2022–2025 |

**Data:** `oly_history.json` — Per-season stats: attempts, makes, FG%, zone splits, top player

**Key findings:**
- 3PT share grew from 22% (2008) → 36% (2022), trend of +0.6%/yr
- Spanoulis was the top shot-taker for 8 consecutive seasons (2010–2017)
- Mid-range shots dropped from 12% → 7%
- 2022 was peak OLY: 40.4% FG, 36% from three, 3,001 attempts

---

### Panathinaikos (2007–2025)
Same comprehensive analysis for the rival club.

| Chart | Description |
|-------|-------------|
| `pan_evolution_2007_2025.png` | 3-panel overview: shot distribution, 3PT trend, volume |
| `pan_paint_vs_3pt.png` | Paint vs Three closing gap (40pp → 31pp) |
| `pan_era_radar.png` | DNA by era (Diamantidis → Calathes → Nunn) |
| `pan_shot_leaders.png` | Timeline of top shooters (Calathes' 4-year run) |
| `pan_efficiency_vs_volume.png` | FG% vs shot attempts scatter by season |
| `gravity_map_PAN_{year}.png` | Gravity maps for 2007, 2010, 2013, 2016, 2020, 2022–2025 |

**Data:** `pan_history.json`

**Key findings:**
- Slower 3PT adoption: +0.3%/yr vs Olympiacos' +0.6%/yr
- Calathes dominated for 4 straight seasons (2016–2019)
- 2018 was uniquely mid-range heavy (14% — highest in the dataset)
- Best season: 2024 (3,190 attempts, 40.0% FG)

---

### Greek Derby Head-to-Head

| Chart | Description |
|-------|-------------|
| `derby_mirror.png` | Side-by-side bars for 3PT%, FG%, Paint% per season |
| `derby_gap_tracker.png` | Difference plot showing who leads in each category over time |
| `derby_era_radar.png` | Both teams' DNA overlaid on same radar per era |
| `gravity_map_PAN_vs_OLY_{year}.png` | Side-by-side gravity maps for 2022–2025 |

---

## 📁 Data Sources

| File Pattern | Description | Seasons |
|---|---|---|
| `shot_data_{year}_{year}.csv` | Shot-level data (coordinates, action type, player, team) | 2007–2025 |
| `pbp_data_2023_2025.csv` | Play-by-play data with lineup tracking | 2023–2025 |
| `data/pbp_{year}.csv` | Cached play-by-play data per season | 2007–2025 |
| `coach_tactics_final*.csv` | After-timeout play analysis | 2024–2025 |
| `lineup_stats_*.json` | Lineup analysis results (5-man, 2-man, anchor) | 2024–2025 |
| `oly_history.json` / `pan_history.json` | Historical shot analysis per season | 2007–2025 |
| `clutch_*.json` | Clutch performance rankings | 2007–2024 |
| `heat_checks_*.json` | Scoring streak data | 2007–2024 |
| `team_code_mapping.json` | Team code → full name lookup table | — |

---

## 🛠️ Tech Stack

- **Python 3.x** with virtual environment (`.venv`)
- **Data:** `pandas`, `numpy`
- **Visualization:** `matplotlib`, `seaborn`
- **API:** [`euroleague_api`](https://pypi.org/project/euroleague-api/) — Official Euroleague data access
- **Caching:** Local CSV/JSON caching to minimize API calls

---

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/KonstantinosLaloudakis/EuroleaguePythonProject.git
cd EuroleaguePythonProject

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install pandas numpy matplotlib seaborn euroleague_api

# Run any module
python the_gravity_map.py
python the_lineup_analyzer.py
python streaks_and_bursts.py
python teeter_totter.py
python comeback_kings.py
```

Configure seasons in each script's `SEASON` / `START_SEASON` / `END_SEASON` variables.

---

## 📝 License

This project is for educational and analytical purposes. Euroleague data is sourced via the official API.
