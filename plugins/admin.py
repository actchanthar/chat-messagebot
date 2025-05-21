from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def check_admin(user_id, update):
    if user_id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return False
    return True

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update) or not context.args:
        return
    try:
        value = int(context.args[0])
        await db.set_invite_requirement(value)
        await update.message.reply_text(f"Invite requirement set to {value}.")
    except ValueError:
        await update.message.reply_text("Please provide a number.")

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update) or not context.args:
        return
    channel_id = context.args[0]
    await db.add_force_sub_channel(channel_id)
    await update.message.reply_text(f"Added channel {channel_id} for force subscription.")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update) or not context.args:
        return
    channel_id = context.args[0]
    await db.remove_force_sub_channel(channel_id)
    await update.message.reply_text(f"Removed channel {channel_id} from force subscription.")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    channels = await db.get_force_sub_channels()
    message = "Force Subscription Channels:\n" + "\n".join(channels) if channels else "No channels set."
    await update.message.reply_text(message)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update) or len(context.args) < 2:
        return
    target_id, amount = context.args[0], int(context.args[1])
    user = await db.get_user(target_id)
    if user:
        new_balance = user.get("balance", 0) + amount
        await db.update_user(target_id, {"balance": new_balance})
        await update.message.reply_text(f"Added {amount} kyats to user {target_id}.")
        await context.bot.send_message(target_id, f"You received a bonus of {amount} kyats!")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update) or not context.args:
        return
    try:
        value = int(context.args[0])
        await db.set_message_rate(value)
        await update.message.reply_text(f"Set message rate to {value} messages = 1 kyat.")
    except ValueError:
        await update.message.reply_text("Please provide a number.")

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return
    target_id, amount = context.args[0], int(context.args[1])
    sender = await db.get_user(user_id)
    receiver = await db.get_user(target_id)
    if not sender or not receiver or sender["balance"] < amount:
        await update.message.reply_text("Transfer failed: Insufficient balance or user not found.")
        return
    await db.update_user(user_id, {"balance": sender["balance"] - amount})
    await db.update_user(target_id, {"balance": receiver["balance"] + amount})
    await update.message.reply_text(f"Transferred {amount} kyats to {target_id}.")
    await context.bot.send_message(target_id, f"You received {amount} kyats from {sender['name']}!")

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    await db.set_count_messages(True)
    await update.message.reply_text("Message counting enabled.")

async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not await check_admin(user_id, update):
        return
    await db.set_count_messages(False)
    await update.message.reply_text("Message counting disabled.")

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