import os
import logging
from datetime import datetime, timedelta
import motor.motor_asyncio
from pymongo import ReturnDocument
import hashlib

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize database connection"""
        self.client = None
        self.db = None
        self.users_collection = None
        self.messages_collection = None
        self.spam_threshold = 5  # Number of similar messages allowed within time_window
        self.time_window = 60 * 30  # 30 minutes in seconds

    async def connect(self):
        """Connect to MongoDB"""
        try:
            # Get MongoDB URI from environment variable
            mongodb_uri = os.environ.get("MONGODB_URI")
            if not mongodb_uri:
                logger.error("MONGODB_URI environment variable not set")
                return False

            # Connect to MongoDB
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri)
            self.db = self.client.telegram_bot
            
            # Create collections
            self.users_collection = self.db.users
            self.messages_collection = self.db.messages
            
            # Create indexes
            await self.users_collection.create_index("user_id", unique=True)
            await self.messages_collection.create_index("user_id")
            await self.messages_collection.create_index("timestamp")
            
            logger.info("Connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")

    async def get_user(self, user_id):
        """Get user data from database"""
        return await self.users_collection.find_one({"user_id": user_id})

    async def create_or_update_user(self, user_id, user_data):
        """Create or update user in database"""
        result = await self.users_collection.find_one_and_update(
            {"user_id": user_id},
            {"$set": user_data},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return result

    async def increment_user_message_count(self, user_id, first_name):
        """Increment user message count and balance"""
        result = await self.users_collection.find_one_and_update(
            {"user_id": user_id},
            {
                "$inc": {"messages": 1, "balance": 1},
                "$set": {"name": first_name}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return result

    async def reset_user_balance(self, user_id):
        """Reset user balance to zero (mark as paid)"""
        result = await self.users_collection.find_one_and_update(
            {"user_id": user_id},
            {"$set": {"balance": 0}},
            return_document=ReturnDocument.AFTER
        )
        return result

    async def get_top_users(self, limit=10):
        """Get top users by message count"""
        cursor = self.users_collection.find().sort("messages", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_all_stats(self):
        """Get stats for all users"""
        total_messages = 0
        total_balance = 0
        
        cursor = self.users_collection.find()
        users = await cursor.to_list(length=100)
        
        for user in users:
            total_messages += user.get("messages", 0)
            total_balance += user.get("balance", 0)
            
        return {
            "users": users,
            "total_messages": total_messages,
            "total_balance": total_balance
        }

    async def reset_all_stats(self):
        """Reset all stats (admin only)"""
        await self.users_collection.delete_many({})
        await self.messages_collection.delete_many({})
        return True

    async def record_message(self, user_id, text):
        """Record message in history for spam detection"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        await self.messages_collection.insert_one({
            "user_id": user_id,
            "text_hash": text_hash,
            "timestamp": datetime.now()
        })
        
        # Clean old messages
        cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
        await self.messages_collection.delete_many({"timestamp": {"$lt": cutoff_time}})

    async def is_spam(self, user_id, text):
        """Check if message is spam (too similar to recent messages)"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
        
        # Count similar messages within time window
        count = await self.messages_collection.count_documents({
            "user_id": user_id,
            "text_hash": text_hash,
            "timestamp": {"$gt": cutoff_time}
        })
        
        return count >= self.spam_threshold

# Create a global instance
db = Database()