import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME

async def migrate():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    users = db.users

    async for user in users.find():
        if "message_timestamps" in user and isinstance(user["message_timestamps"], list):
            # Already a list, no change needed
            continue
        # If somehow stored as deque or malformed, reset to empty list
        await users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"message_timestamps": []}}
        )
    print("Migration complete")

if __name__ == "__main__":
    asyncio.run(migrate())