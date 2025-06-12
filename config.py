import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MONGODB_NAME = os.getenv("MONGODB_NAME")
MONGODB_URL = os.getenv("MONGODB_URL")
WITHDRAWAL_THRESHOLD = float(os.getenv("WITHDRAWAL_THRESHOLD", 100))
DAILY_WITHDRAWAL_LIMIT = float(os.getenv("DAILY_WITHDRAWAL_LIMIT", 2500))
CURRENCY = os.getenv("CURRENCY", "kyat")
COUNT_MESSAGES = os.getenv("COUNT_MESSAGES", "True").lower() == "true"
GROUP_CHAT_IDS = os.getenv("GROUP_CHAT_IDS", "").split(",") if os.getenv("GROUP_CHAT_IDS") else []
CHANNEL_IDS = os.getenv("CHANNEL_IDS", "").split(",") if os.getenv("CHANNEL_IDS") else []
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
PAYMENT_METHODS = os.getenv("PAYMENT_METHODS", "").split(",") if os.getenv("PAYMENT_METHODS") else []
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []
INVITE_THRESHOLD = int(os.getenv("INVITE_THRESHOLD", 2))