from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
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
        self.withdrawals = self.db.withdrawals
        self.transactions = self.db.transactions

    async def get_user(self, user_id: str):
        try:
            user = await self.users.find_one({"user_id": user_id})
            if user:
                user["message_timestamps"] = user.get("message_timestamps", [])[-10:]
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id: str, name: Dict[str, str], referred_by: Optional[str] = None):
        try:
            user = {
                "user_id": user_id,
                "first_name": name.get("first_name", ""),
                "last_name": name.get("last_name", ""),
                "balance": 0.0,
                "messages": 0,
                "group_messages": {},
                "withdrawn_today": 0.0,
                "total_withdrawn": 0.0,
                "last_withdrawal": None,
                "banned": False,
                "spam_count": 0,
                "last_activity": datetime.utcnow(),
                "message_timestamps": [],
                "invites": 0,
                "successful_referrals": 0,
                "pending_withdrawals": [],
                "referred_by": referred_by,
                "created_at": datetime.utcnow(),
                "user_level": 1,
                "total_earnings": 0.0
            }
            
            await self.users.insert_one(user)
            
            # Process referral bonus
            if referred_by:
                await self._process_referral_bonus(referred_by, user_id)
                
            logger.info(f"Created new user {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, updates: Dict[str, Any]):
        try:
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return []

    async def add_bonus(self, user_id: str, amount: float):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            new_balance = user.get("balance", 0) + amount
            return await self.update_user(user_id, {"balance": new_balance})
        except Exception as e:
            logger.error(f"Error adding bonus to user {user_id}: {e}")
            return False

    async def get_message_rate(self):
        try:
            setting = await self.settings.find_one({"type": "message_rate"})
            return setting["value"] if setting else 3
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

    async def set_message_rate(self, messages_per_kyat: int):
        try:
            await self.settings.update_one(
                {"type": "message_rate"},
                {"$set": {"value": messages_per_kyat}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_group_message_count(self, group_id: str):
        try:
            pipeline = [
                {"$match": {f"group_messages.{group_id}": {"$exists": True}}},
                {"$group": {"_id": None, "total_messages": {"$sum": f"$group_messages.{group_id}"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=None)
            return result[0]["total_messages"] if result else 0
        except Exception as e:
            logger.error(f"Error retrieving message count: {e}")
            return 0

    async def process_message_earning(self, user_id: str, group_id: str):
        try:
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return {"success": False, "reason": "User not found or banned"}
            
            message_rate = await self.get_message_rate()
            new_message_count = user.get("messages", 0) + 1
            
            # Calculate earning
            earning = 1.0 / message_rate if new_message_count % message_rate == 0 else 0
            new_balance = user.get("balance", 0) + earning
            new_total_earnings = user.get("total_earnings", 0) + earning
            
            # Update group messages
            group_messages = user.get("group_messages", {})
            group_messages[group_id] = group_messages.get(group_id, 0) + 1
            
            # Update user level
            new_level = min(10, (new_message_count // 1000) + 1)
            
            updates = {
                "messages": new_message_count,
                "group_messages": group_messages,
                "balance": new_balance,
                "total_earnings": new_total_earnings,
                "user_level": new_level,
                "last_activity": datetime.utcnow()
            }
            
            success = await self.update_user(user_id, updates)
            
            return {
                "success": success,
                "earning": earning,
                "new_balance": new_balance,
                "message_count": new_message_count,
                "level_up": new_level > user.get("user_level", 1)
            }
            
        except Exception as e:
            logger.error(f"Error processing message earning: {e}")
            return {"success": False, "reason": "Processing error"}

    async def create_withdrawal_request(self, user_id: str, amount: float, payment_method: str, payment_details: str):
        try:
            user = await self.get_user(user_id)
            if not user or user.get("balance", 0) < amount:
                return {"success": False, "reason": "Insufficient balance"}
            
            # Create withdrawal request
            withdrawal_request = {
                "user_id": user_id,
                "amount": amount,
                "payment_method": payment_method,
                "payment_details": payment_details,
                "status": "pending",
                "created_at": datetime.utcnow()
            }
            
            result = await self.withdrawals.insert_one(withdrawal_request)
            withdrawal_id = str(result.inserted_id)
            
            # Reserve balance
            new_balance = user.get("balance", 0) - amount
            await self.update_user(user_id, {"balance": new_balance})
            
            return {"success": True, "withdrawal_id": withdrawal_id}
            
        except Exception as e:
            logger.error(f"Error creating withdrawal request: {e}")
            return {"success": False, "reason": "Processing error"}

    async def _process_referral_bonus(self, referrer_id: str, new_user_id: str):
        try:
            referral_bonus = 25  # Fixed bonus amount
            referrer = await self.get_user(referrer_id)
            
            if referrer and not referrer.get("banned", False):
                new_balance = referrer.get("balance", 0) + referral_bonus
                new_referrals = referrer.get("successful_referrals", 0) + 1
                
                await self.update_user(referrer_id, {
                    "balance": new_balance,
                    "successful_referrals": new_referrals
                })
                
                logger.info(f"Referral bonus {referral_bonus} awarded to {referrer_id}")
        except Exception as e:
            logger.error(f"Error processing referral bonus: {e}")

# Singleton instance
db = Database()
