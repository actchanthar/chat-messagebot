from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = str(update.effective_user.id)
    try:
        channels = await db.get_force_sub_channels()
        if not channels:
            logger.info(f"No force-sub channels for user {user_id}")
            return True

        keyboard = []
        subscribed = True
        for channel_id in channels:
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or chat.username or channel_id
                if chat.username:
                    channel_name = f"@{chat.username}"
                member = await context.bot.get_chat_member(channel_id, user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    subscribed = False
                    channel_link = f"https://t.me/{chat.username or channel_id.lstrip('-')}"
                    keyboard.append([InlineKeyboardButton(f"Join {channel_name}", url=channel_link)])
            except Exception as e:
                logger.error(f"Error checking membership for user {user_id} in channel {channel_id}: {e}")
                continue

        if not subscribed:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Please join the required channels to use this bot:\nကျေးဇူးပြု၍ ဤဘော့ကိုအသုံးပြုရန် လိုအပ်သောချန်နယ်များသို့ ဝင်ရောက်ပါ။",
                reply_markup=reply_markup
            )
            logger.info(f"User {user_id} not subscribed to all required channels")
            return False
        logger.info(f"User {user_id} passed subscription check")
        return True
    except Exception as e:
        logger.error(f"Error in checksubscription for user {user_id}: {e}")
        await update.message.reply_text("An error occurred while checking subscriptions.")
        return False

def register_handlers(application: Application):
    application.add_handler(CommandHandler("checksubscription", checksubscription))