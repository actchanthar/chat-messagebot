from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    sender_name = update.effective_user.full_name or "Unknown"

    try:
        # Fetch all eligible users (not banned, not the sender)
        eligible_users = await db.users.find(
            {"banned": False, "user_id": {"$ne": user_id}},
            {"user_id": 1, "name": 1, "_id": 0}
        ).to_list(length=None)

        if not eligible_users:
            await update.message.reply_text("No other users available to pair with!")
            logger.info(f"No eligible users for /couple by user {user_id}")
            return

        # Pick a random user
        random_user = random.choice(eligible_users)
        random_name = random_user.get("name", "Unknown")

        # Send pairing message
        message = f"{sender_name} and {random_name} are now a couple! 💕"
        await update.message.reply_text(message)
        logger.info(f"User {user_id} ({sender_name}) paired with {random_user['user_id']} ({random_name}) via /couple")

    except Exception as e:
        await update.message.reply_text("Failed to find a couple. Try again later!")
        logger.error(f"Error in /couple for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("couple", couple))