import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_referral_links():
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_NAME]
        users_collection = db.users

        # Find users without referral_link
        users = await users_collection.find({"referral_link": {"$exists": False}}).to_list(length=None)
        logger.info(f"Found {len(users)} users without referral_link")

        # Update each user
        for user in users:
            user_id = user["user_id"]
            referral_link = f"https://t.me/ACTChatBot?start={user_id}"
            result = await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"referral_link": referral_link}}
            )
            if result.modified_count > 0:
                logger.info(f"Added referral_link to user {user_id}")
            else:
                logger.info(f"No changes made for user {user_id}")

        logger.info("Migration completed")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(migrate_referral_links())