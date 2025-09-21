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

# Receipt and Announcement Settings - FIXED
RECEIPT_CHANNEL_ID = "-1002978328897"  # Your @actearnproof channel ID
RECEIPT_CHANNEL_NAME = "@actearnproof"

# Withdrawal receipts go ONLY to proof channel
ANNOUNCEMENT_GROUPS = [
    "-1002978328897"  # Only send withdrawal proofs here
]

# Regular announcements (new users, milestones) can go to main group
GENERAL_ANNOUNCEMENT_GROUPS = [
    "-1002061898677"  # Your main earning group
]

# Enable auto announcements
AUTO_ANNOUNCE_WITHDRAWALS = True
AUTO_ANNOUNCE_NEW_USERS = True
AUTO_ANNOUNCE_MILESTONES = True

# Referral Settings
DEFAULT_REFERRAL_REWARD = 50  # 50 kyat per referral as requested
DEFAULT_MESSAGE_RATE = 3      # 3 messages = 1 kyat as requested

# Welcome Settings
WELCOME_BONUS = 100  # New users get 100 kyat welcome bonus

# Phone Bill Reward for top users
PHONE_BILL_REWARD = 1000
