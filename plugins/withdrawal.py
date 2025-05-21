from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Debugging: Confirm file is loaded
print("Loading withdrawal.py")
print("Defining withdraw function")

async def withdraw(update: Update oito_context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command received from user {user_id} in chat {chat_id}")
    
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use /withdraw in a private chat.")
        return
    
    await update.message.reply_text("Withdrawal feature is under maintenance. Please try again later.")

# Debugging: Confirm register_handlers is defined
print("Defining register_handlers function")

def register_handlers(application: Application) -> None:
    logger.info("Registering withdrawal handlers")
    application.add_handler(CommandHandler("withdraw", withdraw))
    print("Withdrawal handler registered")