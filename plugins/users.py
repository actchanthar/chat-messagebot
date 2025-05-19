from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":  # Admin ID
        await update.message.reply_text("Unauthorized.")
        return
    count = await db.get_user_count()
    await update.message.reply_text(f"Total users: {count}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("users", users))