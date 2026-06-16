import os
import io
from PIL import Image, ImageDraw, ImageFont

# Hex Colors
COLOR_BG = (10, 13, 22)         # Deep Dark Navy
COLOR_CARD = (18, 25, 41)       # Dark Slate Blue
COLOR_ACCENT = (0, 240, 255)    # Neon Light Blue / Cyan
COLOR_BORDER = (26, 35, 51)     # Border Blue
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_GRAY = (176, 184, 198)
COLOR_GREEN = (56, 161, 105)
COLOR_RED = (229, 62, 62)

RANK_COLORS = {
    "E": (142, 142, 142),
    "D": (160, 90, 44),
    "C": (56, 161, 105),
    "B": (49, 130, 206),
    "A": (128, 90, 213),
    "S": (229, 62, 62),
    "National": (214, 158, 46)
}

def get_font(font_name="segoeui.ttf", size=16):
    try:
        font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", font_name)
        if not os.path.exists(font_path):
            # Try Arial if Segoe UI is missing
            font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()

def draw_hud_borders(draw, width, height, glow_color=COLOR_ACCENT):
    # Main outer border
    draw.rectangle([5, 5, width - 6, height - 6], outline=(15, 20, 32), width=2)
    # Inner thin border
    draw.rectangle([10, 10, width - 11, height - 11], outline=COLOR_BORDER, width=1)
    
    # Corner HUD accent brackets
    bracket_len = 30
    bracket_width = 3
    # Top-Left
    draw.line([10, 10, 10 + bracket_len, 10], fill=glow_color, width=bracket_width)
    draw.line([10, 10, 10, 10 + bracket_len], fill=glow_color, width=bracket_width)
    # Top-Right
    draw.line([width - 11, 10, width - 11 - bracket_len, 10], fill=glow_color, width=bracket_width)
    draw.line([width - 11, 10, width - 11, 10 + bracket_len], fill=glow_color, width=bracket_width)
    # Bottom-Left
    draw.line([10, height - 11, 10 + bracket_len, height - 11], fill=glow_color, width=bracket_width)
    draw.line([10, height - 11, 10, height - 11 - bracket_len], fill=glow_color, width=bracket_width)
    # Bottom-Right
    draw.line([width - 11, height - 11, width - 11 - bracket_len, height - 11], fill=glow_color, width=bracket_width)
    draw.line([width - 11, height - 11, width - 11, height - 11 - bracket_len], fill=glow_color, width=bracket_width)

def generate_welcome_card(hunter_name: str, rank_letter: str, rank_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 380
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT)
    draw_hud_borders(draw, width, height, glow_color=accent_color)
    
    # Header Font
    font_title = get_font("segoeuib.ttf", 26)
    font_subtitle = get_font("segoeuii.ttf", 14)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Title
    draw.text((300, 35), "SOLO LEVELING JOURNAL", fill=COLOR_ACCENT, font=font_title, anchor="mm")
    draw.text((300, 65), "System Active Monitoring & Log", fill=COLOR_TEXT_GRAY, font=font_subtitle, anchor="mm")
    draw.line([50, 80, 550, 80], fill=COLOR_BORDER, width=1)
    
    # Inner Status Card
    draw.rounded_rectangle([40, 100, 560, 340], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Avatar Circle
    draw.ellipse([70, 130, 170, 230], fill=(22, 33, 56), outline=accent_color, width=2)
    draw.text((120, 180), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 40), anchor="mm")
    
    # Profile Info
    draw.text((200, 135), "HUNTER IDENTIFICATION", fill=COLOR_TEXT_GRAY, font=get_font("segoeuib.ttf", 12))
    draw.text((200, 155), hunter_name, fill=COLOR_TEXT_WHITE, font=font_bold)
    draw.text((200, 185), f"Class/Title: {rank_title}", fill=accent_color, font=font_reg)
    
    # Small stats row
    draw.text((200, 220), "Total Cleared Log:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((340, 220), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((200, 250), "Active Quest Days:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((340, 250), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    # System Status label
    draw.rounded_rectangle([200, 290, 340, 315], radius=5, fill=(13, 49, 31))
    draw.text((270, 302), "SYSTEM ACTIVE", fill=(72, 187, 120), font=get_font("segoeuib.ttf", 12), anchor="mm")
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_status_card(hunter_name: str, rank_letter: str, rank_title: str, xp_percent: int, streak_days: int, streak_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 750
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT)
    draw_hud_borders(draw, width, height, glow_color=accent_color)
    
    # Fonts
    font_header = get_font("segoeuib.ttf", 28)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    font_small = get_font("segoeui.ttf", 13)
    
    # Header Window
    draw.text((300, 45), "STATUS WINDOW", fill=COLOR_ACCENT, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # 1. Profile Block
    draw.rounded_rectangle([40, 95, 560, 220], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    # Avatar Circle
    draw.ellipse([70, 110, 180, 205], fill=(22, 33, 56), outline=accent_color, width=2)
    draw.text((125, 157), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 46), anchor="mm")
    
    # Basic Profile Info
    draw.text((210, 115), "NAME:", fill=COLOR_TEXT_GRAY, font=font_small)
    draw.text((270, 115), hunter_name, fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((210, 145), "RANK:", fill=COLOR_TEXT_GRAY, font=font_small)
    draw.text((270, 145), f"{rank_letter}-Rank ({rank_title})", fill=accent_color, font=font_bold)
    
    draw.text((210, 175), "GUILD:", fill=COLOR_TEXT_GRAY, font=font_small)
    draw.text((270, 175), "Solo Leveling Hunter", fill=COLOR_TEXT_WHITE, font=font_reg)
    
    # 2. Stats Block
    draw.text((45, 245), "HUNTER STATISTICS", fill=COLOR_TEXT_GRAY, font=get_font("segoeuib.ttf", 14))
    draw.rounded_rectangle([40, 270, 560, 420], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    stats_y = 290
    # Stat 1
    draw.text((70, stats_y), "Cleared Activities (Logs):", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((480, stats_y), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    # Stat 2
    draw.text((70, stats_y + 35), "Active Quest Days:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((480, stats_y + 35), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    # Stat 3
    draw.text((70, stats_y + 70), "Current Login Streak:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((480, stats_y + 70), f"{streak_days} Days", fill=(255, 179, 0) if streak_days > 0 else COLOR_TEXT_WHITE, font=font_bold)
    
    # 3. Level & XP Progress Block
    draw.text((45, 445), "RANK PROGRESS & EXPERIENCE (XP)", fill=COLOR_TEXT_GRAY, font=get_font("segoeuib.ttf", 14))
    draw.rounded_rectangle([40, 470, 560, 580], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Progress Text
    draw.text((70, 490), f"Current Rank: {rank_letter}", fill=COLOR_TEXT_WHITE, font=font_reg)
    draw.text((480, 490), f"{xp_percent}%", fill=COLOR_ACCENT, font=font_bold)
    
    # Progress Bar Background
    bar_x1, bar_y1, bar_x2, bar_y2 = 70, 525, 530, 545
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=5, fill=(15, 23, 42), outline=COLOR_BORDER, width=1)
    # Progress Bar Fill
    bar_width = int((bar_x2 - bar_x1) * xp_percent / 100)
    if bar_width > 0:
        draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + bar_width, bar_y2], radius=5, fill=accent_color)
        
    # 4. Streak Milestones & Titles
    if streak_days > 0:
        draw.text((45, 605), "ACTIVE BUFFS & TITLES", fill=COLOR_TEXT_GRAY, font=get_font("segoeuib.ttf", 14))
        draw.rounded_rectangle([40, 630, 560, 710], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
        
        draw.ellipse([65, 645, 105, 685], fill=(36, 28, 11), outline=(255, 179, 0), width=1)
        draw.text((85, 665), "F", fill=(255, 179, 0), font=get_font("segoeuib.ttf", 20), anchor="mm")
        
        draw.text((120, 645), "Active Buff: Streak Monarch", fill=(255, 179, 0), font=font_bold)
        draw.text((120, 672), f"Title: {streak_title} ({streak_days} Days Daily Logs)", fill=COLOR_TEXT_GRAY, font=font_small)
    else:
        # Guidance tip if no streak
        draw.text((45, 605), "ACTIVE BUFFS & TITLES", fill=COLOR_TEXT_GRAY, font=get_font("segoeuib.ttf", 14))
        draw.rounded_rectangle([40, 630, 560, 710], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
        draw.text((300, 670), "No active buffs. Log daily to unlock Hunter Titles!", fill=COLOR_TEXT_GRAY, font=font_small, anchor="mm")
        
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_agenda_card(date_str: str, active_quests: list, cleared_quests: list) -> bytes:
    width, height = 600, 780
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    # Red Warning Glow for Daily Quest board
    draw_hud_borders(draw, width, height, glow_color=(255, 85, 0))
    
    font_header = get_font("segoeuib.ttf", 24)
    font_bold = get_font("segoeuib.ttf", 16)
    font_reg = get_font("segoeui.ttf", 14)
    font_small = get_font("segoeui.ttf", 12)
    
    # Header
    draw.text((300, 40), "DAILY QUEST AGENDA", fill=(255, 85, 0), font=font_header, anchor="mm")
    draw.text((300, 68), f"Quest Date: {date_str}", fill=COLOR_TEXT_GRAY, font=font_small, anchor="mm")
    draw.line([50, 85, 550, 85], fill=COLOR_BORDER, width=1)
    
    # Section 1: Active Quests (Reminders)
    draw.text((45, 105), "🔴 ACTIVE QUESTS (Reminders)", fill=COLOR_RED, font=font_bold)
    draw.rounded_rectangle([40, 130, 560, 380], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 150
    if not active_quests:
        draw.text((300, 250), "No active quests for today.", fill=COLOR_TEXT_GRAY, font=font_reg, anchor="mm")
    else:
        for q in active_quests[:6]: # limit to 6 items to prevent overflow
            q_time = q.get("remind_at", "").split("T")[1][:5] if "T" in q.get("remind_at", "") else q.get("remind_at", "")[:5]
            q_text = q.get("text", "")
            if len(q_text) > 42:
                q_text = q_text[:39] + "..."
            
            draw.rounded_rectangle([55, y, 70, y+15], radius=2, fill=(45, 18, 18), outline=COLOR_RED, width=1)
            draw.text((85, y-2), f"[{q_time}] {q_text}", fill=COLOR_TEXT_WHITE, font=font_reg)
            y += 35
            
    # Section 2: Cleared Quests (Logs)
    draw.text((45, 415), "🟢 CLEARED QUESTS (Logs)", fill=COLOR_GREEN, font=font_bold)
    draw.rounded_rectangle([40, 440, 560, 740], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 460
    if not cleared_quests:
        draw.text((300, 580), "No logs recorded today. Start writing to clear quests!", fill=COLOR_TEXT_GRAY, font=font_reg, anchor="mm")
    else:
        for l in cleared_quests[:7]: # limit to 7 items to prevent overflow
            l_time = l.get("time", "")[:5]
            l_text = l.get("text", "")
            if len(l_text) > 42:
                l_text = l_text[:39] + "..."
                
            draw.text((60, y-2), "✓", fill=COLOR_GREEN, font=font_bold)
            draw.text((85, y-2), f"[{l_time}] {l_text}", fill=COLOR_TEXT_GRAY, font=font_reg)
            y += 35
            
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_stats_card(total_entries: int, active_days: int, first_date: str, last_date: str) -> bytes:
    width, height = 600, 480
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_hud_borders(draw, width, height, glow_color=COLOR_ACCENT)
    
    font_header = get_font("segoeuib.ttf", 26)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Title
    draw.text((300, 40), "HUNTER STATISTICS", fill=COLOR_ACCENT, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # Outer box
    draw.rounded_rectangle([40, 95, 560, 440], radius=10, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 120
    draw.text((70, y), "Total Clear Entries:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((350, y), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "Days Active in System:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((350, y), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "First Log Registered:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((350, y), str(first_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    y += 50
    draw.text((70, y), "Latest Log Registered:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((350, y), str(last_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    # Level estimation
    level = (total_entries // 10) + 1
    y += 65
    draw.line([60, y, 540, y], fill=COLOR_BORDER, width=1)
    
    y += 20
    draw.text((70, y), "Estimated Hunter Level:", fill=COLOR_TEXT_GRAY, font=font_reg)
    draw.text((350, y), f"Lv. {level}", fill=COLOR_ACCENT, font=font_bold)
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()
