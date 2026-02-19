from euroleague_api import standings, player_stats

def check_api():
    print("--- Standings ---")
    try:
        s = standings.Standings()
        df_standings = s.get_standings(season=2025)
        if not df_standings.empty:
            print(df_standings.columns.tolist())
            print(df_standings.head(2).to_dict('records'))
    except Exception as e:
        print(f"Standings Error: {e}")

    print("\n--- Player Stats ---")
    try:
        p = player_stats.PlayerStats()
        # "Traditional" stats usually contain PTS, REB, AST etc.
        df_stats = p.get_player_stats(season=2025, endpoint='traditional', phase_type_code='RS') 
        if not df_stats.empty:
             print(df_stats.columns.tolist())
             print(df_stats.head(2).to_dict('records'))
    except Exception as e:
        print(f"Player Stats Error: {e}")

if __name__ == "__main__":
    check_api()
