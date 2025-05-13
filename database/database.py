# database/database.py
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from config import MONGODB_URL, MONGODB_NAME

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db["users"]
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

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
                "banned": False
            }
            await self.users.insert_one(user)
            logger.info(f"Created new user {user_id} in database")
            return await self.get_user(user_id)
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, data):
        try:
            result = await self.users.update_one({"user_id": user_id}, {"$set": data})
            logger.info(f"Updated user {user_id} with data: {data}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def get_top_users(self):
        try:
            top_users = await self.users.find().sort("messages", -1).limit(10).to_list(length=10)
            logger.info(f"Retrieved top 10 users: {top_users}")
            return top_users
        except Exception as e:
            logger.error(f"Error retrieving top users: {e}")
            return []

db = Database()