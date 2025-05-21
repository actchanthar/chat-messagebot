# config.py
import os

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo")  # Fallback for local testing
BOT_USERNAME = "@actearnbot"  # Bot's Telegram username

# MongoDB settings
MONGODB_NAME = os.getenv("MONGODB_NAME", "actchat1")
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/actchat1?retryWrites=true&w=majority&appName=Cluster0"
)  # Fallback for local testing

# Withdrawal settings
WITHDRAWAL_THRESHOLD = 100  # Minimum withdrawal amount in kyat
DAILY_WITHDRAWAL_LIMIT = 5000  # Daily withdrawal limit per user in kyat
CURRENCY = "kyat"  # Currency unit for balances and withdrawals

# Message counting settings
COUNT_MESSAGES = True  # Enable/disable message counting globally
MESSAGES_PER_KYAT = 3  # Number of messages required to earn 1 kyat (default)

# Group and channel settings
GROUP_CHAT_IDS = [
    "-1002061898677",  # Primary group for message counting
    "-1001756870040",  # Secondary group for announcements
]
LOG_CHANNEL_ID = "-1002555129360"  # Channel for admin logs and withdrawal requests

# Force-subscription channels
REQUIRED_CHANNELS = [
    "-1002097823468",  # Channel 1 for force-subscription
    "-1002171798406",  # Channel 2 for force-subscription
]

# Payment methods supported for withdrawals
PAYMENT_METHODS = [
    "KBZ Pay",
    "Wave Pay",
    "Phone Bill",
]

# Admin settings
ADMIN_IDS = ["5062124930"]  # List of admin user IDs with special permissions

# Referral settings
DEFAULT_REQUIRED_INVITES = 15  # Number of invites required to unlock withdrawals
REFERRAL_BONUS_INVITER = 25  # Bonus for the inviter per valid invite (in kyat)
REFERRAL_BONUS_INVITED = 50  # Bonus for the invited user upon joining channels (in kyat)

# Miscellaneous
PHONE_BILL_AMOUNTS = [1000, 2000, 3000, 4000, 5000]  # Allowed Phone Bill withdrawal amounts
WEEKLY_REWARD_AMOUNT = 100  # Amount for weekly top user rewards (in kyat)