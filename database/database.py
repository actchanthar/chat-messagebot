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
        self.groups = self.db["groups"]
        self.spam_threshold = 5
        self.time_window = 30 * 60  # 30 minutes

    async def init(self):
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._create_indexes
        )

    def _create_indexes(self):
        existing_indexes = self.users.index_information()
        if "user_id_1" not in existing_indexes:
            try:
                self.users.create_index("user_id", unique=True)
            except errors.DuplicateKeyError:
                pass
        
        if "user_id_1_timestamp_1" not in existing_indexes:
            self.messages.create_index([("user_id", 1), ("timestamp", 1)])
        
        groups_indexes = self.groups.index_information()
        if "group_id_1" not in groups_indexes:
            try:
                self.groups.create_index("group_id", unique=True)
            except errors.DuplicateKeyError:
                pass

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
        return result

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
        query = self.users.find().sort("messages", -1)
        if limit is not None:
            query = query.limit(limit)
        users = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(query)
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

    async def add_group(self, group_id):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.groups.update_one(
                {"group_id": group_id},
                {"$setOnInsert": {"group_id": group_id}},
                upsert=True
            )
        )

    async def get_groups(self):
        groups = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(self.groups.find())
        )
        return [group["group_id"] for group in groups]

db = Database()