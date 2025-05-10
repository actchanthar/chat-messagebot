import os
from pymongo import MongoClient, errors
from datetime import datetime, timedelta
import asyncio

class Database:
    def __init__(self):
        self.client = MongoClient(os.environ.get("MONGODB_URI"))
        self.db = self.client["actchat"]
        self.users = self.db["users"]
        self.messages = self.db["messages"]
        self.spam_threshold = 5
        self.time_window = 30 * 60  # 30 minutes

    async def init(self):
        # Check and create indexes if they don't exist
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._create_indexes
        )

    def _create_indexes(self):
        # Get existing indexes
        existing_indexes = self.users.index_information()
        
        # Create user_id index if it doesn't exist
        if "user_id_1" not in existing_indexes:
            try:
                self.users.create_index("user_id", unique=True)
            except errors.DuplicateKeyError:
                pass  # Ignore if index creation fails due to existing index
        
        # Create messages index if it doesn't exist
        if "user_id_1_timestamp_1" not in existing_indexes:
            self.messages.create_index([("user_id", 1), ("timestamp", 1)])

    async def get_user(self, user_id):
        user = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.find_one({"user_id": user_id})
        )
        return user

    async def create_user(self, user_id, name):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.update_one(
                {"user_id": user_id},
                {"$setOnInsert": {
                    "user_id": user_id,
                    "name": name,
                    "messages": 0,
                    "balance": 0.0,
                    "notified_10kyat": False
                }},
                upsert=True
            )
        )

    async def increment_message(self, user_id, name, text):
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.find_one_and_update(
                {"user_id": user_id},
                {
                    "$inc": {"messages": 1, "balance": 1.0},
                    "$set": {"name": name}
                },
                return_document=True
            )
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.messages.insert_one(
                {"user_id": user_id, "text": text, "timestamp": datetime.now()}
            )
        )
        return result  # Return updated user document

    async def mark_notified_10kyat(self, user_id):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.update_one(
                {"user_id": user_id},
                {"$set": {"notified_10kyat": True}}
            )
        )

    async def add_bonus(self, user_id, amount):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": amount}}
            )
        )

    async def get_top_users(self, limit=10):
        users = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(self.users.find().sort("messages", -1).limit(limit))
        )
        return users

    async def reset_stats(self):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.delete_many({})
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.messages.delete_many({})
        )

    async def reset_balance(self, user_id):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.users.update_one(
                {"user_id": user_id},
                {"$set": {"balance": 0.0, "notified_10kyat": False}}
            )
        )

    async def is_spam(self, user_id, text):
        cutoff = datetime.now() - timedelta(seconds=self.time_window)
        messages = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(self.messages.find(
                {"user_id": user_id, "timestamp": {"$gt": cutoff}}
            ))
        )

        if len(text.strip()) < 5:
            return True

        from difflib import SequenceMatcher
        message_counts = {}
        for msg in messages:
            similarity = SequenceMatcher(None, text.lower(), msg["text"].lower()).ratio()
            if similarity > 0.9:
                return True
            message_counts[msg["text"]] = message_counts.get(msg["text"], 0) + 1
            if message_counts[msg["text"]] >= self.spam_threshold:
                return True
        
        if messages:
            last_ts = messages[-1]["timestamp"]
            if (datetime.now() - last_ts) < timedelta(seconds=5):
                return True
        
        return False

# Create global db instance
db = Database()