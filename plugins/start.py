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

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    # Handle referral
    if context.args and context.args[0].isdigit():
        referrer_id = context.args[0]
        if referrer_id != user_id and await db.get_user(referrer_id):
            await db.update_user(user_id, {"referrer": referrer_id})
            logger.info(f"Set referrer {referrer_id} for user {user_id}")
            force_sub_channels = await db.get_force_sub_channels()
            if force_sub_channels:
                await update.message.reply_text(
                    "Please join the required channels using /checksubscription to complete your referral."
                )
                return

    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    welcome_message = (
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        f"Your referral link: {referral_link}\n"
        "Invite friends to earn 25 kyats per join!\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, disable_web_page_preview=True)
    logger.info(f"Sent welcome message to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))