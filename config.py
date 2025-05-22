import os

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo")
BOT_USERNAME = "@actearnbot"

# MongoDB settings
MONGODB_NAME = os.getenv("MONGODB_NAME", "actchat1")
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/actchat1?retryWrites=true&w=majority&appName=Cluster0"
)

# Withdrawal settings
WITHDRAWAL_THRESHOLD = 100
DAILY_WITHDRAWAL_LIMIT = 5000
CURRENCY = "kyat"

# Message counting settings
COUNT_MESSAGES = True
MESSAGES_PER_KYAT = 3

# Group and channel settings
GROUP_CHAT_IDS = [
    "-1002061898677",  # Primary group for message counting
]
LOG_CHANNEL_ID = "-1002555129360"

# Force-subscription channels
REQUIRED_CHANNELS = [
    "-1002097823468",
    "-1002171798406",
]

# Payment methods supported for withdrawals
PAYMENT_METHODS = [
    "KBZ Pay",
    "Wave Pay",
    "Phone Bill",
]

# Admin settings
ADMIN_IDS = ["5062124930"]

# Referral settings
DEFAULT_REQUIRED_INVITES = 15
REFERRAL_BONUS_INVITER = 25
REFERRAL_BONUS_INVITED = 50

# Miscellaneous
PHONE_BILL_AMOUNTS = [1000, 2000, 3000, 4000, 5000]
WEEKLY_REWARD_AMOUNT = 100