# plugins/help.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /help command from user {user_id} in chat {chat_id}")

    # Determine how to reply based on whether this is a command or callback
    if update.message:
        reply_func = update.message.reply_text
    elif update.callback_query:
        reply_func = update.callback_query.message.reply_text
    else:
        logger.error(f"No valid message or callback query for user {user_id}")
        return

    await reply_func(
        "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
        "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
        "အမိန့်များ:\n"
        "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
        "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
        "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
        "/help - ဤစာကိုပြရန်"
    )
    logger.info(f"Successfully sent /help response to user {user_id} in chat {chat_id}")

def register_handlers(application):
    logger.info("Registering help handlers")
    application.add_handler(CommandHandler("help", help_command))