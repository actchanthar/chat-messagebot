from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized.")
        return

    try:
        if not context.args:
            await update.message.reply_text("Usage: /setinvite <number>")
            return

        number = int(context.args[0])
        await db.set_setting("invite_requirement", number)
        await update.message.reply_text(f"Invite requirement set to {number}.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error in setinvite for user {user_id}: {e}")
        await update.message.reply_text("An error occurred. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering setinvite handlers")
    application.add_handler(CommandHandler("setinvite", setinvite, block=False))