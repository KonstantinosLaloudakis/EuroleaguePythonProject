from euroleague_api import play_by_play_data
import pandas as pd

def debug_clutch_data():
    season = 2025
    pbp = play_by_play_data.PlayByPlay()
    print(f"Fetching data for season {season} (partial check)...")
    
    # Just fetch a few rounds or games if possible, but the API might fetch all.
    # We'll just fetch normally.
    df = pbp.get_game_play_by_play_data_multiple_seasons(season, season)
    
    print(f"Total rows: {len(df)}")
    
    # Process Scores on FULL DF (needed for correct context)
    if 'POINTS_A' in df.columns and 'POINTS_B' in df.columns:
        df['POINTS_A'] = pd.to_numeric(df['POINTS_A'], errors='coerce')
        df['POINTS_B'] = pd.to_numeric(df['POINTS_B'], errors='coerce')
        df['POINTS_A'] = df.groupby('Gamecode')['POINTS_A'].ffill().fillna(0)
        df['POINTS_B'] = df.groupby('Gamecode')['POINTS_B'].ffill().fillna(0)
        
        # Calculate Pre-Play Margin
        df['Prev_POINTS_A'] = df.groupby('Gamecode')['POINTS_A'].shift(1).fillna(0)
        df['Prev_POINTS_B'] = df.groupby('Gamecode')['POINTS_B'].shift(1).fillna(0)
        df['PrePlayMargin'] = abs(df['Prev_POINTS_A'] - df['Prev_POINTS_B'])
    
    # Filter for Hifi
    player = "HIFI, NADIR"
    df_player = df[df['PLAYER'] == player].copy()
    
    # Filter for Period >= 4
    if 'PERIOD' in df_player.columns:
        df_player['PERIOD'] = pd.to_numeric(df_player['PERIOD'], errors='coerce')
        df_player = df_player[df_player['PERIOD'] >= 4]
    
    # Filter for Time <= 5 mins
    def get_seconds(t):
        try:
            m, s = map(int, str(t).split(':'))
            return m*60 + s
        except:
            return 9999
            
    df_player['SecondsRemaining'] = df_player['MARKERTIME'].apply(get_seconds)
    df_player = df_player[df_player['SecondsRemaining'] <= 300]
    
    # Clutch rows
    # Filter by PrePlayMargin <= 5
    clutch_rows = df_player[df_player['PrePlayMargin'] <= 5]
    
    clutch_rows['ScoreMargin'] = abs(clutch_rows['POINTS_A'] - clutch_rows['POINTS_B'])
    
    print(f"Total 'Clutch' plays found for {player}: {len(clutch_rows)}")
    print("Sample clutch rows (Playtype, PointsA, PointsB, Margin, Time):")
    # Removed DORSTY
    print(clutch_rows[['Gamecode', 'MARKERTIME', 'PLAYTYPE', 'POINTS_A', 'POINTS_B', 'ScoreMargin']].head(20))
    
    # Check if empty scores were converted to 0 and thus counted as clutch
    # If 0-0 in Period 4, likely data error unless it's a very scoreless game (unlikely in Q4)
    zeros = clutch_rows[(clutch_rows['POINTS_A'] == 0) & (clutch_rows['POINTS_B'] == 0)]
    if not zeros.empty:
        print(f"WARNING: {len(zeros)} rows have 0-0 score within clutch filters! This indicates missing score data.")
        print(zeros[['Gamecode', 'MARKERTIME', 'PLAYTYPE']].head())
        
        # Count how many of these are actual scoring plays that contributed to the stats
        scoring_plays = zeros[zeros['PLAYTYPE'].isin(['2FGM', '3FGM', 'FTM'])]
        print(f"Of these 0-0 rows, {len(scoring_plays)} are SCORING plays that wrongfully counted towards clutch stats.")

if __name__ == "__main__":
    debug_clutch_data()
