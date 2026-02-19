from euroleague_clutch_analysis import ClutchAnalysis
import pandas as pd
import json

class ClutchLogExtractor(ClutchAnalysis):
    def extract_clutch_logs(self):
        # 1. Fetch Data (uses parent method logic but we need to access internal df)
        print(f"Fetching play-by-play data for {self.start_season}...")
        
        # We need to call parental data fetch or copy logic. 
        # Parent fetch_and_calculate_stats does everything and saves files. 
        # We want to INTERCEPT the dataframe 'clutch_df'.
        # Since parent method prints and returns nothing, we might need to duplicate the fetch logic
        # OR inherit and override.
        
        # Let's copy the fetch logic for safety and modification
        from euroleague_api import play_by_play_data
        pbp = play_by_play_data.PlayByPlay()
        
        try:
            full_df = pbp.get_game_play_by_play_data_multiple_seasons(self.start_season, self.end_season)
        except Exception as e:
            print(f"Error: {e}")
            return

        if full_df.empty:
            print("No data.")
            return

        # Preprocessing (Same as parent)
        full_df['POINTS_A'] = pd.to_numeric(full_df['POINTS_A'], errors='coerce')
        full_df['POINTS_B'] = pd.to_numeric(full_df['POINTS_B'], errors='coerce')
        full_df['POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].ffill().fillna(0)
        full_df['POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].ffill().fillna(0)
        full_df['Prev_POINTS_A'] = full_df.groupby('Gamecode')['POINTS_A'].shift(1).fillna(0)
        full_df['Prev_POINTS_B'] = full_df.groupby('Gamecode')['POINTS_B'].shift(1).fillna(0)
        full_df['PrePlayMargin'] = abs(full_df['Prev_POINTS_A'] - full_df['Prev_POINTS_B'])
        
        full_df['SecondsRemaining'] = full_df['MARKERTIME'].apply(self.get_seconds_from_time)
        full_df['PERIOD'] = pd.to_numeric(full_df['PERIOD'], errors='coerce')
        
        # Filter Clutch
        clutch_df = full_df[
            (full_df['PERIOD'] >= 4) & 
            (full_df['SecondsRemaining'] <= 300) & 
            (full_df['PrePlayMargin'] <= 5)
        ].copy()
        
        print(f"Found {len(clutch_df)} clutch events.")
        
        # Extract Scoring Events
        clutch_logs = []
        
        for index, row in clutch_df.iterrows():
            play_type = row.get('PLAYTYPE', '')
            player_name = row.get('PLAYER', 'Unknown')
            game_code = row.get('Gamecode')
            points = 0
            
            if '2FGM' in play_type: points = 2
            elif '3FGM' in play_type: points = 3
            elif 'FTM' in play_type: points = 1
            
            if points > 0:
                clutch_logs.append({
                    'GameCode': game_code,
                    'Player': player_name,
                    'ClutchPoints': points
                })

        # Save Logs
        output_file = 'clutch_logs_2025.json'
        with open(output_file, 'w') as f:
            json.dump(clutch_logs, f, indent=4)
        print(f"Saved {len(clutch_logs)} scoring events to {output_file}")

if __name__ == "__main__":
    extractor = ClutchLogExtractor(2025, 2025)
    extractor.extract_clutch_logs()
