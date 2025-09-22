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
MAX_DAILY_WITHDRAWAL = 4000

# Smart Anti-Spam Settings - PROTECT NORMAL USERS
MAX_EMOJI_COUNT = 2  # Increased - allow more emojis for normal users
MAX_LINKS_COUNT = 3  # Increased - allow more links for normal sharing
MIN_MESSAGE_LENGTH = 1  # Reduced - allow very short messages
MAX_MESSAGE_LENGTH = 1000  # Increased - allow longer messages for normal chat
MAX_REPEATED_CHARS = 5  # Increased - allow more repeated chars (hahaha, etc)
MAX_MESSAGES_PER_MINUTE = 20  # Increased - allow more messages for active users
SPAM_COOLDOWN_MINUTES = 2  # Reduced - shorter cooldown, more forgiving

# Rapid Spam Detection Settings (New)
RAPID_MESSAGE_THRESHOLD = 2.0  # Seconds between messages to be considered rapid
MAX_RAPID_MESSAGES = 3  # Max rapid messages before considered spam
RAPID_WINDOW_SECONDS = 10  # Time window to check for rapid messages
MAX_MESSAGES_IN_WINDOW = 8  # Max messages allowed in rapid window

# Only the most obvious spam keywords (very restrictive)
SPAM_KEYWORDS = [
    # Only single letters and obvious meaningless combinations
    "dmd", "dmmd", "dmdm", "dm", "md", "m", "d", "g", "f", "k",
    # Only clear nonsense patterns
    "dd", "mm", "ff", "kk", "gg", "rr"
]

# Only the most obvious spam patterns (very restrictive)
SPAM_PATTERNS = [
    r'^[a-z]{1,2}$',  # Only single/double letters (d, dm)
    r'(.)\1{5,}',     # 6+ repeated characters (dddddd)
    r'^[^\w\s]*$',    # Only special characters (!!!, @@@)
    r'^\s*$',         # Empty or whitespace only
]

# Normal User Protection Patterns (New)
MEANINGFUL_PATTERNS = [
    r'.{10,}',        # 10+ characters = meaningful
    r'\w+\s+\w+',     # Multiple words = meaningful
    r'[\u1000-\u109F]+',  # Myanmar text = meaningful
    r'\d+',           # Contains numbers = meaningful
    r'[?!.]',         # Contains punctuation = meaningful
    r'(how|what|when|where|why|who|hello|hi|good|thank|ok|yes|no)',  # Normal words
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

# Smart Anti-Spam Feature Flags (New)
PROTECT_NORMAL_USERS = True      # Enable normal user protection
MYANMAR_LANGUAGE_SUPPORT = True  # Enable Myanmar language warnings
SMART_SPAM_DETECTION = True      # Enable smart spam detection
AUTO_FORGIVE_ENABLED = True      # Auto-reset warnings after cooldown
GENTLE_MODE_ENABLED = True       # Enable gentle anti-spam mode

# Logging and Debug Settings
DETAILED_SPAM_LOGGING = True     # Log spam detection details
LOG_NORMAL_USERS = False         # Don't spam logs with normal user activity
LOG_EARNING_NOTIFICATIONS = True # Log when users earn money
