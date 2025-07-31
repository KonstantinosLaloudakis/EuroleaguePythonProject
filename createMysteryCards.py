"""
Enhanced Mystery Player Card Creator

Integrates with euroleague_data_fetcher.py to create mystery player cards
using real EuroLeague API data.
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import math
import json
import random
from typing import Dict, List, Optional
from euroleague_data_fetcher import EuroLeagueDataFetcher

# Constants for better maintainability
CARD_WIDTH = 400
CARD_HEIGHT = 600
POSITION_BOX_SIZE = (80, 60)
LOGO_SIZE = 60
PLAYER_IMG_HEIGHT_RATIO = 0.55
PLAYER_IMG_WIDTH_RATIO = 0.85
GLOW_SIZE = 10
CORNER_SIZE = 30

# Color constants
GOLD_GRADIENT_START = (255, 215, 0)
GOLD_GRADIENT_END = (184, 134, 139)
BORDER_COLORS = [(139, 69, 19), (160, 82, 45), (205, 133, 63)]
CORNER_COLOR = (255, 215, 0, 100)

# Mystery card colors based on difficulty
DIFFICULTY_COLORS = {
    "easy": {
        "gradient_start": (144, 238, 144),  # Light green
        "gradient_end": (34, 139, 34),      # Forest green
        "border": [(60, 179, 113), (46, 125, 50), (27, 94, 32)]
    },
    "medium": {
        "gradient_start": (255, 215, 0),    # Gold (original)
        "gradient_end": (184, 134, 139),    # Original
        "border": [(139, 69, 19), (160, 82, 45), (205, 133, 63)]
    },
    "hard": {
        "gradient_start": (220, 20, 60),    # Crimson
        "gradient_end": (139, 0, 0),        # Dark red
        "border": [(128, 0, 0), (165, 42, 42), (178, 34, 34)]
    }
}


def load_fonts():
    """Load fonts with proper fallback handling."""
    font_paths = [
        # Windows
        ("arial.ttf", "arialbd.ttf"),
        # Linux
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        # macOS
        ("/System/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Arial Bold.ttf"),
        # Additional Linux paths
        ("/usr/share/fonts/TTF/arial.ttf", "/usr/share/fonts/TTF/arialbd.ttf"),
    ]
    
    for regular_path, bold_path in font_paths:
        try:
            return {
                'position': ImageFont.truetype(bold_path, 22),
                'name': ImageFont.truetype(bold_path, 28),
                'stats_label': ImageFont.truetype(regular_path, 16),
                'stats_value': ImageFont.truetype(bold_path, 26),
                'mystery_title': ImageFont.truetype(bold_path, 32),
                'hint': ImageFont.truetype(regular_path, 14)
            }
        except (OSError, IOError):
            continue
    
    # Final fallback to default fonts
    print("Warning: Could not load custom fonts, using default fonts")
    default_font = ImageFont.load_default()
    return {
        'position': default_font,
        'name': default_font,
        'stats_label': default_font,
        'stats_value': default_font,
        'mystery_title': default_font,
        'hint': default_font
    }


def create_mystery_card(
        mystery_data: Dict,
        output_path: str,
        show_answer: bool = False,
        generic_logo_path: str = "euroleague_logo.png"
):
    """
    Create a mystery player card from EuroLeague API data.
    
    Args:
        mystery_data (Dict): Processed player data from euroleague_data_fetcher
        output_path (str): Where to save the generated card
        show_answer (bool): Whether to reveal the player name
        generic_logo_path (str): Path to generic EuroLeague logo
    """
    
    stats = mystery_data['stats']
    context = mystery_data['context']
    hints = mystery_data['hints']
    difficulty = context.get('difficulty', 'medium')
    
    # Card dimensions
    width, height = CARD_WIDTH, CARD_HEIGHT

    # Create card with gradient background
    card = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Get difficulty colors
    colors = DIFFICULTY_COLORS.get(difficulty, DIFFICULTY_COLORS['medium'])
    
    # Create gradient background based on difficulty
    gradient_start = colors['gradient_start']
    gradient_end = colors['gradient_end']
    
    for y in range(height):
        ratio = y / height
        r = int(gradient_start[0] + (gradient_end[0] - gradient_start[0]) * ratio)
        g = int(gradient_start[1] + (gradient_end[1] - gradient_start[1]) * ratio)
        b = int(gradient_start[2] + (gradient_end[2] - gradient_start[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Add metallic shine effect
    shine_overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    shine_draw = ImageDraw.Draw(shine_overlay)

    # Diagonal shine lines
    for i in range(0, width + height, 20):
        shine_draw.line([(i, 0), (i - height, height)], fill=(255, 255, 255, 15), width=2)

    card = Image.alpha_composite(card, shine_overlay)

    # Add difficulty-specific patterns
    pattern_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    pattern_draw = ImageDraw.Draw(pattern_overlay)

    if difficulty == "easy":
        # Circle patterns for easy
        for i in range(0, width, 60):
            for j in range(0, height, 60):
                pattern_draw.ellipse([i+20, j+20, i+30, j+30], fill=(255, 255, 255, 12))
    elif difficulty == "hard":
        # Triangle patterns for hard
        for i in range(0, width, 50):
            for j in range(0, height, 50):
                triangle_points = [(i+25, j+10), (i+35, j+30), (i+15, j+30)]
                pattern_draw.polygon(triangle_points, fill=(255, 255, 255, 10))
    else:
        # Default diamond patterns for medium
        for i in range(0, width, 40):
            for j in range(0, height, 40):
                diamond_points = [
                    (i + 20, j + 10), (i + 30, j + 20),
                    (i + 20, j + 30), (i + 10, j + 20)
                ]
                pattern_draw.polygon(diamond_points, fill=(255, 255, 255, 8))

    card = Image.alpha_composite(card, pattern_overlay)
    draw = ImageDraw.Draw(card)

    # Draw card outline with difficulty-specific borders
    border_colors = colors['border']
    for i, color in enumerate(border_colors):
        thickness = 3 - i
        draw.rectangle(
            [(i, i), (width - 1 - i, height - 1 - i)],
            outline=color,
            width=thickness
        )

    # Load fonts
    try:
        fonts = load_fonts()
        font_position = fonts['position']
        font_name = fonts['name']
        font_stats_label = fonts['stats_label']
        font_stats_value = fonts['stats_value']
        font_mystery_title = fonts['mystery_title']
        font_hint = fonts['hint']
    except:
        print("Error loading fonts. Using default fonts.")
        default_font = ImageFont.load_default()
        font_position = default_font
        font_name = default_font
        font_stats_label = default_font
        font_stats_value = default_font
        font_mystery_title = default_font
        font_hint = default_font

    # Difficulty badge (top-left)
    difficulty_text = f"{difficulty.upper()}"
    diff_bbox = draw.textbbox((0, 0), difficulty_text, font=font_position)
    diff_width = diff_bbox[2] - diff_bbox[0]
    
    # Create difficulty badge
    badge_width = max(diff_width + 20, 90)
    badge_height = 35
    badge_x, badge_y = 15, 15
    
    # Badge background
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
        radius=8,
        fill=(0, 0, 0, 180),
        outline=border_colors[0],
        width=2
    )
    
    # Badge text
    text_x = badge_x + (badge_width - diff_width) // 2
    text_y = badge_y + 8
    draw.text((text_x, text_y), difficulty_text, font=font_position, fill="white")

    # Season info (top-right)
    season_text = context.get('season', '2023-24')
    draw.text((width - 80, 20), season_text, font=font_stats_label, fill=(255, 255, 255))

    # Generic EuroLeague logo (top-right)
    try:
        if os.path.exists(generic_logo_path):
            logo = Image.open(generic_logo_path).convert("RGBA")
            logo = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            card.paste(logo, (width - 90, 50), logo)
        else:
            # Draw a placeholder circle if no logo
            draw.ellipse([width - 90, 50, width - 30, 110], 
                        outline=(255, 255, 255), width=2)
            draw.text((width - 75, 70), "EL", font=font_name, fill=(255, 255, 255))
    except Exception as e:
        print(f"Could not load logo: {e}")

    # Mystery player silhouette or question mark (center area)
    silhouette_y = 130
    silhouette_height = int(height * 0.4)  # 40% of card height
    
    # Create a question mark or silhouette placeholder
    if not show_answer:
        # Draw large question mark
        question_mark = "?"
        
        # Calculate size for question mark
        temp_font_size = 120
        try:
            question_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", temp_font_size)
        except:
            question_font = font_mystery_title
        
        q_bbox = draw.textbbox((0, 0), question_mark, font=question_font)
        q_width = q_bbox[2] - q_bbox[0]
        q_height = q_bbox[3] - q_bbox[1]
        
        q_x = (width - q_width) // 2
        q_y = silhouette_y + (silhouette_height - q_height) // 2
        
        # Draw question mark with glow effect
        for offset in range(3, 0, -1):
            draw.text((q_x + offset, q_y + offset), question_mark, 
                     font=question_font, fill=(0, 0, 0, 100))
        
        draw.text((q_x, q_y), question_mark, font=question_font, fill=(255, 255, 255))
    
    # Player name area
    name_y = silhouette_y + silhouette_height + 20
    
    if show_answer:
        player_name = context['player_name']
        team_name = context['team']
        
        # Draw player name
        name_bbox = draw.textbbox((0, 0), player_name, font=font_name)
        name_width = name_bbox[2] - name_bbox[0]
        
        draw_outlined_text(
            draw,
            (width // 2 - name_width // 2, name_y),
            player_name,
            font_name,
            fill_color=(255, 255, 255),
            outline_color=(34, 34, 34),
            shadow_color=(0, 0, 0, 120)
        )
        
        # Draw team name
        team_bbox = draw.textbbox((0, 0), team_name, font=font_stats_label)
        team_width = team_bbox[2] - team_bbox[0]
        draw.text((width // 2 - team_width // 2, name_y + 35), 
                 team_name, font=font_stats_label, fill=(220, 220, 220))
        
        stats_start_y = name_y + 70
    else:
        # Mystery player text
        mystery_text = "MYSTERY PLAYER"
        mystery_bbox = draw.textbbox((0, 0), mystery_text, font=font_name)
        mystery_width = mystery_bbox[2] - mystery_bbox[0]
        
        draw_outlined_text(
            draw,
            (width // 2 - mystery_width // 2, name_y),
            mystery_text,
            font_name,
            fill_color=(255, 255, 255),
            outline_color=(34, 34, 34),
            shadow_color=(0, 0, 0, 120)
        )
        
        stats_start_y = name_y + 50

    # Stats section
    left_col_x = 60
    right_col_x = 240
    stat_y = stats_start_y
    stat_spacing = 25

    stat_keys = list(stats.keys())
    for i, stat_key in enumerate(stat_keys[:6]):  # Display up to 6 stats
        if i < 3:
            x = left_col_x
            y = stat_y + (i * stat_spacing)
        else:
            x = right_col_x
            y = stat_y + ((i - 3) * stat_spacing)

        # Format stat value
        stat_value = str(stats[stat_key])
        if '.' in stat_value:
            try:
                stat_value = f"{float(stat_value):.1f}"
            except ValueError:
                pass

        # Draw stat value with shadow
        draw.text((x + 1, y + 1), stat_value, font=font_stats_value, fill=(0, 0, 0, 150))
        draw.text((x, y), stat_value, font=font_stats_value, fill=(255, 255, 255))

        # Draw stat label
        value_bbox = draw.textbbox((0, 0), stat_value, font=font_stats_value)
        value_width = value_bbox[2] - value_bbox[0]
        
        label_x = x + value_width + 10
        draw.text((label_x + 1, y + 1), stat_key, font=font_stats_label, fill=(0, 0, 0, 100))
        draw.text((label_x, y), stat_key, font=font_stats_label, fill=(220, 220, 220))

    # Hints section (bottom)
    if hints and not show_answer:
        hints_y = height - 80
        hints_title = "HINTS:"
        draw.text((20, hints_y - 20), hints_title, font=font_stats_label, fill=(255, 255, 255))
        
        for i, hint in enumerate(hints[:3]):  # Show up to 3 hints
            hint_y = hints_y + (i * 18)
            draw.text((25, hint_y), f"• {hint}", font=font_hint, fill=(200, 200, 200))

    # Add corner decorations
    corner_size = CORNER_SIZE
    corner_color = CORNER_COLOR

    # Top corners
    draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=corner_color)
    draw.polygon([(width, 0), (width - corner_size, 0), (width, corner_size)], fill=corner_color)

    # Bottom corners
    draw.polygon([(0, height), (corner_size, height), (0, height - corner_size)], fill=corner_color)
    draw.polygon([(width, height), (width - corner_size, height), (width, height - corner_size)], fill=corner_color)

    # Convert to RGB for saving
    final_card = Image.new('RGB', (width, height), (255, 255, 255))
    final_card.paste(card, (0, 0), card)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_card.save(output_path)
    print(f"✅ Mystery card saved: {output_path}")


def draw_outlined_text(draw, pos, text, font, fill_color, outline_color, shadow_color):
    """Draw text with outline and shadow effects."""
    x, y = pos
    # Draw shadow first (offset)
    draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)

    # Draw outline (multiple directions)
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_color)


def create_mystery_card_set(season: int = 2023, count_per_difficulty: int = 5):
    """
    Create a complete set of mystery cards from EuroLeague data.
    
    Args:
        season (int): Season year (e.g., 2023 for 2023-24)
        count_per_difficulty (int): Number of cards per difficulty level
    """
    
    print(f"🏀 Creating Mystery Card Set for {season}-{season+1} Season")
    print("=" * 60)
    
    # Initialize data fetcher
    fetcher = EuroLeagueDataFetcher()
    
    difficulties = ["easy", "medium", "hard"]
    all_cards_created = []
    
    # Create output directories
    os.makedirs("mystery_cards/questions", exist_ok=True)
    os.makedirs("mystery_cards/answers", exist_ok=True)
    
    for difficulty in difficulties:
        print(f"\n🎯 Creating {difficulty.upper()} difficulty cards...")
        
        # Get mystery players for this difficulty
        mystery_players = fetcher.get_mystery_players(
            season=season,
            count=count_per_difficulty,
            difficulty=difficulty,
            min_games=20
        )
        
        for i, player_data in enumerate(mystery_players):
            player_name = player_data['context']['player_name']
            # Clean filename
            safe_name = "".join(c for c in player_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            
            # Create question card (mystery)
            question_path = f"mystery_cards/questions/{difficulty}_{i+1}_{safe_name}_mystery.png"
            create_mystery_card(
                mystery_data=player_data,
                output_path=question_path,
                show_answer=False
            )
            
            # Create answer card (revealed)
            answer_path = f"mystery_cards/answers/{difficulty}_{i+1}_{safe_name}_answer.png"
            create_mystery_card(
                mystery_data=player_data,
                output_path=answer_path,
                show_answer=True
            )
            
            all_cards_created.append({
                'player': player_name,
                'difficulty': difficulty,
                'question_card': question_path,
                'answer_card': answer_path,
                'stats': player_data['stats'],
                'hints': player_data['hints']
            })
    
    # Save card index
    with open("mystery_cards/card_index.json", 'w', encoding='utf-8') as f:
        json.dump(all_cards_created, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Created {len(all_cards_created)} mystery card pairs!")
    print(f"📁 Question cards saved in: mystery_cards/questions/")
    print(f"📁 Answer cards saved in: mystery_cards/answers/")
    print(f"📋 Card index saved in: mystery_cards/card_index.json")
    
    return all_cards_created


def main():
    """Create mystery cards using real EuroLeague data."""
    
    try:
        # Create mystery card set
        card_set = create_mystery_card_set(
            season=2023,
            count_per_difficulty=3  # 3 cards per difficulty = 9 total cards
        )
        
        if card_set:
            print(f"\n📊 Summary:")
            for difficulty in ["easy", "medium", "hard"]:
                count = len([c for c in card_set if c['difficulty'] == difficulty])
                print(f"   {difficulty.capitalize()}: {count} cards")
        
    except Exception as e:
        print(f"❌ Error creating mystery cards: {e}")
        print("Make sure you have activated the virtual environment with euroleague-api installed")


if __name__ == "__main__":
    main()