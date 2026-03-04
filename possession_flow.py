"""
Possession State Flow Engine — 2025-26 Season
Parses raw play-by-play into distinct possessions, classifying:
  - Start State (how the possession began)
  - Outcome (how the possession ended)
Then builds a transition matrix for Sankey diagram visualization.
"""

import pandas as pd
import numpy as np
import json

# Play types that signal possession changes
POSSESSION_ENDERS = {'2FGM', '3FGM', 'TO', 'FTM', 'FTA'}  # FTA only if last FT
SHOT_MISSES = {'2FGA', '3FGA'}
REBOUNDS = {'D', 'O'}

# Classify what started a possession
START_STATES = {
    'D': 'Defensive Rebound',
    'ST': 'Live-Ball Steal',
    '2FGM': 'After Made 2PT',
    '3FGM': 'After Made 3PT',
    'FTM': 'After Made FT',
    'BP': 'Period Start',
    'JB': 'Jump Ball',
    'TO': 'After Turnover',
    'TOUT': 'After Timeout',
    'TOUT_TV': 'After Timeout',
}

# Classify shot outcomes
OUTCOMES = {
    '2FGM': '2PT Make',
    '3FGM': '3PT Make',
    '2FGA': '2PT Miss',
    '3FGA': '3PT Miss',
    'TO': 'Turnover',
    'FTM': 'FT Make',
    'FTA': 'FT Miss',
}


def parse_possessions(df, team_code):
    """
    Parse play-by-play data into individual possessions for a specific team.
    Returns a list of possession dicts with start_state, outcome, and whether assisted.
    """
    possessions = []
    current_poss = None
    last_event_by_other_team = None
    last_global_event = None
    
    for _, row in df.iterrows():
        pt = str(row['PLAYTYPE']).strip()
        team = str(row['CODETEAM']).strip()
        
        # Skip non-play events (substitutions, timeouts as standalone)
        if pt in ('IN', 'OUT', 'EG', 'EP', 'nan', ''):
            continue
            
        # Track the last meaningful event by the OTHER team (for Start State classification)
        if team != team_code and pt not in ('BP', 'JB', 'TOUT', 'TOUT_TV', 'nan', ''):
            last_event_by_other_team = pt
            
        last_global_event = pt
            
        # === POSSESSION START DETECTION ===
        # A new possession for our team starts when:
        # 1. The team gets the ball after the other team's possession ended
        # 2. A period begins
        # 3. After a jump ball
        
        if team == team_code:
            if current_poss is None:
                # Start a new possession
                # Determine how this possession started
                if last_event_by_other_team in START_STATES:
                    start = START_STATES[last_event_by_other_team]
                elif last_event_by_other_team in SHOT_MISSES:
                    start = 'Defensive Rebound'  # They missed, we got the board
                else:
                    start = 'Dead Ball / Inbound'
                    
                current_poss = {
                    'start_state': start,
                    'events': [],
                    'assisted': False,
                    'outcome': None,
                    'shot_type': None,
                }
            
            # Track events in this possession
            current_poss['events'].append(pt)
            
            # Check for assist
            if pt == 'AS':
                current_poss['assisted'] = True
                
            # Check for possession-ending events
            if pt in ('2FGM', '3FGM'):
                current_poss['outcome'] = OUTCOMES[pt]
                current_poss['shot_type'] = 'assisted' if current_poss['assisted'] else 'unassisted'
                possessions.append(current_poss)
                current_poss = None
                last_event_by_other_team = pt  # For the OTHER team's next possession
                
            elif pt in ('2FGA', '3FGA'):
                # Shot missed — possession might continue with offensive rebound
                current_poss['outcome'] = OUTCOMES[pt]
                # Don't end yet; wait to see if O-rebound happens
                
            elif pt == 'O':
                # Offensive rebound — possession continues!
                current_poss['outcome'] = None  # Reset outcome, possession lives on
                current_poss['start_state'] = 'Offensive Rebound'  # Reclassify
                
            elif pt == 'TO':
                current_poss['outcome'] = 'Turnover'
                possessions.append(current_poss)
                current_poss = None
                
            elif pt in ('FTM', 'FTA'):
                # Free throws — check if it's the last one
                playinfo = str(row.get('PLAYINFO', ''))
                # Detect "X/X" pattern (e.g., "2/2" means last FT)
                if '/' in playinfo:
                    parts = playinfo.split('(')[1].split('/') if '(' in playinfo else ['', '']
                    try:
                        current = int(parts[0].strip())
                        total = int(parts[1].split(')')[0].strip().split(' ')[0])
                        if current == total:
                            # Last free throw
                            if pt == 'FTM':
                                current_poss['outcome'] = 'FT Make'
                            else:
                                current_poss['outcome'] = 'FT Miss'
                            possessions.append(current_poss)
                            current_poss = None
                    except (ValueError, IndexError):
                        pass
                        
        else:
            # Other team has the ball — if we had an active possession that ended
            # with a miss and no O-rebound, close it now
            if current_poss is not None and current_poss['outcome'] is not None:
                possessions.append(current_poss)
                current_poss = None
                
        # Period start / end resets
        if pt == 'BP':
            if current_poss is not None and current_poss['outcome'] is not None:
                possessions.append(current_poss)
            current_poss = None
            last_event_by_other_team = 'BP'
            
    return possessions


def build_transition_matrix(possessions):
    """Build the transition counts for the Sankey diagram."""
    # Start -> Outcome transitions
    start_to_outcome = {}
    # Start -> Assisted/Unassisted -> Outcome (3-level)
    full_flow = {}
    
    for poss in possessions:
        start = poss['start_state']
        outcome = poss['outcome']
        if outcome is None:
            continue
            
        # Simplify start states for cleaner Sankey
        if start in ('After Made 2PT', 'After Made 3PT', 'After Made FT'):
            start = 'After Made Basket'
        if start in ('Period Start', 'Jump Ball', 'Dead Ball / Inbound'):
            start = 'Dead Ball'
        if start == 'After Timeout':
            start = 'Dead Ball'
        if start == 'After Turnover':
            start = 'After Opponent TO'
            
        # Determine middle node (play type)
        if outcome in ('2PT Make', '3PT Make'):
            middle = 'Assisted' if poss['assisted'] else 'Unassisted'
        elif outcome in ('2PT Miss', '3PT Miss'):
            middle = 'Contested'
        elif outcome == 'Turnover':
            middle = 'Ball Handling'
        elif outcome in ('FT Make', 'FT Miss'):
            middle = 'Drawn Foul'
        else:
            middle = 'Other'
            
        # Track Start -> Middle
        key_sm = (start, middle)
        start_to_outcome[key_sm] = start_to_outcome.get(key_sm, 0) + 1
        
        # Track Middle -> Outcome
        key_mo = (middle, outcome)
        full_flow[key_mo] = full_flow.get(key_mo, 0) + 1
        
    return start_to_outcome, full_flow


def analyze_team(team_code):
    """Full analysis pipeline for one team."""
    print(f"\n{'='*60}")
    print(f"  POSSESSION STATE FLOW — {team_code}")
    print(f"{'='*60}")
    
    df = pd.read_csv('pbp_2025.csv')
    df = df.sort_values(['Gamecode', 'NUMBEROFPLAY']).reset_index(drop=True)
    
    possessions = parse_possessions(df, team_code)
    print(f"  Parsed {len(possessions)} possessions for {team_code}")
    
    # Count start states
    start_counts = {}
    outcome_counts = {}
    for p in possessions:
        s = p['start_state']
        start_counts[s] = start_counts.get(s, 0) + 1
        o = p['outcome']
        if o:
            outcome_counts[o] = outcome_counts.get(o, 0) + 1
    
    print(f"\n  --- Start States ---")
    for k, v in sorted(start_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:<25} {v:>5} ({v/len(possessions)*100:.1f}%)")
        
    print(f"\n  --- Outcomes ---")
    for k, v in sorted(outcome_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:<25} {v:>5} ({v/len(possessions)*100:.1f}%)")
    
    start_to_mid, mid_to_out = build_transition_matrix(possessions)
    
    # Save for the Sankey visualizer
    result = {
        'team': team_code,
        'total_possessions': len(possessions),
        'start_to_middle': {f"{k[0]} -> {k[1]}": v for k, v in start_to_mid.items()},
        'middle_to_outcome': {f"{k[0]} -> {k[1]}": v for k, v in mid_to_out.items()},
    }
    
    return result


def main():
    teams_to_analyze = ['OLY', 'PAM', 'PAN', 'MAD', 'MCO', 'MUN', 'BAR', 'ZAL', 'TEL']
    
    all_results = {}
    for team in teams_to_analyze:
        result = analyze_team(team)
        all_results[team] = result
        
    with open('possession_flow.json', 'w') as f:
        json.dump(all_results, f, indent=4)
    print(f"\nSaved possession flow data to possession_flow.json")


if __name__ == '__main__':
    main()
