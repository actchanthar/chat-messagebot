import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].replace(".", "").isdigit():
        await update.message.reply_text("Usage: /add_bonus <user_id> <amount>")
        return

    target_user_id = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    try:
        target_user = await db.get_user(target_user_id)
        if not target_user:
            await update.message.reply_text("Target user not found.")
            return

        await db.update_balance(target_user_id, amount)
        await update.message.reply_text(f"Added {amount} {CURRENCY} to user {target_user_id}.")
        try:
            await context.bot.send_message(
                LOG_CHANNEL_ID,
                f"Admin {user_id} added {amount} {CURRENCY} to user {target_user_id}."
            )
            await context.bot.send_message(
                target_user_id,
                f"You received a bonus of {amount} {CURRENCY}! Your new balance: {target_user['balance'] + amount} {CURRENCY}"
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {target_user_id} or log channel: {e}")
    except Exception as e:
        logger.error(f"Error in add_bonus for user {target_user_id}: {e}")
        await update.message.reply_text("Failed to add bonus.")

async def set_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /setinvite <user_id> <count>")
        return

    target_user_id = context.args[0]
    count = int(context.args[1])
    try:
        target_user = await db.get_user(target_user_id)
        if not target_user:
            await update.message.reply_text("Target user not found.")
            return

        await db.update_user(target_user_id, {"invites": count})
        await update.message.reply_text(f"Set invites to {count} for user {target_user_id}.")
    except Exception as e:
        logger.error(f"Error in set_invite for user {target_user_id}: {e}")
        await update.message.reply_text("Failed to set invites.")

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    messages_per_kyat = int(context.args[0])
    try:
        await db.set_message_rate(messages_per_kyat)
        await update.message.reply_text(f"Messages per kyat set to {messages_per_kyat}.")
    except Exception as e:
        logger.error(f"Error setting messages_per_kyat: {e}")
        await update.message.reply_text("Failed to set messages per kyat.")

def register_handlers(application: Application):
    logger.info("Registering admin handlers")
    application.add_handler(CommandHandler("add_bonus", add_bonus))
    application.add_handler(CommandHandler("setinvite", set_invite))
    application.add_handler(CommandHandler("setmessage", set_message))