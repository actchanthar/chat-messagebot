from pymongo import MongoClient
from bson import ObjectId
from config import MONGODB_URL, MONGODB_NAME
import datetime
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users_collection = self.db.users
        self.settings_collection = self.db.settings

    def get_user(self, user_id: str):
        user = self.users_collection.find_one({"user_id": user_id})
        if user:
            logger.info(f"Retrieved user {user_id} from database: {user}")
        return user

    def create_user(self, user_id: str, name: str, referrer_id: str = None):
        user = {
            "user_id": user_id,
            "name": name,
            "balance": 0.0,
            "messages": 0,
            "notified_10kyat": False,
            "last_withdrawal": None,
            "withdrawn_today": 0,
            "group_messages": {},
            "message_timestamps": [],
            "subscribed_channels": [],
            "pending_withdrawals": [],
            "invited_users": 0,
        }
        if referrer_id:
            user["referrer_id"] = referrer_id
        result = self.users_collection.insert_one(user)
        logger.info(f"Created user {user_id} with referrer {referrer_id}, result: {result.inserted_id}")
        return self.get_user(user_id)

    def update_user(self, user_id: str, update_data: dict):
        if "message_timestamps" in update_data:
            update_data["message_timestamps"] = update_data["message_timestamps"][-1000:]
        result = self.users_collection.update_one(
            {"user_id": user_id}, {"$set": update_data}
        )
        logger.info(f"Updated user {user_id}: {update_data}, result: {result.modified_count}")
        return result.modified_count > 0

    def get_bot_settings(self):
        settings = self.settings_collection.find_one({"_id": "settings"}) or {}
        logger.info(f"Retrieved bot settings: {settings}")
        return settings

    def update_bot_settings(self, data: dict):
        result = self.settings_collection.update_one(
            {"_id": "settings"},
            {"$set": data},
            upsert=True
        )
        logger.info(f"Updated bot settings: {data}, result: {result.modified_count}")
        return result.modified_count > 0

    # Keep other methods as in your version
    def increment_invited_users(self, user_id: str):
        result = self.users_collection.update_one(
            {"user_id": user_id}, {"$inc": {"invited_users": 1}}
        )
        logger.info(f"Incremented invited_users for user {user_id}, result: {result.modified_count}")
        return result.modified_count > 0

    def get_all_users(self):
        users = list(self.users_collection.find())
        logger.info(f"Retrieved {len(users)} users from database")
        return users

    def get_total_users(self):
        total = self.users_collection.count_documents({})
        logger.info(f"Retrieved total users: {total}")
        return total

    def get_required_channels(self):
        settings = self.settings_collection.find_one({"_id": "channels"})
        channels = settings.get("required_channels", []) if settings else []
        logger.info(f"Retrieved required channels: {channels}")
        return channels

    def set_required_channels(self, channels: list):
        result = self.settings_collection.update_one(
            {"_id": "channels"},
            {"$set": {"required_channels": channels}},
            upsert=True
        )
        logger.info(f"Set required channels to {channels}, result: {result.modified_count}")
        return result.modified_count > 0

    def get_phone_bill_reward(self):
        settings = self.settings_collection.find_one({"_id": "phone_bill_reward"})
        reward = settings.get("reward", "1000 Kyat") if settings else "1000 Kyat"
        logger.info(f"Retrieved phone bill reward: {reward}")
        return reward

    def get_phone_bill_reward_text(self):
        settings = self.settings_collection.find_one({"_id": "phone_bill_reward"})
        reward = settings.get("reward", "1000 Kyat") if settings else "1000 Kyat"
        logger.info(f"Retrieved phone bill reward text: {reward}")
        return reward

    def set_phone_bill_reward_text(self, reward_text: str):
        result = self.settings_collection.update_one(
            {"_id": "phone_bill_reward"},
            {"$set": {"reward": reward_text}},
            upsert=True
        )
        logger.info(f"Set phone bill reward text to {reward_text}, result: {result.modified_count}")
        return result.modified_count > 0

    def mark_broadcast_failure(self, user_id: str):
        result = self.users_collection.update_one(
            {"user_id": user_id}, {"$set": {"failed_broadcast": True}}
        )
        logger.info(f"Marked broadcast failure for user {user_id}, result: {result.modified_count}")
        return result.modified_count > 0

    def delete_failed_broadcast_users(self):
        result = self.users_collection.delete_many({"failed_broadcast": True})
        logger.info(f"Deleted {result.deleted_count} users with failed broadcasts")
        return result.deleted_count

    def get_top_users_by_invites(self):
        users = list(
            self.users_collection.find()
            .sort("invited_users", -1)
            .limit(10)
        )
        logger.info(f"Retrieved {len(users)} top users by invites")
        return users

    def can_withdraw(self, user_id: str, bot_username: str):
        logger.info(f"Starting can_withdraw for user {user_id}")
        try:
            user = self.get_user(user_id)
            logger.info(f"User data for {user_id}: {user}")
            if not user:
                logger.error(f"User {user_id} not found")
                return False, "User not found. Please start with /start."

            from config import WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, DEFAULT_REQUIRED_INVITES
            balance = user.get("balance", 0)
            logger.info(f"User {user_id} balance: {balance}")
            if balance < WITHDRAWAL_THRESHOLD:
                return False, f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw."

            required_channels = self.get_required_channels() or []
            logger.info(f"Required channels: {required_channels}")
            if required_channels:
                subscribed_channels = user.get("subscribed_channels", [])
                logger.info(f"User {user_id} subscribed channels: {subscribed_channels}")
                not_subscribed = [ch for ch in required_channels if ch not in subscribed_channels]
                if not_subscribed:
                    return False, "You must join all required channels to withdraw. Use /start to see the list."

            invited_users = user.get("invited_users", 0)
            logger.info(f"User {user_id} invited_users: {invited_users}")
            if invited_users < DEFAULT_REQUIRED_INVITES:
                invite_link = f"https://t.me/{bot_username}?start=referral_{user_id}"
                return False, (
                    f"You need at least {DEFAULT_REQUIRED_INVITES} invited users to withdraw. You have {invited_users}.\n"
                    f"ငွေထုတ်ယူရန် အနည်းဆုံး {DEFAULT_REQUIRED_INVITES} ဦးကို ဖိတ်ခေါ်ရပါမည်။ သင်သည် ယခုထိ {invited_users} ဦးကို ဖိတ်ခေါ်ထားပါသည်။\n"
                    f"Your Invite Link: {invite_link}"
                )

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.datetime.now()
            logger.info(f"User {user_id} last_withdrawal: {last_withdrawal}, withdrawn_today: {withdrawn_today}")
            if last_withdrawal:
                last_withdrawal_date = last_withdrawal.date()
                current_date = current_time.date()
                if last_withdrawal_date == current_date and withdrawn_today >= DAILY_WITHDRAWAL_LIMIT:
                    return False, f"You've reached the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}."

            logger.info(f"User {user_id} is eligible to withdraw")
            return True, "Eligible to withdraw."
        except Exception as e:
            logger.error(f"Error in can_withdraw for user {user_id}: {str(e)}", exc_info=True)
            return False, "Error checking eligibility. Please try again later or contact support."

    def check_rate_limit(self, user_id: str, time_window: int = 30) -> bool:
        user = self.get_user(user_id)
        if not user:
            logger.info(f"User {user_id} not found for rate limit check")
            return False
        timestamps = user.get("message_timestamps", [])
        now = datetime.datetime.now()
        recent_timestamps = [ts for ts in timestamps if (now - ts).total_seconds() <= time_window]
        logger.info(f"User {user_id} has {len(recent_timestamps)} messages in last {time_window} seconds")
        return len(recent_timestamps) < 2

db = Database()