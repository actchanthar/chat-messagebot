# config.py

import os

# Bot token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Channel ID and username for subscription check from environment variables
CHANNEL_ID = os.environ.get("CHANNEL_ID")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")

# Group chat ID for sending withdrawal announcements
GROUP_CHAT_ID = "-1002061898677"  # Already set in your config

# Admin IDs from environment variable (comma-separated string converted to list)
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")

# Currency for display
CURRENCY = "kyat"  # Already set in your config

# Minimum withdrawal threshold
WITHDRAWAL_THRESHOLD = 100  # Already set in your config, updated to 100

# Daily withdrawal limit
DAILY_WITHDRAWAL_LIMIT = int(os.environ.get("DAILY_WITHDRAWAL_LIMIT", 5000))  # Default to 5000 if not set

# Payment methods
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Phone Bill"]  # Already set in your config