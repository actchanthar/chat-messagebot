from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            logger.info(f"Retrieved user {user_id} from database: {user}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def create_user(self, user_id, name):
        try:
            user = {
                "user_id": user_id,
                "name": name,
                "balance": 0,
                "messages": 0,
                "withdrawn_today": 0,
                "last_withdrawal": None,
                "banned": False,
                "notified_10kyat": False
            }
            result = await self.users.insert_one(user)
            logger.info(f"Created new user {user_id} with name {name}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates})
            if result.modified_count > 0:
                updated_user = await self.users.find_one({"user_id": user_id})
                logger.info(f"Updated user {user_id}: {updates}")
                return True
            logger.info(f"No changes made to user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_all_users(self):
        try:
            users = await self.users.find().to_list(length=None)
            logger.info(f"Retrieved all users: {users}")
            return users
        except Exception as e:
            logger.error(f"Error retrieving all users: {e}")
            return None

    async def get_top_users(self, limit=10):
        try:
            top_users = await self.users.find(
                {"banned": False},
                {"user_id": 1, "name": 1, "messages": 1, "balance": 1, "_id": 0}
            ).sort("messages", -1).limit(limit).to_list(length=limit)
            logger.info(f"Retrieved top {limit} users: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users: {e}")
            return []

    async def add_group(self, group_id):
        try:
            # Check if group already exists
            existing_group = await self.groups.find_one({"group_id": group_id})
            if existing_group:
                logger.info(f"Group {group_id} already exists in approved groups")
                return "exists"
            
            result = await self.groups.insert_one({"group_id": group_id})
            logger.info(f"Added group {group_id} to approved groups")
            return True
        except Exception as e:
            logger.error(f"Error adding group {group_id}: {str(e)}")
            return False

    async def get_approved_groups(self):
        try:
            groups = await self.groups.find({}, {"group_id": 1, "_id": 0}).to_list(length=None)
            group_ids = [group["group_id"] for group in groups]
            logger.info(f"Retrieved approved groups: {group_ids}")
            return group_ids
        except Exception as e:
            logger.error(f"Error retrieving approved groups: {e}")
            return []

# Singleton instance
db = Database()