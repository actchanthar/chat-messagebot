# Bot Configuration
BOT_TOKEN = "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo"

# Database Configuration
MONGODB_URL = "mongodb+srv://act:actdata@cluster0.z6trhoh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # or your MongoDB Atlas URL
MONGODB_NAME = "message_earning_bot"

# Admin Configuration
ADMIN_IDS = ["5062124930"]  # Add your Telegram user IDs
LOG_CHANNEL_ID = "-1002555129360"  # Channel for logging activities

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
