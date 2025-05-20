from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
from collections import deque
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.users = self.db.users
        self.channels = self.db.channels
        self.pending_withdrawals = self.db.pending_withdrawals

    async def get_user(self, user_id: str):
        logger.info(f"Retrieving user {user_id}")
        user = await self.users.find_one({"user_id": user_id})
        if user:
            # Convert recent_messages back to deque if it exists
            if "recent_messages" in user:
                user["recent_messages"] = deque(user["recent_messages"], maxlen=5)
        return user

    async def create_user(self, user_id: str, name: str):
        logger.info(f"Creating user {user_id}")
        user = {
            "user_id": user_id,
            "name": name,
            "balance": 0,
            "invited_users": 0,
            "invites": 0,
            "group_messages": {},
            "withdrawn_today": 0,
            "recent_messages": deque([], maxlen=5),  # Initialize as deque
            "referral_link": f"https://t.me/ACTChatBot?start={user_id}",
        }
        # Convert deque to list for MongoDB storage
        user_for_db = user.copy()
        user_for_db["recent_messages"] = list(user["recent_messages"])
        try:
            await self.users.insert_one(user_for_db)
            logger.info(f"User {user_id} created successfully")
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise

    async def update_user(self, user_id: str, update_data: dict):
        logger.info(f"Updating user {user_id} with data: {update_data}")
        # Convert deque to list if recent_messages is in update_data
        update_data_for_db = update_data.copy()
        if "recent_messages" in update_data_for_db:
            update_data_for_db["recent_messages"] = list(update_data_for_db["recent_messages"])
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": update_data_for_db},
            upsert=True
        )
        logger.info(f"User {user_id} updated successfully")

    # Placeholder methods for other functionalities
    async def get_channels(self):
        return await self.channels.find().to_list(length=None)

    async def increment_invite(self, referrer_id: str, user_id: str):
        await self.users.update_one(
            {"user_id": referrer_id},
            {"$inc": {"invites": 1, "balance": 25}, "$addToSet": {"invited_users": user_id}}
        )
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": 50}}
        )

    async def get_top_users(self, limit: int, sort_by: str):
        if sort_by == "invites":
            return await self.users.find().sort("invites", -1).limit(limit).to_list(length=None)
        elif sort_by == "messages":
            return await self.users.find().sort({"group_messages.-1002061898677": -1}).limit(limit).to_list(length=None)
        return []

    async def get_phone_bill_reward(self):
        return "Phone Bill Reward"

    async def add_pending_withdrawal(self, user_id: str, amount: int, date):
        await self.pending_withdrawals.insert_one({
            "user_id": user_id,
            "amount": amount,
            "date": date,
            "status": "pending"
        })

db = Database()