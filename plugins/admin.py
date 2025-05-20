from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setinvite <number>")
        return

    try:
        num = int(context.args[0])
        await db.users.update_many({}, {"$set": {"invite_requirement": num}})
        await update.message.reply_text(f"Invite requirement set to {num} for all users.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin set invite requirement to {num}")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addchnl <channel_id>")
        return

    channel_id = context.args[0]
    if await db.add_force_sub_channel(channel_id):
        await update.message.reply_text(f"Added channel {channel_id} to force subscription.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin added force-sub channel {channel_id}")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return

    channel_id = context.args[0]
    if await db.remove_force_sub_channel(channel_id):
        await update.message.reply_text(f"Removed channel {channel_id} from force subscription.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin removed force-sub channel {channel_id}")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_force_sub_channels()
    if not channels:
        await update.message.reply_text("No force-sub channels added.")
        return

    message = "Force-sub channels:\n" + "\n".join(f"- {ch}" for ch in channels)
    await update.message.reply_text(message)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /Add_bonus <user_id> <amount>")
        return

    target_id, amount = context.args
    try:
        amount = float(amount)
        user = await db.get_user(target_id)
        if user:
            new_balance = user.get("balance", 0) + amount
            await db.update_user(target_id, {"balance": new_balance})
            await update.message.reply_text(f"Added {amount} kyat bonus to user {target_id}.")
            await context.bot.send_message(LOG_CHANNEL_ID, f"Admin added {amount} kyat bonus to user {target_id}")
    except ValueError:
        await update.message.reply_text("Invalid amount.")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    try:
        num = int(context.args[0])
        if await db.set_message_rate(num):
            await update.message.reply_text(f"Set to {num} messages per kyat.")
            await context.bot.send_message(LOG_CHANNEL_ID, f"Admin set message rate to {num} messages per kyat")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

async def debug_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    user = await db.get_user(user_id)
    if user:
        messages = user.get("messages", 0)
        balance = user.get("balance", 0)
        rate = await db.get_message_rate()
        await update.message.reply_text(f"Messages: {messages}, Balance: {balance}, Rate: {rate} msg/kyat")
    else:
        await update.message.reply_text("User not found.")

def register_handlers(application: Application):
    logger.info("Registering admin handlers")
    application.add_handler(CommandHandler("setinvite", setinvite))
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))
    application.add_handler(CommandHandler("Add_bonus", add_bonus))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("debug_message_count", debug_message_count))