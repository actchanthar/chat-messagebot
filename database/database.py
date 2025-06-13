from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups
        self.rewards = self.db.rewards
        self.settings = self.db.settings
        self.channels = self.db.channels
        self.message_history = {}

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            if user:
                # Ensure message_timestamps is a list
                user["message_timestamps"] = user.get("message_timestamps", [])[:5]
                logger.info(f"Retrieved user {user_id} from database")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id, name, referred_by=None):
        try:
            user = {
                "user_id": user_id,
                "first_name": name.get("first_name", ""),
                "last_name": name.get("last_name", ""),
                "balance": 0,
                "messages": 0,
                "group_messages": {"-1002061898677": 0},
                "withdrawn_today": 0,
                "last_withdrawal": None,
                "banned": False,
                "notified_10kyat": False,
                "last_activity": datetime.utcnow(),
                "message_timestamps": [],  # Use list instead of deque
                "invites": 0,
                "pending_withdrawals": [],
                "referred_by": referred_by
            }
            result = await self.users.insert_one(user)
            logger.info(f"Created new user {user_id} with name {name}, referred by {referred_by}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            # Ensure message_timestamps is truncated to 5 items
            if "message_timestamps" in updates:
                updates["message_timestamps"] = updates["message_timestamps"][:5]
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
            if result.modified_count > 0:
                updates_log = {k: v for k, v in updates.items()}
                if "message_timestamps" in updates_log:
                    updates_log["message_timestamps"] = f"[{len(updates['message_timestamps'])} timestamps]"
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
            for user in users:
                user["message_timestamps"] = user.get("message_timestamps", [])[:5]
            logger.info(f"Retrieved all users: {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def get_top_users(self, limit=10, sort_by="messages"):
        try:
            if sort_by == "invites":
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "first_name": 1, "last_name": 1, "invites": 1, "balance": 1, "group_messages": 1, "_id": 0}
                ).sort("invites", -1).limit(limit).to_list(length=limit)
            else:
                top_users = await self.users.find(
                    {"banned": False},
                    {"user_id": 1, "first_name": 1, "last_name": 1, "messages": 1, "balance": 1, "group_messages": 1, "_id": 0}
                ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users by {sort_by}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users by {sort_by}: {e}")
            return []

    async def add_group(self, group_id):
        try:
            if group_id != "-1002061898677":
                logger.info(f"Attempted to add non-approved group {group_id}")
                return False
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
            if group_id != "-1002061898677":
                logger.info(f"Message count requested for non-approved group {group_id}")
                return 0
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
                {"$set": {"value": messages_per_kyat}},
                upsert=True
            )
            logger.info(f"Set message rate to: {messages_per_kyat} messages per kyat")
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_message_rate(self):
        try:
            setting = await self.settings.find_one({"type": "message_rate"})
            return setting["value"] if setting and "value" in setting else 3
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

    async def set_referral_reward(self, amount):
        try:
            await self.settings.update_one(
                {"type": "referral_reward"},
                {"$set": {"value": int(amount)}},
                upsert=True
            )
            logger.info(f"Set referral reward to: {amount} kyat")
            return True
        except Exception as e:
            logger.error(f"Error setting referral reward: {e}")
            return False

    async def get_referral_reward(self):
        try:
            setting = await self.settings.find_one({"type": "referral_reward"})
            return setting["value"] if setting and "value" in setting else 25
        except Exception as e:
            logger.error(f"Error retrieving referral reward: {e}")
            return 25

    async def add_channel(self, channel_id, channel_name):
        try:
            existing_channel = await self.channels.find_one({"channel_id": channel_id})
            if existing_channel:
                logger.info(f"Channel {channel_id} already exists")
                return "exists"
            result = await self.channels.insert_one({"channel_id": channel_id, "channel_name": channel_name})
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
            logger.info(f"Retrieved channels: {len(channels)} channels")
            return channels
        except Exception as e:
            logger.error(f"Error retrieving channels: {e}")
            return []

    async def add_bonus(self, user_id, amount):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            current_balance = user.get("balance", 0)
            await self.update_user(user_id, {"balance": current_balance + amount})
            logger.info(f"Added bonus of {amount} kyat to user {user_id}")
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
            new_from_balance = from_user.get("balance", 0) - amount
            new_to_balance = to_user.get("balance", 0) + amount
            await self.update_user(from_user_id, {"balance": new_from_balance})
            await self.update_user(to_user_id, {"balance": new_to_balance})
            logger.info(f"Transferred {amount} kyat from user {from_user_id} to user {to_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error transferring balance from {from_user_id} to {to_user_id}: {e}")
            return False

    async def reset_withdrawals(self, user_id=None):
        try:
            if user_id:
                result = await self.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"pending_withdrawals": []}}
                )
                logger.info(f"Reset pending withdrawals for user {user_id}")
                return result.modified_count > 0
            else:
                result = await self.users.update_many(
                    {},
                    {"$set": {"pending_withdrawals": []}}
                )
                logger.info(f"Reset pending withdrawals for {result.modified_count} users")
                return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resetting withdrawals: {e}")
            return False

    async def check_rate_limit(self, user_id, message_text=None):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False

            current_time = datetime.utcnow()
            if user_id not in self.message_history:
                self.message_history[user_id] = []

            timestamps = user.get("message_timestamps", [])
            timestamps.append(current_time)
            timestamps = timestamps[-5:]  # Keep last 5 timestamps
            await self.update_user(user_id, {"message_timestamps": timestamps})
            if len(timestamps) == 5 and (current_time - timestamps[0]).total_seconds() < 60:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return True

            if message_text:
                if self.message_history[user_id] and self.message_history[user_id][-1] == message_text:
                    logger.warning(f"Duplicate message detected for user {user_id}")
                    return True
                self.message_history[user_id].append(message_text)
                self.message_history[user_id] = self.message_history[user_id][-5:]  # Keep last 5 messages

            return False
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            return False

    async def increment_message_count(self, user_id):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            new_message_count = user.get("messages", 0) + 1
            group_messages = user.get("group_messages", {})
            group_messages["-1002061898677"] = group_messages.get("-1002061898677", 0) + 1
            await self.update_user(user_id, {
                "messages": new_message_count,
                "group_messages": group_messages
            })
            logger.info(f"Incremented message count for user {user_id} to {new_message_count}")
            return True
        except Exception as e:
            logger.error(f"Error incrementing message count for user {user_id}: {e}")
            return False

    async def update_user_name(self, user_id, first_name, last_name):
        try:
            updates = {
                "first_name": first_name,
                "last_name": last_name
            }
            result = await self.update_user(user_id, updates)
            logger.info(f"Updated name for user {user_id} to {first_name} {last_name}")
            return result
        except Exception as e:
            logger.error(f"Error updating name for user {user_id}: {e}")
            return False

# Singleton instance
db = Database()