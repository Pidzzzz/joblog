# SoloLeveling Journal Bot

A Telegram bot for personal daily journaling. Log your activities, search past entries, and track your productivity — all from Telegram.

## Changelog

### v2.0 — 2026-06-15
- **Hunter Rank System** — Rank progression: E → D → C → B → A → S → National Level (based on total entries)
- **XP Progress Bar** — Visual progress bar to next rank
- **Streak Tracking** — Track consecutive logging days with milestone titles (Shadow Soldier → Shadow Monarch)
- **Interactive Delete Log** — Select individual entries to delete with toggle buttons, or delete all at once
- **Auto-Restart Fix** — Restart button now works properly on Windows with confirmation message
- **Menu Improvement** — Previous bot message auto-deleted when logging to prevent double buttons
- **Markdown Fix** — Fixed reserved character parsing errors
- **Dev Script** — `dev-restart.ps1` for quick stop/pull/start workflow

## Features

- **Instant Logging** — Send any message to the bot, it's saved automatically
- **Manual Commands** — `/log <activity>` for explicit entries
- **Hunter Rank System** — Progress from E-Rank to National Level Hunter
- **Streak Tracking** — Earn titles for consecutive logging days
- **Daily Review** — `/today`, `/yesterday`, `/date YYYY-MM-DD`
- **Search** — `/search <keyword>` to find past entries
- **Statistics** — `/stats` shows total entries, active days, first/last date
- **Interactive Delete** — Select and delete individual entries
- **Reminders** — Daily and one-time reminders with `/remind`
- **Private** — Only you can use the bot (owner-only access)

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show main menu |
| `/rank` | Check your Hunter Rank and progress |
| `/agenda` | View today's agenda (Active & Cleared Quests) |
| `/log <text>` | Save a journal entry |
| `/today` | View today's entries |
| `/yesterday` | View yesterday's entries |
| `/date YYYY-MM-DD` | View entries for a specific date |
| `/search <keyword>` | Search entries by keyword |
| `/all` | List all dates with entries |
| `/stats` | Show journal statistics |
| `/del <id>` | Delete an entry by ID |
| `/clear` | Interactive delete menu |
| `/remind <HH:MM> <text>` | Set daily reminder |
| `/remindat <YYYY-MM-DD HH:MM> <text>` | Set one-time reminder |
| `/reminders` | List active reminders |
| `/unremind <id>` | Remove a reminder |
| `/restart` | Restart the bot |

## Setup

1. Clone the repo:
   ```
   git clone https://github.com/Pidzzzz/joblog.git
   cd joblog
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create `.env` file:
   ```
   BOT_TOKEN=your_telegram_bot_token
   DEVELOPER_ID=your_telegram_user_id
   ```

4. Run the bot:
   ```
   python bot.py
   ```

## Tech Stack

- Python 3.14
- python-telegram-bot
- JSON-based local storage
