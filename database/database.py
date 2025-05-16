from pymongo import MongoClient
from collections import deque
import datetime
import logging
from config import MONGODB_URL, MONGODB_NAME, DEFAULT_REQUIRED_INVITES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongodb_url, mongodb_name):
        self.client = MongoClient(mongodb_url)
        self.db = self.client[mongodb_name]

    async def get_user(self, user_id: str):
        user = self.db.users.find_one({"user_id": user_id})
        if user and "message_timestamps" in user:
            user["message_timestamps"] = deque(user["message_timestamps"], maxlen=1000)
        logger.info(f"Retrieved user {user_id} from database: {user}")
        return user

    async def create_user(self, user_id: str, name: str, referrer_id: str = None):
        user = {
            "user_id": user_id,
            "name": name,
            "balance": 0,
            "messages": 0,
            "group_messages": {},
            "message_timestamps": [],
            "last_activity": datetime.datetime.utcnow(),
            "referrer_id": referrer_id,
            "invited_users": 0,
            "subscribed_channels": []
        }
        self.db.users.insert_one(user)
        logger.info(f"Created user {user_id} in database")
        user["message_timestamps"] = deque([], maxlen=1000)
        return user

    async def update_user(self, user_id: str, updates: dict):
        if "message_timestamps" in updates and isinstance(updates["message_timestamps"], deque):
            updates["message_timestamps"] = list(updates["message_timestamps"])
        self.db.users.update_one({"user_id": user_id}, {"$set": updates})
        logger.info(f"Updated user {user_id}: {updates}")

    async def check_rate_limit(self, user_id: str, max_messages: int = 5, time_window: int = 60) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        now = datetime.datetime.utcnow()
        timestamps = user.get("message_timestamps", deque(maxlen=1000))

        while timestamps and (now - timestamps[0]).total_seconds() > time_window:
            timestamps.popleft()

        if len(timestamps) >= max_messages:
            logger.warning(f"User {user_id} exceeded rate limit: {len(timestamps)} messages in {time_window} seconds")
            return False

        timestamps.append(now)
        await self.update_user(user_id, {"message_timestamps": timestamps})
        return True

    async def get_force_sub_channels(self):
        settings = self.db.settings.find_one({"type": "force_sub_channels"})
        channels = settings.get("value", []) if settings else []
        logger.info(f"Retrieved force-sub channels: {channels}")
        return channels

    async def set_force_sub_channels(self, channels: list) -> bool:
        try:
            self.db.settings.update_one(
                {"type": "force_sub_channels"},
                {"$set": {"value": channels}},
                upsert=True
            )
            logger.info(f"Updated force-sub channels: {channels}")
            return True
        except Exception as e:
            logger.error(f"Error updating force-sub channels: {e}")
            return False

    async def update_subscription_status(self, user_id: str, channel_id: str, is_member: bool):
        user = await self.get_user(user_id)
        if not user:
            return
        subscribed_channels = user.get("subscribed_channels", [])
        if is_member and channel_id not in subscribed_channels:
            subscribed_channels.append(channel_id)
        elif not is_member and channel_id in subscribed_channels:
            subscribed_channels.remove(channel_id)
        await self.update_user(user_id, {"subscribed_channels": subscribed_channels})

    async def increment_invited_users(self, user_id: str):
        self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"invited_users": 1}}
        )
        logger.info(f"Incremented invited_users for user {user_id}")

    async def get_all_users(self):
        users = list(self.db.users.find())
        for user in users:
            if "message_timestamps" in user:
                user["message_timestamps"] = deque(user["message_timestamps"], maxlen=1000)
        return users

    async def get_phone_bill_reward(self):
        return 1000

    async def can_withdraw(self, user_id: str) -> tuple[bool, str]:
        user = await self.get_user(user_id)
        if not user:
            return False, "User not found. Please start with /start."
        
        invited_users = user.get("invited_users", 0)
        required_invites = DEFAULT_REQUIRED_INVITES  # From config.py (15 invites)
        
        if invited_users < required_invites:
            return False, (
                f"You need to invite at least {required_invites} users to withdraw. "
                f"You have invited {invited_users} users so far.\n"
                f"ငွေထုတ်ယူရန် အနည်းဆုံး {required_invites} ဦးကို ဖိတ်ခေါ်ရပါမည်။ "
                f"သင်သည် ယခုထိ {invited_users} ဦးကို ဖိတ်ခေါ်ထားပါသည်။"
            )
        return True, ""

# Initialize and export the db instance
db = Database(MONGODB_URL, MONGODB_NAME)