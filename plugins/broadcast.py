from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, pin=False):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    success_count = 0
    for user in users:
        try:
            msg = await context.bot.send_message(user["user_id"], message)
            if pin:
                await context.bot.pin_chat_message(user["user_id"], msg.message_id, disable_notification=True)
            success_count += 1
        except Exception:
            continue
    await update.message.reply_text(f"Sent to {success_count} users.")

async def pbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await broadcast(update, context, pin=True)

def register_handlers(application):
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("pbroadcast", pbroadcast))