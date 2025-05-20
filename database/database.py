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
                "referrals": [],  # Added for referral tracking
                "invite_requirement": 15  # Default invite requirement
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

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def get_top_users(self, limit=10):
        try:
            top_users = await self.users.find(
                {"banned": False},
                {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "group_messages": 1, "referrals": 1, "_id": 0}
            ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users: {e}")
            return []

    async def add_group(self, group_id):
        try:
            if await self.groups.find_one({"group_id": group_id}):
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
            return setting.get("value", "Phone Bill 1000 kyat")
        except Exception as e:
            logger.error(f"Error retrieving phone_bill_reward: {e}")
            return "Phone Bill 1000 kyat"

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

    # Force Subscription Methods
    async def add_force_sub_channel(self, channel_id):
        try:
            await self.settings.update_one(
                {"type": "force_sub_channels"},
                {"$addToSet": {"channels": channel_id}},
                upsert=True
            )
            logger.info(f"Added force sub channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding force sub channel {channel_id}: {e}")
            return False

    async def remove_force_sub_channel(self, channel_id):
        try:
            await self.settings.update_one(
                {"type": "force_sub_channels"},
                {"$pull": {"channels": channel_id}}
            )
            logger.info(f"Removed force sub channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing force sub channel {channel_id}: {e}")
            return False

    async def get_force_sub_channels(self):
        try:
            setting = await self.settings.find_one({"type": "force_sub_channels"})
            return setting.get("channels", []) if setting else []
        except Exception as e:
            logger.error(f"Error retrieving force sub channels: {e}")
            return []

    async def check_user_subscription(self, user_id, channel_id):
        try:
            chat_member = await self.client.get_chat_member(channel_id, int(user_id))
            return chat_member.status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
            return False

    # Referral Methods
    async def add_referral(self, referrer_id, referred_id):
        try:
            await self.users.update_one(
                {"user_id": referrer_id},
                {"$addToSet": {"referrals": referred_id}}
            )
            logger.info(f"Added referral {referred_id} for user {referrer_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding referral for user {referrer_id}: {e}")
            return False

    async def get_referrals(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user.get("referrals", [])
        except Exception as e:
            logger.error(f"Error retrieving referrals for user {user_id}: {e}")
            return []

    # Message Rate Setting
    async def set_message_rate(self, messages_per_kyat):
        try:
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"value": messages_per_kyat}},
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
            return setting.get("value", 3)  # Default: 3 messages = 1 kyat
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

# Singleton instance with bot client injection
class DatabaseWithClient(Database):
    def __init__(self, bot_client):
        super().__init__()
        self.client = bot_client

db = None

def init_db(bot_client):
    global db
    db = DatabaseWithClient(bot_client)