from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=30000)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups
        self.rewards = self.db.rewards
        self.settings = self.db.settings
        self.withdrawals = self.db.withdrawals

    async def test_connection(self):
        """Test the MongoDB connection by listing collections."""
        try:
            await self.db.list_collection_names()
            logger.info("MongoDB connection test successful")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise

    async def _ensure_indexes(self):
        try:
            await self.users.create_index([("user_id", 1)], unique=True)
            await self.users.create_index([("invite_count", -1)])
            await self.users.create_index([("messages", -1)])
            await self.groups.create_index([("group_id", 1)], unique=True)
            await self.settings.create_index([("type", 1)], unique=True)
            await self.withdrawals.create_index([("withdrawal_id", 1)], unique=True)
            logger.info("Database indexes ensured")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    # ... (keep all other methods as they are) ...

# Defer database initialization
db = None

async def initialize_database():
    global db
    db = Database()
    await db.test_connection()
    await db._ensure_indexes()
    logger.info("Database initialized successfully")