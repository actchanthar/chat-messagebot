# Bot Configuration
BOT_TOKEN = "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo"

# Database Configuration
MONGODB_URL = "mongodb+srv://act:actdata@cluster0.z6trhoh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGODB_NAME = "message_earning_bot"

# Admin Configuration
ADMIN_IDS = ["5062124930"]
LOG_CHANNEL_ID = "-1002555129360"

# Bot Settings
CURRENCY = "kyat"
APPROVED_GROUPS = ["-1002061898677"]
MESSAGE_RATE = 3

# Withdrawal Settings
MIN_WITHDRAWAL = 200
MAX_DAILY_WITHDRAWAL = 10000

# Anti-Spam Settings
MAX_EMOJI_COUNT = 8
MAX_LINKS_COUNT = 2

# Spam Keywords and Patterns
SPAM_KEYWORDS = [
    "free money", "click here", "buy now", "win prize", "guaranteed profit",
    "join channel", "earn money", "make money", "100% free", "limited time",
    "act now", "download app", "visit link", "call now", "whatsapp me"
]

SPAM_PATTERNS = [
    r'https?://bit\.ly/\w+',
    r'https?://tinyurl\.com/\w+',
    r'(?:telegram\.me|t\.me)/\w+',
    r'[A-Z]{6,}',
    r'(.)\1{5,}',
    r'\b(?:\+?95|09)\d{8,9}\b.*(?:call|contact|whatsapp)',
]

# NEW: Announcement and Receipt Settings
ANNOUNCEMENT_GROUPS = [
    "-1002061898677",  # Your main earning group
]

RECEIPT_CHANNEL_ID = "-1002978328897"  # Use your log channel for now, or create new receipt channel
RECEIPT_CHANNEL_NAME = "@actearnproof"  # Your receipt channel

# Enable auto announcements
AUTO_ANNOUNCE_WITHDRAWALS = True
