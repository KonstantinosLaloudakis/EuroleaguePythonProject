"""
Demo script for EuroLeague Mystery Player Cards

This script demonstrates how to use the system to:
1. Fetch real EuroLeague player data
2. Create mystery cards with different difficulty levels
3. Show examples of the guessing game
"""

import json
import random
from euroleague_data_fetcher import EuroLeagueDataFetcher
from createMysteryCards import create_mystery_card


def demo_data_fetching():
    """Demonstrate fetching EuroLeague data."""
    
    print("🏀 EuroLeague Mystery Cards - Data Fetching Demo")
    print("=" * 60)
    
    # Initialize the data fetcher
    fetcher = EuroLeagueDataFetcher()
    
    # Fetch some player data
    print("\n📊 Fetching 2023-24 season data...")
    season_stats = fetcher.get_season_stats(2023)
    
    if not season_stats.empty:
        print(f"✅ Found {len(season_stats)} player records")
        
        # Show some top performers
        top_scorers = season_stats.nlargest(5, 'pointsScored')
        print(f"\n🔥 Top 5 Scorers:")
        for i, (_, player) in enumerate(top_scorers.iterrows(), 1):
            name = player.get('player.name', 'Unknown')
            team = player.get('player.team.name', 'Unknown')
            points = player.get('pointsScored', 0)
            print(f"   {i}. {name} ({team}) - {points:.1f} PPG")
            
        # Show top PIR performers
        top_pir = season_stats.nlargest(5, 'pir')
        print(f"\n⭐ Top 5 PIR (Performance Index Rating):")
        for i, (_, player) in enumerate(top_pir.iterrows(), 1):
            name = player.get('player.name', 'Unknown')
            team = player.get('player.team.name', 'Unknown')
            pir = player.get('pir', 0)
            print(f"   {i}. {name} ({team}) - {pir:.1f} PIR")


def demo_mystery_card_creation():
    """Demonstrate creating mystery cards."""
    
    print("\n\n🎯 Mystery Card Creation Demo")
    print("=" * 60)
    
    # Get some mystery players
    fetcher = EuroLeagueDataFetcher()
    
    print("\n🔍 Creating sample mystery cards...")
    
    # Create one card for each difficulty
    difficulties = ["easy", "medium", "hard"]
    sample_cards = []
    
    for difficulty in difficulties:
        print(f"\n📋 Creating {difficulty.upper()} difficulty card...")
        
        mystery_players = fetcher.get_mystery_players(
            season=2023,
            count=1,
            difficulty=difficulty,
            min_games=15
        )
        
        if mystery_players:
            player_data = mystery_players[0]
            
            # Create the mystery card (question)
            question_path = f"demo_cards/{difficulty}_mystery.png"
            create_mystery_card(
                mystery_data=player_data,
                output_path=question_path,
                show_answer=False
            )
            
            # Create the answer card
            answer_path = f"demo_cards/{difficulty}_answer.png"
            create_mystery_card(
                mystery_data=player_data,
                output_path=answer_path,
                show_answer=True
            )
            
            sample_cards.append({
                'difficulty': difficulty,
                'player': player_data['context']['player_name'],
                'stats': player_data['stats'],
                'hints': player_data['hints'],
                'question_card': question_path,
                'answer_card': answer_path
            })
            
            print(f"✅ Created {difficulty} cards for {player_data['context']['player_name']}")
    
    return sample_cards


def demo_guessing_game(sample_cards):
    """Demonstrate the guessing game interaction."""
    
    print("\n\n🎮 Mystery Player Guessing Game Demo")
    print("=" * 60)
    
    for card in sample_cards:
        print(f"\n🃏 {card['difficulty'].upper()} DIFFICULTY CARD")
        print("-" * 40)
        
        print("📊 Player Statistics:")
        for stat, value in card['stats'].items():
            print(f"   {stat}: {value}")
        
        print("\n💡 Hints:")
        for i, hint in enumerate(card['hints'], 1):
            print(f"   {i}. {hint}")
        
        print(f"\n❓ Who is this mystery player?")
        print(f"💭 Think about it...")
        print(f"🎯 Answer: {card['player']}")
        
        input("\nPress Enter to continue to next card...")


def show_stat_explanations():
    """Show what different stats mean for the guessing game."""
    
    print("\n\n📚 Statistics Guide for Mystery Cards")
    print("=" * 60)
    
    stat_explanations = {
        "Easy Cards": {
            "PTS": "Points per game - How much they score",
            "REB": "Rebounds per game - How many rebounds they grab",
            "AST": "Assists per game - How many assists they make",
            "PIR": "Performance Index Rating - EuroLeague's overall rating",
            "MIN": "Minutes per game - How much they play",
            "3P%": "Three-point percentage - How good they shoot from 3"
        },
        "Medium Cards": {
            "PIR": "Performance Index Rating - Overall impact metric",
            "eFG%": "Effective Field Goal % - Shooting efficiency",
            "STL": "Steals per game - Defensive pressure",
            "TOV": "Turnovers per game - Ball handling mistakes",
            "AST/TO": "Assist to Turnover ratio - Decision making"
        },
        "Hard Cards": {
            "USG%": "Usage percentage - How much offense runs through them",
            "TS%": "True Shooting % - Most accurate shooting metric",
            "BLK%": "Block percentage - Rim protection rate",
            "AST%": "Assist percentage - Playmaking when on court",
            "OREB%": "Offensive rebound percentage - Getting offensive boards"
        }
    }
    
    for difficulty, stats in stat_explanations.items():
        print(f"\n🎯 {difficulty}:")
        for stat, explanation in stats.items():
            print(f"   {stat:8} - {explanation}")


def main():
    """Run the complete demo."""
    
    print("🚀 EuroLeague Mystery Player Cards - Complete Demo")
    print("🏀 Create mystery cards using real EuroLeague data!")
    
    try:
        # 1. Show data fetching capabilities
        demo_data_fetching()
        
        # 2. Create sample mystery cards
        sample_cards = demo_mystery_card_creation()
        
        # 3. Show statistics explanations
        show_stat_explanations()
        
        # 4. Demo the guessing game
        if sample_cards:
            demo_guessing_game(sample_cards)
        
        print(f"\n🎉 Demo Complete!")
        print(f"📁 Sample cards saved in: demo_cards/")
        print(f"🔍 Check out the generated PNG files to see your mystery cards!")
        
        print(f"\n💡 Next Steps:")
        print(f"   • Use createMysteryCards.py to generate full card sets")
        print(f"   • Customize difficulty levels and stat combinations")
        print(f"   • Create themed card sets (guards only, big men, etc.)")
        print(f"   • Add team logos and player images for full cards")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        print("Make sure you're in the virtual environment with all dependencies installed")


if __name__ == "__main__":
    main()