from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from collections import deque
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=30000)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups
        self.rewards = self.db.rewards
        self.settings = self.db.settings
        self.message_history = {}
        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            self.users.create_index([("user_id", 1)], unique=True)
            self.users.create_index([("invite_count", -1)])
            self.users.create_index([("messages", -1)])
            self.groups.create_index([("group_id", 1)], unique=True)
            self.settings.create_index([("type", 1)], unique=True)
            logger.info("Database indexes ensured")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": str(user_id)})
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id, name, username=None):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user = {
                    "user_id": str(user_id),
                    "name": name or "Unknown",
                    "username": username,
                    "balance": 0.0,
                    "messages": 0,
                    "group_messages": {"-1002061898677": 0},
                    "withdrawn_today": 0,
                    "last_withdrawal": None,
                    "banned": False,
                    "notified_10kyat": False,
                    "last_activity": datetime.utcnow(),
                    "message_timestamps": [],
                    "referrer": None,
                    "invites": [],
                    "invite_count": 0
                }
                await self.users.insert_one(user)
                await self._increment_total_users()
                logger.info(f"Created user {user_id}")
                return user
            except Exception as e:
                if "duplicate key" in str(e).lower():
                    return await self.get_user(user_id)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Failed to create user {user_id}: {e}")
                    return None

    async def update_user(self, user_id, updates):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if "messages" in updates:
                    updates["messages"] = max(0, updates["messages"])
                if "invite_count" in updates:
                    updates["invite_count"] = max(0, updates["invite_count"])
                if "balance" in updates:
                    updates["balance"] = max(0, updates["balance"])
                if "message_timestamps" in updates and isinstance(updates["message_timestamps"], deque):
                    updates["message_timestamps"] = list(updates["message_timestamps"])
                logger.info(f"Updating user {user_id} with: {updates}")
                result = await self.users.update_one({"user_id": str(user_id)}, {"$set": updates})
                if result.modified_count > 0:
                    logger.info(f"Updated user {user_id} successfully")
                else:
                    logger.warning(f"No changes made for user {user_id}")
                return result.modified_count > 0
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Error updating user {user_id}: {e}")
                    return False

    async def get_top_users(self, by="messages", limit=10):
        try:
            sort_field = "invite_count" if by == "invites" else "messages"
            top_users = await self.users.find(
                {"banned": False, sort_field: {"$gt": 0}},
                {"user_id": 1, "name": 1, "username": 1, "messages": 1, "balance": 1, "group_messages": 1, "invite_count": 1, "_id": 0}
            ).sort([(sort_field, -1)]).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {by}: {[u['user_id'] for u in top_users]}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users by {by}: {e}")
            return []

    async def get_total_users(self):
        try:
            stats = await self.settings.find_one({"type": "total_users"})
            count = stats.get("count", 0) if stats else await self.users.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error retrieving total users: {e}")
            return 0

    async def _increment_total_users(self):
        try:
            await self.settings.update_one(
                {"type": "total_users"},
                {"$inc": {"count": 1}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error incrementing total users: {e}")

    async def add_invite(self, referrer_id, invitee_id):
        try:
            referrer = await self.get_user(referrer_id)
            if not referrer or str(invitee_id) in referrer.get("invites", []):
                return
            await self.users.update_one(
                {"user_id": str(referrer_id)},
                {"$addToSet": {"invites": str(invitee_id)}, "$inc": {"invite_count": 1}}
            )
            logger.info(f"Added invite {invitee_id} to referrer {referrer_id}")
        except Exception as e:
            logger.error(f"Error adding invite for referrer {referrer_id}: {e}")

    async def get_message_rate(self):
        try:
            settings = await self.settings.find_one({"type": "message_rate"})
            return settings.get("value", 3) if settings else 3
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

    async def set_message_rate(self, value):
        try:
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"value": value}},
                upsert=True
            )
            logger.info(f"Set message rate to {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def check_rate_limit(self, user_id, message_text=None):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            current_time = datetime.utcnow()
            timestamps = deque(user.get("message_timestamps", []), maxlen=5)
            timestamps.append(current_time)
            await self.update_user(user_id, {"message_timestamps": list(timestamps)})
            if len(timestamps) == 5 and (current_time - timestamps[0]).total_seconds() < 60:
                return True
            if message_text and user_id in self.message_history and self.message_history[user_id] == message_text:
                return True
            self.message_history[user_id] = message_text
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

    async def get_force_sub_channels(self):
        try:
            settings = await self.settings.find_one({"type": "force_sub_channels"})
            return settings.get("channels", []) if settings else []
        except Exception as e:
            logger.error(f"Error retrieving force sub channels: {e}")
            return []

    async def add_force_sub_channel(self, channel_id):
        try:
            await self.settings.update_one(
                {"type": "force_sub_channels"},
                {"$addToSet": {"channels": str(channel_id)}},
                upsert=True
            )
            logger.info(f"Added force sub channel {channel_id}")
        except Exception as e:
            logger.error(f"Error adding force sub channel {channel_id}: {e}")

    async def get_invite_requirement(self):
        try:
            settings = await self.settings.find_one({"type": "invite_requirement"})
            return settings.get("value", 0) if settings else 0
        except Exception as e:
            logger.error(f"Error retrieving invite requirement: {e}")
            return 0

    async def get_count_messages(self):
        try:
            settings = await self.settings.find_one({"type": "count_messages"})
            value = settings.get("value", True) if settings else True
            logger.info(f"Retrieved count_messages: {value}")
            return value
        except Exception as e:
            logger.error(f"Error retrieving count_messages: {e}")
            return True

    async def set_count_messages(self, value):
        try:
            result = await self.settings.update_one(
                {"type": "count_messages"},
                {"$set": {"value": value}},
                upsert=True
            )
            logger.info(f"Set count_messages to {value}")
            return result.matched_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error setting count_messages to {value}: {e}")
            return False

    async def get_last_reward_time(self):
        try:
            reward = await self.rewards.find_one({"type": "weekly_invites"})
            if not reward:
                await self.rewards.insert_one({"type": "weekly_invites", "last_reward": datetime.utcnow()})
                return datetime.utcnow()
            return reward["last_reward"]
        except Exception as e:
            logger.error(f"Error retrieving last reward time: {e}")
            return datetime.utcnow()

    async def update_reward_time(self):
        try:
            await self.rewards.update_one({"type": "weekly_invites"}, {"$set": {"last_reward": datetime.utcnow()}})
            logger.info("Updated weekly reward time")
        except Exception as e:
            logger.error(f"Error updating reward time: {e}")

    async def award_weekly_rewards(self):
        try:
            last_reward = await self.get_last_reward_time()
            if datetime.utcnow() < last_reward + timedelta(days=7):
                return False
            top_users = await self.get_top_users(by="invites", limit=3)
            reward_amount = 10000
            for user in top_users:
                user_id = user["user_id"]
                current_balance = user.get("balance", 0)
                await self.update_user(user_id, {"balance": current_balance + reward_amount})
                logger.info(f"Awarded {reward_amount} kyat to user {user_id}")
            await self.update_reward_time()
            return True
        except Exception as e:
            logger.error(f"Error awarding weekly rewards: {e}")
            return False

db = Database()