from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from collections import deque

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
        self.channels = self.db.channels  # New collection for force-sub channels
        self.message_history = {}  # In-memory cache for duplicate checking
        self.message_rate = 3  # Default: 3 messages = 1 kyat

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
                "invites": 0,  # Track number of successful invites
                "referrer_id": None,  # Who referred this user
                "referral_link": f"https://t.me/ACTChatBot?start={user_id}"  # Unique referral link
            }
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id} with name {name}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            if "message_timestamps" in updates:
                updates["message_timestamps"] = list(updates["message_timestamps"])
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
            if result.modified_count > 0:
                updates_log = {k: v if k != "message_timestamps" else f"[{len(v)} timestamps]" for k, v in updates.items()}
                logger.info(f"Updated user {user_id}: {updates_log}")
                return True
            logger.info(f"No changes made to user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def get_top_users(self, limit=10, sort_by="messages"):
        try:
            if sort_by == "invites":
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "name": 1, "invites": 1, "balance": 1, "group_messages": 1, "_id": 0}
                ).sort("invites", -1).limit(limit).to_list(length=limit)
            else:
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "group_messages": 1, "_id": 0}
                ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {sort_by}: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users by {sort_by}: {e}")
            return []

    async def add_group(self, group_id):
        try:
            existing_group = await self.groups.find_one({"group_id": group_id})
            if existing_group:
                logger.info(f"Group {group_id} already exists")
                return "exists"
            await self.groups.insert_one({"group_id": group_id})
            logger.info(f"Added group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding group {group_id}: {e}")
            return False

    async def get_approved_groups(self):
        try:
            groups = await self.groups.find({}, {"group_id": 1, "_id": 0}).to_list(length=None)
            group_ids = [group["group_id"] for group in groups]
            logger.info(f"Retrieved approved groups: {group_ids}")
            return group_ids
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
            total_messages = result[0]["total_messages"] if result else 0
            logger.info(f"Total messages in group {group_id}: {total_messages}")
            return total_messages
        except Exception as e:
            logger.error(f"Error retrieving message count for group {group_id}: {e}")
            return 0

    async def get_last_reward_time(self):
        try:
            reward = await self.rewards.find_one({"type": "weekly"})
            if not reward:
                await self.rewards.insert_one({"type": "weekly", "last_reward": datetime.utcnow()})
                return datetime.utcnow()
            return reward["last_reward"]
        except Exception as e:
            logger.error(f"Error retrieving last reward time: {e}")
            return datetime.utcnow()

    async def update_reward_time(self):
        try:
            await self.rewards.update_one({"type": "weekly"}, {"$set": {"last_reward": datetime.utcnow()}})
            logger.info("Updated weekly reward time")
        except Exception as e:
            logger.error(f"Error updating reward time: {e}")

    async def award_weekly_rewards(self):
        try:
            last_reward = await self.get_last_reward_time()
            if datetime.utcnow() < last_reward + timedelta(days=7):
                return False

            top_users = await self.get_top_users(3)
            reward_amount = 100
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

    async def get_phone_bill_reward(self):
        try:
            setting = await self.settings.find_one({"type": "phone_bill_reward"})
            return setting["value"] if setting and "value" in setting else "Phone Bill 1000 kyat"
        except Exception as e:
            logger.error(f"Error retrieving phone_bill_reward: {e}")
            return "Phone Bill 1000 kyat"

    async def set_message_rate(self, rate):
        try:
            self.message_rate = rate
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"value": rate}},
                upsert=True
            )
            logger.info(f"Set message rate to {rate} messages per kyat")
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_message_rate(self):
        try:
            setting = await self.settings.find_one({"type": "message_rate"})
            return setting["value"] if setting and "value" in setting else self.message_rate
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return self.message_rate

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
                logger.warning(f"Rate limit exceeded for user {user_id} (5 messages per minute)")
                return True

            if message_text:
                if user_id in self.message_history and self.message_history[user_id] == message_text:
                    logger.warning(f"Duplicate message detected for user {user_id}")
                    return True
                self.message_history[user_id] = message_text

            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

    async def add_channel(self, channel每一个id, channel_name):
        try:
            existing_channel = await self.channels.find_one({"channel_id": channel_id})
            if existing_channel:
                logger.info(f"Channel {channel_id} already exists")
                return "exists"
            await self.channels.insert_one({"channel_id": channel_id, "name": channel_name})
            logger.info(f"Added channel {channel_id} ({channel_name})")
            return True
        except Exception as e:
            logger.error(f"Error adding channel {channel_id}: {e}")
            return False

    async def remove_channel(self, channel_id):
        try:
            result = await self.channels.delete_one({"channel_id": channel_id})
            if result.deleted_count > 0:
                logger.info(f"Removed channel {channel_id}")
                return True
            logger.info(f"Channel {channel_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error removing channel {channel_id}: {e}")
            return False

    async def get_channels(self):
        try:
            channels = await self.channels.find({}, {"channel_id": 1, "name": 1, "_id": 0}).to_list(length=None)
            logger.info(f"Retrieved channels: {channels}")
            return channels
        except Exception as e:
            logger.error(f"Error retrieving channels: {e}")
            return []

    async def set_invite_threshold(self, threshold):
        try:
            await self.settings.update_one(
                {"type": "invite_threshold"},
                {"$set": {"value": threshold}},
                upsert=True
            )
            logger.info(f"Set invite threshold to {threshold}")
            return True
        except Exception as e:
            logger.error(f"Error setting invite threshold: {e}")
            return False

    async def get_invite_threshold(self):
        try:
            setting = await self.settings.find_one({"type": "invite_threshold"})
            return setting["value"] if setting and "value" in setting else 15
        except Exception as e:
            logger.error(f"Error retrieving invite threshold: {e}")
            return 15

    async def increment_invite(self, referrer_id, invited_user_id):
        try:
            referrer = await self.get_user(referrer_id)
            invited_user = await self.get_user(invited_user_id)
            if not referrer or not invited_user:
                logger.error(f"Referrer {referrer_id} or invited user {invited_user_id} not found")
                return False

            await self.update_user(referrer_id, {"invites": referrer.get("invites", 0) + 1, "balance": referrer.get("balance", 0) + 25})
            await self.update_user(invited_user_id, {"balance": invited_user.get("balance", 0) + 50, "referrer_id": referrer_id})
            logger.info(f"Incremented invites for {referrer_id}, awarded 25 kyat. Awarded 50 kyat to {invited_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing invite for {referrer_id}: {e}")
            return False

    async def reset_withdrawals(self, user_id=None):
        try:
            if user_id:
                await self.update_user(user_id, {"withdrawn_today": 0, "last_withdrawal": None})
                logger.info(f"Reset withdrawals for user {user_id}")
            else:
                await self.users.update_many({}, {"$set": {"withdrawn_today": 0, "last_withdrawal": None}})
                logger.info("Reset withdrawals for all users")
            return True
        except Exception as e:
            logger.error(f"Error resetting withdrawals: {e}")
            return False

    async def add_bonus(self, user_id, amount):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            new_balance = user.get("balance", 0) + amount
            await self.update_user(user_id, {"balance": new_balance})
            logger.info(f"Added {amount} kyat bonus to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding bonus to user {user_id}: {e}")
            return False

    async def transfer_balance(self, from_user_id, to_user_id, amount):
        try:
            from_user = await self.get_user(from_user_id)
            to_user = await self.get_user(to_user_id)
            if not from_user or not to_user:
                return False
            if from_user.get("balance", 0) < amount:
                return False
            await self.update_user(from_user_id, {"balance": from_user.get("balance", 0) - amount})
            await self.update_user(to_user_id, {"balance": to_user.get("balance", 0) + amount})
            logger.info(f"Transferred {amount} kyat from {from_user_id} to {to_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error transferring balance: {e}")
            return False

    async def get_random_users(self, count=2):
        try:
            users = await self.users.find({"banned": False}).to_list(length=None)
            from random import sample
            return sample(users, min(count, len(users)))
        except Exception as e:
            logger.error(f"Error getting random users: {e}")
            return []

db = Database()