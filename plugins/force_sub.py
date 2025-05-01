# plugins/force_sub.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from config import REQUIRED_CHANNELS

async def check_subscription(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    all_subscribed = True

    for channel_id in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                all_subscribed = False
                break
        except:
            all_subscribed = False
            break

    if not all_subscribed:
        keyboard = [[InlineKeyboardButton("ချန်နယ်သို့ ဝင်ပါ", url=f"https://t.me/{channel_id}") for channel_id in REQUIRED_CHANNELS]]
        keyboard.append([InlineKeyboardButton("စစ်ဆေးရန် ✅", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("ဆက်လက်ရှာဖွေရန် ချန်�နယ်များသို့ ဝင်ပါ။", reply_markup=reply_markup)
        return False
    return True