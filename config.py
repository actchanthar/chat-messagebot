import os

# Bot token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# MongoDB URI from environment variable
MONGODB_URI = os.environ.get("MONGODB_URI")

# Admin user IDs (list of strings)
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")

# Spam detection settings
SPAM_THRESHOLD = 5  # Number of similar messages allowed within time window
TIME_WINDOW = 60 * 30  # 30 minutes in seconds

# Reward settings
REWARD_PER_MESSAGE = 1  # Kyat per message

# Currency symbol
CURRENCY = "kyat"