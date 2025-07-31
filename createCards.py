from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import math


def create_fifa_style_card(
        player_name,
        stats,
        image_path,
        logo_path,
        output_path,
        position="PG"  # Point Guard, SG, SF, PF, C
):
    # Card dimensions (portrait orientation like FIFA)
    width, height = 400, 600

    # Create card with gradient background
    card = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))

    # Create golden gradient background
    draw = ImageDraw.Draw(card)

    # Create gold gradient effect
    for y in range(height):
        # Gold gradient from light to dark
        ratio = y / height
        r = int(255 - (255 - 184) * ratio)
        g = int(215 - (215 - 134) * ratio)
        b = int(0 + (139 - 0) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Add metallic shine effect
    shine_overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    shine_draw = ImageDraw.Draw(shine_overlay)

    # Diagonal shine lines
    for i in range(0, width + height, 20):
        shine_draw.line([(i, 0), (i - height, height)], fill=(255, 255, 255, 15), width=2)

    card = Image.alpha_composite(card, shine_overlay)

    # Add team-colored background patterns (subtle)
    pattern_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    pattern_draw = ImageDraw.Draw(pattern_overlay)

    # Add subtle geometric patterns
    for i in range(0, width, 40):
        for j in range(0, height, 40):
            # Small diamond patterns
            diamond_points = [
                (i + 20, j + 10),
                (i + 30, j + 20),
                (i + 20, j + 30),
                (i + 10, j + 20)
            ]
            pattern_draw.polygon(diamond_points, fill=(255, 255, 255, 8))

    card = Image.alpha_composite(card, pattern_overlay)
    draw = ImageDraw.Draw(card)

    # Draw card outline with multiple borders for depth
    border_colors = [(139, 69, 19), (160, 82, 45), (205, 133, 63)]
    for i, color in enumerate(border_colors):
        thickness = 3 - i
        draw.rectangle(
            [(i, i), (width - 1 - i, height - 1 - i)],
            outline=color,
            width=thickness
        )

    # Load fonts - more modern, sports-themed styling
    try:
        # Try to use bold variants for better impact
        font_position = ImageFont.truetype("arialbd.ttf", 22)  # Arial Bold
        font_name = ImageFont.truetype("arialbd.ttf", 28)  # Smaller but bolder
        font_stats_label = ImageFont.truetype("arial.ttf", 16)
        font_stats_value = ImageFont.truetype("arialbd.ttf", 26)  # Bold for numbers
    except:
        try:
            # Fallback to regular arial
            font_position = ImageFont.truetype("arial.ttf", 22)
            font_name = ImageFont.truetype("arial.ttf", 28)
            font_stats_label = ImageFont.truetype("arial.ttf", 16)
            font_stats_value = ImageFont.truetype("arial.ttf", 26)
        except:
            # Final fallback
            font_position = ImageFont.load_default()
            font_name = ImageFont.load_default()
            font_stats_label = ImageFont.load_default()
            font_stats_value = ImageFont.load_default()

    # Position badge (top-left, simplified)
    position_x, position_y = 30, 40
    position_bg = Image.new('RGBA', (80, 60), (0, 0, 0, 0))
    position_draw = ImageDraw.Draw(position_bg)

    # Position background shape (rounded rectangle)
    position_draw.rounded_rectangle(
        [(5, 5), (75, 55)],
        radius=10,
        fill=(34, 34, 34, 220),
        outline=(255, 215, 0),
        width=2
    )

    # Position text
    pos_bbox = position_draw.textbbox((0, 0), position, font=font_position)
    pos_text_width = pos_bbox[2] - pos_bbox[0]
    position_draw.text(
        (40 - pos_text_width // 2, 20),
        position,
        font=font_position,
        fill="white"
    )

    card.paste(position_bg, (position_x, position_y), position_bg)

    # Team logo (top-right)
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize((60, 60), Image.LANCZOS)
        card.paste(logo, (width - 90, 50), logo)
    except FileNotFoundError:
        print(f"Logo not found: {logo_path}")

    # Player image (centered, much larger - 70% of card height)
    try:
        player_img = Image.open(image_path).convert("RGBA")
        # Resize maintaining aspect ratio - much larger now
        img_width, img_height = player_img.size
        target_height = int(height * 0.55)  # 55% of card height
        target_width = int((target_height / img_height) * img_width)
        max_width = int(width * 0.85)  # 85% of card width

        if target_width > max_width:
            target_width = max_width
            target_height = int((target_width / img_width) * img_height)

        player_img = player_img.resize((target_width, target_height), Image.LANCZOS)

        # Center the image
        img_x = (width - target_width) // 2
        img_y = 130

        # Add subtle glow effect around player
        glow_size = 10
        glow_img = Image.new('RGBA', (target_width + glow_size * 2, target_height + glow_size * 2), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)

        # Create multiple glow layers for smooth effect
        for i in range(glow_size, 0, -1):
            alpha = int(15 * (glow_size - i + 1) / glow_size)
            glow_draw.rectangle(
                [i - 1, i - 1, target_width + glow_size + i, target_height + glow_size + i],
                outline=(255, 215, 0, alpha),
                width=2
            )

        # Paste glow first, then player image
        card.paste(glow_img, (img_x - glow_size, img_y - glow_size), glow_img)
        card.paste(player_img, (img_x, img_y), player_img)

        # Add subtle border around player image
        border_img = Image.new('RGBA', (target_width + 4, target_height + 4), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.rectangle([0, 0, target_width + 3, target_height + 3], outline=(255, 215, 0, 180), width=2)
        card.paste(border_img, (img_x - 2, img_y - 2), border_img)

        player_img_bottom = img_y + target_height
    except FileNotFoundError:
        print(f"Player image not found: {image_path}")
        player_img_bottom = 400

    # Player name with enhanced styling (shadow and outline effects)
    name_y = player_img_bottom + 20

    # Function to draw text with outline and shadow
    def draw_outlined_text(draw, pos, text, font, fill_color, outline_color, shadow_color):
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

    # Split long names if needed
    if len(player_name) > 15:
        names = player_name.split()
        if len(names) > 1:
            first_line = " ".join(names[:-1])
            second_line = names[-1]
        else:
            first_line = player_name[:15]
            second_line = player_name[15:]

        # Center first line with effects
        name1_bbox = draw.textbbox((0, 0), first_line, font=font_name)
        name1_width = name1_bbox[2] - name1_bbox[0]
        draw_outlined_text(
            draw,
            (width // 2 - name1_width // 2, name_y),
            first_line,
            font_name,
            fill_color=(255, 255, 255),  # White text
            outline_color=(34, 34, 34),  # Dark outline
            shadow_color=(0, 0, 0, 120)  # Semi-transparent shadow
        )

        # Center second line with effects
        name2_bbox = draw.textbbox((0, 0), second_line, font=font_name)
        name2_width = name2_bbox[2] - name2_bbox[0]
        draw_outlined_text(
            draw,
            (width // 2 - name2_width // 2, name_y + 30),
            second_line,
            font_name,
            fill_color=(255, 255, 255),
            outline_color=(34, 34, 34),
            shadow_color=(0, 0, 0, 120)
        )
        stats_start_y = name_y + 70
    else:
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
        stats_start_y = name_y + 40

    # Stats section - use actual basketball stats
    stat_mapping = {
        "PTS": ("PTS", stats.get("PTS", 0)),
        "REB": ("REB", stats.get("REB", 0)),
        "AST": ("AST", stats.get("AST", 0)),
        "PIR": ("PIR", stats.get("PIR", 0)),
        "STL": ("STL", stats.get("STL", 0)),  # Steals if available
        "BLK": ("BLK", stats.get("BLK", 0))  # Blocks if available
    }

    # Use actual basketball stats (no conversion)
    basketball_stats = {}
    for key, (label, value) in stat_mapping.items():
        if isinstance(value, (int, float)):
            # Format to 1 decimal place if it's a float, otherwise keep as int
            if value % 1 == 0:
                basketball_stats[label] = str(int(value))
            else:
                basketball_stats[label] = f"{value:.1f}"
        else:
            basketball_stats[label] = "0"

    # Stats layout - clean text only, no backgrounds
    left_col_x = 60
    right_col_x = 240
    stat_y = stats_start_y
    stat_spacing = 25

    stat_keys = list(basketball_stats.keys())
    for i, stat_key in enumerate(stat_keys[:6]):
        if i < 3:
            x = left_col_x
            y = stat_y + (i * stat_spacing)
        else:
            x = right_col_x
            y = stat_y + ((i - 3) * stat_spacing)

        # Get stat value
        stat_value = basketball_stats[stat_key]

        # Draw stat value with shadow (bold, white)
        draw.text((x + 1, y + 1), stat_value, font=font_stats_value, fill=(0, 0, 0, 150))
        draw.text((x, y), stat_value, font=font_stats_value, fill=(255, 255, 255))

        # Calculate position for label
        value_bbox = draw.textbbox((0, 0), stat_value, font=font_stats_value)
        value_width = value_bbox[2] - value_bbox[0]

        # Draw stat label with shadow - adjust for font size difference
        label_x = x + value_width + 10
        # Offset the smaller font to align with the larger stat value font
        label_y_offset = 3  # Adjust smaller font to align with larger font baseline
        draw.text((label_x + 1, y + label_y_offset + 1), stat_key, font=font_stats_label, fill=(0, 0, 0, 100))
        draw.text((label_x, y + label_y_offset), stat_key, font=font_stats_label, fill=(220, 220, 220))

    # Add subtle corner decorations
    corner_size = 30
    corner_color = (255, 215, 0, 100)

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
    print(f"✅ FIFA-style card saved: {output_path}")


# Example usage
stats = {
    "PTS": 12.4,
    "REB": 4.7,
    "AST": 3.2,
    "PIR": 15.6,
    "STL": 1.2,
    "BLK": 0.8
}

create_fifa_style_card(
    player_name="Vasilije Micić",
    stats=stats,
    image_path="player_cards/player_images/MICIC VASILIJE.webp",
    logo_path="player_cards/team_logos/Anadolu_Efes_Istanbul/Anadolu_Efes_Istanbul_small.png",
    output_path="player_cards/generated/micic_fifa_card_new1.png",
    position="PG"
)