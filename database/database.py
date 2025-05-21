from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME, REQUIRED_CHANNELS
import logging
from datetime import datetime, timedelta
import asyncio
import pymongo.errors

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db.users
            self.groups = self.db.groups
            self.rewards = self.db.rewards
            self.settings = self.db.settings
            self.message_history = {}
            self.lock = asyncio.Lock()
            logger.info("Initialized MongoDB connection")
        except pymongo.errors.ConnectionError as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            raise

    async def get_user(self, user_id):
        try:
            async with self.lock:
                user = await self.users.find_one({"user_id": user_id})
                if user:
                    if isinstance(user.get("invited_users"), list):
                        await self.update_user(user_id, {"invited_users": len(user["invited_users"]) if user["invited_users"] else 0})
                    logger.info(f"Retrieved user {user_id}: {user}")
                else:
                    logger.warning(f"No user found for ID {user_id}")
                return user
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error retrieving user {user_id}: {e}", exc_info=True)
            return None

    async def create_user(self, user_id, name, inviter_id=None):
        try:
            async with self.lock:
                existing_user = await self.get_user(user_id)
                if existing_user:
                    logger.info(f"User {user_id} already exists")
                    return existing_user
                user = {
                    "user_id": user_id,
                    "name": name,
                    "balance": 0,
                    "messages": 0,
                    "group_messages": {"-1002061898677": 0, "-1001756870040": 0},
                    "withdrawn_today": 0,
                    "last_withdrawal": None,
                    "banned": False,
                    "notified_10kyat": False,
                    "last_activity": datetime.utcnow(),
                    "message_timestamps": [],
                    "inviter": inviter_id if inviter_id and await self.get_user(inviter_id) else None,
                    "invited_users": 0,
                    "joined_channels": False,
                    "username": None
                }
                for attempt in range(3):
                    try:
                        await self.users.insert_one(user)
                        logger.info(f"Created user {user_id} with inviter {inviter_id}")
                        return user
                    except pymongo.errors.PyMongoError as e:
                        logger.error(f"Attempt {attempt + 1} failed to create user {user_id}: {e}")
                        await asyncio.sleep(0.5)
                logger.error(f"Failed to create user {user_id} after 3 attempts")
                return None
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}", exc_info=True)
            return None

    async def update_user(self, user_id, updates):
        try:
            async with self.lock:
                result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
                if result.modified_count > 0:
                    updates_log = {k: v for k, v in updates.items()}
                    if "message_timestamps" in updates_log:
                        updates_log["message_timestamps"] = f"[{len(updates['message_timestamps'])} timestamps]"
                    logger.info(f"Updated user {user_id}: {updates_log}")
                    return True
                logger.info(f"No changes for user {user_id}")
                return False
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error updating user {user_id}: {e}", exc_info=True)
            return False

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database error retrieving users: {e}", exc_info=True)
            return []

    async def get_top_users(self, limit=10):
        try:
            top_users = await self.users.find(
                {"banned": False},
                {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "group_messages": 1, "invited_users": 1, "_id": 0}
            ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users")
            return top_users
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error retrieving top users: {e}", exc_info=True)
            return []

    async def get_required_channels(self):
        try:
            channels = await self.get_setting("required_channels", REQUIRED_CHANNELS)
            logger.info(f"Retrieved required channels: {channels}")
            return channels if channels else REQUIRED_CHANNELS
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error retrieving required channels: {e}", exc_info=True)
            return REQUIRED_CHANNELS

    async def get_setting(self, setting_type, default=None):
        try:
            setting = await self.settings.find_one({"type": setting_type})
            value = setting["value"] if setting else default
            logger.info(f"Retrieved setting {setting_type}: {value}")
            return value
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error retrieving setting {setting_type}: {e}", exc_info=True)
            return default

    async def set_setting(self, setting_type, value):
        try:
            await self.settings.update_one({"type": setting_type}, {"$set": {"value": value}}, upsert=True)
            logger.info(f"Set {setting_type} to {value}")
            return True
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error setting {setting_type}: {e}", exc_info=True)
            return False

    async def fix_users(self):
        try:
            async with self.lock:
                users = await self.users.find().to_list(length=None)
                for user in users:
                    updates = {}
                    if isinstance(user.get("invited_users"), list):
                        updates["invited_users"] = len(user["invited_users"]) if user["invited_users"] else 0
                    if "group_messages" not in user:
                        updates["group_messages"] = {"-1002061898677": 0, "-1001756870040": 0}
                    if "message_timestamps" not in user or not isinstance(user["message_timestamps"], list):
                        updates["message_timestamps"] = []
                    if "joined_channels" not in user:
                        updates["joined_channels"] = False
                    if updates:
                        await self.update_user(user["user_id"], updates)
                        logger.info(f"Fixed user {user['user_id']}: {updates}")
                logger.info("User migration completed")
                return True
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error in user migration: {e}", exc_info=True)
            return False

db = Database()