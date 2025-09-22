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

# Enhanced Anti-Spam Settings
MAX_EMOJI_COUNT = 3  # Maximum emojis per message
MAX_LINKS_COUNT = 1  # Maximum links per message
MIN_MESSAGE_LENGTH = 3  # Minimum message length
MAX_MESSAGE_LENGTH = 500  # Maximum message length
MAX_REPEATED_CHARS = 3  # Maximum repeated characters
MAX_MESSAGES_PER_MINUTE = 8  # Maximum messages per user per minute
SPAM_COOLDOWN_MINUTES = 5  # Cooldown period for spammers

# Enhanced Spam Keywords (case insensitive)
SPAM_KEYWORDS = [
    "dmd", "dmmd", "dmdm", "mdm", "dm", "md", "rm", "em", "m",
    "gm", "fkf", "kf", "mdfof", "rrkrek", "x.x", "g",
    "haha", "lol", "wtf", "omg", "bruh", "ok", "yes", "no",
    "test", "testing", "spam", "bot", "earn", "money", "dmr",
    "mf", "dkf", "rkrek", "ddmd", "dmr", "d", "f", "k",
    "dd", "mm", "ff", "kk", "gg", "rr", "tt", "pp"
]

# Enhanced Spam Patterns (regex)
SPAM_PATTERNS = [
    r'^[a-z]{1,3}$',  # Single/double/triple letters (d, dm, dmd)
    r'^[A-Z]{1,3}$',  # Single caps (D, DM, DMD)
    r'(.)\1{2,}',  # Repeated characters (aaa, ddd, mmm)
    r'^(ha|haha|lol|wtf|omg|bruh|ok|yes|no|test)$',  # Common spam words
    r'(.{1,3})\1{2,}',  # Repeated patterns (dmdmdm)
    r'^[^\w\s]+$',  # Only special characters
    r'^\s*$',  # Empty or whitespace only
    r'^[a-z]$',  # Single letter
    r'^[0-9]{1,3}$',  # Short numbers
    r'^(.)\\1+$',  # Same character repeated
]

# Receipt and Announcement Settings
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
DEFAULT_REFERRAL_REWARD = 50  # 50 kyat per referral
DEFAULT_MESSAGE_RATE = 3      # 3 messages = 1 kyat

# Welcome Settings
WELCOME_BONUS = 100  # New users get 100 kyat welcome bonus

# Phone Bill Reward for top users
PHONE_BILL_REWARD = 1000
