# SoloLeveling Journal Bot

A Telegram bot for personal daily journaling. Log your activities, search past entries, and track your productivity — all from Telegram.

## Features

- **Instant Logging** — Send any message to the bot, it's saved automatically
- **Manual Commands** — `/log <activity>` for explicit entries
- **Daily Review** — `/today`, `/yesterday`, `/date YYYY-MM-DD`
- **Search** — `/search <keyword>` to find past entries
- **Statistics** — `/stats` shows total entries, active days, first/last date
- **Delete** — `/del <id>` to remove an entry
- **Private** — Only you can use the bot (owner-only access)

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help menu |
| `/agenda` | View today's agenda (Active & Cleared Quests) |
| `/log <text>` | Save a journal entry |
| `/today` | View today's entries |
| `/yesterday` | View yesterday's entries |
| `/date YYYY-MM-DD` | View entries for a specific date |
| `/search <keyword>` | Search entries by keyword |
| `/all` | List all dates with entries |
| `/stats` | Show journal statistics |
| `/del <id>` | Delete an entry by ID |

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
