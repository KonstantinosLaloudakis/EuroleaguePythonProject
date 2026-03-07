"""
🏀 EUROLEAGUE ANALYTICS MASTER REFRESH PIPELINE
=================================================
One command to update everything after a new round.

Usage:
    python refresh_all.py              # Full refresh (fetch + compute + visualize)
    python refresh_all.py --no-fetch   # Skip data fetch (just recompute + visualize)
    python refresh_all.py --viz-only   # Only regenerate visualizations
    python refresh_all.py --commit     # Automatically stage and commit new round files
"""

import subprocess
import sys
import time
import os

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

PYTHON = os.path.join('.venv', 'Scripts', 'python.exe') if os.name == 'nt' else 'python3'


def run_step(name, script, args=None):
    """Run a script and print status."""
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}⏳ {name}...{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    cmd = [PYTHON, script]
    if args:
        cmd.extend(args)
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print(f"{GREEN}✅ {name} completed in {elapsed:.1f}s{RESET}")
        return True
    else:
        print(f"{RED}❌ {name} FAILED (exit code {result.returncode}){RESET}")
        return False


def main():
    args = sys.argv[1:]
    skip_fetch = '--no-fetch' in args
    viz_only = '--viz-only' in args
    
    print(f"\n{BOLD}{YELLOW}{'='*60}{RESET}")
    print(f"{BOLD}{YELLOW}  🏀 EUROLEAGUE ANALYTICS - FULL REFRESH PIPELINE{RESET}")
    print(f"{BOLD}{YELLOW}{'='*60}{RESET}")
    
    start_time = time.time()
    results = []

    # ── COMPUTE CURRENT ROUND FOR HISTORY KEEPING ──
    try:
        import json
        with open('mvp_standings_derived.json', 'r') as f:
            standings = json.load(f)
        max_gp = max((t.get('GP', 0) for t in standings.values()), default=0)
        round_suffix = f"_R{max_gp}" if max_gp > 0 else ""
    except Exception as e:
        print(f"{YELLOW}⚠️  Could not determine current round for suffix: {e}{RESET}")
        round_suffix = ""
    
    os.environ['EUROLEAGUE_ROUND_SUFFIX'] = round_suffix
    if round_suffix:
        print(f"{CYAN}📌 Active Round Suffix for Outputs: {round_suffix}{RESET}")
    
    # ── PHASE 1: DATA FETCH ──
    if not skip_fetch and not viz_only:
        print(f"\n{BOLD}📡 PHASE 1: Fetching Latest Data{RESET}")
        results.append(('Fetch Game Stats', run_step(
            'Fetching game stats from Euroleague API',
            'fetch_mvp_data_v2.py'
        )))
        results.append(('Fetch Play-By-Play', run_step(
            'Fetching play-by-play data from Euroleague API',
            'fetch_pbp.py',
            ['--force']
        )))
        results.append(('Parse Game Data', run_step(
            'Parsing game results',
            'parse_mvp_data.py'
        )))
    else:
        print(f"\n{YELLOW}⏭️  Skipping data fetch{RESET}")
    
    # ── PHASE 2: COMPUTE ENGINES ──
    if not viz_only:
        print(f"\n{BOLD}🧮 PHASE 2: Running Compute Engines{RESET}")
        results.append(('Adjusted Ratings', run_step(
            'Computing KenPom Adjusted Ratings + SOS',
            'calculate_adjusted_ratings.py'
        )))
        results.append(('MVP Scores', run_step(
            'Computing MVP Ladder Scores',
            'calculate_mvp_scores.py'
        )))
        results.append(('TPM Ratings', run_step(
            'Computing True Plus-Minus (TPM)',
            'calculate_tpm.py'
        )))
        results.append(('WIR Ratings', run_step(
            'Computing Weighted Impact Ratings (WIR)',
            'calculate_wir.py'
        )))
        results.append(('WPA Ratings', run_step(
            'Computing Win Probability Added (WPA)',
            'calculate_wpa.py'
        )))
        results.append(('Elo Ratings', run_step(
            'Computing Elo Ratings',
            'calculate_elo.py'
        )))
        results.append(('Monte Carlo Sim', run_step(
            'Running Monte Carlo Simulation (10K iterations)',
            'simulate_monte_carlo.py'
        )))
    else:
        print(f"\n{YELLOW}⏭️  Skipping compute engines{RESET}")
    
    # ── PHASE 3: VISUALIZATIONS ──
    print(f"\n{BOLD}🎨 PHASE 3: Generating Visualizations{RESET}")
    
    viz_scripts = [
        ('Remaining SOS Table', 'visualize_remaining_sos.py'),
        ('Playoff Matrix', 'visualize_playoff_matrix.py'),
        ('Wins Profile Matrix', 'visualize_wins_profile.py'),
        ('Seed Distribution', 'visualize_seed_distribution.py'),
        ('Clutch Matchups', 'visualize_clutch_matchups.py'),
        ('Schedule Grid', 'visualize_schedule_grid.py'),
        ('Power Trajectory', 'visualize_power_trajectory.py'),
        ('Round Preview Card', 'visualize_round_preview.py'),
        ('MVP Ladder', 'visualize_mvp_ladder.py'),
        ('TPM vs WIR Quadrants', 'visualize_tpm_wir.py'),
        ('WIR vs PIR', 'visualize_wir.py'),
        ('WPA Leaders', 'visualize_wpa.py'),
    ]
    
    for name, script in viz_scripts:
        if os.path.exists(script):
            results.append((name, run_step(f'Generating {name}', script)))
        else:
            print(f"{YELLOW}⚠️  {script} not found, skipping{RESET}")
    
    # ── PHASE 4: ANIMATIONS (optional, slower) ──
    if '--with-animations' in args:
        print(f"\n{BOLD}🎬 PHASE 4: Generating Animations{RESET}")
        results.append(('Standings Race GIF', run_step(
            'Generating Standings Race Animation',
            'visualize_standings_race.py'
        )))
    else:
        print(f"\n{YELLOW}⏭️  Skipping animations (use --with-animations to include){RESET}")
    
    # ── PHASE 5: GIT AUTOMATION ──
    if '--commit' in args and round_suffix:
        print(f"\n{BOLD}📦 PHASE 5: Git Automation{RESET}")
        import glob
        files_to_add = glob.glob(f"*{round_suffix}.png") + glob.glob(f"*{round_suffix}.json")
        if files_to_add:
            round_num = round_suffix.replace('_R', '')
            print(f"{CYAN}Staging {len(files_to_add)} files for Round {round_num}...{RESET}")
            subprocess.run(['git', 'add'] + files_to_add)
            
            commit_msg = f"feat(analytics): update visualizations for Round {round_num}"
            print(f"{CYAN}Committing: '{commit_msg}'{RESET}")
            git_result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
            
            if git_result.returncode == 0:
                print(f"{GREEN}✅ Git commit successful{RESET}")
                results.append(('Git Commit', True))
            else:
                print(f"{YELLOW}⚠️  Git commit output:\n{git_result.stdout}{RESET}")
                results.append(('Git Commit', False))
        else:
            print(f"{YELLOW}⚠️  No files found with suffix {round_suffix} to commit.{RESET}")
    
    # ── SUMMARY ──
    total_time = time.time() - start_time
    
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}📊 REFRESH COMPLETE — {total_time:.1f}s total{RESET}")
    print(f"{'='*60}")
    
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    
    for name, ok in results:
        status = f"{GREEN}✅{RESET}" if ok else f"{RED}❌{RESET}"
        print(f"  {status} {name}")
    
    print(f"\n  {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}")
    
    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
