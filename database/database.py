from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging
from datetime import datetime, timedelta
from collections import deque
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.groups = self.db.groups
        self.rewards = self.db.rewards
        self.settings = self.db.settings
        self.message_history = {}

    # Existing methods (unchanged unless specified) ...

    async def get_user(self, user_id):
        try:
            user = await self.users.find_one({"user_id": user_id})
            logger.info(f"Retrieved user {user_id}: {user}")
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
                "withdrawn_today": 0,
                "last_withdrawal": None,
                "banned": False,
                "notified_10kyat": False,
                "last_activity": datetime.utcnow(),
                "message_timestamps": deque(maxlen=5),
                "inviter_id": None,
                "invite_count": 0,
                "invited_users": [],
                "referral_rewarded": False
            }
            await self.users.insert_one(user)
            logger.info(f"Created user {user_id} with invite_count=0")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def update_user(self, user_id, updates):
        try:
            current_user = await self.get_user(user_id)
            logger.info(f"Before update: user {user_id} invite_count={current_user.get('invite_count', 0) if current_user else 'N/A'}")
            result = await self.users.update_one({"user_id": user_id}, {"$set": updates}, upsert=True)
            if result.modified_count > 0 or result.upserted_id:
                logger.info(f"Updated user {user_id}: {updates}")
                updated_user = await self.get_user(user_id)
                logger.info(f"After update: user {user_id} invite_count={updated_user.get('invite_count', 0) if updated_user else 'N/A'}")
                return True
            logger.info(f"No changes for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    # New method for handling referrals
    async def add_referral(self, inviter_id, new_user_id):
        try:
            result = await self.users.update_one(
                {"user_id": inviter_id},
                {
                    "$inc": {"invite_count": 1},
                    "$push": {"invited_users": new_user_id}
                },
                upsert=False  # Do not create a new document if inviter doesn’t exist
            )
            if result.matched_count > 0:
                if result.modified_count > 0:
                    logger.info(f"Added referral for inviter {inviter_id}: new_user {new_user_id}, invite_count incremented")
                else:
                    logger.warning(f"Inviter {inviter_id} found but invite_count not incremented (possibly already updated)")
                return True
            else:
                logger.info(f"No user found to add referral for inviter {inviter_id}")
                return False
        except Exception as e:
            logger.error(f"Error adding referral for inviter {inviter_id}: {e}")
            return False

    # Other existing methods (unchanged) ...

db = Database()