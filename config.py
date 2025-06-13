# config.py
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Sensitive/environment-specific settings from .env
BOT_TOKEN = os.getenv("BOT_TOKEN", "8179173521:AAHR-kOrobpw0xLSTiQRabRbCY0y5p-w5mg")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@ACTMoneyBot")
MONGODB_NAME = os.getenv("MONGODB_NAME", "actmoney")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "-1002555129360")
ADMIN_IDS = os.getenv("ADMIN_IDS", "5062124930").split(",")  # Split into list if multiple IDs

# Non-sensitive settings
WITHDRAWAL_THRESHOLD = 100
DAILY_WITHDRAWAL_LIMIT = 5000
CURRENCY = "kyat"
COUNT_MESSAGES = True
GROUP_CHAT_IDS = ["-1002061898677"]  # Restrict to single group
CHANNEL_IDS = ["-1002097823468", "-1001610001670", "-1002171798406"]
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Phone Bill"]
INVITE_THRESHOLD = 2
REFERRAL_REWARD = 25  # Default referral reward (kyat per referred user)