from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/addbonus command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can add bonuses.")
        logger.info(f"User {user_id} attempted /addbonus but is not an admin")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addbonus <user_id> <amount>")
        logger.info(f"User {user_id} provided invalid arguments for /addbonus")
        return

    target_user_id = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        logger.info(f"User {user_id} provided invalid amount for /addbonus")
        return

    user = db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        logger.info(f"User {target_user_id} not found for /addbonus by {user_id}")
        return

    new_balance = user.get("balance", 0) + amount
    db.update_user(target_user_id, {"balance": new_balance})
    message = f"Added {amount} kyat to user {target_user_id}. New balance: {new_balance} kyat."

    try:
        await update.message.reply_text(message)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} added {amount} kyat to user {target_user_id}."
        )
        logger.info(f"Added bonus for user {target_user_id} by admin {user_id}")
    except Exception as e:
        logger.error(f"Failed to send /addbonus response to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Failed to send /addbonus response to {user_id}: {e}"
        )

def register_handlers(application: Application):
    logger.info("Registering add_bonus handlers")
    application.add_handler(CommandHandler("addbonus", add_bonus))