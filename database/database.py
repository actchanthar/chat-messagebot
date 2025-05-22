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
            if user:
                logger.debug(f"Retrieved user {user_id}")
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
                    "name": name,
                    "username": username,
                    "balance": 0.0,
                    "messages": 0,
                    "group_messages": {"-1002061898677": 0},
                    "withdrawn_today": 0,
                    "last_withdrawal": None,
                    "banned": False,
                    "notified_10kyat": False,
                    "last_activity": datetime.utcnow(),
                    "message_timestamps": deque(maxlen=5),
                    "referrer": None,
                    "invites": [],
                    "invite_count": 0
                }
                await self.users.insert_one(user)
                logger.info(f"Created user {user_id} with name {name}, username {username}")
                await self._increment_total_users()
                return user
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} error creating user {user_id}: {e}")
                if "duplicate key" in str(e).lower():
                    logger.warning(f"User {user_id} already exists")
                    return await self.get_user(user_id)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return None
        return None

    async def update_user(self, user_id, updates):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self.users.update_one({"user_id": str(user_id)}, {"$set": updates})
                if result.modified_count > 0:
                    updates_log = {k: v if k != "message_timestamps" else f"[{len(updates['message_timestamps'])} timestamps]" for k, v in updates.items()}
                    logger.debug(f"Updated user {user_id}: {updates_log}")
                    return True
                logger.debug(f"No changes made to user {user_id}")
                return False
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} error updating user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return False
        return False

    async def get_all_users(self):
        try:
            users = await self.users.find(
                {},
                {"user_id": 1, "name": 1, "username": 1, "messages": 1, "balance": 1, "group_messages": 1, "invite_count": 1}
            ).to_list(length=None)
            logger.debug(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def get_top_users(self, by="messages", limit=10):
        try:
            sort_field = "invite_count" if by == "invites" else "messages"
            top_users = await self.users.find(
                {"banned": False, sort_field: {"$gt": 0}},
                {"user_id": 1, "name": 1, "username": 1, "messages": 1, "balance": 1, "group_messages": 1, "invite_count": 1, "_id": 0}
            ).sort(sort_field, -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {by}: {[u['user_id'] for u in top_users]}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users by {by}: {e}")
            return []

    async def get_total_users(self):
        try:
            stats = await self.settings.find_one({"type": "total_users"})
            count = stats.get("count", 0) if stats else 0
            if count == 0:
                count = await self.users.count_documents({})
                await self.settings.update_one(
                    {"type": "total_users"},
                    {"$set": {"count": count}},
                    upsert=True
                )
            logger.debug(f"Retrieved total users: {count}")
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
            logger.debug("Incremented total users")
        except Exception as e:
            logger.error(f"Error incrementing total users: {e}")

    async def add_group(self, group_id):
        try:
            if await self.groups.find_one({"group_id": str(group_id)}):
                logger.info(f"Group {group_id} already exists")
                return "exists"
            await self.groups.insert_one({"group_id": str(group_id)})
            logger.info(f"Added group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding group {group_id}: {e}")
            return False

    async def get_approved_groups(self):
        try:
            groups = await self.groups.find({}, {"group_id": 1, "_id": 0}).to_list(length=None)
            return [group["group_id"] for group in groups]
        except Exception as e:
            logger.error(f"Error retrieving approved groups: {e}")
            return []

    async def get_group_message_count(self, group_id):
        try:
            pipeline = [
                {"$match": {f"group_messages.{group_id}": {"$exists": True}}},
                {"$group": {"_id": None, "total_messages": {"$sum": f"$group_messages.{group_id}"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=None)
            return result[0]["total_messages"] if result else 0
        except Exception as e:
            logger.error(f"Error retrieving message count for group {group_id}: {e}")
            return 0

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

    async def get_phone_bill_reward(self):
        try:
            setting = await self.settings.find_one({"type": "phone_bill_reward"})
            return setting.get("value", "Phone Bill 1000 kyat") if setting else "Phone Bill 1000 kyat"
        except Exception as e:
            logger.error(f"Error retrieving phone_bill_reward: {e}")
            return "Phone Bill 1000 kyat"

    async def set_phone_bill_reward(self, reward_text):
        try:
            await self.settings.update_one(
                {"type": "phone_bill_reward"},
                {"$set": {"value": reward_text}},
                upsert=True
            )
            logger.info(f"Set phone_bill_reward to: {reward_text}")
            return True
        except Exception as e:
            logger.error(f"Error setting phone_bill_reward: {e}")
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
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return True
            if message_text and user_id in self.message_history and self.message_history[user_id] == message_text:
                logger.warning(f"Duplicate message from user {user_id}")
                return True
            self.message_history[user_id] = message_text
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

    async def get_force_sub_channels(self):
        try:
            settings = await self.settings.find_one({"type": "force_sub_channels"})
            channels = settings.get("channels", []) if settings else []
            logger.info(f"Retrieved force sub channels: {channels}")
            return channels
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

    async def remove_force_sub_channel(self, channel_id):
        try:
            await self.settings.update_one(
                {"type": "force_sub_channels"},
                {"$pull": {"channels": str(channel_id)}}
            )
            logger.info(f"Removed force sub channel {channel_id}")
        except Exception as e:
            logger.error(f"Error removing force sub channel {channel_id}: {e}")

    async def get_invite_requirement(self):
        try:
            settings = await self.settings.find_one({"type": "invite_requirement"})
            return settings.get("value", 0) if settings else 0
        except Exception as e:
            logger.error(f"Error retrieving invite requirement: {e}")
            return 0

    async def set_invite_requirement(self, value):
        try:
            await self.settings.update_one(
                {"type": "invite_requirement"},
                {"$set": {"value": value}},
                upsert=True
            )
            logger.info(f"Set invite requirement to {value}")
        except Exception as e:
            logger.error(f"Error setting invite requirement: {e}")

    async def add_invite(self, referrer_id, invitee_id):
        try:
            referrer = await self.get_user(referrer_id)
            if not referrer:
                logger.warning(f"Referrer {referrer_id} not found for invite {invitee_id}")
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
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")

    async def get_last_couple_time(self):
        try:
            setting = await self.settings.find_one({"type": "last_couple_time"})
            return setting.get("value") if setting else datetime.utcnow() - timedelta(minutes=11)
        except Exception as e:
            logger.error(f"Error retrieving last couple time: {e}")
            return datetime.utcnow() - timedelta(minutes=11)

    async def set_last_couple_time(self, time):
        try:
            await self.settings.update_one(
                {"type": "last_couple_time"},
                {"$set": {"value": time}},
                upsert=True
            )
            logger.info(f"Set last couple time to {time}")
        except Exception as e:
            logger.error(f"Error setting last couple time: {e}")

    async def get_random_users(self, count=2):
        try:
            pipeline = [{"$match": {"banned": False}}, {"$sample": {"size": count}}]
            users = await self.users.aggregate(pipeline).to_list(length=count)
            return users
        except Exception as e:
            logger.error(f"Error retrieving random users: {e}")
            return []

    async def get_count_messages(self):
        try:
            settings = await self.settings.find_one({"type": "count_messages"})
            return settings.get("value", True) if settings else True
        except Exception as e:
            logger.error(f"Error retrieving count_messages: {e}")
            return True

    async def set_count_messages(self, value):
        try:
            await self.settings.update_one(
                {"type": "count_messages"},
                {"$set": {"value": value}},
                upsert=True
            )
            logger.info(f"Set count_messages to {value}")
        except Exception as e:
            logger.error(f"Error setting count_messages: {e}")

db = Database()