import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_NAME, GROUP_CHAT_IDS
from datetime import datetime

async def migrate():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    users = db.users

    default_fields = {
        "balance": 0,
        "messages": 0,
        "group_messages": {gid: 0 for gid in GROUP_CHAT_IDS},
        "withdrawn_today": 0,
        "last_withdrawal": None,
        "banned": False,
        "notified_10kyat": False,
        "last_activity": datetime.utcnow(),
        "message_timestamps": [],
        "invites": 0,
        "pending_withdrawals": [],
        "first_name": "",
        "last_name": "",
        "username": ""
    }

    async for user in users.find():
        updates = {}
        for key, default_value in default_fields.items():
            if key not in user:
                updates[key] = default_value
        if "message_timestamps" in user and not isinstance(user["message_timestamps"], list):
            updates["message_timestamps"] = []
        if updates:
            await users.update_one(
                {"user_id": user["user_id"]},
                {"$set": updates}
            )
    print("Migration complete")

if __name__ == "__main__":
    asyncio.run(migrate())