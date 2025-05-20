import os
import logging
import logging.handlers
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from collections import deque

# Set up logging
log_file = '/tmp/bot.log'
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            logger.debug("Starting Database initialization")
            mongo_url = os.getenv('MONGODB_URL', 'mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/actchat1?retryWrites=true&w=majority&appName=Cluster0')
            mongo_db_name = os.getenv('MONGODB_NAME', 'actchat1')
            logger.debug(f"MongoDB URL (partial): {mongo_url[:30]}...")
            logger.debug(f"MongoDB database name: {mongo_db_name}")

            if not mongo_url or not mongo_db_name:
                logger.error("MONGODB_URL or MONGODB_NAME is not set")
                raise ValueError("MONGODB_URL or MONGODB_NAME is not set")

            logger.info("Connecting to MongoDB")
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            self.db = self.mongo_client[mongo_db_name]
            self.users = self.db.users
            logger.info("MongoDB client initialized successfully")

            logger.debug("Testing MongoDB connection")
            self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection test successful")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}", exc_info=True)
            raise

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            logger.debug(f"Retrieved user {user_id}: {user}")
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
                "group_messages": {"-1002061898677": 0},
                "last_activity": datetime.utcnow()
            }
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

class DatabaseWithClient(Database):
    def __init__(self, bot_client):
        try:
            logger.debug("Starting DatabaseWithClient initialization")
            super().__init__()
            self.bot_client = bot_client
            logger.info("DatabaseWithClient initialized")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseWithClient: {e}", exc_info=True)
            raise

db = None

def init_db(bot_client):
    global db
    try:
        logger.debug("Starting database initialization")
        db = DatabaseWithClient(bot_client)
        logger.info("Database singleton initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise