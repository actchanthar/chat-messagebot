from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /add_bonus attempt by user {user_id}")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /add_bonus <user_id> <amount>")
            logger.info(f"Invalid /add_bonus syntax by user {user_id}: {args}")
            return

        target_user_id, amount_str = args
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await update.message.reply_text("Invalid amount. Please provide a positive number.")
            logger.info(f"Invalid amount in /add_bonus by user {user_id}: {amount_str}")
            return

        # Fetch target user
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text(f"User {target_user_id} not found.")
            logger.info(f"User {target_user_id} not found for /add_bonus by user {user_id}")
            return

        # Update balance
        current_balance = user.get("balance", 0)
        new_balance = current_balance + amount
        updates = {"balance": new_balance}
        success = await db.update_user(target_user_id, updates)
        if not success:
            await update.message.reply_text("Failed to update user balance.")
            logger.error(f"Failed to update balance for user {target_user_id} via /add_bonus")
            return

        # Send reply to admin
        await update.message.reply_text(
            f"Added {amount:.2f} kyat to user {target_user_id}. New balance: {new_balance:.2f} kyat."
        )

        # Log to LOG_CHANNEL_ID
        log_message = (
            f"Admin {user_id} added {amount:.2f} kyat to user {target_user_id}. "
            f"New balance: {new_balance:.2f} kyat."
        )
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
        logger.info(f"User {user_id} added {amount:.2f} kyat to user {target_user_id}")

    except Exception as e:
        await update.message.reply_text("Error processing /add_bonus. Try again later.")
        logger.error(f"Error in /add_bonus for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("add_bonus", add_bonus))