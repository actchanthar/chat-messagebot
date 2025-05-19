from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setinvite <number>")
        return
    threshold = int(context.args[0])
    await db.set_setting("invite_threshold", threshold)
    await update.message.reply_text(f"Invite threshold set to {threshold}.")

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /addchnl <channel_id>")
        return
    channel_id = context.args[0]
    await db.add_channel(channel_id)
    await update.message.reply_text(f"Added {channel_id} to force-sub channels.")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /setmessage <messages_per_kyat>")
        return
    rate = int(context.args[0])
    await db.set_setting("message_rate", rate)
    await update.message.reply_text(f"Set {rate} messages = 1 kyat.")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("setinvite", setinvite))
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("setmessage", setmessage))