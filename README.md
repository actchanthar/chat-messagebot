# Telegram Chat Activity Reward Bot

A modular Telegram bot that rewards users for being active in group chats. For each message sent, users earn 1 kyat (Myanmar currency). The bot prevents spam by detecting repeated messages and stores data in MongoDB.

## Features

- **Message Counting**: Tracks how many messages each user sends
- **Reward System**: 1 message = 1 kyat
- **Spam Prevention**: Ignores repeated messages to prevent reward farming
- **Statistics**: View top active users and their earnings
- **Balance Checking**: Users can check their current balance
- **MongoDB Database**: Persistent storage using MongoDB

## Project Structure

```
telegram-chat-activity-bot/
├── bot.py                  # Main entry point
├── config.py               # Configuration variables
├── requirements.txt        # Dependencies
├── Procfile                # For Heroku deployment
├── README.md               # Documentation
├── database/
│   ├── __init__.py
│   └── database.py         # MongoDB connection and methods
└── plugins/
    ├── __init__.py
    ├── start.py            # /start and /help commands
    ├── balance.py          # Balance checking
    ├── stats.py            # Statistics commands
    ├── admin.py            # Admin commands
    └── message_handler.py  # Message processing logic
```

## Commands

- `/start` - Introduction to the bot
- `/help` - Display help information
- `/balance` - Check your current balance
- `/stats` - View chat statistics
- `/reset` - Reset all statistics (admin only)
- `/pay` - Mark a user as paid (admin only)

## Setup Instructions

### Prerequisites

- Python 3.8+
- A Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- MongoDB database (can use MongoDB Atlas free tier)

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/telegram-chat-activity-bot.git
   cd telegram-chat-activity-bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```
   export TELEGRAM_TOKEN=your_bot_token_here
   export MONGODB_URI=your_mongodb_connection_string
   export ADMIN_IDS=your_telegram_id,another_admin_id
   ```

4. Run the bot:
   ```
   python bot.py
   ```

### Deploying to Heroku

1. Create a Heroku account if you don't have one
2. Install Heroku CLI
3. Login to Heroku:
   ```
   heroku login
   ```

4. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```

5. Set your config variables:
   ```
   heroku config:set TELEGRAM_TOKEN=your_bot_token_here
   heroku config:set MONGODB_URI=your_mongodb_connection_string
   heroku config:set ADMIN_IDS=your_telegram_id,another_admin_id
   ```

6. Deploy to Heroku:
   ```
   git push heroku main
   ```

7. Start the worker:
   ```
   heroku ps:scale worker=1
   ```

## MongoDB Setup

1. Create a free MongoDB Atlas account: https://www.mongodb.com/cloud/atlas
2. Create a new cluster
3. Create a database user with read/write permissions
4. Get your connection string from MongoDB Atlas
5. Replace `your_mongodb_connection_string` with your actual connection string

## Admin Setup

To use admin commands, set the ADMIN_IDS environment variable with comma-separated Telegram user IDs.

## How to Use

1. Add the bot to your Telegram group
2. Grant the bot admin privileges in the group
3. The bot will automatically start counting messages
4. Users can check their balance with the `/balance` command
5. Admins can view statistics with the `/stats` command
6. After paying users, admins can reset their balance with the `/pay` command