from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from collections import deque

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.mongo_client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.mongo_client[MONGODB_NAME]
            self.users = self.db.users
            self.groups = self.db.groups
            self.rewards = self.db.rewards
            self.settings = self.db.settings
            self.message_history = {}  # In-memory cache for duplicate checking
            logger.info("MongoDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            logger.info(f"Retrieved user {user_id}: {user}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id, name):
        try:
            user = {
                "user_id": user_id,
                "name": name,
                "balance": 0,
                "messages": 0,
                "group_messages": {"-1002061898677": 0},
                "withdrawn_today": 0,
                "last_withdrawal": None,
                "banned": False,
                "notified_10kyat": False,
                "last_activity": datetime.utcnow(),
                "message_timestamps": deque(maxlen=5),
                "referrals": [],
                "invite_requirement": 15
            }
            await self.users.insert_one(user)
            logger.info(f"Created new user {user_id} with name {name}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
            if result.modified_count > 0:
                updates_log = {k: v if k != "message_timestamps" else f"[{len(updates['message_timestamps'])} timestamps]" for k, v in updates.items()}
                logger.info(f"Updated user {user_id}: {updates_log}")
                return True
            logger.info(f"No changes made to user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def check_rate_limit(self, user_id, message_text=None):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False

            current_time = datetime.utcnow()
            if user_id not in self.message_history:
                self.message_history[user_id] = deque(maxlen=5)

            timestamps = user.get("message_timestamps", deque(maxlen=5))
            timestamps.append(current_time)
            await self.update_user(user_id, {"message_timestamps": list(timestamps)})
            if len(timestamps) == 5 and (current_time - timestamps[0]).total_seconds() < 60:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return True

            if message_text and user_id in self.message_history and self.message_history[user_id] == message_text:
                logger.warning(f"Duplicate message detected for user {user_id}")
                return True
            self.message_history[user_id] = message_text
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

class DatabaseWithClient(Database):
    def __init__(self, bot_client):
        try:
            super().__init__()  # Initialize MongoDB client
            self.bot_client = bot_client  # Store Telegram bot client separately
            logger.info("DatabaseWithClient initialized with bot client")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseWithClient: {e}")
            raise

db = None

def init_db(bot_client):
    global db
    try:
        db = DatabaseWithClient(bot_client)
        logger.info("Database singleton initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise