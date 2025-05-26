from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS, GROUP_CHAT_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /Add_bonus <user_id> <amount>")
        return

    target_user_id, amount = args[0], args[1]
    try:
        amount = float(amount)
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("User not found.")
            return

        new_balance = user.get("balance", 0) + amount
        await db.update_user(target_user_id, {"balance": new_balance})
        await update.message.reply_text(f"Added {amount} kyat to user {target_user_id}. New balance: {new_balance} kyat.")
        logger.info(f"Admin {user_id} added bonus {amount} to user {target_user_id}")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please provide a number.")
    except Exception as e:
        logger.error(f"Error adding bonus for user {target_user_id}: {e}")
        await update.message.reply_text("Error adding bonus. Please try again.")

async def set_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /setinvite <user_id> <count>")
        return

    target_user_id, count = args[0], args[1]
    try:
        count = int(count)
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("User not found.")
            return

        await db.update_user(target_user_id, {"invited_users": count})
        await update.message.reply_text(f"Set invite count to {count} for user {target_user_id}.")
        logger.info(f"Admin {user_id} set invite count to {count} for user {target_user_id}")
    except ValueError:
        await update.message.reply_text("Invalid count. Please provide a number.")
    except Exception as e:
        logger.error(f"Error setting invite count for user {target_user_id}: {e}")
        await update.message.reply_text("Error setting invite count. Please try again.")

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /setmessage <user_id> <count>")
        return

    target_user_id, count = args[0], args[1]
    try:
        count = int(count)
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("User not found.")
            return

        target_group = GROUP_CHAT_IDS[0]
        group_messages = user.get("group_messages", {})
        group_messages[target_group] = count
        await db.update_user(target_user_id, {"group_messages": group_messages})
        await update.message.reply_text(f"Set message count to {count} for user {target_user_id} in group {target_group}.")
        logger.info(f"Admin {user_id} set message count to {count} for user {target_user_id}")
    except ValueError:
        await update.message.reply_text("Invalid count. Please provide a number.")
    except Exception as e:
        logger.error(f"Error setting message count for user {target_user_id}: {e}")
        await update.message.reply_text("Error setting message count. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering admin handlers")
    application.add_handler(CommandHandler("Add_bonus", add_bonus))
    application.add_handler(CommandHandler("setinvite", set_invite))
    application.add_handler(CommandHandler("setmessage", set_message))