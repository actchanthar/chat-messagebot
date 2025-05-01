from pymongo import MongoClient
from config import MONGO_URI
import time

client = MongoClient(MONGO_URI)
db = client["actchat"]  # Updated to your database name

users_collection = db["users"]
messages_collection = db["messages"]
withdrawals_collection = db["withdrawals"]
chat_groups_collection = db["chat_groups"]

async def get_user(user_id, chat_id):
    return users_collection.find_one({"user_id": user_id, "chat_id": chat_id})

async def update_user(user_id, chat_id, data):
    users_collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"$set": data},
        upsert=True
    )

async def log_message(user_id, chat_id, message_text, timestamp):
    messages_collection.insert_one({
        "user_id": user_id,
        "chat_id": chat_id,
        "message_text": message_text,
        "timestamp": timestamp
    })

async def create_withdrawal_request(user_id, chat_id, amount):
    request = {
        "user_id": user_id,
        "chat_id": chat_id,
        "amount": amount,
        "status": "pending",
        "timestamp": time.time()
    }
    result = withdrawals_collection.insert_one(request)
    return {"_id": result.inserted_id, **request}

async def add_chat_group(chat_id, admin_ids):
    chat_groups_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"admin_ids": admin_ids}},
        upsert=True
    )

async def get_chat_group(chat_id):
    return chat_groups_collection.find_one({"chat_id": chat_id})

async def get_all_chat_groups():
    return list(chat_groups_collection.find())