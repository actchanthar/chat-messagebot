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

# Enhanced Anti-Spam Settings - GENTLER APPROACH
MAX_EMOJI_COUNT = 5  # Increased from 3 to 5 - allow more emojis
MAX_LINKS_COUNT = 2  # Keep at 2
MIN_MESSAGE_LENGTH = 2  # Reduced from 3 to 2 - allow shorter messages
MAX_MESSAGE_LENGTH = 500  # Keep same
MAX_REPEATED_CHARS = 4  # Increased from 3 to 4 - allow more repeated chars
MAX_MESSAGES_PER_MINUTE = 15  # Increased from 8 to 15 - allow more messages
SPAM_COOLDOWN_MINUTES = 5  # Keep 5 minutes

# More specific spam keywords (only obvious spam)
SPAM_KEYWORDS = [
    # Only obvious single/double letter spam
    "dmd", "dmmd", "dmdm", "mdm", "dm", "md", "rm", "em", "m",
    "g", "f", "k", "d", "dd", "mm", "ff", "kk", "gg", "rr",
    # Obvious meaningless combinations
    "fkf", "kf", "mdfof", "rrkrek", "x.x", "dmr", "mf", "dkf"
]

# Only obvious spam patterns - removed normal text patterns
SPAM_PATTERNS = [
    r'^[a-z]{1,2}$',  # Only d, dm, dmd (1-2 letters)
    r'(.)\1{4,}',  # 5+ repeated characters (aaaaa, ddddd)
    r'^[^\w\s]+$',  # Only special characters (!@#$%)
    r'^\s*$',  # Empty or whitespace only messages
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
DEFAULT_REFERRAL_REWARD = 50  # 50 kyat per referral as requested
DEFAULT_MESSAGE_RATE = 3      # 3 messages = 1 kyat as requested

# Welcome Settings
WELCOME_BONUS = 100  # New users get 100 kyat welcome bonus

# Phone Bill Reward for top users
PHONE_BILL_REWARD = 1000

# Myanmar Language Settings
MYANMAR_WARNINGS = True  # Enable Myanmar language warnings
GENTLE_MODE = True       # Enable gentle anti-spam mode
AUTO_FORGIVE_MINUTES = 5  # Auto-reset warnings after 5 minutes
