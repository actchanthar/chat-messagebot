from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found, creating new user")
        user = await db.create_user(user_id, update.effective_user.full_name)
    else:
        # Update user name in case it has changed
        await db.update_user(user_id, {"name": update.effective_user.full_name})

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        await update.message.reply_text("You are banned from using this bot.")
        return

    # Get top users for the leaderboard
    top_users = await db.get_top_users()
    if not top_users:
        logger.warning("No top users found or error retrieving top users")
        leaderboard = "No top users available yet."
    else:
        leaderboard = "🏆 Top Users (by messages):\n"
        for i, top_user in enumerate(top_users, 1):
            leaderboard += f"{i}. {top_user['name']} - {top_user['messages']} messages\n"

    # Create the welcome message
    welcome_message = (
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        f"အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        f"{leaderboard}\n\n"
        "Use the buttons below to check your balance, withdraw your earnings, or join our group.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ သင့်ဝင်ငွေများကို ထုတ်ယူရန် သို့မဟုတ် ကျွန်ုပ်တို့၏ အုပ်စုသို့ ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    # Add buttons for balance, withdraw, developer contact, and earnings group
    keyboard = [
        [
            InlineKeyboardButton("Check Balance 💰", callback_data="balance"),
            InlineKeyboardButton("Withdraw 💸", callback_data="withdraw"),
        ],
        [
            InlineKeyboardButton("It Dev 💻", url="https://t.me/When_the_night_falls_my_soul_se"),  # Replace YourUsername with your actual Telegram username
            InlineKeyboardButton("Earnings Group 👥", url="https://t.me/+yuVWepSGgZQ4ZWY1"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        logger.info(f"Sent /start response to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /start response to user {user_id} in chat {chat_id}: {e}")
        await update.message.reply_text("Error sending welcome message. Please try again later.")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))