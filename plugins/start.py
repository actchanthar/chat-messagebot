# plugins/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /start command from user {user_id} in chat {chat_id}")

    # Clear any existing state
    logger.info(f"Clearing context.user_data for user {user_id}: {context.user_data}")
    context.user_data.clear()

    # Register user in the database if not already present
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
        logger.info(f"Created new user {user_id} in database")

    try:
        top_users = await db.get_top_users()
        top_users_text = "ထိပ်တန်းအသုံးပြုသူ ၁၀ ဦး:\n"
        if not top_users:
            top_users_text += "အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။\n"
        else:
            for i, user in enumerate(top_users, 1):
                top_users_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"

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

        await update.message.reply_photo(
            photo="https://i.imghippo.com/files/cbg1841XQ.jpg",
            caption=(
                "အုပ်စုစကားဝိုင်းစီမံခန့်ခွဲမှုဘော့မှကြိုဆိုပါတယ်!\n\n"
                "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                f"{top_users_text}\n"
                "အမိန့်များ:\n"
                "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
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

# Handle inline button callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Button callback for user {user_id}, data: {data}")

    if data == "withdraw":
        from plugins.withdrawal import withdraw  # Import here to avoid circular imports
        await withdraw(update, context)
    elif data == "balance":
        from plugins.balance import balance
        await balance(update, context)
    elif data == "top":
        from plugins.top import top
        await top(update, context)
    elif data == "help":
        await help_command(update, context)

def register_handlers(application):
    logger.info("Registering start and help handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(withdraw|balance|top|help)$"))