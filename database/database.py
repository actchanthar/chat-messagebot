from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime
from bson import ObjectId

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.channels = self.db.channels
        self.withdrawals = self.db.withdrawals
        self.settings = self.db.settings

    async def create_user(self, user_id: str, name: str, invited_by: str = None) -> dict:
        user = {
            "user_id": user_id,
            "name": name,
            "balance": 0,
            "messages": 0,
            "group_messages": {},
            "invites": 0,
            "invited_by": invited_by,
            "subscriptions": [],
            "banned": False,
            "created_at": datetime.utcnow()
        }
        try:
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def get_user(self, user_id: str) -> dict:
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, data: dict) -> bool:
        try:
            result = await self.users.update_one({"user_id": user_id}, {"$set": data})
            logger.info(f"Updated user {user_id}: {data}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_all_users(self) -> list:
        try:
            users = await self.users.find().to_list(None)
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def add_invite(self, inviter_id: str, invitee_id: str) -> bool:
        try:
            await self.users.update_one(
                {"user_id": inviter_id},
                {"$inc": {"invites": 1}, "$push": {"invited_users": invitee_id}}
            )
            logger.info(f"Added invite for {inviter_id}: {invitee_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding invite for {inviter_id}: {e}")
            return False

    async def get_invites(self, user_id: str) -> int:
        try:
            user = await self.get_user(user_id)
            return user.get("invites", 0) if user else 0
        except Exception as e:
            logger.error(f"Error getting invites for {user_id}: {e}")
            return 0

    async def add_channel(self, channel_id: str, name: str, username: str = None) -> bool:
        try:
            await self.channels.update_one(
                {"channel_id": channel_id},
                {"$set": {"name": name, "username": username, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Added/updated channel {channel_id}: {name}")
            return True
        except Exception as e:
            logger.error(f"Error adding channel {channel_id}: {e}")
            return False

    async def delete_channel(self, channel_id: str) -> bool:
        try:
            result = await self.channels.delete_one({"channel_id": channel_id})
            logger.info(f"Deleted channel {channel_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting channel {channel_id}: {e}")
            return False

    async def get_channels(self) -> list:
        try:
            channels = await self.channels.find().to_list(None)
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def update_subscription(self, user_id: str, channel_id: str) -> bool:
        try:
            await self.users.update_one(
                {"user_id": user_id},
                {"$addToSet": {"subscriptions": channel_id}}
            )
            logger.info(f"Updated subscription for user {user_id} in channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id} in {channel_id}: {e}")
            return False

    async def is_user_subscribed(self, user_id: str, channel_id: str) -> bool:
        try:
            user = await self.get_user(user_id)
            return channel_id in user.get("subscriptions", []) if user else False
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in {channel_id}: {e}")
            return False

    async def get_required_channels(self) -> list:
        try:
            channels = await self.get_channels()
            return [c["channel_id"] for c in channels]
        except Exception as e:
            logger.error(f"Error getting required channels: {e}")
            return []

    async def add_withdrawal(self, user_id: str, amount: float, payment_method: str, payment_details: str) -> bool:
        try:
            withdrawal = {
                "user_id": user_id,
                "amount": amount,
                "payment_method": payment_method,
                "payment_details": payment_details,
                "status": "PENDING",
                "created_at": datetime.utcnow()
            }
            await self.withdrawals.insert_one(withdrawal)
            logger.info(f"Added withdrawal for user {user_id}: {amount}")
            return True
        except Exception as e:
            logger.error(f"Error adding withdrawal for user {user_id}: {e}")
            return False

    async def reset_withdrawals(self, user_id: str = None) -> bool:
        try:
            if user_id:
                result = await self.withdrawals.delete_many({"user_id": user_id, "status": "PENDING"})
            else:
                result = await self.withdrawals.delete_many({"status": "PENDING"})
            logger.info(f"Reset {result.deleted_count} pending withdrawals for user {user_id or 'all'}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error resetting withdrawals for user {user_id or 'all'}: {e}")
            return False

    async def add_bonus(self, user_id: str, amount: float) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            new_balance = user.get("balance", 0) + amount
            await self.update_user(user_id, {"balance": new_balance})
            logger.info(f"Added bonus {amount} to user {user_id}, new balance: {new_balance}")
            return True
        except Exception as e:
            logger.error(f"Error adding bonus for user {user_id}: {e}")
            return False

    async def transfer_balance(self, from_user_id: str, to_user_id: str, amount: float) -> bool:
        try:
            from_user = await self.get_user(from_user_id)
            to_user = await self.get_user(to_user_id)
            if not from_user or not to_user or from_user.get("balance", 0) < amount:
                return False
            await self.update_user(from_user_id, {"balance": from_user.get("balance", 0) - amount})
            await self.update_user(to_user_id, {"balance": to_user.get("balance", 0) + amount})
            logger.info(f"Transferred {amount} from {from_user_id} to {to_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error transferring balance from {from_user_id} to {to_user_id}: {e}")
            return False

    async def get_phone_bill_reward(self) -> str:
        try:
            setting = await self.settings.find_one({"key": "phone_bill_reward"})
            return setting.get("value", "Unknown") if setting else "Unknown"
        except Exception as e:
            logger.error(f"Error getting phone bill reward: {e}")
            return "Unknown"

    async def set_phone_bill_reward(self, value: str) -> bool:
        try:
            await self.settings.update_one(
                {"key": "phone_bill_reward"},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Set phone bill reward to {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting phone bill reward: {e}")
            return False

    async def get_invite_requirement(self) -> int:
        try:
            setting = await self.settings.find_one({"key": "invite_requirement"})
            return int(setting.get("value", 0)) if setting else 0
        except Exception as e:
            logger.error(f"Error getting invite requirement: {e}")
            return 0

    async def set_invite_requirement(self, value: int) -> bool:
        try:
            await self.settings.update_one(
                {"key": "invite_requirement"},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Set invite requirement to {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting invite requirement: {e}")
            return False

    async def get_messages_per_kyat(self) -> float:
        try:
            setting = await self.settings.find_one({"key": "messages_per_kyat"})
            return float(setting.get("value", 1)) if setting else 1
        except Exception as e:
            logger.error(f"Error getting messages per kyat: {e}")
            return 1

    async def set_messages_per_kyat(self, value: float) -> bool:
        try:
            await self.settings.update_one(
                {"key": "messages_per_kyat"},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Set messages per kyat to {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting messages per kyat: {e}")
            return False

db = Database()