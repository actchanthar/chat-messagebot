# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Database Configuration
MONGODB_URL = "mongodb://localhost:27017"  # or your MongoDB Atlas URL
MONGODB_NAME = "message_earning_bot"

# Admin Configuration
ADMIN_IDS = ["YOUR_ADMIN_USER_ID"]  # Add your Telegram user IDs
LOG_CHANNEL_ID = "YOUR_LOG_CHANNEL_ID"  # Channel for logging activities

# Bot Settings
CURRENCY = "kyat"
APPROVED_GROUPS = ["-1002061898677"]  # Groups where users can earn
MESSAGE_RATE = 3  # Messages per kyat (3 messages = 1 kyat)

# Withdrawal Settings
MIN_WITHDRAWAL = 200        # Minimum withdrawal amount
MAX_DAILY_WITHDRAWAL = 10000  # Maximum daily withdrawal per user

# Anti-Spam Settings
MAX_EMOJI_COUNT = 8
MAX_LINKS_COUNT = 2

# Spam Keywords
SPAM_KEYWORDS = [
    "free money", "click here", "buy now", "win prize", "guaranteed profit",
    "join channel", "earn money", "make money", "100% free", "limited time",
    "act now", "download app", "visit link", "call now", "whatsapp me"
]

# Spam Patterns
SPAM_PATTERNS = [
    r'https?://bit\.ly/\w+',
    r'https?://tinyurl\.com/\w+',
    r'(?:telegram\.me|t\.me)/\w+',
    r'[A-Z]{6,}',  # 6+ consecutive capitals
    r'(.)\1{5,}',  # 5+ repeated characters
    r'\b(?:\+?95|09)\d{8,9}\b.*(?:call|contact|whatsapp)',
]
