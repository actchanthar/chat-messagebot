# config.py
# Bot token
BOT_TOKEN = "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo"

# MongoDB settings
MONGODB_NAME = "actchat1"
MONGODB_URL = "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Withdrawal settings
WITHDRAWAL_THRESHOLD = 100  # Minimum balance required to withdraw (in kyat)
DAILY_WITHDRAWAL_LIMIT = 2500  # Maximum withdrawal amount per day (in kyat)
CURRENCY = "kyat"

# Message counting and group settings
COUNT_MESSAGES = True  # Enable counting messages for earnings
GROUP_CHAT_IDS = ["-1002061898677", "-1002217915135"]  # List of approved group chat IDs

# Log channel ID for admin notifications (e.g., withdrawal requests, broadcast logs)
LOG_CHANNEL_ID = "-1002555129360"  # Admin channel for logging (verified from previous logs)

# Payment methods supported for withdrawals
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Phone Bill"]

# Additional settings for enhanced functionality
ADMIN_USER_ID = "5062124930"  # Admin user ID for restricted commands (e.g., /setinvite, /broadcast)
DEFAULT_REQUIRED_INVITES = 15  # Default number of invites required for withdrawal (can be changed via /setinvite)