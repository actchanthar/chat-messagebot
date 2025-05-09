import os

# Bot token from environment variable
BOT_TOKEN = os.environ.get("7784918819:AAGxcb10Je-oSKZVoOGDjpcpaFgMq1FNTr8")

# MongoDB URI from environment variable
MONGODB_URI = os.environ.get("mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Admin user IDs (list of strings)
ADMIN_IDS = os.environ.get("ADMIN_IDS", "5062124930").split(",")

# Spam detection settings
SPAM_THRESHOLD = 5  # Number of similar messages allowed within time window
TIME_WINDOW = 60 * 30  # 30 minutes in seconds

# Reward settings
REWARD_PER_MESSAGE = 1  # Kyat per message

# Currency symbol
CURRENCY = "kyat"