from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from config import BOT_TOKEN
from plugins import message_counter, force_sub, withdrawal, add_group, add_bonus  # Add add_bonus
from database.database import get_user

async def start(update: Update, context: CallbackContext):
    if await force_sub.check_subscription(update, context):
        await update.message.reply_text(
            "မင်္ဂလာပါ! စာပို့ရင်း ပိုက်ဆံရှာပါ။ 1 message = 1 ကျပ်\n"
            "သင့်လက်ကျန်ငွေကို စစ်ဆေးရန် /balance ကို အသုံးပြုပါ။\n"
            "ငွေထုတ်ယူရန် အနည်းဆုံး 100 ကျပ် လိုအပ်ပါတယ်။ /withdraw ကို အသုံးပြုပါ။"
        )

async def check_balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user = await get_user(user_id, chat_id)
    balance = user.get("balance", 0) if user else 0
    await update.message.reply_text(f"@{update.effective_user.username} သင့်မှာ {balance} ကျပ် ရှိပါတယ်။")

async def handle_check_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    is_subscribed = await force_sub.check_subscription(update, context)
    if is_subscribed:
        await query.message.reply_text("သင်သည် လိုအပ်သော ချန်နယ်များသို့ ဝင်ပြီးပါပြီ။ စာပို့ရင်း ပိုက်ဆံရှာနိုင်ပါပြီ။")
    else:
        pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("withdraw", withdrawal.withdraw))
    application.add_handler(CommandHandler("addgroup", add_group.add_group))
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(CommandHandler("add_bonus", add_bonus.add_bonus))  # Add this line
    application.add_handler(CallbackQueryHandler(handle_check_subscription, pattern="check_subscription"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_counter.count_message))

    application.run_polling()

if __name__ == "__main__":
    main()