# SoloLeveling Journal Bot

A Telegram bot for personal daily journaling with Solo Leveling theme. Log your activities, track your rank, and level up your productivity — all from Telegram.

## Features

### Core
- **Instant Logging** — Send any message, it's saved automatically
- **Manual Commands** — `/log <activity>` for explicit entries
- **Daily Review** — `/today`, `/yesterday`, `/date YYYY-MM-DD`
- **Search** — `/search <keyword>` to find past entries
- **Archive** — `/all` shows all dates with entries

### Gamification
- **Hunter Rank System** — E → D → C → B → A → S → National Level
- **XP Progress Bar** — Visual progress to next rank
- **Streak Tracking** — Consecutive logging days with milestone titles
  - 7 days: Shadow Soldier
  - 14 days: Riser
  - 30 days: Commander
  - 60 days: Marshal
  - 90 days: Shadow Monarch

### Reminders
- **Daily Reminders** — `/remind HH:MM <text>`
- **One-time Reminders** — `/remindat YYYY-MM-DD HH:MM <text>`
- **Interactive Buttons** — Click to select time/date, no need to memorize commands

### Export
- **PDF Export** — `/export` with options:
  - Today
  - Last 7 days
  - This month
  - All entries
  - Custom date range

### UI/UX
- **Inline Keyboard Menu** — Section-specific buttons for cleaner navigation
- **Auto-delete Messages** — Confirmation messages disappear after 3 seconds
- **Clean Chat** — `/start` clears previous messages
- **Command Suggestions** — Type `/` to see all available commands

### System
- **AI Info** — `/ai` shows model info and usage statistics
- **Auto-restart** — Bot sends menu to all active users on restart
- **User Tracking** — Tracks active users for notifications

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show main menu |
| `/rank` | Check Hunter Rank and progress |
| `/ai` | AI system info and statistics |
| `/agenda` | View today's agenda |
| `/log <text>` | Save a journal entry |
| `/today` | View today's entries |
| `/yesterday` | View yesterday's entries |
| `/date YYYY-MM-DD` | View entries for a specific date |
| `/search <keyword>` | Search entries by keyword |
| `/all` | List all dates with entries |
| `/stats` | Show journal statistics |
| `/export` | Export journal to PDF |
| `/del <id>` | Delete an entry by ID |
| `/clear` | Interactive delete menu |
| `/remind HH:MM <text>` | Set daily reminder |
| `/remindat YYYY-MM-DD HH:MM <text>` | Set one-time reminder |
| `/reminders` | List active reminders |
| `/unremind <id>` | Remove a reminder |
| `/restart` | Restart the bot |

## Project Structure

```
joblog/
├── bot.py              # Main entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── dev-restart.ps1     # Development restart script
├── start-bot.ps1       # Production start script
├── dream.ps1           # Memory backup script
└── src/
    ├── handlers.py     # Handler router
    ├── commands.py     # Command handlers
    ├── callbacks.py    # Callback query handlers
    ├── helpers.py      # Utilities and keyboards
    ├── storage.py      # JSON-based storage
    ├── scheduler.py    # APScheduler for reminders
    ├── ranks.py        # Rank system logic
    ├── pdf_export.py   # PDF generation
    └── user_tracker.py # Active user tracking
```

## Setup

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from @BotFather)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Pidzzzz/joblog.git
   cd joblog
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your tokens.

4. Run the bot:
   ```bash
   python bot.py
   ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `DEVELOPER_ID` | Your Telegram user ID | Yes |

## Development

### Quick Restart
```powershell
# Restart bot
.\dev-restart.ps1

# Pull updates and restart
.\dev-restart.ps1 -Pull

# Run in watch mode (auto-restart on changes)
.\dev-restart.ps1 -Watch

# Install auto-restart (every hour)
.\dev-restart.ps1 -Install
```

### Backup Memory
```powershell
# Save session memory
.\dream.ps1
```

## Tech Stack

- **Python** 3.14
- **python-telegram-bot** 22.8 — Telegram Bot API
- **APScheduler** — Task scheduling for reminders
- **fpdf2** — PDF generation
- **JSON** — Local data storage

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built with ❤️ by [Pidzzzz](https://github.com/Pidzzzz) using MiMoCode AI Assistant
