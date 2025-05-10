import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")
CURRENCY = "kyat"
