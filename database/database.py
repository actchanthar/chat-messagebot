import motor.motor_asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import asyncio

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.settings = None
        self.connected = False

    async def connect(self):
        """Connect to MongoDB"""
        try:
            from config import MONGODB_URL, MONGODB_NAME
            self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db.users
            self.settings = self.db.settings
            
            # Test connection
            await self.client.admin.command('ping')
            self.connected = True
            logger.info("✅ Connected to MongoDB successfully")
            
            # Initialize settings if not exists
            await self.initialize_settings()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def initialize_settings(self):
        """Initialize default settings"""
        try:
            settings_doc = await self.settings.find_one({"_id": "bot_settings"})
            if not settings_doc:
                default_settings = {
                    "_id": "bot_settings",
                    "referral_reward": 50,
                    "message_rate": 3,
                    "last_order_id": 0,
                    "created_at": datetime.now(timezone.utc)
                }
                await self.settings.insert_one(default_settings)
                logger.info("✅ Initialized default settings")
        except Exception as e:
            logger.error(f"Error initializing settings: {e}")

    async def get_settings(self):
        """Get bot settings"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            if not settings:
                await self.initialize_settings()
                settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings or {}
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {}

    async def update_settings(self, updates: dict):
        """Update bot settings"""
        try:
            result = await self.settings.update_one(
                {"_id": "bot_settings"},
                {"$set": updates},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

    async def get_referral_reward(self):
        """Get current referral reward amount"""
        try:
            settings = await self.get_settings()
            return settings.get("referral_reward", 50)
        except Exception as e:
            logger.error(f"Error getting referral reward: {e}")
            return 50

    async def get_message_rate(self):
        """Get current message earning rate"""
        try:
            settings = await self.get_settings()
            return settings.get("message_rate", 3)
        except Exception as e:
            logger.error(f"Error getting message rate: {e}")
            return 3

    async def get_channels(self):
        """Get mandatory channels - LEGACY METHOD"""
        return await self.get_mandatory_channels()

    async def get_mandatory_channels(self):
        """Get all mandatory channels"""
        try:
            channels_doc = await self.settings.find_one({"_id": "mandatory_channels"})
            return channels_doc.get("channels", []) if channels_doc else []
        except Exception as e:
            logger.error(f"Error getting mandatory channels: {e}")
            return []

    async def add_mandatory_channel(self, channel_id: str, channel_name: str, added_by: str = "admin"):
        """Add a mandatory channel"""
        try:
            # Get current channels
            channels_doc = await self.settings.find_one({"_id": "mandatory_channels"})
            current_channels = channels_doc.get("channels", []) if channels_doc else []
            
            # Check if channel already exists
            for channel in current_channels:
                if channel.get("channel_id") == channel_id:
                    return False  # Channel already exists
            
            # Add new channel
            new_channel = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "added_by": added_by,
                "added_at": datetime.now(timezone.utc).isoformat()
            }
            
            current_channels.append(new_channel)
            
            # Update in database
            await self.settings.update_one(
                {"_id": "mandatory_channels"},
                {"$set": {"channels": current_channels}},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding mandatory channel: {e}")
            return False

    async def remove_mandatory_channel(self, channel_id: str):
        """Remove a mandatory channel"""
        try:
            # Get current channels
            channels_doc = await self.settings.find_one({"_id": "mandatory_channels"})
            if not channels_doc:
                return False
            
            current_channels = channels_doc.get("channels", [])
            
            # Remove channel with matching ID
            updated_channels = [ch for ch in current_channels if ch.get("channel_id") != channel_id]
            
            # Check if anything was removed
            if len(updated_channels) == len(current_channels):
                return False  # No channel was removed
            
            # Update in database
            await self.settings.update_one(
                {"_id": "mandatory_channels"},
                {"$set": {"channels": updated_channels}}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing mandatory channel: {e}")
            return False

    async def create_user(self, user_id: str, user_data: dict, referred_by: str = None):
        """Create a new user - FIXED SIGNATURE"""
        try:
            user_doc = {
                "user_id": user_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "username": user_data.get("username", ""),
                "balance": 100,  # Welcome bonus
                "total_earnings": 100,
                "total_withdrawn": 0,
                "withdrawn_today": 0,
                "messages": 0,
                "user_level": 1,
                "banned": False,
                "invites": 0,
                "successful_referrals": 0,
                "referred_by": referred_by or "",
                "referral_code": f"REF_{user_id}",
                "message_count": 0,
                "last_message_time": None,
                "pending_withdrawals": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.users.insert_one(user_doc)
            if result.inserted_id:
                # Process referral if exists
                if referred_by:
                    await self.process_referral(referred_by, user_id)
                
                return user_doc
            return None
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def process_referral(self, referrer_id: str, referred_id: str):
        """Process referral reward"""
        try:
            referral_reward = await self.get_referral_reward()
            
            # Give reward to referrer
            await self.users.update_one(
                {"user_id": referrer_id},
                {
                    "$inc": {
                        "balance": referral_reward,
                        "total_earnings": referral_reward,
                        "successful_referrals": 1
                    }
                }
            )
            
            logger.info(f"Processed referral: {referrer_id} got {referral_reward} for referring {referred_id}")
            
        except Exception as e:
            logger.error(f"Error processing referral: {e}")

    async def get_user(self, user_id: str):
        """Get user by ID"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, updates: dict):
        """Update user data"""
        try:
            updates["last_activity"] = datetime.now(timezone.utc).isoformat()
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def ban_user(self, user_id: str, reason: str = "Banned by admin"):
        """Ban a user"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "banned": True,
                        "ban_reason": reason,
                        "banned_at": datetime.now(timezone.utc).isoformat()
                    }
                }
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
                    "$set": {
                        "banned": False,
                        "unbanned_at": datetime.now(timezone.utc).isoformat()
                    },
                    "$unset": {"ban_reason": ""}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False

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
            logger.error(f"Error getting total users count: {e}")
            return 0

    async def get_total_earnings(self):
        """Get total earnings across all users"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$total_earnings"}}}
            ]
            result = await self.users.aggregate(pipeline).to_list(1)
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
            result = await self.users.aggregate(pipeline).to_list(1)
            return result[0]["total"] if result else 0
        except Exception as e:
            logger.error(f"Error getting total withdrawals: {e}")
            return 0

    async def get_user_rank_by_earnings(self, user_id: str):
        """Get user's rank by total earnings"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_earnings = user.get("total_earnings", 0)
            higher_earners = await self.users.count_documents({
                "total_earnings": {"$gt": user_earnings},
                "banned": {"$ne": True}
            })
            return higher_earners + 1
        except Exception as e:
            logger.error(f"Error getting user rank by earnings: {e}")
            return 0

    async def get_user_rank(self, user_id: str, field: str):
        """Get user's rank by specified field"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return 0
            
            user_value = user.get(field, 0)
            higher_users = await self.users.count_documents({
                field: {"$gt": user_value},
                "banned": {"$ne": True}
            })
            return higher_users + 1
        except Exception as e:
            logger.error(f"Error getting user rank by {field}: {e}")
            return 0

    async def get_top_users(self, limit: int = 10, sort_by: str = "total_earnings"):
        """Get top users by specified field"""
        try:
            # Valid sort fields
            valid_fields = ["total_earnings", "messages", "balance", "total_withdrawn", "successful_referrals"]
            
            if sort_by not in valid_fields:
                sort_by = "total_earnings"
            
            cursor = self.users.find(
                {"banned": {"$ne": True}}  # Exclude banned users
            ).sort(sort_by, -1).limit(limit)
            
            users = await cursor.to_list(length=limit)
            return users
            
        except Exception as e:
            logger.error(f"Error getting top users by {sort_by}: {e}")
            return []

    async def get_user_stats_summary(self):
        """Get summary statistics for all users"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_users": {"$sum": 1},
                        "total_earnings": {"$sum": "$total_earnings"},
                        "total_withdrawn": {"$sum": "$total_withdrawn"},
                        "total_messages": {"$sum": "$messages"},
                        "active_users": {
                            "$sum": {
                                "$cond": [{"$eq": ["$banned", False]}, 1, 0]
                            }
                        },
                        "banned_users": {
                            "$sum": {
                                "$cond": [{"$eq": ["$banned", True]}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            result = await self.users.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                return {
                    "total_users": stats.get("total_users", 0),
                    "active_users": stats.get("active_users", 0),
                    "banned_users": stats.get("banned_users", 0),
                    "total_earnings": stats.get("total_earnings", 0),
                    "total_withdrawn": stats.get("total_withdrawn", 0),
                    "total_messages": stats.get("total_messages", 0),
                    "system_balance": stats.get("total_earnings", 0) - stats.get("total_withdrawn", 0)
                }
            
            return {
                "total_users": 0,
                "active_users": 0,
                "banned_users": 0,
                "total_earnings": 0,
                "total_withdrawn": 0,
                "total_messages": 0,
                "system_balance": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats summary: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "banned_users": 0,
                "total_earnings": 0, 
                "total_withdrawn": 0,
                "total_messages": 0,
                "system_balance": 0
            }

    async def get_leaderboard_data(self, sort_by: str = "total_earnings", limit: int = 15):
        """Get leaderboard data with rankings"""
        try:
            valid_fields = ["total_earnings", "messages", "balance", "total_withdrawn", "successful_referrals"]
            
            if sort_by not in valid_fields:
                sort_by = "total_earnings"
            
            # Get top users (exclude banned)
            cursor = self.users.find(
                {"banned": {"$ne": True}},  # Exclude banned users
                {
                    "user_id": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "username": 1,
                    "total_earnings": 1,
                    "messages": 1,
                    "balance": 1,
                    "total_withdrawn": 1,
                    "successful_referrals": 1,
                    "created_at": 1,
                    "banned": 1
                }
            ).sort(sort_by, -1).limit(limit)
            
            users = await cursor.to_list(length=limit)
            
            # Add rankings
            for i, user in enumerate(users):
                user["rank"] = i + 1
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting leaderboard data by {sort_by}: {e}")
            return []

    async def get_recent_activities(self, limit: int = 10):
        """Get recent user activities"""
        try:
            cursor = self.users.find(
                {"banned": {"$ne": True}},
                {
                    "user_id": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "created_at": 1,
                    "last_activity": 1,
                    "total_earnings": 1,
                    "messages": 1
                }
            ).sort("last_activity", -1).limit(limit)
            
            users = await cursor.to_list(length=limit)
            return users
            
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return []

    async def get_withdrawal_stats(self):
        """Get withdrawal statistics"""
        try:
            pipeline = [
                {
                    "$match": {
                        "total_withdrawn": {"$gt": 0},
                        "banned": {"$ne": True}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_withdrawers": {"$sum": 1},
                        "total_withdrawn": {"$sum": "$total_withdrawn"},
                        "avg_withdrawal": {"$avg": "$total_withdrawn"},
                        "max_withdrawal": {"$max": "$total_withdrawn"}
                    }
                }
            ]
            
            result = await self.users.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                return {
                    "total_withdrawers": stats.get("total_withdrawers", 0),
                    "total_withdrawn": stats.get("total_withdrawn", 0),
                    "avg_withdrawal": stats.get("avg_withdrawal", 0),
                    "max_withdrawal": stats.get("max_withdrawal", 0)
                }
            
            return {
                "total_withdrawers": 0,
                "total_withdrawn": 0,
                "avg_withdrawal": 0,
                "max_withdrawal": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting withdrawal stats: {e}")
            return {
                "total_withdrawers": 0,
                "total_withdrawn": 0,
                "avg_withdrawal": 0,
                "max_withdrawal": 0
            }

    async def process_message_earning(self, user_id: str, group_id: str, context):
        """Process message earning for user"""
        try:
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return False
            
            current_messages = user.get("message_count", 0) + 1
            message_rate = await self.get_message_rate()
            
            # Check if user should earn (every N messages)
            should_earn = (current_messages % message_rate) == 0
            
            updates = {
                "messages": user.get("messages", 0) + 1,
                "message_count": current_messages,
                "last_message_time": datetime.now(timezone.utc).isoformat()
            }
            
            if should_earn:
                # User earns 1 currency unit
                new_balance = user.get("balance", 0) + 1
                new_total_earnings = user.get("total_earnings", 0) + 1
                
                updates.update({
                    "balance": new_balance,
                    "total_earnings": new_total_earnings
                })
                
                await self.update_user(user_id, updates)
                return True  # Earned money
            else:
                await self.update_user(user_id, updates)
                return False  # No earning this message
                
        except Exception as e:
            logger.error(f"Error processing message earning for {user_id}: {e}")
            return False

    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("✅ Database connection closed")

# Global database instance
db = Database()

async def init_database():
    """Initialize database connection"""
    await db.connect()
    return db
