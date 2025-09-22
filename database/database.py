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
        """Initialize default settings - IMPROVED"""
        try:
            settings_doc = await self.settings.find_one({"_id": "bot_settings"})
            if not settings_doc:
                default_settings = {
                    "_id": "bot_settings",
                    "referral_reward": 50,
                    "message_rate": 3,
                    "last_order_id": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                result = await self.settings.insert_one(default_settings)
                if result.inserted_id:
                    logger.info("✅ Initialized default settings successfully")
                else:
                    logger.error("❌ Failed to initialize default settings")
            else:
                logger.info("✅ Settings document already exists")
        except Exception as e:
            logger.error(f"Error initializing settings: {e}")

    async def get_settings(self):
        """Get bot settings"""
        try:
            settings = await self.settings.find_one({"_id": "bot_settings"})
            if not settings:
                logger.warning("Settings not found, initializing...")
                await self.initialize_settings()
                settings = await self.settings.find_one({"_id": "bot_settings"})
            return settings or {}
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {}

    async def update_settings(self, updates: dict):
        """Update bot settings - COMPLETELY FIXED"""
        try:
            logger.info(f"Attempting to update settings: {updates}")
            
            # Add timestamp to updates
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # First check if settings document exists
            existing_settings = await self.settings.find_one({"_id": "bot_settings"})
            
            if existing_settings:
                # Update existing document
                result = await self.settings.update_one(
                    {"_id": "bot_settings"},
                    {"$set": updates}
                )
                logger.info(f"Update existing - modified: {result.modified_count}, matched: {result.matched_count}")
                
                if result.matched_count == 0:
                    logger.error("❌ No document matched the filter")
                    return False
                    
            else:
                # Create new document if it doesn't exist
                logger.info("Settings document doesn't exist, creating new one...")
                default_settings = {
                    "_id": "bot_settings",
                    "referral_reward": 50,
                    "message_rate": 3,
                    "last_order_id": 0,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                default_settings.update(updates)
                
                result = await self.settings.insert_one(default_settings)
                logger.info(f"Created new settings document: {result.inserted_id}")
        
            # Always verify the final result
            verification = await self.settings.find_one({"_id": "bot_settings"})
            
            if verification:
                success = True
                for key, expected_value in updates.items():
                    if key == "updated_at":  # Skip timestamp verification
                        continue
                        
                    actual_value = verification.get(key)
                    if actual_value == expected_value:
                        logger.info(f"✅ Successfully verified {key} = {actual_value}")
                    else:
                        logger.error(f"❌ Verification failed for {key}: expected {expected_value}, got {actual_value}")
                        success = False
                
                return success
            else:
                logger.error("❌ Settings document not found after update attempt")
                return False
                
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
            logger.info(f"Adding mandatory channel: {channel_id} - {channel_name} by {added_by}")
            
            # Get current channels
            channels_doc = await self.settings.find_one({"_id": "mandatory_channels"})
            current_channels = channels_doc.get("channels", []) if channels_doc else []
            
            # Check if channel already exists
            for channel in current_channels:
                if channel.get("channel_id") == channel_id:
                    logger.warning(f"Channel {channel_id} already exists")
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
            result = await self.settings.update_one(
                {"_id": "mandatory_channels"},
                {"$set": {"channels": current_channels, "updated_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True
            )
            
            logger.info(f"Database update result: modified={result.modified_count}, upserted={result.upserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding mandatory channel {channel_id}: {e}")
            return False

    async def remove_mandatory_channel(self, channel_id: str):
        """Remove a mandatory channel"""
        try:
            # Get current channels
            channels_doc = await self.settings.find_one({"_id": "mandatory_channels"})
            if not channels_doc:
                return False
            
            current_channels = channels_doc.get("channels", [])
            initial_count = len(current_channels)
            
            # Remove channel with matching ID
            updated_channels = [ch for ch in current_channels if ch.get("channel_id") != channel_id]
            
            # Check if anything was removed
            if len(updated_channels) == initial_count:
                return False  # No channel was removed
            
            # Update in database
            await self.settings.update_one(
                {"_id": "mandatory_channels"},
                {"$set": {"channels": updated_channels, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            logger.info(f"Removed channel {channel_id}, remaining: {len(updated_channels)}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing mandatory channel: {e}")
            return False

    async def create_user(self, user_id: str, user_data: dict, referred_by: str = None):
        """Create a new user with advanced referral system"""
        try:
            logger.info(f"Creating user {user_id} with referrer {referred_by}")
            
            user_doc = {
                "user_id": user_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "username": user_data.get("username", ""),
                "balance": 100,  # Welcome bonus
                "total_earnings": 100,  # Welcome bonus counted as earnings
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
                "referral_channels_joined": False,  # Track if user joined mandatory channels
                "referral_reward_given": False,     # Track if referrer got reward
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.users.insert_one(user_doc)
            if result.inserted_id:
                logger.info(f"Successfully created user {user_id} with balance {user_doc['balance']}")
                
                # If referred by someone, log it but don't give reward yet
                if referred_by:
                    logger.info(f"User {user_id} was referred by {referred_by} - reward pending channel joins")
                    
                    # Increment referrer's invites count (not successful_referrals yet)
                    await self.users.update_one(
                        {"user_id": referred_by},
                        {"$inc": {"invites": 1}}
                    )
                
                return user_doc
            
            logger.error(f"Failed to insert user {user_id} into database")
            return None
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def check_and_process_referral_reward(self, user_id: str, context):
        """Check if referred user joined channels and give referrer reward"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            referred_by = user.get("referred_by")
            if not referred_by or user.get("referral_reward_given", False):
                return False  # No referrer or reward already given
            
            # Check if user joined all mandatory channels
            from plugins.withdrawal import check_user_subscriptions
            requirements_met, joined, not_joined, referral_count = await check_user_subscriptions(user_id, context)
            
            channels_joined = len(not_joined) == 0  # All channels joined
            previously_joined = user.get("referral_channels_joined", False)
            
            if channels_joined and not previously_joined:
                # User just joined all channels - give referrer reward
                referral_reward = await self.get_referral_reward()
                
                # Give reward to referrer
                referrer_update = await self.users.update_one(
                    {"user_id": referred_by},
                    {
                        "$inc": {
                            "balance": referral_reward,
                            "total_earnings": referral_reward,
                            "successful_referrals": 1
                        }
                    }
                )
                
                # Mark user as channels joined and reward given
                user_update = await self.users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "referral_channels_joined": True,
                            "referral_reward_given": True
                        }
                    }
                )
                
                if referrer_update.modified_count > 0:
                    logger.info(f"Referral reward processed: {referred_by} got {referral_reward} for {user_id} joining channels")
                    
                    # Notify referrer about the reward
                    try:
                        referrer_user = await context.bot.get_chat(int(referred_by))
                        referred_user = await context.bot.get_chat(int(user_id))
                        
                        from config import CURRENCY
                        await context.bot.send_message(
                            chat_id=referred_by,
                            text=(
                                f"🎉 **REFERRAL REWARD EARNED!**\n\n"
                                f"👤 **{referred_user.first_name or 'User'}** joined all mandatory channels!\n"
                                f"💰 **You earned:** {referral_reward} {CURRENCY}\n\n"
                                f"🔗 **Keep inviting friends to earn more!**\n"
                                f"📋 **Your referral link:** https://t.me/{context.bot.username}?start=ref_{referred_by}"
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify referrer {referred_by}: {e}")
                    
                    return True
            
            elif not channels_joined and previously_joined:
                # User left channels - remove referrer reward
                referral_reward = await self.get_referral_reward()
                
                # Remove reward from referrer (if they still have enough balance)
                referrer = await self.get_user(referred_by)
                if referrer and referrer.get("balance", 0) >= referral_reward:
                    await self.users.update_one(
                        {"user_id": referred_by},
                        {
                            "$inc": {
                                "balance": -referral_reward,
                                "total_earnings": -referral_reward,
                                "successful_referrals": -1
                            }
                        }
                    )
                    
                    # Mark user as channels left
                    await self.users.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "referral_channels_joined": False,
                                "referral_reward_given": False
                            }
                        }
                    )
                    
                    logger.info(f"Referral reward removed: {referred_by} lost {referral_reward} because {user_id} left channels")
                    
                    # Notify referrer about the removal
                    try:
                        from config import CURRENCY
                        await context.bot.send_message(
                            chat_id=referred_by,
                            text=(
                                f"⚠️ **REFERRAL REWARD REMOVED**\n\n"
                                f"👤 Your referred user left mandatory channels\n"
                                f"💸 **Removed:** {referral_reward} {CURRENCY}\n\n"
                                f"💡 **They need to rejoin channels for you to get the reward back**"
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify referrer about removal {referred_by}: {e}")
                    
                    return True
            
            # Update user's channel status if changed
            if channels_joined != previously_joined:
                await self.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"referral_channels_joined": channels_joined}}
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking referral reward for {user_id}: {e}")
            return False

    async def process_referral(self, referrer_id: str, referred_id: str):
        """Process referral reward - LEGACY METHOD"""
        logger.info(f"Legacy referral processing called: {referrer_id} -> {referred_id}")
        return True

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
            valid_fields = ["total_earnings", "messages", "balance", "total_withdrawn", "successful_referrals"]
            
            if sort_by not in valid_fields:
                sort_by = "total_earnings"
            
            cursor = self.users.find(
                {"banned": {"$ne": True}}
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
            
            cursor = self.users.find(
                {"banned": {"$ne": True}},
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

    async def update_user_telegram_info(self, user_id: str, telegram_user):
        """Update user's Telegram info in database"""
        try:
            updates = {
                "first_name": telegram_user.first_name or "",
                "last_name": telegram_user.last_name or "",
                "username": telegram_user.username or "",
                "last_name_update": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user Telegram info for {user_id}: {e}")
            return False

    async def bulk_update_user_names(self, context):
        """Bulk update user names from Telegram API"""
        try:
            cursor = self.users.find(
                {
                    "$or": [
                        {"first_name": {"$in": ["", None, "None", "null"]}},
                        {"first_name": {"$exists": False}},
                        {"last_name": {"$in": ["", None, "None", "null"]}},
                        {"username": {"$in": ["", None, "None", "null"]}}
                    ],
                    "banned": {"$ne": True}
                },
                {"user_id": 1, "first_name": 1, "last_name": 1, "username": 1}
            ).limit(50)
            
            users_to_update = await cursor.to_list(length=50)
            updated_count = 0
            
            for user in users_to_update:
                try:
                    user_id = user.get("user_id")
                    if not user_id:
                        continue
                    
                    telegram_user = await context.bot.get_chat(int(user_id))
                    
                    if telegram_user:
                        await self.update_user_telegram_info(user_id, telegram_user)
                        updated_count += 1
                        logger.info(f"Updated user info for {user_id}: {telegram_user.first_name}")
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to update user {user_id}: {e}")
                    continue
            
            logger.info(f"Bulk updated {updated_count} user names")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk update user names: {e}")
            return 0

    async def process_message_earning(self, user_id: str, group_id: str, context):
        """Process message earning for user"""
        try:
            user = await self.get_user(user_id)
            if not user or user.get("banned", False):
                return False
            
            current_messages = user.get("message_count", 0) + 1
            message_rate = await self.get_message_rate()
            
            should_earn = (current_messages % message_rate) == 0
            
            updates = {
                "messages": user.get("messages", 0) + 1,
                "message_count": current_messages,
                "last_message_time": datetime.now(timezone.utc).isoformat()
            }
            
            if should_earn:
                new_balance = user.get("balance", 0) + 1
                new_total_earnings = user.get("total_earnings", 0) + 1
                
                updates.update({
                    "balance": new_balance,
                    "total_earnings": new_total_earnings
                })
                
                await self.update_user(user_id, updates)
                return True
            else:
                await self.update_user(user_id, updates)
                return False
                
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
