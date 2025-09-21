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
        self.challenges = self.db.challenges
        self.channels = self.db.channels

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
                "total_earnings": 0.0,
                "achievements": [],
                "last_daily_login": None,
                "is_premium": False,
                "premium_expires": None,
                "used_free_trial": False,
                "last_premium_daily_claim": None,
                "premium_earnings_today": 0
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
            new_total_earnings = user.get("total_earnings", 0) + amount
            return await self.update_user(user_id, {
                "balance": new_balance, 
                "total_earnings": new_total_earnings
            })
        except Exception as e:
            logger.error(f"Error adding bonus to user {user_id}: {e}")
            return False

    # NEW METHODS - Missing from original database
    async def get_top_users(self, limit: int, sort_field: str):
        """Get top users sorted by a specific field"""
        try:
            users = await self.users.find({}).sort(sort_field, -1).limit(limit).to_list(length=limit)
            return users
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []

    async def get_daily_challenges(self, user_id: str, date):
        """Get daily challenges for a user"""
        try:
            challenges = await self.challenges.find_one({
                "user_id": user_id, 
                "date": date.isoformat()
            })
            return challenges.get("challenges", []) if challenges else []
        except Exception as e:
            logger.error(f"Error getting daily challenges: {e}")
            return []

    async def save_daily_challenges(self, user_id: str, date, challenges: list):
        """Save daily challenges for a user"""
        try:
            await self.challenges.update_one(
                {"user_id": user_id, "date": date.isoformat()},
                {"$set": {"challenges": challenges, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving daily challenges: {e}")
            return False

    async def get_challenge_history(self, user_id: str, limit: int = 10):
        """Get challenge history for a user"""
        try:
            history = await self.challenges.find({"user_id": user_id}).sort("date", -1).limit(limit).to_list(length=limit)
            processed_history = []
            for record in history:
                challenges = record.get("challenges", [])
                total_challenges = len(challenges)
                completed_challenges = len([c for c in challenges if c.get("completed", False)])
                total_rewards = sum(c.get("reward", 0) for c in challenges if c.get("completed", False))
                
                processed_history.append({
                    "date": datetime.fromisoformat(record["date"]),
                    "total_challenges": total_challenges,
                    "completed_challenges": completed_challenges,
                    "total_rewards": total_rewards
                })
            return processed_history
        except Exception as e:
            logger.error(f"Error getting challenge history: {e}")
            return []

    async def get_user_rank_by_earnings(self, user_id: str):
        """Get user's rank by total earnings"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_earnings = user.get("total_earnings", 0)
            higher_users = await self.users.count_documents({"total_earnings": {"$gt": user_earnings}})
            return higher_users + 1
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0

    async def get_user_messages_today(self, user_id: str):
        """Get user's message count for today"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            # For simplicity, return a calculated value based on recent activity
            last_activity = user.get("last_activity")
            if last_activity and last_activity.date() == datetime.utcnow().date():
                # Estimate based on total messages (this is simplified)
                return min(user.get("messages", 0) % 100, 50)  # Max 50 per day estimate
            return 0
        except Exception as e:
            logger.error(f"Error getting messages today: {e}")
            return 0

    async def get_user_rank(self, user_id: str, field: str):
        """Get user's rank in a specific field"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_value = user.get(field, 0)
            higher_users = await self.users.count_documents({field: {"$gt": user_value}})
            return higher_users + 1
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0

    async def get_total_users_count(self):
        """Get total number of users"""
        try:
            return await self.users.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total users count: {e}")
            return 0

    async def get_active_users_count(self, hours: int):
        """Get count of active users in the last X hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return await self.users.count_documents({
                "last_activity": {"$gte": cutoff_time}
            })
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 0

    async def get_total_messages_count(self):
        """Get total messages count across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total_messages": {"$sum": "$messages"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total_messages"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total messages count: {e}")
            return 0

    async def get_total_earnings(self):
        """Get total earnings across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total_earnings": {"$sum": "$total_earnings"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total_earnings"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total earnings: {e}")
            return 0

    async def get_total_withdrawals(self):
        """Get total withdrawals across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total_withdrawn": {"$sum": "$total_withdrawn"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total_withdrawn"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total withdrawals: {e}")
            return 0

    async def get_premium_users_count(self):
        """Get count of premium users"""
        try:
            current_time = datetime.utcnow()
            return await self.users.count_documents({
                "is_premium": True,
                "premium_expires": {"$gt": current_time}
            })
        except Exception as e:
            logger.error(f"Error getting premium users count: {e}")
            return 0

    async def get_banned_users_count(self):
        """Get count of banned users"""
        try:
            return await self.users.count_documents({"banned": True})
        except Exception as e:
            logger.error(f"Error getting banned users count: {e}")
            return 0

    async def get_new_users_count(self, days: int):
        """Get count of new users in the last X days"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            return await self.users.count_documents({
                "created_at": {"$gte": cutoff_time}
            })
        except Exception as e:
            logger.error(f"Error getting new users count: {e}")
            return 0

    async def get_messages_today_count(self):
        """Get total messages sent today"""
        try:
            # This is simplified - in a real implementation, you'd track daily message counts
            today = datetime.utcnow().date()
            active_today = await self.get_active_users_count(24)
            return active_today * 10  # Estimate: 10 messages per active user
        except Exception as e:
            logger.error(f"Error getting messages today count: {e}")
            return 0

    async def get_phone_bill_reward(self):
        """Get phone bill reward amount"""
        try:
            setting = await self.settings.find_one({"type": "phone_bill_reward"})
            return setting["value"] if setting else 1000
        except Exception as e:
            logger.error(f"Error getting phone bill reward: {e}")
            return 1000

    async def get_referral_reward(self):
        """Get referral reward amount"""
        try:
            setting = await self.settings.find_one({"type": "referral_reward"})
            return setting["value"] if setting else 25
        except Exception as e:
            logger.error(f"Error getting referral reward: {e}")
            return 25

    async def get_message_rate(self):
        """Get message rate (messages per kyat)"""
        try:
            setting = await self.settings.find_one({"type": "message_rate"})
            return setting["value"] if setting else 3
        except Exception as e:
            logger.error(f"Error retrieving message rate: {e}")
            return 3

    async def set_message_rate(self, messages_per_kyat: int):
        """Set message rate"""
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
        """Get total message count for a group"""
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

    async def get_channels(self):
        """Get all channels for subscription check"""
        try:
            channels = await self.channels.find({}).to_list(length=None)
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def process_message_earning(self, user_id: str, group_id: str):
        """Process message earning for a user"""
        try:
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return {"success": False, "reason": "User not found or banned"}
            
            message_rate = await self.get_message_rate()
            new_message_count = user.get("messages", 0) + 1
            
            # Calculate earning
            earning = 1.0 / message_rate if new_message_count % message_rate == 0 else 0
            
            # Check if user is premium (double earnings)
            if user.get("is_premium", False) and user.get("premium_expires") and user.get("premium_expires") > datetime.utcnow():
                earning *= 2  # Double earnings for premium users
            
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
        """Create a withdrawal request"""
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
            
            # Reserve balance (don't deduct yet, wait for approval)
            # new_balance = user.get("balance", 0) - amount
            # await self.update_user(user_id, {"balance": new_balance})
            
            return {"success": True, "withdrawal_id": withdrawal_id}
            
        except Exception as e:
            logger.error(f"Error creating withdrawal request: {e}")
            return {"success": False, "reason": "Processing error"}

    async def _process_referral_bonus(self, referrer_id: str, new_user_id: str):
        """Process referral bonus"""
        try:
            referral_bonus = await self.get_referral_reward()
            referrer = await self.get_user(referrer_id)
            
            if referrer and not referrer.get("banned", False):
                new_balance = referrer.get("balance", 0) + referral_bonus
                new_referrals = referrer.get("successful_referrals", 0) + 1
                new_total_earnings = referrer.get("total_earnings", 0) + referral_bonus
                
                await self.update_user(referrer_id, {
                    "balance": new_balance,
                    "successful_referrals": new_referrals,
                    "total_earnings": new_total_earnings
                })
                
                logger.info(f"Referral bonus {referral_bonus} awarded to {referrer_id}")
        except Exception as e:
            logger.error(f"Error processing referral bonus: {e}")

# Singleton instance
db = Database()
