from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def check_admin(user_id, update):
    if str(user_id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        logger.warning(f"Unauthorized admin attempt by user {user_id}")
        return False
    return True

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setinvite <number>")
        return
    try:
        value = int(context.args[0])
        if value < 0:
            await update.message.reply_text("Invite requirement must be non-negative.")
            return
        await db.set_invite_requirement(value)
        await update.message.reply_text(f"Invite requirement set to {value}.")
        logger.info(f"User {user_id} set invite requirement to {value}")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        logger.error(f"Invalid number for /setinvite by user {user_id}: {context.args[0]}")
    except Exception as e:
        await update.message.reply_text("Failed to set invite requirement.")
        logger.error(f"Error in /setinvite for user {user_id}: {e}")

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /addchnl <channel_id>")
        return
    channel_id = context.args[0]
    try:
        # Validate channel ID format (e.g., -1001234567890)
        if not channel_id.startswith("-100") or not channel_id[4:].isdigit():
            await update.message.reply_text("Invalid channel ID format. Use -100 followed by numbers.")
            return
        # Check if bot is admin in the channel
        chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if chat_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("Bot must be an admin in the channel.")
            return
        await db.add_force_sub_channel(channel_id)
        await update.message.reply_text(f"Added channel {channel_id} for force subscription.")
        logger.info(f"User {user_id} added force sub channel {channel_id}")
    except Exception as e:
        await update.message.reply_text("Failed to add channel.")
        logger.error(f"Error in /addchnl for user {user_id}: {e}")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return
    channel_id = context.args[0]
    try:
        channels = await db.get_force_sub_channels()
        if channel_id not in channels:
            await update.message.reply_text(f"Channel {channel_id} is not in the force subscription list.")
            return
        await db.remove_force_sub_channel(channel_id)
        await update.message.reply_text(f"Removed channel {channel_id} from force subscription.")
        logger.info(f"User {user_id} removed force sub channel {channel_id}")
    except Exception as e:
        await update.message.reply_text("Failed to remove channel.")
        logger.error(f"Error in /delchnl for user {user_id}: {e}")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    try:
        channels = await db.get_force_sub_channels()
        if not channels:
            await update.message.reply_text("No force subscription channels set.")
        else:
            message = "Force Subscription Channels:\n" + "\n".join(channels)
            await update.message.reply_text(message)
        logger.info(f"User {user_id} listed force sub channels")
    except Exception as e:
        await update.message.reply_text("Failed to list channels.")
        logger.error(f"Error in /listchnl for user {user_id}: {e}")

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add_bonus <user_id> <amount>")
        return
    try:
        target_id, amount = context.args[0], int(context.args[1])
        user = await db.get_user(target_id)
        if not user:
            await update.message.reply_text("User not found.")
            return
        new_balance = user.get("balance", 0) + amount
        await db.update_user(target_id, {"balance": new_balance})
        await update.message.reply_text(f"Added {amount} kyats to user {target_id}.")
        await context.bot.send_message(target_id, f"You received a bonus of {amount} kyats!")
        logger.info(f"User {user_id} added {amount} kyats to user {target_id}")
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        logger.error(f"Invalid amount for /add_bonus by user {user_id}: {context.args[1]}")
    except Exception as e:
        await update.message.reply_text("Failed to add bonus.")
        logger.error(f"Error in /add_bonus for user {user_id}: {e}")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setmessage <number>")
        return
    try:
        value = int(context.args[0])
        if value <= 0:
            await update.message.reply_text("Message rate must be positive.")
            return
        await db.set_message_rate(value)
        await update.message.reply_text(f"Set message rate to {value} messages = 1 kyat.")
        logger.info(f"User {user_id} set message rate to {value}")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        logger.error(f"Invalid number for /setmessage by user {user_id}: {context.args[0]}")
    except Exception as e:
        await update.message.reply_text("Failed to set message rate.")
        logger.error(f"Error in /setmessage for user {user_id}: {e}")

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return
    try:
        target_id, amount = context.args[0], int(context.args[1])
        sender = await db.get_user(user_id)
        receiver = await db.get_user(target_id)
        if not sender or not receiver:
            await update.message.reply_text("User not found.")
            return
        if sender["balance"] < amount:
            await update.message.reply_text("Insufficient balance.")
            return
        await db.update_user(user_id, {"balance": sender["balance"] - amount})
        await db.update_user(target_id, {"balance": receiver["balance"] + amount})
        await update.message.reply_text(f"Transferred {amount} kyats to {target_id}.")
        await context.bot.send_message(target_id, f"You received {amount} kyats from {sender['name']}!")
        logger.info(f"User {user_id} transferred {amount} kyats to {target_id}")
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        logger.error(f"Invalid amount for /transfer by user {user_id}: {context.args[1]}")
    except Exception as e:
        await update.message.reply_text("Failed to transfer.")
        logger.error(f"Error in /transfer for user {user_id}: {e}")

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    try:
        await db.set_count_messages(True)
        await update.message.reply_text("Message counting enabled.")
        logger.info(f"User {user_id} enabled message counting")
    except Exception as e:
        await update.message.reply_text("Failed to enable message counting.")
        logger.error(f"Error in /on for user {user_id}: {e}")

async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    try:
        await db.set_count_messages(False)
        await update.message.reply_text("Message counting disabled.")
        logger.info(f"User {user_id} disabled message counting")
    except Exception as e:
        await update.message.reply_text("Failed to disable message counting.")
        logger.error(f"Error in /off for user {user_id}: {e}")

def register_handlers(application):
    application.add_handler(CommandHandler("setinvite", setinvite))
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))
    application.add_handler(CommandHandler("add_bonus", add_bonus))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("transfer", transfer))
    application.add_handler(CommandHandler("on", on))
    application.add_handler(CommandHandler("off", off))