from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_NAME]
            self.users = self.db.users
            self.groups = self.db.groups
            self.rewards = self.db.rewards
            self.settings = self.db.settings
            self.message_history = {}  # In-memory cache
            logger.info("MongoDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise

    async def check_rate_limit(self, user_id, message_text):
        # Your rate limit logic here
        pass  # Replace with actual implementation

class DatabaseWithClient(Database):
    def __init__(self, bot_client):
        super().__init__()
        self.bot_client = bot_client  # Separate bot client
        logger.info("DatabaseWithClient initialized with bot client")

db = None

def init_db(bot_client):
    global db
    try:
        db = DatabaseWithClient(bot_client)
        logger.info("Database singleton initialized")
    except Exception as e:
        logger.error(f"Failed to initialize db: {e}")
        raise