# 🏀 EuroLeague Mystery Player Cards

Create FIFA-style mystery player cards using real EuroLeague basketball statistics for an engaging guessing game!

## 🌟 Features

- **Real EuroLeague Data**: Fetches current player statistics using the official EuroLeague API
- **Multiple Difficulty Levels**: Easy, Medium, and Hard cards with different stat combinations
- **Beautiful Card Design**: FIFA-style cards with difficulty-based color schemes
- **Comprehensive Statistics**: PIR, scoring, rebounding, assists, shooting percentages, and advanced metrics
- **Mystery Game Ready**: Question cards (hidden player) and answer cards (revealed player)
- **Season Context**: Cards include season information and team performance hints

## 🎯 Card Difficulty Levels

### 🟢 Easy Cards
- **Stats**: Points, Rebounds, Assists, PIR, Minutes, 3P%
- **Hints**: Team name, season, position, playoff status
- **Color**: Green gradient
- **Target**: Casual basketball fans

### 🟡 Medium Cards  
- **Stats**: PIR, Effective FG%, Rebounds, Steals, Turnovers, Assist/TO ratio
- **Hints**: Playoff status, games played, position
- **Color**: Gold gradient (classic)
- **Target**: Basketball enthusiasts

### 🔴 Hard Cards
- **Stats**: Usage%, True Shooting%, Block%, Assist%, Offensive Rebound%
- **Hints**: Minimal (European player, contributor status)
- **Color**: Red gradient
- **Target**: Basketball analytics experts

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Virtual environment (recommended)

### Installation

1. **Clone or download the project files**

2. **Set up virtual environment**:
```bash
python3 -m venv euroleague_env
source euroleague_env/bin/activate  # On Windows: euroleague_env\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install euroleague-api pandas Pillow
```

### 🎮 Basic Usage

#### Create Mystery Card Set
```python
# Generate 3 cards per difficulty (9 total cards)
python createMysteryCards.py
```

This creates:
- `mystery_cards/questions/` - Mystery cards for guessing
- `mystery_cards/answers/` - Answer cards with player names
- `mystery_cards/card_index.json` - Complete card metadata

#### Run Interactive Demo
```python
# See the system in action with sample data
python demo_mystery_cards.py
```

#### Fetch Custom Player Data
```python
from euroleague_data_fetcher import EuroLeagueDataFetcher

fetcher = EuroLeagueDataFetcher()

# Get star players (PIR > 15.0)
star_players = fetcher.get_star_players(season=2023, min_pir=15.0)

# Get custom mystery players
mystery_players = fetcher.get_mystery_players(
    season=2023,
    count=5,
    difficulty="medium",
    min_games=20
)
```

## 📊 Available Statistics

### Traditional Stats
- **PTS**: Points per game
- **REB**: Total rebounds per game  
- **AST**: Assists per game
- **STL**: Steals per game
- **BLK**: Blocks per game
- **MIN**: Minutes per game
- **TOV**: Turnovers per game

### Shooting Stats
- **3P%**: Three-point field goal percentage
- **FT%**: Free throw percentage
- **2P%**: Two-point field goal percentage

### Advanced Stats
- **PIR**: Performance Index Rating (EuroLeague's signature metric)
- **AST/TO**: Assist-to-turnover ratio
- **Usage%**: Percentage of team possessions used
- **TS%**: True shooting percentage
- **eFG%**: Effective field goal percentage

## 🎨 Customization Options

### Create Position-Specific Cards
```python
# Point guard focus
pg_stats = ["AST", "AST/TO", "STL", "3P%", "PIR", "MIN"]

# Center focus  
center_stats = ["REB", "BLK", "FG%", "OREB", "PF", "MIN"]
```

### Custom Difficulty Levels
```python
# Create your own stat combinations
custom_stats = {
    "rookie_challenge": ["PTS", "MIN", "Age", "Games", "PIR", "Team_Success"],
    "veteran_master": ["AST/TO", "TS%", "OREB%", "DEF_RTG", "USG%", "BLK%"]
}
```

### Season Selection
```python
# Different seasons available
seasons = [2023, 2022, 2021, 2020, 2019]  # 2023 = 2023-24 season

for season in seasons:
    cards = create_mystery_card_set(season=season)
```

## 📁 Project Structure

```
├── euroleague_data_fetcher.py    # API data fetching and processing
├── createMysteryCards.py         # Enhanced card creation with mystery features  
├── createCards.py               # Original FIFA-style card creator
├── demo_mystery_cards.py        # Interactive demonstration
├── test_euroleague_api.py       # API testing utilities
├── mystery_cards/               # Generated mystery cards
│   ├── questions/              # Mystery cards (player hidden)
│   ├── answers/               # Answer cards (player revealed)  
│   └── card_index.json        # Card metadata and stats
└── mystery_cards_data/         # Raw player data (JSON)
```

## 🎲 Game Ideas

### Individual Challenge
1. Show mystery card
2. Analyze stats and hints
3. Guess the player
4. Reveal answer card

### Group Competition
- **Speed Round**: First to guess correctly wins
- **Elimination**: Wrong guess = out
- **Point System**: Harder difficulties = more points
- **Team Battle**: Guards vs Forwards vs Centers

### Educational Use
- **Stat Learning**: Understand what different metrics mean
- **Player Recognition**: Learn EuroLeague players and teams  
- **Basketball Analytics**: Appreciate advanced statistics
- **European Basketball**: Explore EuroLeague history and current players

## 🔧 Advanced Configuration

### Custom Card Appearance
```python
# Modify colors in createMysteryCards.py
DIFFICULTY_COLORS = {
    "custom": {
        "gradient_start": (255, 165, 0),  # Orange
        "gradient_end": (255, 69, 0),     # Red-orange
        "border": [(255, 140, 0), (255, 69, 0), (139, 69, 19)]
    }
}
```

### Add Team Logos
```python
# Place team logo files in a logos/ directory
create_mystery_card(
    mystery_data=player_data,
    output_path="custom_card.png",
    generic_logo_path="logos/real_madrid.png"
)
```

### Filter by Team or League Performance
```python
# Only playoff teams
playoff_players = fetcher.get_mystery_players(
    season=2023,
    team_filter="playoff_teams"
)

# Championship teams only
champions = fetcher.get_mystery_players(
    season=2023, 
    team_filter="final_four"
)
```

## 🐛 Troubleshooting

### Common Issues

**Font warnings**: Default fonts will be used if custom fonts aren't found. Cards will still generate successfully.

**API errors**: Check internet connection. The EuroLeague API occasionally has maintenance periods.

**Empty datasets**: Some seasons or stat categories may have limited data. Try different parameters.

### Error Solutions

```bash
# If PIL/Pillow issues
pip install --upgrade Pillow

# If pandas issues  
pip install --upgrade pandas

# If API connection issues
pip install --upgrade euroleague-api requests
```

## 📈 Future Enhancements

- [ ] Player photos integration
- [ ] Team logo automatic fetching
- [ ] Multi-language support
- [ ] Web interface for card generation
- [ ] Historical season comparisons
- [ ] EuroCup league support
- [ ] Mobile-responsive card designs
- [ ] Interactive online guessing game

## 🤝 Contributing

Feel free to enhance the project by:
- Adding new stat combinations
- Improving card designs
- Adding more difficulty levels
- Creating themed card sets
- Optimizing API calls
- Adding new game modes

## 📜 License

This project uses the EuroLeague API for educational and entertainment purposes. Please respect EuroLeague's terms of service when using their data.

## 🙏 Credits

- **EuroLeague API**: [euroleague-api](https://github.com/giasemidis/euroleague_api) by Georgios Giasemidis
- **Card Design**: Inspired by FIFA Ultimate Team cards
- **Basketball Statistics**: Official EuroLeague Basketball data

---

**🏀 Start creating your mystery player cards and challenge your basketball knowledge today!**
 
