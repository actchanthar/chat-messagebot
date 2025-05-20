from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from collections import deque
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups
        self.rewards = self.db.rewards
        self.settings = self.db.settings
        self.message_history = {}  # In-memory cache for duplicate checking

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
                "inviter_id": None,
                "invite_count": 0,  # Ensure invite_count is initialized
                "invited_users": [],
                "referral_rewarded": False
            }
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id} with invite_count=0")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            # Log the current state before update
            current_user = await self.get_user(user_id)
            logger.info(f"Before update: user {user_id} invite_count={current_user.get('invite_count', 0) if current_user else 'N/A'}")
            
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates}, upsert=True)
            if result.modified_count > 0 or result.upserted_id:
                logger.info(f"Updated user {user_id}: {updates}")
                # Verify the update
                updated_user = await self.get_user(user_id)
                logger.info(f"After update: user {user_id} invite_count={updated_user.get('invite_count', 0) if updated_user else 'N/A'}")
                return True
            logger.info(f"No changes for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            return users
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            return []

    async def get_user_count(self):
        try:
            count = await self.users.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    async def get_top_users(self, limit=10, by="messages"):
        try:
            if by == "invites":
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "name": 1, "invite_count": 1, "balance": 1, "_id": 0}
                ).sort("invite_count", -1).limit(limit).to_list(length=limit)
            else:
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "group_messages": 1, "_id": 0}
                ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {by}: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users: {e}")
            return []

    async def add_channel(self, channel_id):
        try:
            await self.settings.update_one({"type": "force_sub_channels"}, {"$addToSet": {"channels": channel_id}}, upsert=True)
            logger.info(f"Added channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding channel {channel_id}: {e}")
            return False

    async def remove_channel(self, channel_id):
        try:
            await self.settings.update_one({"type": "force_sub_channels"}, {"$pull": {"channels": channel_id}})
            logger.info(f"Removed channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing channel {channel_id}: {e}")
            return False

    async def get_force_sub_channels(self):
        try:
            setting = await self.settings.find_one({"type": "force_sub_channels"})
            return setting.get("channels", []) if setting else []
        except Exception as e:
            logger.error(f"Error retrieving channels: {e}")
            return []

    async def get_group_messages(self, group_id):
        try:
            users = await self.users.find({"group_messages." + group_id: {"$exists": True}}).to_list(length=None)
            return {user["user_id"]: user["group_messages"].get(group_id, 0) for user in users}
        except Exception as e:
            logger.error(f"Error retrieving group messages for {group_id}: {e}")
            return {}

    async def get_setting(self, setting_type, default=None):
        try:
            setting = await self.settings.find_one({"type": setting_type})
            return setting.get("value", default) if setting else default
        except Exception as e:
            logger.error(f"Error retrieving {setting_type}: {e}")
            return default

    async def set_setting(self, setting_type, value):
        try:
            await self.settings.update_one({"type": setting_type}, {"$set": {"value": value}}, upsert=True)
            logger.info(f"Set {setting_type} to {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting {setting_type}: {e}")
            return False

    async def check_rate_limit(self, user_id, message_text=None):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            current_time = datetime.utcnow()
            timestamps = user.get("message_timestamps", deque(maxlen=5))
            timestamps.append(current_time)
            await self.update_user(user_id, {"message_timestamps": list(timestamps)})
            if len(timestamps) == 5 and (current_time - timestamps[0]).total_seconds() < 60:
                return True
            if message_text and user_id in self.message_history and self.message_history[user_id] == message_text:
                return True
            self.message_history[user_id] = message_text
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for {user_id}: {e}")
            return False

db = Database()