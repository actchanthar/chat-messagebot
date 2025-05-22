from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    sender_username = update.effective_user.username
    sender_name = update.effective_user.full_name or "Unknown"
    chat_id = update.effective_chat.id

    # Format sender mention
    sender_mention = f"@{sender_username}" if sender_username else f"[{sender_name}](tg://user?id={user_id})"

    try:
        # Fetch all eligible users (not banned, not the sender)
        eligible_users = await db.users.find(
            {"banned": False, "user_id": {"$ne": user_id}},
            {"user_id": 1, "name": 1, "username": 1, "_id": 0}
        ).to_list(length=None)

        if not eligible_users:
            await update.message.reply_text("No other users available to pair with!", parse_mode="Markdown")
            logger.info(f"No eligible users for /couple by user {user_id} in chat {chat_id}")
            return

        # Pick a random user
        random_user = random.choice(eligible_users)
        random_user_id = random_user.get("user_id")
        random_username = random_user.get("username")
        random_name = random_user.get("name", "Unknown")

        # Format random user mention
        random_mention = f"@{random_username}" if random_username and random_username != "None" else f"[{random_name}](tg://user?id={random_user_id})"

        # Send pairing message with mentions
        message = f"{sender_mention} and {random_mention} are now a couple! 💕"
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"User {user_id} ({sender_name}) paired with {random_user_id} ({random_name}) via /couple in chat {chat_id}")

    except Exception as e:
        await update.message.reply_text("Failed to find a couple. Try again later!", parse_mode="Markdown")
        logger.error(f"Error in /couple for user {user_id} in chat {chat_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("couple", couple))