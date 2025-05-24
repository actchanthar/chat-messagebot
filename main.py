import logging
import asyncio
import os
from telegram.ext import Application, CommandHandler
from telegram import Update
from motor.motor_asyncio import AsyncIOMotorClient

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot and MongoDB settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo")
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://2234act:2234act@cluster0.rwjacbj.mongodb.net/actchat1?retryWrites=true&w=majority&appName=Cluster0"
)
MONGODB_NAME = os.getenv("MONGODB_NAME", "actchat1")

# Initialize MongoDB
client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=30000)
db = client[MONGODB_NAME]
users_collection = db.users

# Ensure indexes
try:
    users_collection.create_index([("user_id", 1)], unique=True)
    logger.info("Database indexes ensured")
except Exception as e:
    logger.error(f"Failed to create indexes: {e}")

# Basic database functions
async def get_user(user_id):
    try:
        user = await users_collection.find_one({"user_id": str(user_id)})
        return user
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        return None

async def create_user(user_id, name, username=None):
    try:
        user = {
            "user_id": str(user_id),
            "name": name or "Unknown",
            "username": username,
            "balance": 0.0,
            "messages": 0,
        }
        await users_collection.insert_one(user)
        logger.info(f"Created user {user_id}")
        return user
    except Exception as e:
        logger.error(f"Failed to create user {user_id}: {e}")
        return None

# Command handlers
async def start(update: Update, context):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id, update.effective_user.full_name, update.effective_user.username)
    await update.message.reply_text(f"Hello {user['name']}! Welcome to the bot. Your balance: {user['balance']} kyat.")

# Initialize the application
application = Application.builder().token(BOT_TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))

async def pre_start_cleanup():
    logger.info("Performing pre-start cleanup...")
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted any existing webhook to ensure polling mode")
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")

async def main():
    await pre_start_cleanup()
    logger.info("Starting bot with polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")