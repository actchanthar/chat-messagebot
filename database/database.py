import logging
from datetime import datetime
from collections import deque
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME, GROUP_CHAT_IDS, CHANNEL_IDS

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db.users
            self.settings = self.db.settings
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def create_user(self, user_id: str, name: dict) -> bool:
        try:
            existing_user = await self.users.find_one({"user_id": user_id})
            if existing_user:
                logger.info(f"User {user_id} already exists")
                return False
            user = {
                "user_id": user_id,
                "first_name": name.get("first_name", ""),
                "last_name": name.get("last_name", ""),
                "username": name.get("username", ""),
                "balance": 0.0,
                "messages": 0,
                "group_messages": {str(gid): 0 for gid in GROUP_CHAT_IDS},
                "withdrawn_today": 0.0,
                "last_withdrawal": None,
                "banned": False,
                "notified_10kyat": False,
                "last_activity": datetime.utcnow(),
                "message_timestamps": [],  # Store as list instead of deque
                "invites": 0,
                "pending_withdrawals": []
            }
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False

    async def get_user(self, user_id: str) -> dict | None:
        try:
            user = await self.users.find_one({"user_id": str(user_id)})
            if user and "message_timestamps" in user:
                # Convert list back to deque when retrieving
                user["message_timestamps"] = deque(user["message_timestamps"], maxlen=5)
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, updates: dict) -> bool:
        try:
            # Convert deque to list if message_timestamps is in updates
            if "message_timestamps" in updates and isinstance(updates["message_timestamps"], deque):
                updates["message_timestamps"] = list(updates["message_timestamps"])
            result = await self.users.update_one(
                {"user_id": str(user_id)},
                {"$set": updates}
            )
            logger.info(f"Updated user {user_id} with {updates}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def increment_messages(self, user_id: str, chat_id: str) -> bool:
        try:
            await self.users.update_one(
                {"user_id": str(user_id)},
                {
                    "$inc": {
                        "messages": 1,
                        f"group_messages.{chat_id}": 1
                    },
                    "$set": {"last_activity": datetime.utcnow()}
                }
            )
            logger.info(f"Incremented messages for user {user_id} in chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing messages for user {user_id}: {e}")
            return False

    async def update_balance(self, user_id: str, amount: float) -> bool:
        try:
            await self.users.update_one(
                {"user_id": str(user_id)},
                {"$inc": {"balance": amount}},
                upsert=True
            )
            logger.info(f"Updated balance for user {user_id} by {amount}")
            return True
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False

    async def check_rate_limit(self, user_id: str) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user:
                logger.warning(f"User {user_id} not found for rate limit check")
                return False

            current_time = datetime.utcnow()
            timestamps = deque(user.get("message_timestamps", []), maxlen=5)
            timestamps.append(current_time)
            await self.update_user(user_id, {"message_timestamps": timestamps})  # deque will be converted to list in update_user

            if len(timestamps) == 5 and (current_time - timestamps[0]).total_seconds() < 60:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

    async def get_message_rate(self) -> int:
        try:
            settings = await self.settings.find_one({"type": "message_rate"})
            rate = settings.get("value", 3) if settings else 3
            logger.info(f"Retrieved message rate: {rate}")
            return rate
        except Exception as e:
            logger.error(f"Error getting message rate: {e}")
            return 3

    async def set_message_rate(self, messages_per_kyat: int) -> bool:
        try:
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"value": messages_per_kyat}},
                upsert=True
            )
            logger.info(f"Set message rate to {messages_per_kyat}")
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_channels(self) -> list:
        """Retrieve the list of channel IDs from the settings collection or config."""
        try:
            settings = await self.settings.find_one({"type": "channels"})
            if settings and "channels" in settings:
                logger.info("Retrieved channels from database")
                return settings["channels"]
            logger.info("No channels in database, returning CHANNEL_IDS from config")
            return CHANNEL_IDS
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return CHANNEL_IDS

# Instantiate the Database class to create the 'db' object
try:
    db = Database()
    logger.info("Database instance created")
except Exception as e:
    logger.error(f"Failed to initialize Database: {e}")
    raise