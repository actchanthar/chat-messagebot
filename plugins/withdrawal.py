from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from config import LOG_CHANNEL, MIN_WITHDRAWAL
from database.database import get_user, update_user, create_withdrawal_request

async def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user = await get_user(user_id, chat_id)

    if not user or user.get("balance", 0) < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"သင့်လက်ကျန်ငွေ မလုံလောက်ပါ။ အနည်းဆုံး {MIN_WITHDRAWAL} ကျပ် လိုအပ်ပါတယ်။"
        )
        return

    amount = user.get("balance", 0)
    request = await create_withdrawal_request(user_id, chat_id, amount)

    log_message = (
        f"🆕 ငွေထုတ်ယူမှု တောင်းဆိုချက်\n"
        f"User ID: {user_id}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Amount: {amount} ကျပ်\n"
        f"Status: PENDING"
    )
    keyboard = [
        [InlineKeyboardButton("အတည်ပြုရန် ✅", callback_data=f"approve_{request['_id']}"),
         InlineKeyboardButton("ငြင်းပယ်ရန် ❌", callback_data=f"reject_{request['_id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    log_msg = await context.bot.send_message(
        chat_id=LOG_CHANNEL,
        text=log_message,
        reply_markup=reply_markup
    )
    await context.bot.pin_chat_message(chat_id=LOG_CHANNEL, message_id=log_msg.message_id)

    await update.message.reply_text(
        "သင့်ငွေထုတ်ယူမှု တောင်းဆိုချက်ကို တင်ပြပြီးပါပြီ။ အက်ဒမင် အတည်ပြုမှုကို စောင့်ပါ။"
    )