from pymongo import MongoClient
from collections import deque
import datetime
import logging
from config import MONGODB_URL, MONGODB_NAME, DEFAULT_REQUIRED_INVITES, ADMIN_IDS

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
        }
        self.db.users.insert_one(user)
        logger.info(f"Created user {user_id} in database")
        user["message_timestamps"] = deque([], maxlen=1000)
        return user

    async def update_user(self, user_id: str, updates: dict):
        if "message_timestamps" in updates and isinstance(updates["message_timestamps"], deque):
            updates["message_timestamps"] = list(updates["message_timestamps"])
        result = self.db.users.update_one({"user_id": user_id}, {"$set": updates})
        logger.info(f"Updated user {user_id}: {updates}, result: {result.modified_count}")
        return result

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

    async def increment_invited_users(self, user_id: str):
        result = self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"invited_users": 1}}
        )
        logger.info(f"Incremented invited_users for user {user_id}, result: {result.modified_count}")
        return result.modified_count > 0

    async def get_all_users(self):
        users = list(self.db.users.find())
        for user in users:
            if "message_timestamps" in user:
                user["message_timestamps"] = deque(user["message_timestamps"], maxlen=1000)
        return users

    async def get_phone_bill_reward(self):
        return 1000

    async def can_withdraw(self, user_id: str, bot_username: str) -> tuple[bool, str]:
        user = await self.get_user(user_id)
        if not user:
            return False, "User not found. Please start with /start."

        # Admins bypass invite requirement
        if user_id in ADMIN_IDS:
            return True, ""

        invited_users = user.get("invited_users", 0)
        required_invites = DEFAULT_REQUIRED_INVITES

        if invited_users < required_invites:
            invite_link = f"https://t.me/{bot_username}?start=referrer={user_id}"
            return False, (
                f"You need to invite at least {required_invites} users to withdraw. "
                f"You have invited {invited_users} users so far.\n"
                f"ငွေထုတ်ယူရန် အနည်းဆုံး {required_invites} ဦးကို ဖိတ်ခေါ်ရပါမည်။ "
                f"သင်သည် ယခုထိ {invited_users} ဦးကို ဖိတ်ခေါ်ထားပါသည်။\n\n"
                f"Your Link: {invite_link}\n"
                "ဤလင့်ခ်ကို မျှဝေပြီး အသုံးပြုသူများကို ဖိတ်ကြားပါ။ "
                "ဖိတ်ကြားမှုများကို ချက်ချင်းရေတွက်သော်လည်း ငွေထုတ်ရန် လိုအပ်သော ချန်နယ်များသို့ ဝင်ရောက်ရပါမည်။"
            )
        return True, ""

    async def set_required_channels(self, channels: list):
        self.db.required_channels.replace_one(
            {"_id": "force_sub"},
            {"_id": "force_sub", "channels": channels},
            upsert=True
        )
        logger.info(f"Set required channels to {channels}")

    async def get_required_channels(self):
        result = self.db.required_channels.find_one({"_id": "force_sub"})
        channels = result["channels"] if result and "channels" in result else []
        logger.info(f"Retrieved required channels: {channels}")
        return channels

    async def get_message_rate(self):
        config = self.db.bot_config.find_one({"_id": "message_rate"})
        rate = config["rate"] if config and "rate" in config else 1  # Default: 1 message = 1 kyat
        logger.info(f"Retrieved message rate: {rate} messages per kyat")
        return rate

    async def set_message_rate(self, rate: int):
        self.db.bot_config.replace_one(
            {"_id": "message_rate"},
            {"_id": "message_rate", "rate": rate},
            upsert=True
        )
        logger.info(f"Set message rate to {rate} messages per kyat")

    async def create_withdrawal(self, withdrawal: dict):
        self.db.withdrawals.insert_one(withdrawal)
        logger.info(f"Created withdrawal {withdrawal['withdrawal_id']} for user {withdrawal['user_id']}")

    async def get_withdrawal(self, withdrawal_id: str):
        withdrawal = self.db.withdrawals.find_one({"withdrawal_id": withdrawal_id})
        logger.info(f"Retrieved withdrawal {withdrawal_id}: {withdrawal}")
        return withdrawal

    async def update_withdrawal(self, withdrawal_id: str, updates: dict):
        result = self.db.withdrawals.update_one({"withdrawal_id": withdrawal_id}, {"$set": updates})
        logger.info(f"Updated withdrawal {withdrawal_id}: {updates}, result: {result.modified_count}")
        return result

    async def get_user_withdrawals(self, user_id: str):
        withdrawals = list(self.db.withdrawals.find({"user_id": user_id}))
        logger.info(f"Retrieved {len(withdrawals)} withdrawals for user {user_id}")
        return withdrawals

    async def get_pending_withdrawals(self):
        withdrawals = list(self.db.withdrawals.find({"status": "pending"}))
        logger.info(f"Retrieved {len(withdrawals)} pending withdrawals")
        return withdrawals

db = Database(MONGODB_URL, MONGODB_NAME)