import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY, APPROVED_GROUPS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add_bonus <user_id> <amount>")
        return

    target_user_id = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    try:
        success = await db.add_bonus(target_user_id, amount)
        if success:
            user = await db.get_user(target_user_id)
            new_balance = user.get("balance", 0) if user else 0
            await update.message.reply_text(
                f"Added {int(amount)} {CURRENCY} to user {target_user_id}. New balance: {int(new_balance)} {CURRENCY}."
            )
            try:
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"Admin {user_id} added {int(amount)} {CURRENCY} bonus to user {target_user_id}."
                )
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"You received a bonus of {int(amount)} {CURRENCY}! Your new balance is {int(new_balance)} {CURRENCY}."
                )
            except Exception as e:
                logger.error(f"Failed to notify: {e}")
        else:
            await update.message.reply_text("Failed to add bonus. User not found.")
    except Exception as e:
        await update.message.reply_text("An error occurred.")

async def set_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setinvite <user_id> <count>")
        return

    target_user_id = context.args[0]
    try:
        count = int(context.args[1])
        await db.update_user(target_user_id, {"invites": count})
        await update.message.reply_text(f"Set invites to {count} for user {target_user_id}.")
    except Exception as e:
        await update.message.reply_text("Failed to set invites.")

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    try:
        messages_per_kyat = int(context.args[0])
        await db.set_message_rate(messages_per_kyat)
        await update.message.reply_text(f"Messages per kyat set to {messages_per_kyat}.")
    except Exception as e:
        await update.message.reply_text("Failed to set messages per kyat.")

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /checkgroup <group_id>")
        return

    group_id = context.args[0]
    if group_id not in APPROVED_GROUPS:
        await update.message.reply_text("Group not approved for message counting.")
        return

    try:
        total_messages = await db.get_group_message_count(group_id)
        message_rate = await db.get_message_rate()
        await update.message.reply_text(
            f"Group {group_id} is approved for message counting.\n"
            f"Total messages counted: {total_messages:,}\n"
            f"Earning rate: {message_rate} messages = 1 kyat"
        )
    except Exception as e:
        await update.message.reply_text("Error checking group.")

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addgroup <group_id>")
        return

    group_id = context.args[0]
    if group_id == "-1002061898677":
        await update.message.reply_text(f"Group {group_id} is already approved.")
    else:
        await update.message.reply_text("Only group -1002061898677 can be added.")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("add_bonus", add_bonus))
    application.add_handler(CommandHandler("Add_bonus", add_bonus))
    application.add_handler(CommandHandler("setinvite", set_invite))
    application.add_handler(CommandHandler("setmessage", set_message))
    application.add_handler(CommandHandler("checkgroup", checkgroup))
    application.add_handler(CommandHandler("addgroup", addgroup))
