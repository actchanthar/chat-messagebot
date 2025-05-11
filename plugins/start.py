from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
        "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
        "အမိန့်များ:\n"
        "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
        "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
        "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
        "/help - ဤစာကိုပြရန်"
    )

def register_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))