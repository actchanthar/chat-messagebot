import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
GROUP_CHAT_ID = "-1002061898677"  # Replace with your group chat ID
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")
CURRENCY = "kyat"
WITHDRAWAL_THRESHOLD = 100  # Minimum balance for withdrawal
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Phone Bill"]
# Add other config variables like BOT_TOKEN, CHANNEL_ID, etc.