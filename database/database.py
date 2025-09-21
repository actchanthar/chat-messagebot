import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timezone
import os
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.channels = None
        self.settings = None
        
    async def connect(self):
        """Connect to MongoDB database"""
        try:
            # Get MongoDB URI from environment variable or use default
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            database_name = os.getenv("DATABASE_NAME", "telegram_earning_bot")
            
            self.client = AsyncIOMotorClient(mongodb_uri)
            self.db = self.client[database_name]
            
            # Collections
            self.users = self.db.users
            self.channels = self.db.channels
            self.settings = self.db.settings
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully")
            
            # Initialize default settings
            await self.init_default_settings()
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    async def init_default_settings(self):
        """Initialize default bot settings"""
        try:
            default_settings = {
                "_id": "bot_settings",
                "referral_reward": 25,  # Default 25 kyat per referral
                "message_rate": 3,      # Default 3 messages = 1 kyat
                "min_withdrawal": 200,
                "max_daily_withdrawal": 10000
            }
            
            await self.settings.update_one(
                {"_id": "bot_settings"},
                {"$setOnInsert": default_settings},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error initializing default settings: {e}")

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user data from database"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_id: str, user_data: Dict, referred_by: Optional[str] = None) -> Optional[Dict]:
        """Create new user in database"""
        try:
            new_user = {
                "user_id": user_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "balance": 0,
                "total_earnings": 0,
                "total_withdrawn": 0,
                "withdrawn_today": 0,
                "messages": 0,
                "user_level": 1,
                "invites": 0,
                "successful_referrals": 0,
                "referred_by": referred_by,
                "banned": False,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "pending_withdrawals": [],
                "message_count_for_earning": 0
            }
            
            result = await self.users.insert_one(new_user)
            if result.inserted_id:
                logger.info(f"Created new user {user_id}")
                return new_user
            return None
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, update_data: Dict) -> bool:
        """Update user data in database"""
        try:
            # Add last activity timestamp
            update_data["last_activity"] = datetime.now(timezone.utc)
            
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def process_message_earning(self, user_id: str, group_id: str, context) -> bool:
        """Process message for earning - Updated with configurable rate"""
        try:
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return False
            
            # Get current message rate from settings
            message_rate = await self.get_message_rate()
            
            current_count = user.get("message_count_for_earning", 0) + 1
            
            # Update message count
            await self.update_user(user_id, {
                "messages": user.get("messages", 0) + 1,
                "message_count_for_earning": current_count
            })
            
            # Check if user should earn (every X messages based on rate)
            if current_count >= message_rate:
                # Reset counter and give reward
                current_balance = user.get("balance", 0)
                total_earnings = user.get("total_earnings", 0)
                
                await self.update_user(user_id, {
                    "balance": current_balance + 1,
                    "total_earnings": total_earnings + 1,
                    "message_count_for_earning": 0,  # Reset counter
                    "last_activity": datetime.now(timezone.utc)
                })
                
                return True  # User earned money
            
            return False  # User didn't earn this time
        except Exception as e:
            logger.error(f"Error processing message earning for {user_id}: {e}")
            return False

    async def get_all_users(self) -> List[Dict]:
        """Get all users from database"""
        try:
            users = []
            async for user in self.users.find({}):
                users.append(user)
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_total_users_count(self) -> int:
        """Get total number of users"""
        try:
            count = await self.users.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error getting users count: {e}")
            return 0

    async def get_user_rank_by_earnings(self, user_id: str) -> int:
        """Get user rank by total earnings"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_earnings = user.get("total_earnings", 0)
            
            # Count users with higher earnings
            higher_count = await self.users.count_documents({
                "total_earnings": {"$gt": user_earnings}
            })
            
            return higher_count + 1
        except Exception as e:
            logger.error(f"Error getting user rank for {user_id}: {e}")
            return 0

    async def get_user_rank(self, user_id: str, field: str) -> int:
        """Get user rank by specified field"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_value = user.get(field, 0)
            
            # Count users with higher values
            higher_count = await self.users.count_documents({
                field: {"$gt": user_value}
            })
            
            return higher_count + 1
        except Exception as e:
            logger.error(f"Error getting user rank for {user_id}: {e}")
            return 0

    async def get_channels(self) -> List[Dict]:
        """Get all channels from database"""
        try:
            channels = []
            async for channel in self.channels.find({}):
                channels.append(channel)
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def add_channel(self, channel_id: str, channel_name: str) -> bool:
        """Add channel to database"""
        try:
            channel_data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "added_at": datetime.now(timezone.utc)
            }
            
            result = await self.channels.insert_one(channel_data)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error adding channel: {e}")
            return False

    async def remove_channel(self, channel_id: str) -> bool:
        """Remove channel from database"""
        try:
            result = await self.channels.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing channel: {e}")
            return False

    # Settings methods
    async def update_settings(self, settings: dict) -> bool:
        """Update bot settings"""
        try:
            await self.settings.update_one(
                {"_id": "bot_settings"},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    async def get_settings(self) -> dict:
        """Get bot settings"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings or {}
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {}

    async def get_referral_reward(self) -> int:
        """Get current referral reward amount"""
        try:
            settings = await self.get_settings()
            return settings.get("referral_reward", 25)  # Default 25 kyat
        except Exception as e:
            logger.error(f"Error getting referral reward: {e}")
            return 25

    async def get_message_rate(self) -> int:
        """Get current message earning rate"""
        try:
            settings = await self.get_settings()
            return settings.get("message_rate", 3)  # Default 3 messages = 1 kyat
        except Exception as e:
            logger.error(f"Error getting message rate: {e}")
            return 3

    async def get_leaderboard(self, field: str = "total_earnings", limit: int = 10) -> List[Dict]:
        """Get leaderboard by specified field"""
        try:
            leaderboard = []
            cursor = self.users.find({}).sort(field, -1).limit(limit)
            
            async for user in cursor:
                leaderboard.append(user)
            
            return leaderboard
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

    async def get_user_stats(self, user_id: str) -> Dict:
        """Get comprehensive user statistics"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return {}
            
            total_users = await self.get_total_users_count()
            earning_rank = await self.get_user_rank_by_earnings(user_id)
            message_rank = await self.get_user_rank(user_id, "messages")
            
            return {
                "user": user,
                "total_users": total_users,
                "earning_rank": earning_rank,
                "message_rank": message_rank
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def ban_user(self, user_id: str) -> bool:
        """Ban a user"""
        try:
            result = await self.update_user(user_id, {"banned": True})
            return result
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False

    async def unban_user(self, user_id: str) -> bool:
        """Unban a user"""
        try:
            result = await self.update_user(user_id, {"banned": False})
            return result
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False

    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()

# Create database instance
db = Database()

async def init_database():
    """Initialize database connection"""
    success = await db.connect()
    if not success:
        raise Exception("Failed to connect to database")
    return db
