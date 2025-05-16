# config.py
# Bot token
BOT_TOKEN = "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo"

# MongoDB settings
MONGODB_NAME = "actchat1"
MONGODB_URL = "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/actchat1?retryWrites=true&w=majority&appName=Cluster0"

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
FORCE_SUB_CHANNEL_LINKS = {
    "-1002171798406": "https://t.me/+placeholder_link"  # Replace with actual invite link for -1002171798406
}
FORCE_SUB_CHANNEL_NAMES = {
    "-1002171798406": "New Channel"  # Replace with actual channel name
}