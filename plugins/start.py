from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import config
import logging
from plugins.balance import balance as balance_handler, withdraw as withdraw_handler
from plugins.top import top as top_handler

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /start command from user {user_id} in chat {chat_id}")

    try:
        # Get top 10 users
        top_users = await db.get_top_users()
        top_users_text = "ထိပ်တန်းအသုံးပြုသူ ၁၀ ဦး:\n"
        if not top_users:
            top_users_text += "အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။\n"
        else:
            for i, user in enumerate(top_users, 1):
                top_users_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"

        # Define inline keyboard buttons
        keyboard = [
            [
                InlineKeyboardButton("ထုတ်ယူရန်", callback_data="withdraw"),
                InlineKeyboardButton("လက်ကျန်", callback_data="balance"),
            ],
            [
                InlineKeyboardButton("ထိပ်တန်း", callback_data="top"),
                InlineKeyboardButton("အကူအညီ", callback_data="help"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send welcome message with image and buttons in Myanmar
        await update.message.reply_photo(
            photo="https://i.imghippo.com/files/cbg1841XQ.jpg",
            caption=(
                "အုပ်စုစကားဝိုင်းစီမံခန့်ခွဲမှုဘော့မှကြိုဆိုပါတယ်!\n\n"
                "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                f"{top_users_text}\n"
                "အမိန့်များ:\n"
                "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                "/top -ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                "ထုတ်ယူရန်တောင်းဆိုရန်\n"
                "/help - ဤစာကိုပြရန်"
            ),
            reply_markup=reply_markup
        )
        logger.info(f"Successfully sent /start response to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /start response to user {user_id} in chat {chat_id}: {e}")
        raise

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /help command from user {user_id} in chat {chat_id}")

    try:
        await update.message.reply_text(
            "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
            "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
            "အမိန့်များ:\n"
            "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
            "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
            "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
            "/help - ဤစာကိုပြရန်"
        )
        logger.info(f"Successfully sent /help response to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /help response to user {user_id} in chat {chat_id}: {e}")
        raise

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat.id)
    callback_data = query.data
    logger.info(f"Received button press from user {user_id} in chat {chat_id}: {callback_data}")

    try:
        if callback_data == "balance":
            await balance_handler(update, context)
        elif callback_data == "withdraw":
            await withdraw_handler(update, context)
        elif callback_data == "top":
            await top_handler(update, context)
        elif callback_data == "help":
            # Simulate the /help command
            await query.message.reply_text(
                "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
                "အမိန့်များ:\n"
                "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
                "/help - ဤစာကိုပြရန်"
            )
            logger.info(f"Sent help response to user {user_id} via button in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to handle button {callback_data} for user {user_id} in chat {chat_id}: {e}")
        await query.message.reply_text("An error occurred while processing your request.")
        raise

def register_handlers(application):
    logger.info("Registering start, help, and button handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_button))