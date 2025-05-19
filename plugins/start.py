from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command by user {user_id} in chat {chat_id}")

    # Handle referral
    if context.args and context.args[0].startswith("referral_"):
        inviter_id = context.args[0].replace("referral_", "")
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name)
            await db.update_user(user_id, {"inviter_id": inviter_id})
            logger.info(f"User {user_id} joined via referral from {inviter_id}")

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    referral_link = f"https://t.me/{context.bot.username}?start=referral_{user_id}"
    welcome_message = (
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages and inviting friends!\n"
        f"Referral Link: {referral_link}\n"
        "Invite 15 users who join our channels to withdraw!\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")],
        [InlineKeyboardButton("Referral Users", callback_data="referral_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))