import os
import sys

def validate_env_vars():
    required_vars = ["TELEGRAM_TOKEN", "MONGODB_URI"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

validate_env_vars()

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MONGODB_URI = os.environ.get("MONGODB_URI")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")
SPAM_THRESHOLD = 5
TIME_WINDOW = 60 * 30
REWARD_PER_MESSAGE = 1
CURRENCY = "kyat"