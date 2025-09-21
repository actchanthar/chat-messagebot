from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import MONGODB_URL, MONGODB_NAME, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.channels = None
        self.settings = None
        self.withdrawals = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db.users
            self.channels = self.db.channels
            self.settings = self.db.settings
            self.withdrawals = self.db.withdrawals
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully")
            
            # Initialize default settings
            await self.init_default_settings()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def init_default_settings(self):
        """Initialize default bot settings"""
        try:
            # Check if settings exist
            settings = await self.settings.find_one({"_id": "bot_settings"})
            
            if not settings:
                default_settings = {
                    "_id": "bot_settings",
                    "message_rate": 3,  # 3 messages = 1 kyat
                    "referral_reward": 25,  # 25 kyat per referral
                    "phone_bill_reward": 1000,  # 1000 kyat for top users
                    "min_withdrawal": 200,
                    "max_daily_withdrawal": 10000,
                    "welcome_bonus": 100,
                    "created_at": datetime.utcnow()
                }
                await self.settings.insert_one(default_settings)
                logger.info("✅ Default settings initialized")
                
        except Exception as e:
            logger.error(f"Error initializing settings: {e}")

    async def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    # User Management
    async def get_user(self, user_id: str):
        """Get user by ID"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_id: str, user_data: dict, referred_by: str = None):
        """Create new user"""
        try:
            user_doc = {
                "user_id": user_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "balance": 100,  # Welcome bonus
                "total_earnings": 100,  # Include welcome bonus in earnings
                "total_withdrawn": 0,
                "withdrawn_today": 0,
                "messages": 0,
                "user_level": 1,
                "successful_referrals": 0,
                "invites": 0,
                "referred_by": referred_by,
                "is_premium": False,
                "banned": False,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "last_withdrawal": None,
                "pending_withdrawals": [],
                "group_messages": {},
                "message_count_for_earning": 0  # Track messages for earning
            }
            
            result = await self.users.insert_one(user_doc)
            if result.inserted_id:
                logger.info(f"Created new user {user_id}")
                return user_doc
            return None
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, update_data: dict):
        """Update user data"""
        try:
            update_data["last_activity"] = datetime.utcnow()
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def add_balance(self, user_id: str, amount: float):
        """Add balance to user"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "balance": amount,
                        "total_earnings": amount
                    },
                    "$set": {"last_activity": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding balance to user {user_id}: {e}")
            return False

    async def add_bonus(self, user_id: str, amount: float):
        """Add bonus to user (separate from regular earnings)"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"balance": amount},
                    "$set": {"last_activity": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding bonus to user {user_id}: {e}")
            return False

    async def increment_user_messages(self, user_id: str, group_id: str = None):
        """Increment user message count"""
        try:
            update_query = {
                "$inc": {"messages": 1},
                "$set": {"last_activity": datetime.utcnow()}
            }
            
            if group_id:
                update_query["$inc"][f"group_messages.{group_id}"] = 1
            
            result = await self.users.update_one(
                {"user_id": user_id},
                update_query
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing messages for user {user_id}: {e}")
            return False

    async def process_message_earning(self, user_id: str, group_id: str, context=None):
        """Process message for earning calculation - UPDATED"""
        try:
            # Get user
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return False
            
            # Increment message count
            await self.increment_user_messages(user_id, group_id)
            
            # Get current message rate and earning counter
            message_rate = await self.get_message_rate()
            current_count = user.get("message_count_for_earning", 0) + 1
            
            # Update earning counter
            await self.update_user(user_id, {
                "message_count_for_earning": current_count
            })
            
            # Check if user should earn (every X messages)
            if current_count >= message_rate:
                # Award 1 kyat and reset counter
                await self.add_balance(user_id, 1)
                await self.update_user(user_id, {
                    "message_count_for_earning": 0  # Reset counter
                })
                
                # Check for milestones after earning
                if context:
                    await self.check_and_announce_milestones(user_id, context)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing message earning for user {user_id}: {e}")
            return False

    # Statistics and Rankings
    async def get_all_users(self):
        """Get all users"""
        try:
            cursor = self.users.find({})
            users = await cursor.to_list(length=None)
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_total_users_count(self):
        """Get total number of users"""
        try:
            count = await self.users.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0

    async def get_active_users_count(self, hours: int):
        """Get count of users active in last X hours"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            count = await self.users.count_documents({
                "last_activity": {"$gte": since}
            })
            return count
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 0

    async def get_new_users_count(self, days: int):
        """Get count of new users in last X days"""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            count = await self.users.count_documents({
                "created_at": {"$gte": since}
            })
            return count
        except Exception as e:
            logger.error(f"Error getting new users count: {e}")
            return 0

    async def get_premium_users_count(self):
        """Get count of premium users"""
        try:
            count = await self.users.count_documents({"is_premium": True})
            return count
        except Exception as e:
            logger.error(f"Error getting premium users count: {e}")
            return 0

    async def get_banned_users_count(self):
        """Get count of banned users"""
        try:
            count = await self.users.count_documents({"banned": True})
            return count
        except Exception as e:
            logger.error(f"Error getting banned users count: {e}")
            return 0

    async def get_total_messages_count(self):
        """Get total messages sent by all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$messages"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total messages: {e}")
            return 0

    async def get_messages_today_count(self):
        """Get total messages sent today"""
        try:
            # Simplified - return estimated daily messages
            total_messages = await self.get_total_messages_count()
            return total_messages // 30  # Rough estimate of daily messages
        except Exception as e:
            logger.error(f"Error getting messages today count: {e}")
            return 0

    async def get_total_earnings(self):
        """Get total earnings across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$total_earnings"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total earnings: {e}")
            return 0

    async def get_total_withdrawals(self):
        """Get total withdrawals across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$total_withdrawn"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(length=1)
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total withdrawals: {e}")
            return 0

    async def get_top_users(self, limit: int, sort_field: str):
        """Get top users by specified field"""
        try:
            cursor = self.users.find({}).sort(sort_field, -1).limit(limit)
            users = await cursor.to_list(length=limit)
            return users
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []

    async def get_user_rank(self, user_id: str, field: str):
        """Get user's rank in specified field"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_value = user.get(field, 0)
            rank = await self.users.count_documents({field: {"$gt": user_value}}) + 1
            return rank
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0

    async def get_user_rank_by_earnings(self, user_id: str):
        """Get user's rank by total earnings"""
        return await self.get_user_rank(user_id, "total_earnings")

    async def get_user_messages_today(self, user_id: str):
        """Get user's messages sent today (simplified)"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            # Simplified - could implement proper daily tracking
            total_messages = user.get("messages", 0)
            return min(total_messages, 50)  # Cap at 50 for daily estimate
        except Exception as e:
            logger.error(f"Error getting user messages today: {e}")
            return 0

    # Channel Management
    async def get_channels(self):
        """Get all mandatory channels"""
        try:
            cursor = self.channels.find({})
            channels = await cursor.to_list(length=None)
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def add_channel(self, channel_id: str, channel_name: str):
        """Add mandatory channel"""
        try:
            channel_doc = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "added_at": datetime.utcnow()
            }
            result = await self.channels.insert_one(channel_doc)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error adding channel: {e}")
            return False

    async def remove_channel(self, channel_id: str):
        """Remove mandatory channel"""
        try:
            result = await self.channels.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing channel: {e}")
            return False

    # Settings Management - UPDATED
    async def update_settings(self, settings: dict):
        """Update bot settings"""
        try:
            result = await self.settings.update_one(
                {"_id": "bot_settings"},
                {"$set": settings},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    async def get_settings(self):
        """Get bot settings"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings or {}
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {}

    async def get_message_rate(self):
        """Get current message rate (messages per kyat)"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings.get("message_rate", 3) if settings else 3
        except Exception as e:
            logger.error(f"Error getting message rate: {e}")
            return 3

    async def set_message_rate(self, rate: int):
        """Set message rate"""
        try:
            result = await self.update_settings({"message_rate": rate})
            return result
        except Exception as e:
            logger.error(f"Error setting message rate: {e}")
            return False

    async def get_referral_reward(self):
        """Get referral reward amount"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings.get("referral_reward", 25) if settings else 25
        except Exception as e:
            logger.error(f"Error getting referral reward: {e}")
            return 25

    async def set_referral_reward(self, amount: float):
        """Set referral reward amount"""
        try:
            result = await self.update_settings({"referral_reward": amount})
            return result
        except Exception as e:
            logger.error(f"Error setting referral reward: {e}")
            return False

    async def get_phone_bill_reward(self):
        """Get phone bill reward for top users"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings.get("phone_bill_reward", 1000) if settings else 1000
        except Exception as e:
            logger.error(f"Error getting phone bill reward: {e}")
            return 1000

    async def set_phone_bill_reward(self, amount: float):
        """Set phone bill reward amount"""
        try:
            result = await self.update_settings({"phone_bill_reward": amount})
            return result
        except Exception as e:
            logger.error(f"Error setting phone bill reward: {e}")
            return False

    async def get_welcome_bonus(self):
        """Get welcome bonus amount"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings.get("welcome_bonus", 100) if settings else 100
        except Exception as e:
            logger.error(f"Error getting welcome bonus: {e}")
            return 100

    async def set_welcome_bonus(self, amount: float):
        """Set welcome bonus amount"""
        try:
            result = await self.update_settings({"welcome_bonus": amount})
            return result
        except Exception as e:
            logger.error(f"Error setting welcome bonus: {e}")
            return False

    # Milestone checking with announcements
    async def check_and_announce_milestones(self, user_id: str, context=None):
        """Check if user reached any milestones and announce"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return
            
            # Import here to avoid circular imports
            try:
                from plugins.announcements import announcement_system
            except ImportError:
                logger.warning("Announcement system not available")
                return
            
            user_name = user.get('first_name', 'User')
            total_earnings = int(user.get('total_earnings', 0))
            total_referrals = user.get('successful_referrals', 0)
            
            # Check earning milestones
            earning_milestones = [100000, 50000, 25000, 10000, 5000]
            for milestone in earning_milestones:
                if total_earnings >= milestone:
                    # Check if this is a recent achievement (rough estimation)
                    previous_earnings = total_earnings - 100  # Rough check
                    if previous_earnings < milestone:
                        await announcement_system.announce_milestone_reached(
                            user_id=user_id,
                            user_name=user_name,
                            milestone_type="earnings",
                            amount=milestone,
                            context=context
                        )
                    break
            
            # Check referral milestones
            referral_milestones = [50, 25, 10, 5]
            for milestone in referral_milestones:
                if total_referrals >= milestone:
                    await announcement_system.announce_milestone_reached(
                        user_id=user_id,
                        user_name=user_name,
                        milestone_type="referrals",
                        amount=milestone,
                        context=context
                    )
                    break
                    
        except Exception as e:
            logger.error(f"Error checking milestones: {e}")

    # Utility Methods
    async def ban_user(self, user_id: str, reason: str = None):
        """Ban a user"""
        try:
            update_data = {
                "banned": True,
                "banned_at": datetime.utcnow()
            }
            if reason:
                update_data["ban_reason"] = reason
            
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False

    async def unban_user(self, user_id: str):
        """Unban a user"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {"banned": False},
                    "$unset": {"ban_reason": "", "banned_at": ""}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False

    async def is_user_banned(self, user_id: str):
        """Check if user is banned"""
        try:
            user = await self.get_user(user_id)
            return user.get("banned", False) if user else False
        except Exception as e:
            logger.error(f"Error checking if user banned: {e}")
            return False

    async def get_user_statistics(self, user_id: str):
        """Get detailed user statistics"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return None
            
            total_users = await self.get_total_users_count()
            earning_rank = await self.get_user_rank_by_earnings(user_id)
            message_rank = await self.get_user_rank(user_id, "messages")
            
            stats = {
                "user_data": user,
                "total_users": total_users,
                "earning_rank": earning_rank,
                "message_rank": message_rank,
                "messages_today": await self.get_user_messages_today(user_id)
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return None

    # Withdrawal related methods
    async def record_withdrawal(self, user_id: str, amount: float, method: str, details: str, status: str = "PENDING"):
        """Record a withdrawal request"""
        try:
            withdrawal_doc = {
                "user_id": user_id,
                "amount": amount,
                "method": method,
                "details": details,
                "status": status,
                "requested_at": datetime.utcnow(),
                "processed_at": None,
                "processed_by": None
            }
            
            result = await self.withdrawals.insert_one(withdrawal_doc)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error recording withdrawal: {e}")
            return False

    async def get_pending_withdrawals(self):
        """Get all pending withdrawal requests"""
        try:
            cursor = self.withdrawals.find({"status": "PENDING"})
            withdrawals = await cursor.to_list(length=None)
            return withdrawals
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []

# Create global database instance
db = Database()

# Connection management
async def init_database():
    """Initialize database connection"""
    await db.connect()

async def close_database():
    """Close database connection"""
    await db.close_connection()
