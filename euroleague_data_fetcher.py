"""
EuroLeague Data Fetcher for Mystery Player Cards

This script uses the euroleague-api to fetch player statistics
and integrate them with the createCards.py system for mystery player games.
"""

import pandas as pd
from euroleague_api.player_stats import PlayerStats
from euroleague_api.team_stats import TeamStats
from euroleague_api.standings import Standings
import json
import os
from typing import Dict, List, Optional, Tuple
import random


class EuroLeagueDataFetcher:
    """
    Fetches and processes EuroLeague player statistics for mystery card generation.
    """
    
    def __init__(self):
        self.player_stats = PlayerStats("E")  # "E" for EuroLeague
        self.team_stats = TeamStats("E")
        self.standings = Standings("E")
        
        # Define stat mappings for different card difficulties
        self.stat_mappings = {
            "easy": ["PTS", "REB", "AST", "PIR", "MIN", "3P%"],
            "medium": ["PIR", "eFG%", "REB", "STL", "TOV", "AST/TO"],
            "hard": ["USG%", "TS%", "BLK%", "AST%", "OREB%", "DRTG"],
            "position_pg": ["AST", "AST/TO", "STL", "3P%", "PIR", "MIN"],
            "position_sg": ["3PM", "eFG%", "PTS", "STL", "FT%", "USG%"],
            "position_sf": ["PTS", "REB", "3P%", "PIR", "STL", "MIN"],
            "position_pf": ["REB", "FG%", "BLK", "OREB", "PIR", "MIN"],
            "position_c": ["REB", "BLK", "FG%", "OREB", "PF", "MIN"]
        }
    
    def get_season_stats(self, season: int, stat_category: str = "traditional") -> pd.DataFrame:
        """
        Fetch season statistics for all players.
        
        Args:
            season (int): Season year (e.g., 2023 for 2023-24 season)
            stat_category (str): "traditional", "advanced", "misc", "scoring"
            
        Returns:
            pd.DataFrame: Player statistics dataframe
        """
        try:
            print(f"Fetching {stat_category} stats for {season}-{season+1} season...")
            
            # Create params dictionary for the API call
            params = {
                'SeasonCode': f'E{season}',  # E2023 for 2023-24 season
            }
            
            df = self.player_stats.get_player_stats(
                endpoint=stat_category,
                params=params,
                phase_type_code="RS",  # Regular season
                statistic_mode="PerGame"
            )
            
            if df is not None and not df.empty:
                print(f"✅ Successfully fetched {len(df)} player records")
                return df
            else:
                print("⚠️ No data returned from API")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error fetching season stats: {e}")
            return pd.DataFrame()
    
    def get_team_info(self, season: int) -> Dict:
        """Get team information and standings for context."""
        try:
            # Try to get final standings (round 34 is typically the last round)
            standings_df = self.standings.get_standings(season, 34)
            if standings_df is not None and not standings_df.empty:
                # Convert to dict for easy lookup
                team_info = {}
                for _, row in standings_df.iterrows():
                    team_info[row.get('Team', '')] = {
                        'position': row.get('Position', 0),
                        'wins': row.get('W', 0),
                        'losses': row.get('L', 0),
                        'win_pct': row.get('PCT', 0),
                        'playoff_team': row.get('Position', 18) <= 8  # Top 8 make playoffs
                    }
                return team_info
            return {}
        except Exception as e:
            print(f"❌ Error fetching team info: {e}")
            return {}
    
    def process_player_for_mystery_card(self, player_row: pd.Series, 
                                       difficulty: str = "medium",
                                       team_info: Dict = None,
                                       season: int = 2023) -> Dict:
        """
        Process a player's stats into mystery card format.
        
        Args:
            player_row (pd.Series): Player's season statistics
            difficulty (str): Card difficulty level
            team_info (Dict): Team context information
            
        Returns:
            Dict: Processed stats ready for card creation
        """
        
        # Get the relevant stats for this difficulty
        relevant_stats = self.stat_mappings.get(difficulty, self.stat_mappings["medium"])
        
        # Extract basic info
        player_name = player_row.get('Player', 'Unknown Player')
        team_name = player_row.get('Team', 'Unknown Team')
        
        # Create mystery card stats dictionary
        mystery_stats = {}
        
        # Map available stats to mystery card format
        stat_mapping = {
            'PTS': 'pointsScored',
            'REB': 'totalRebounds',
            'AST': 'assists', 
            'PIR': 'pir',
            'STL': 'steals',
            'BLK': 'blocks',
            'MIN': 'minutesPlayed',
            '3P%': 'threePointersPercentage',
            'FG%': 'fieldGoalPercentage',  # This might need to be calculated
            'FT%': 'freeThrowsPercentage',
            'TOV': 'turnovers',
            'PF': 'foulsCommited',
            'Games': 'gamesPlayed',
            'OREB': 'offensiveRebounds',
            'DREB': 'defensiveRebounds',
            '3PM': 'threePointersMade',
            '2P%': 'twoPointersPercentage'
        }
        
        # Extract stats that are available
        for stat_key in relevant_stats:
            api_column = stat_mapping.get(stat_key)
            if api_column and api_column in player_row:
                value = player_row[api_column]
                if pd.notna(value):
                    # Handle percentage values (remove % sign)
                    if isinstance(value, str) and '%' in value:
                        try:
                            mystery_stats[stat_key] = float(value.replace('%', ''))
                        except ValueError:
                            mystery_stats[stat_key] = 0.0
                    else:
                        mystery_stats[stat_key] = float(value)
        
        # Calculate derived stats if needed
        if 'AST/TO' in relevant_stats and 'assists' in player_row and 'turnovers' in player_row:
            assists = player_row['assists']
            turnovers = player_row['turnovers']
            if pd.notna(assists) and pd.notna(turnovers) and turnovers > 0:
                mystery_stats['AST/TO'] = round(assists / turnovers, 2)
        
        # Add context information
        context_info = {
            'player_name': player_row.get('player.name', 'Unknown Player'),
            'team': player_row.get('player.team.name', 'Unknown Team'),
            'season': f"{player_row.get('Season', season)}-{player_row.get('Season', season) + 1}",
            'games_played': player_row.get('gamesPlayed', 0),
            'difficulty': difficulty
        }
        
        # Add team context if available
        if team_info and team_name in team_info:
            context_info['team_success'] = "Playoff Team" if team_info[team_name]['playoff_team'] else "Regular Season"
            context_info['team_wins'] = team_info[team_name]['wins']
        
        return {
            'stats': mystery_stats,
            'context': context_info,
            'hints': self._generate_hints(player_row, context_info, difficulty)
        }
    
    def _generate_hints(self, player_row: pd.Series, context: Dict, difficulty: str) -> List[str]:
        """Generate hints for the mystery player based on difficulty."""
        hints = []
        
        # Basic hints based on difficulty
        if difficulty == "easy":
            hints.append(f"Plays for {context['team']}")
            hints.append(f"Season: {context['season']}")
            if context.get('team_success'):
                hints.append(context['team_success'])
        
        elif difficulty == "medium":
            # More cryptic hints
            if context.get('team_success') == "Playoff Team":
                hints.append("Competes in postseason")
            hints.append(f"Appeared in {context.get('games_played', 0)} games")
            
        elif difficulty == "hard":
            # Very subtle hints
            hints.append("European professional player")
            if context.get('games_played', 0) > 30:
                hints.append("Regular contributor")
        
        # Position-based hints if we can determine position
        position = self._guess_position(player_row)
        if position and difficulty != "hard":
            hints.append(f"Plays {position} position")
        
        return hints
    
    def _guess_position(self, player_row: pd.Series) -> Optional[str]:
        """Guess player position based on stats."""
        assists = player_row.get('assists', 0)
        rebounds = player_row.get('totalRebounds', 0)
        blocks = player_row.get('blocks', 0)
        
        if pd.notna(assists) and assists > 4:
            return "Guard"
        elif pd.notna(blocks) and blocks > 1:
            return "Center"
        elif pd.notna(rebounds) and rebounds > 6:
            return "Forward/Center"
        elif pd.notna(rebounds) and rebounds > 3:
            return "Forward"
        else:
            return "Guard/Forward"
    
    def get_mystery_players(self, season: int, count: int = 10, 
                           difficulty: str = "medium",
                           min_games: int = 15) -> List[Dict]:
        """
        Get a list of players suitable for mystery cards.
        
        Args:
            season (int): Season year
            count (int): Number of players to return
            difficulty (str): Difficulty level
            min_games (int): Minimum games played filter
            
        Returns:
            List[Dict]: List of processed player data for mystery cards
        """
        
        # Fetch player stats and team info
        df = self.get_season_stats(season)
        team_info = self.get_team_info(season)
        
        if df.empty:
            print("❌ No player data available")
            return []
        
        # Filter players by minimum games
        if 'gamesPlayed' in df.columns:
            df = df[df['gamesPlayed'] >= min_games]
        
        # Remove players with too few stats
        df = df.dropna(subset=['pointsScored', 'totalRebounds', 'assists'], how='any')
        
        if len(df) == 0:
            print("❌ No players meet the filtering criteria")
            return []
        
        # Sample random players
        sample_size = min(count, len(df))
        sampled_players = df.sample(n=sample_size)
        
        mystery_players = []
        for _, player_row in sampled_players.iterrows():
            mystery_data = self.process_player_for_mystery_card(
                player_row, difficulty, team_info, season
            )
            mystery_players.append(mystery_data)
        
        print(f"✅ Generated {len(mystery_players)} mystery player cards")
        return mystery_players
    
    def save_mystery_cards_data(self, mystery_players: List[Dict], 
                               filename: str = "mystery_players_data.json"):
        """Save mystery player data to JSON file."""
        try:
            os.makedirs("mystery_cards_data", exist_ok=True)
            filepath = os.path.join("mystery_cards_data", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(mystery_players, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Mystery player data saved to {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving mystery data: {e}")
            return None
    
    def get_star_players(self, season: int, min_pir: float = 15.0) -> List[Dict]:
        """Get star players based on PIR (Performance Index Rating)."""
        df = self.get_season_stats(season)
        team_info = self.get_team_info(season)
        
        if df.empty:
            return []
        
        # Filter for star players
        if 'pir' in df.columns:
            star_df = df[df['pir'] >= min_pir]
        else:
            # Fallback to points if PIR not available
            star_df = df[df['pointsScored'] >= 15.0] if 'pointsScored' in df.columns else df
        
        star_players = []
        for _, player_row in star_df.iterrows():
            mystery_data = self.process_player_for_mystery_card(
                player_row, "easy", team_info, season  # Stars get easy difficulty
            )
            star_players.append(mystery_data)
        
        return star_players[:20]  # Top 20 stars


def main():
    """Example usage of the EuroLeague Data Fetcher."""
    
    print("🏀 EuroLeague Mystery Player Card Data Fetcher")
    print("=" * 50)
    
    # Initialize the fetcher
    fetcher = EuroLeagueDataFetcher()
    
    # Example: Get mystery players for 2023-24 season
    season = 2023
    print(f"\n📊 Fetching data for {season}-{season+1} season...")
    
    # Get different difficulty levels
    difficulties = ["easy", "medium", "hard"]
    
    all_mystery_players = []
    
    for difficulty in difficulties:
        print(f"\n🎯 Generating {difficulty} difficulty cards...")
        mystery_players = fetcher.get_mystery_players(
            season=season,
            count=5,  # 5 players per difficulty
            difficulty=difficulty,
            min_games=20
        )
        
        # Add difficulty tag to each player
        for player in mystery_players:
            player['context']['difficulty'] = difficulty
        
        all_mystery_players.extend(mystery_players)
    
    if all_mystery_players:
        # Save to file
        filename = f"mystery_players_{season}_{season+1}.json"
        fetcher.save_mystery_cards_data(all_mystery_players, filename)
        
        # Print sample data
        print(f"\n📋 Sample Mystery Player Card Data:")
        sample_player = all_mystery_players[0]
        print(f"Player: {sample_player['context']['player_name']}")
        print(f"Team: {sample_player['context']['team']}")
        print(f"Difficulty: {sample_player['context']['difficulty']}")
        print(f"Stats: {sample_player['stats']}")
        print(f"Hints: {sample_player['hints']}")
        
        # Get star players too
        print(f"\n⭐ Fetching star players...")
        star_players = fetcher.get_star_players(season)
        if star_players:
            fetcher.save_mystery_cards_data(star_players, f"star_players_{season}_{season+1}.json")
            print(f"✅ Saved {len(star_players)} star player cards")
    
    print(f"\n🎉 Data fetching complete! Ready to create mystery cards.")


if __name__ == "__main__":
    main()