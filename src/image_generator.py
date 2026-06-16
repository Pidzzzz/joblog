import os
import io
import math
from PIL import Image, ImageDraw, ImageFont

# Hex Colors
COLOR_BG = (11, 15, 26)         # Sleek dark blue-black
COLOR_CARD = (20, 28, 48)       # Translucent slate blue panel
COLOR_BORDER = (35, 48, 77)     # Tech border
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_MUTED = (140, 156, 184) # Muted label color
COLOR_ACCENT_BLUE = (0, 240, 255)  # Neon Cyan
COLOR_GREEN = (46, 204, 113)
COLOR_RED = (231, 76, 60)

RANK_COLORS = {
    "E": (142, 142, 142),
    "D": (180, 115, 70),
    "C": (46, 204, 113),
    "B": (52, 152, 219),
    "A": (155, 89, 182),
    "S": (231, 76, 60),
    "National": (241, 196, 15)
}

def get_font(font_name="segoeui.ttf", size=16):
    try:
        font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", font_name)
        if not os.path.exists(font_path):
            font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()

def draw_background_grid(draw, width, height):
    # Soft high-tech dot-matrix pattern
    for x in range(20, width, 25):
        for y in range(20, height, 25):
            draw.point((x, y), fill=(24, 34, 56))

def draw_hexagon(draw, cx, cy, r, fill, outline, width=1):
    points = []
    for i in range(6):
        angle = math.radians(i * 60 - 30) # vertical alignment
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill, outline=outline, width=width)

def draw_hud_design(draw, width, height, glow_color=COLOR_ACCENT_BLUE):
    # Double thin boundary box
    draw.rectangle([10, 10, width - 11, height - 11], outline=(20, 28, 48), width=2)
    draw.rectangle([15, 15, width - 16, height - 16], outline=COLOR_BORDER, width=1)
    
    # Glowing corner brackets (glow shadow + bright core)
    shadow_color = (int(glow_color[0]/3), int(glow_color[1]/3), int(glow_color[2]/3))
    bracket_len = 35
    
    # Helper to draw glowing lines
    def draw_glow_line(x1, y1, x2, y2):
        draw.line([x1, y1, x2, y2], fill=shadow_color, width=4)
        draw.line([x1, y1, x2, y2], fill=glow_color, width=2)
        
    # Top-Left
    draw_glow_line(15, 15, 15 + bracket_len, 15)
    draw_glow_line(15, 15, 15, 15 + bracket_len)
    # Top-Right
    draw_glow_line(width - 16, 15, width - 16 - bracket_len, 15)
    draw_glow_line(width - 16, 15, width - 16, 15 + bracket_len)
    # Bottom-Left
    draw_glow_line(15, height - 16, 15 + bracket_len, height - 16)
    draw_glow_line(15, height - 16, 15, height - 16 - bracket_len)
    # Bottom-Right
    draw_glow_line(width - 16, height - 16, width - 16 - bracket_len, height - 16)
    draw_glow_line(width - 16, height - 16, width - 16, height - 16 - bracket_len)
    
    # Draw tiny HUD decoration crosses
    draw.text((25, 25), "+", fill=COLOR_BORDER, font=get_font(size=11), anchor="mm")
    draw.text((width - 26, 25), "+", fill=COLOR_BORDER, font=get_font(size=11), anchor="mm")
    draw.text((25, height - 26), "+", fill=COLOR_BORDER, font=get_font(size=11), anchor="mm")
    draw.text((width - 26, height - 26), "+", fill=COLOR_BORDER, font=get_font(size=11), anchor="mm")

def generate_welcome_card(hunter_name: str, rank_letter: str, rank_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 390
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT_BLUE)
    draw_hud_design(draw, width, height, glow_color=accent_color)
    
    # Fonts
    font_title = get_font("segoeuib.ttf", 26)
    font_subtitle = get_font("segoeuii.ttf", 13)
    font_section = get_font("segoeuib.ttf", 12)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Title & Headers
    draw.text((300, 42), "SOLO LEVELING SYSTEM", fill=COLOR_ACCENT_BLUE, font=font_title, anchor="mm")
    draw.text((300, 70), "HUNTER ACTIVITY & LOG REGISTRY", fill=COLOR_TEXT_MUTED, font=font_subtitle, anchor="mm")
    draw.line([50, 85, 550, 85], fill=COLOR_BORDER, width=1)
    
    # Outer Panel card
    draw.rounded_rectangle([40, 105, 560, 345], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Hexagonal Rank Shield
    draw_hexagon(draw, 115, 195, 50, fill=(24, 34, 56), outline=accent_color, width=2)
    draw.text((115, 195), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 42), anchor="mm")
    draw.text((115, 260), "RANK", fill=COLOR_TEXT_MUTED, font=font_section, anchor="mm")
    
    # Information Box
    x_offset = 200
    draw.text((x_offset, 130), "CODENAME / HUNTER NAME", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.text((x_offset, 150), hunter_name.upper(), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((x_offset, 185), "CURRENT TITLE", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.text((x_offset, 205), rank_title, fill=accent_color, font=font_reg)
    
    # Bottom Stats Bar
    draw.line([200, 240, 520, 240], fill=COLOR_BORDER, width=1)
    
    # Left Stat
    draw.text((x_offset, 255), "LOGS RECORDED", fill=COLOR_TEXT_MUTED, font=font_subtitle)
    draw.text((x_offset, 275), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    # Right Stat
    draw.text((380, 255), "DAYS ACTIVE", fill=COLOR_TEXT_MUTED, font=font_subtitle)
    draw.text((380, 275), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    # Small status indicator tag
    draw.rounded_rectangle([455, 125, 535, 145], radius=3, fill=(15, 45, 30))
    draw.text((495, 134), "ONLINE", fill=COLOR_GREEN, font=get_font("segoeuib.ttf", 10), anchor="mm")
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_status_card(hunter_name: str, rank_letter: str, rank_title: str, xp_percent: int, streak_days: int, streak_title: str, total_entries: int, active_days: int) -> bytes:
    width, height = 600, 770
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    accent_color = RANK_COLORS.get(rank_letter, COLOR_ACCENT_BLUE)
    draw_hud_design(draw, width, height, glow_color=accent_color)
    
    # Fonts
    font_header = get_font("segoeuib.ttf", 26)
    font_section = get_font("segoeuib.ttf", 13)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    font_small = get_font("segoeui.ttf", 13)
    
    # Header Window
    draw.text((300, 45), "STATUS WINDOW", fill=COLOR_ACCENT_BLUE, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # 1. Profile Block
    draw.rounded_rectangle([40, 95, 560, 225], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # Hexagonal Rank Shield
    draw_hexagon(draw, 105, 160, 48, fill=(24, 34, 56), outline=accent_color, width=2)
    draw.text((105, 160), rank_letter, fill=accent_color, font=get_font("segoeuib.ttf", 40), anchor="mm")
    
    # Profile labels & values
    x_prof = 180
    draw.text((x_prof, 115), "CODENAME:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 113), hunter_name, fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((x_prof, 145), "HUNTER RANK:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 143), f"{rank_letter}-Rank", fill=accent_color, font=font_bold)
    
    draw.text((x_prof, 175), "CLASS / TITLE:", fill=COLOR_TEXT_MUTED, font=font_small)
    draw.text((x_prof + 95, 173), rank_title, fill=COLOR_TEXT_WHITE, font=font_reg)
    
    # 2. Stats Block
    draw.text((45, 250), "JOURNAL STATISTICS", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 275, 560, 420], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y_stats = 295
    # Stats Items
    draw.text((70, y_stats), "Cleared Quest Logs:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((70, y_stats + 35), "Days Active in System:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats + 35), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    draw.text((70, y_stats + 70), "Active Streak Buff:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, y_stats + 70), f"{streak_days} Days", fill=(255, 185, 0) if streak_days > 0 else COLOR_TEXT_WHITE, font=font_bold)
    
    # 3. Level & XP Progress Block
    level = (total_entries // 10) + 1
    draw.text((45, 445), f"LEVEL & PROGRESSION (Lv. {level})", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 470, 560, 580], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    # XP text labels
    draw.text((70, 490), "Monarch System Sync:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((480, 490), f"{xp_percent}%", fill=accent_color, font=font_bold)
    
    # Modern Segmented Progress Bar
    bar_x1, bar_y1, bar_x2, bar_y2 = 70, 525, 530, 542
    draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=4, fill=(15, 23, 40), outline=COLOR_BORDER, width=1)
    
    bar_width = int((bar_x2 - bar_x1) * xp_percent / 100)
    # Draw glow bar
    if bar_width > 0:
        draw.rounded_rectangle([bar_x1, bar_y1, bar_x1 + bar_width, bar_y2], radius=4, fill=accent_color)
        
    # 4. Buff & Title Milestones
    draw.text((45, 605), "SYSTEM PASSIVE BUFFS", fill=COLOR_TEXT_MUTED, font=font_section)
    draw.rounded_rectangle([40, 630, 560, 715], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    if streak_days > 0:
        draw_hexagon(draw, 80, 672, 22, fill=(48, 38, 15), outline=(255, 185, 0), width=1)
        draw.text((80, 672), "B", fill=(255, 185, 0), font=get_font("segoeuib.ttf", 16), anchor="mm")
        
        draw.text((120, 648), "Active Buff: Streak Monarch", fill=(255, 185, 0), font=font_bold)
        draw.text((120, 675), f"Title unlocked: {streak_title}", fill=COLOR_TEXT_WHITE, font=font_small)
    else:
        draw.text((300, 672), "No active streak buffs. Log daily to level up your titles!", fill=COLOR_TEXT_MUTED, font=font_small, anchor="mm")
        
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_agenda_card(date_str: str, active_quests: list, cleared_quests: list) -> bytes:
    width, height = 600, 780
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    # Orange HUD Warning style for Daily Quest
    draw_hud_design(draw, width, height, glow_color=(255, 102, 0))
    
    font_header = get_font("segoeuib.ttf", 24)
    font_section = get_font("segoeuib.ttf", 15)
    font_bold = get_font("segoeuib.ttf", 16)
    font_reg = get_font("segoeui.ttf", 14)
    font_small = get_font("segoeui.ttf", 12)
    
    # Header
    draw.text((300, 42), "DAILY QUEST BOARD", fill=(255, 102, 0), font=font_header, anchor="mm")
    draw.text((300, 68), f"TARGET DATE: {date_str}", fill=COLOR_TEXT_MUTED, font=font_small, anchor="mm")
    draw.line([50, 85, 550, 85], fill=COLOR_BORDER, width=1)
    
    # 1. Active Quests (Reminders)
    draw.text((45, 105), "⚔️ ACTIVE QUESTS (Reminders)", fill=COLOR_RED, font=font_section)
    draw.rounded_rectangle([40, 130, 560, 380], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 155
    if not active_quests:
        draw.text((300, 255), "No pending active quests. Safe Zone.", fill=COLOR_TEXT_MUTED, font=font_reg, anchor="mm")
    else:
        for q in active_quests[:6]:
            q_time = q.get("remind_at", "").split("T")[1][:5] if "T" in q.get("remind_at", "") else q.get("remind_at", "")[:5]
            q_text = q.get("text", "")
            if len(q_text) > 42:
                q_text = q_text[:39] + "..."
            
            # Draw tech-style check box
            draw.rectangle([55, y+2, 69, y+16], outline=COLOR_RED, width=1)
            draw.text((85, y), f"[{q_time}] {q_text}", fill=COLOR_TEXT_WHITE, font=font_reg)
            y += 35
            
    # 2. Cleared Quests (Logs)
    draw.text((45, 415), "🛡️ CLEARED QUESTS (Daily Logs)", fill=COLOR_GREEN, font=font_section)
    draw.rounded_rectangle([40, 440, 560, 740], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 465
    if not cleared_quests:
        draw.text((300, 590), "No activities recorded. Awaiting quest inputs...", fill=COLOR_TEXT_MUTED, font=font_reg, anchor="mm")
    else:
        for l in cleared_quests[:7]:
            l_time = l.get("time", "")[:5]
            l_text = l.get("text", "")
            if len(l_text) > 42:
                l_text = l_text[:39] + "..."
                
            # Draw green checkmark symbol
            draw.text((55, y), "✓", fill=COLOR_GREEN, font=font_bold)
            draw.text((85, y), f"[{l_time}] {l_text}", fill=COLOR_TEXT_MUTED, font=font_reg)
            y += 35
            
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()

def generate_stats_card(total_entries: int, active_days: int, first_date: str, last_date: str) -> bytes:
    width, height = 600, 480
    img = Image.new("RGB", (width, height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    draw_background_grid(draw, width, height)
    draw_hud_design(draw, width, height, glow_color=COLOR_ACCENT_BLUE)
    
    font_header = get_font("segoeuib.ttf", 26)
    font_section = get_font("segoeuib.ttf", 13)
    font_bold = get_font("segoeuib.ttf", 18)
    font_reg = get_font("segoeui.ttf", 15)
    
    # Header
    draw.text((300, 45), "SYSTEM STATISTICS", fill=COLOR_ACCENT_BLUE, font=font_header, anchor="mm")
    draw.line([50, 75, 550, 75], fill=COLOR_BORDER, width=1)
    
    # Outer Panel
    draw.rounded_rectangle([40, 95, 560, 440], radius=8, fill=COLOR_CARD, outline=COLOR_BORDER, width=1)
    
    y = 125
    draw.text((70, y), "Total Completed Entries:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(total_entries), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "Monarch Active Days:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(active_days), fill=COLOR_TEXT_WHITE, font=font_bold)
    
    y += 50
    draw.text((70, y), "Initial Sync Date:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(first_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    y += 50
    draw.text((70, y), "Last Sync Date:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), str(last_date or "-"), fill=COLOR_TEXT_WHITE, font=font_reg)
    
    y += 65
    draw.line([60, y, 540, y], fill=COLOR_BORDER, width=1)
    
    # Level Estimation
    level = (total_entries // 10) + 1
    y += 20
    draw.text((70, y), "Estimated Hunter Level:", fill=COLOR_TEXT_MUTED, font=font_reg)
    draw.text((350, y), f"Lv. {level}", fill=COLOR_ACCENT_BLUE, font=font_bold)
    
    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio.getvalue()
