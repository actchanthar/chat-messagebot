from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check if user exists, create if not
    user = await db.get_user(user_id)
    if not user:
        user_name = update.effective_user.first_name or "Unknown"
        user = await db.create_user(user_id, user_name)
        if not user:
            await update.message.reply_text("Failed to create user. Please try again later.")
            logger.error(f"Failed to create user {user_id}")
            return

    # Prepare the inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("Check Balance 💰", callback_data="balance"),
            InlineKeyboardButton("Withdraw 🌸", callback_data="withdraw")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Prepare the welcome message with additional text below buttons
    welcome_message = (
        "👋 Hello! Welcome to the bot!\n"
        "မင်္ဂလာပါ! ဘော့တ်သို့ ကြိုဆိုပါတယ်!\n\n"
        "It Dev 5062124930\n"
        "Earnings Group https://t.me/+yuVWepSGgZQ4ZWY1"
    )

    # Send the message with the keyboard
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )
    logger.info(f"Sent /start response to user {user_id} in chat {chat_id}")

    # Optionally, fetch and display top users (if integrated with /top)
    top_users = await db.get_top_users()
    if top_users:
        top_users_text = "🏆 Top Users:\n"
        for i, user in enumerate(top_users, 1):
            top_users_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user.get('balance', 0)} kyat\n"
        await update.message.reply_text(top_users_text)
        logger.info(f"Sent top users list to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))