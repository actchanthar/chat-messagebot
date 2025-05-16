# config.py
# Bot token
BOT_TOKEN = "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo"

# MongoDB settings
MONGODB_NAME = "actchat1"
MONGODB_URL = "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Withdrawal settings
WITHDRAWAL_THRESHOLD = 100
DAILY_WITHDRAWAL_LIMIT = 2500
CURRENCY = "kyat"

# Message counting and group settings
COUNT_MESSAGES = True
GROUP_CHAT_IDS = ["-1002061898677", "-1002217915135"]

# Log channel ID for admin notifications
LOG_CHANNEL_ID = "-1002555129360"

# Payment methods
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Phone Bill"]

# Admin and referral settings
ADMIN_USER_ID = "5062124930"
DEFAULT_REQUIRED_INVITES = 15

# Force-subscription settings
FORCE_SUB_CHANNEL_IDS = ["-1002097823468"]  # Channels users must join to use the bot
FORCE_SUB_CHANNEL_LINKS = {
    "-1002097823468": "https://t.me/yourchannel"  # Replace with the actual invite link
}