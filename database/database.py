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
        self.channels = self.db.channels  # For force-sub channels
        self.message_history = {}  # In-memory cache for duplicate checking

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            logger.info(f"Retrieved user {user_id}: {user}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id, name, referrer_id=None):
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
                "invites": 0,
                "referrer_id": referrer_id,
                "last_couple_time": None,
                "subscribed_channels": []
            }
            result = await self.users.insert_one(user)
            logger.info(f"Created user {user_id} with name {name}, referrer {referrer_id}")
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

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def get_top_users(self, limit=10, by="messages"):
        try:
            if by == "invites":
                sort_key = "invites"
            else:
                sort_key = "messages"
            top_users = await self.users.find(
                {"banned": False},
                {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "group_messages": 1, "invites": 1, "_id": 0}
            ).sort(sort_key, -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {sort_key}: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users by {sort_key}: {e}")
            return []

    async def add_group(self, group_id):
        try:
            existing_group = await self.groups.find_one({"group_id": group_id})
            if existing_group:
                logger.info(f"Group {group_id} already exists")
                return "exists"
            result = await self.groups.insert_one({"group_id": group_id})
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

    async def set_message_rate(self, messages_per_kyat):
        try:
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"messages_per_kyat": messages_per_kyat}},
                upsert=True
            )
            logger.info(f"Set message rate to {messages_per_kyat} messages per kyat")
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_message_rate(self):
        try:
            setting = await self.settings.find_one({"type": "message_rate"})
            return setting["messages_per_kyat"] if setting and "messages_per_kyat" in setting else 3
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

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

    async def add_channel(self, channel_id, channel_name):
        try:
            existing_channel = await self.channels.find_one({"channel_id": channel_id})
            if existing_channel:
                logger.info(f"Channel {channel_id} already exists")
                return "exists"
            result = await self.channels.insert_one({"channel_id": channel_id, "name": channel_name})
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
            channels = await self.channels.find().to_list(length=None)
            logger.info(f"Retrieved {len(channels)} channels")
            return channels
        except Exception as e:
            logger.error(f"Error retrieving channels: {e}")
            return []

    async def update_user_subscription(self, user_id, channel_id, subscribed=True):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            subscribed_channels = user.get("subscribed_channels", [])
            if subscribed and channel_id not in subscribed_channels:
                subscribed_channels.append(channel_id)
            elif not subscribed and channel_id in subscribed_channels:
                subscribed_channels.remove(channel_id)
            await self.update_user(user_id, {"subscribed_channels": subscribed_channels})
            logger.info(f"Updated subscription for user {user_id}: channel {channel_id}, subscribed={subscribed}")
            return True
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False

    async def check_user_subscription(self, user_id, channel_id):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            return channel_id in user.get("subscribed_channels", [])
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            return False

    async def set_invite_requirement(self, invites_needed):
        try:
            await self.settings.update_one(
                {"type": "invite_requirement"},
                {"$set": {"invites_needed": invites_needed}},
                upsert=True
            )
            logger.info(f"Set invite requirement to {invites_needed}")
            return True
        except Exception as e:
            logger.error(f"Error setting invite requirement: {e}")
            return False

    async def get_invite_requirement(self):
        try:
            setting = await self.settings.find_one({"type": "invite_requirement"})
            return setting["invites_needed"] if setting and "invites_needed" in setting else 15
        except Exception as e:
            logger.error(f"Error retrieving invite requirement: {e}")
            return 15

    async def add_invite(self, inviter_id, invited_id):
        try:
            inviter = await self.get_user(inviter_id)
            if not inviter:
                return False
            invites = inviter.get("invites", 0) + 1
            await self.update_user(inviter_id, {"invites": invites})
            logger.info(f"Added invite for {inviter_id}, new count: {invites}")
            return True
        except Exception as e:
            logger.error(f"Error adding invite for {inviter_id}: {e}")
            return False

    async def add_bonus(self, user_id, amount):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            current_balance = user.get("balance", 0)
            await self.update_user(user_id, {"balance": current_balance + amount})
            logger.info(f"Added bonus {amount} kyat to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding bonus for user {user_id}: {e}")
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
            logger.error(f"Error transferring balance from {from_user_id} to {to_user_id}: {e}")
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
            logger.error(f"Error resetting withdrawals for {user_id or 'all users'}: {e}")
            return False

    async def toggle_message_counting(self, enable):
        try:
            await self.settings.update_one(
                {"type": "message_counting"},
                {"$set": {"enabled": enable}},
                upsert=True
            )
            logger.info(f"Message counting {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error toggling message counting: {e}")
            return False

    async def is_message_counting_enabled(self):
        try:
            setting = await self.settings.find_one({"type": "message_counting"})
            return setting["enabled"] if setting and "enabled" in setting else True
        except Exception as e:
            logger.error(f"Error checking message counting status: {e}")
            return True

    async def get_random_couple(self, user_id):
        try:
            users = await self.get_all_users()
            if len(users) < 2:
                return None
            user = await self.get_user(user_id)
            if not user:
                return None
            last_couple_time = user.get("last_couple_time")
            if last_couple_time and (datetime.utcnow() - last_couple_time).total_seconds() < 600:
                return None
            eligible_users = [u for u in users if u["user_id"] != user_id and not u.get("banned", False)]
            if not eligible_users:
                return None
            partner = random.choice(eligible_users)
            await self.update_user(user_id, {"last_couple_time": datetime.utcnow()})
            return partner
        except Exception as e:
            logger.error(f"Error getting random couple for {user_id}: {e}")
            return None

# Singleton instance
db = Database()