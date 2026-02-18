import pandas as pd
from euroleague_api import play_by_play_data
import json

class ClutchAnalysis:
    def __init__(self, start_season, end_season):
        self.start_season = start_season
        self.end_season = end_season
        self.data_filename = f'clutch_stats_{start_season}_{end_season}.json'
        self.rankings_filename = f'clutch_rankings_{start_season}_{end_season}.json'
        self.all_time_rankings_filename = f'clutch_rankings_all_seasons_{start_season}_{end_season}.json'
        self.shots_filename = f'clutch_shots_{start_season}_{end_season}.json'

    def get_seconds_from_time(self, time_str):
        """Converts MM:SS time string to total seconds."""
        try:
            minutes, seconds = map(int, str(time_str).split(':'))
            return minutes * 60 + seconds
        except (ValueError, AttributeError):
            return 0

    def fetch_and_calculate_stats(self):
        pbp = play_by_play_data.PlayByPlay()
        
        print(f"Fetching play-by-play data for seasons {self.start_season}-{self.end_season}...")
        try:
            full_df = pbp.get_game_play_by_play_data_multiple_seasons(self.start_season, self.end_season)
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

        if full_df.empty:
            print("No data fetched.")
            return None

        print(f"Total rows fetched: {len(full_df)}")
        
        if 'POINTS_A' in full_df.columns and 'POINTS_B' in full_df.columns:
            full_df['POINTS_A'] = pd.to_numeric(full_df['POINTS_A'], errors='coerce')
            full_df['POINTS_B'] = pd.to_numeric(full_df['POINTS_B'], errors='coerce')
            
            # Forward fill on FULL dataset
            full_df['POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].ffill().fillna(0)
            full_df['POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].ffill().fillna(0)
            
            # Calculate Pre-Play Margin to determine if the situation was clutch BEFORE the event
            full_df['Prev_POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].shift(1).fillna(0)
            full_df['Prev_POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].shift(1).fillna(0)
            full_df['PrePlayMargin'] = abs(full_df['Prev_POINTS_A'] - full_df['Prev_POINTS_B'])
        else:
            print("Score columns not found!")
            return None

        # Filter for Clutch Moments
        if 'MARKERTIME' in full_df.columns:
             full_df['SecondsRemaining'] = full_df['MARKERTIME'].apply(self.get_seconds_from_time)
        else:
            print("MARKERTIME column not found!")
            return None

        if 'PERIOD' in full_df.columns:
            full_df['PERIOD'] = pd.to_numeric(full_df['PERIOD'], errors='coerce')
            clutch_df = full_df[full_df['PERIOD'] >= 4].copy()
        else:
            print("PERIOD column not found!")
            return None

        # Filter: <= 5 mins (300 seconds)
        clutch_df = clutch_df[clutch_df['SecondsRemaining'] <= 300]

        # Filter based on Pre-Play Margin
        clutch_df = clutch_df[clutch_df['PrePlayMargin'] <= 5]
        
        # Calculate current margin for reference
        clutch_df['ScoreMargin'] = abs(clutch_df['POINTS_A'] - clutch_df['POINTS_B'])
            
        print(f"Found {len(clutch_df)} clutch plays.")
        self.clutch_pbp_df = clutch_df.copy() # Store for shot filtering
        
        results_by_season = {}
        all_clutch_shots = []
        
        for season in range(self.start_season, self.end_season + 1):
            season_clutch_df = clutch_df[clutch_df['Season'] == season]
            player_stats = {}
            
            for index, row in season_clutch_df.iterrows():
                play_type = row.get('PLAYTYPE', '')
                player_name = row.get('PLAYER', 'Unknown')
                team_code = row.get('CODETEAM', '')

                if not player_name or pd.isna(player_name):
                    continue
                    
                if player_name not in player_stats:
                    player_stats[player_name] = {
                        'Player': player_name,
                        'Team': team_code,
                        'Season': season,
                        'ClutchPoints': 0,
                        'ClutchFGM': 0,
                        'ClutchFGA': 0,
                        'ClutchFTM': 0,
                        'ClutchFTA': 0,
                        'Clutch3PM': 0,
                        'ClutchFoulsDrawn': 0, 
                        'ClutchTurnovers': 0
                    }
                    
                stats = player_stats[player_name]
                
                if play_type == '2FGM':
                    stats['ClutchPoints'] += 2
                    stats['ClutchFGM'] += 1
                    stats['ClutchFGA'] += 1
                elif play_type == '2FGA':
                    stats['ClutchFGA'] += 1
                elif play_type == '3FGM':
                    stats['ClutchPoints'] += 3
                    stats['ClutchFGM'] += 1
                    stats['ClutchFGA'] += 1
                    stats['Clutch3PM'] += 1
                elif play_type == '3FGA':
                    stats['ClutchFGA'] += 1
                elif play_type == 'FTM':
                    stats['ClutchPoints'] += 1
                    stats['ClutchFTM'] += 1
                    stats['ClutchFTA'] += 1
                elif play_type == 'FTA':
                     stats['ClutchFTA'] += 1
                elif play_type == 'TO':
                    stats['ClutchTurnovers'] += 1
                elif play_type == 'RV':
                    stats['ClutchFoulsDrawn'] += 1
            
            season_results = []
            for p_name, stats in player_stats.items():
                if stats['ClutchPoints'] == 0 and stats['ClutchFGA'] == 0:
                    continue
                    
                # FG%
                if stats['ClutchFGA'] > 0:
                    stats['FG%'] = f"{(stats['ClutchFGM'] / stats['ClutchFGA']) * 100:.1f}%"
                else:
                    stats['FG%'] = "N/A"
                    
                # FT%
                if stats['ClutchFTA'] > 0:
                    stats['FT%'] = f"{(stats['ClutchFTM'] / stats['ClutchFTA']) * 100:.1f}%"
                else:
                    stats['FT%'] = "N/A"

                season_results.append(stats)
                
            season_results.sort(key=lambda x: x['ClutchPoints'], reverse=True)
            results_by_season[season] = season_results

        # Save Stats
        with open(self.data_filename, 'w', encoding='utf-8') as f:
            json.dump(results_by_season, f, indent=4, ensure_ascii=False)
        print(f"Saved raw stats to {self.data_filename}")
        
        return results_by_season

    def _add_helper_values(self, players):
        for p in players:
            if 'FG%' in p and p['FG%'] != 'N/A':
                 p['_fg_pct_val'] = float(p['FG%'].strip('%'))
            else:
                 p['_fg_pct_val'] = 0.0
            
            if 'FT%' in p and p['FT%'] != 'N/A':
                 p['_ft_pct_val'] = float(p['FT%'].strip('%'))
            else:
                 p['_ft_pct_val'] = 0.0
        return players

    def _clean_helper_values(self, players):
        clean = []
        for p in players:
            new_p = {k: v for k, v in p.items() if not k.startswith('_')}
            clean.append(new_p)
        return clean

    def generate_season_rankings(self, data):
        rankings = {}
        for season, players in data.items():
            players = self._add_helper_values(players)
            season_rankings = {}

            # 1. Top Scorers
            top_scorers = sorted(players, key=lambda x: x['ClutchPoints'], reverse=True)[:10]
            season_rankings["Top Scorers"] = self._clean_helper_values(top_scorers)

            # 2. Ice Cold FT (min 10 attempts)
            ft_shooters = [p for p in players if p['ClutchFTA'] >= 10]
            best_ft = sorted(ft_shooters, key=lambda x: x['_ft_pct_val'], reverse=True)[:10]
            season_rankings["Ice Cold Free Throw Shooters"] = self._clean_helper_values(best_ft)

            # 3. Efficient Killers FG (min 15 attempts)
            fg_shooters = [p for p in players if p['ClutchFGA'] >= 15]
            best_fg = sorted(fg_shooters, key=lambda x: x['_fg_pct_val'], reverse=True)[:10]
            season_rankings["Efficient Killers (FG%)"] = self._clean_helper_values(best_fg)

            # 4. Foul Magnets
            foul_magnets = sorted(players, key=lambda x: x['ClutchFoulsDrawn'], reverse=True)[:10]
            season_rankings["Foul Magnets"] = self._clean_helper_values(foul_magnets)

            # 5. 3-Point Snipers
            snipers = sorted(players, key=lambda x: x['Clutch3PM'], reverse=True)[:10]
            season_rankings["3-Point Snipers"] = self._clean_helper_values(snipers)

            # 6. Turnover Prone
            turnovers = sorted(players, key=lambda x: x['ClutchTurnovers'], reverse=True)[:10]
            season_rankings["Turnover Prone"] = self._clean_helper_values(turnovers)

            rankings[season] = season_rankings

        with open(self.rankings_filename, 'w', encoding='utf-8') as f:
            json.dump(rankings, f, indent=4, ensure_ascii=False)
        print(f"Saved season rankings to {self.rankings_filename}")

    def generate_all_time_rankings(self, data):
        all_performances = []
        for season, players in data.items():
            for p in players:
                # p already has Season from creation, but ensure it exists
                p['Season'] = season 
                all_performances.append(p)
        
        all_performances = self._add_helper_values(all_performances)
        rankings = {}

        # 1. Top Scorers
        top_scorers = sorted(all_performances, key=lambda x: x['ClutchPoints'], reverse=True)[:10]
        rankings["Top Scorers (Best Single Season)"] = self._clean_helper_values(top_scorers)

        # 2. Ice Cold FT (min 15 attempts)
        ft_shooters = [p for p in all_performances if p['ClutchFTA'] >= 15]
        best_ft = sorted(ft_shooters, key=lambda x: x['_ft_pct_val'], reverse=True)[:10]
        rankings["Ice Cold Free Throw Shooters (Best Single Season)"] = self._clean_helper_values(best_ft)

        # 3. Efficient Killers FG (min 20 attempts)
        fg_shooters = [p for p in all_performances if p['ClutchFGA'] >= 20]
        best_fg = sorted(fg_shooters, key=lambda x: x['_fg_pct_val'], reverse=True)[:10]
        rankings["Efficient Killers FG% (Best Single Season)"] = self._clean_helper_values(best_fg)

        # 4. Foul Magnets
        foul_magnets = sorted(all_performances, key=lambda x: x['ClutchFoulsDrawn'], reverse=True)[:10]
        rankings["Foul Magnets (Best Single Season)"] = self._clean_helper_values(foul_magnets)

        # 5. 3-Point Snipers
        snipers = sorted(all_performances, key=lambda x: x['Clutch3PM'], reverse=True)[:10]
        rankings["3-Point Snipers (Best Single Season)"] = self._clean_helper_values(snipers)

        # 6. Turnover Prone
        turnovers = sorted(all_performances, key=lambda x: x['ClutchTurnovers'], reverse=True)[:10]
        rankings["Turnover Prone (Best Single Season)"] = self._clean_helper_values(turnovers)

        with open(self.all_time_rankings_filename, 'w', encoding='utf-8') as f:
            json.dump(rankings, f, indent=4, ensure_ascii=False)
        print(f"Saved all-time rankings to {self.all_time_rankings_filename}")

    def fetch_clutch_shots(self):
        from euroleague_api import shot_data
        print(f"Fetching shot data for seasons {self.start_season}-{self.end_season}...")
        shots = shot_data.ShotData()
        try:
            full_df = shots.get_game_shot_data_multiple_seasons(self.start_season, self.end_season)
        except Exception as e:
            print(f"Error fetching shots: {e}")
            return

        if full_df.empty:
            print("No shot data fetched.")
            return

        print(f"Total shots fetched: {len(full_df)}")
        
        # Ensure consistency with PBP by filtering using the Valid Clutch Plays identified in PBP
        if not hasattr(self, 'clutch_pbp_df') or self.clutch_pbp_df is None:
            print("Warning: PBP data not available for filtering. Using crude approximation.")
            # Crude logic: Pre-Shot logic is approximate
            full_df['POINTS_A'] = pd.to_numeric(full_df['POINTS_A'], errors='coerce').fillna(0)
            full_df['POINTS_B'] = pd.to_numeric(full_df['POINTS_B'], errors='coerce')
            full_df['ScoreMargin'] = abs(full_df['POINTS_A'] - full_df['POINTS_B'])
            # We can't easily do Pre-Shot logic here without PBP, so we use Post-Shot margin 
            # but stricter or looser? 
            # User wants Correct Logic. So we fallback to Post-Shot <= 5 but acknowledge error.
            # Actually, let's just use Post-Shot <= 5 if PBP is missing.
            clutch_shots = full_df[
                (pd.to_numeric(full_df['MINUTE'], errors='coerce') > 35) & 
                (full_df['ScoreMargin'] <= 5)
            ].copy()
        else:
            print("Filtering shots using validated PBP Clutch Plays...")
            # Create a key for matching: Gamecode + Player + Time
            # PBP: 'Gamecode', 'PLAYER', 'MARKERTIME'
            # Shot: 'Gamecode', 'PLAYER', 'CONSOLE'
            
            # Prepare PBP keys of SCORING PLAYS only (others don't match shots)
            # PBP 'PLAYTYPE' in ['2FGM', '3FGM', 'LAYUPMD', 'DUNK'] ? 
            # PBP usually uses '2FGM', '3FGM', 'FTM'. DUNK is usually '2FGM' with extra info.
            # Only MAKES are in PBP as 'FGM'. MISSES are 'FGA'.
            # Shot data has BOTH Makes and Misses.
            
            # PBP Clutch DF contains ALL events (Fouls, TOs, FGMs, FGAs).
            # So we can match FGA and FGM.
            
            # Let's standardize keys
            # PBP
            self.clutch_pbp_df['Key'] = (
                self.clutch_pbp_df['Gamecode'].astype(str) + "_" + 
                self.clutch_pbp_df['PLAYER'].str.strip().str.upper() + "_" + 
                self.clutch_pbp_df['MARKERTIME'].astype(str)
            )
            
            # Shot Data
            full_df['Key'] = (
                full_df['Gamecode'].astype(str) + "_" + 
                full_df['PLAYER'].str.strip().str.upper() + "_" + 
                full_df['CONSOLE'].astype(str)
            )
            
            # Filter Shot Data by Key presence in Clutch PBP
            valid_keys = set(self.clutch_pbp_df['Key'].unique())
            clutch_shots = full_df[full_df['Key'].isin(valid_keys)].copy()
            
            print(f"Filtered to {len(clutch_shots)} clutch shots using PBP cross-reference.")

        makes_actions = ['2FGM', '3FGM', 'LAYUPMD', 'DUNK']
        
        # Format for JSON
        output_data = []
        for index, row in clutch_shots.iterrows():
            action = row.get('ID_ACTION', '').strip()
            # Safety check: Ensure action is recognizable
            
            result = 'Make' if action in makes_actions else 'Miss'
            
            output_data.append({
                'Player': row.get('PLAYER', 'Unknown').strip(),
                'Team': row.get('TEAM', '').strip(),
                'Season': row.get('Season', ''),
                'Type': action,
                'Result': result,
                'CoordX': row.get('COORD_X', 0),
                'CoordY': row.get('COORD_Y', 0),
                'Minute': row.get('MINUTE', 0),
                'Gamecode': row.get('Gamecode', '')
            })
            
        with open(self.shots_filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(output_data)} shots to {self.shots_filename}")

    def run(self):
        data = self.fetch_and_calculate_stats()
        if data:
            self.generate_season_rankings(data)
            self.generate_all_time_rankings(data)
            
        # Run independent shot fetch
        self.fetch_clutch_shots()
            
        print("Done! All files generated.")

if __name__ == "__main__":
    # Example usage: Analyze 2025
    analysis = ClutchAnalysis(2025, 2025)
    analysis.run()
