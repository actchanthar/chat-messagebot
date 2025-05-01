from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import BOT_TOKEN
from plugins import message_counter, force_sub, withdrawal, add_group

async def start(update: Update, context: CallbackContext):
    if await force_sub.check_subscription(update, context):
        await update.message.reply_text("မင်္ဂလာပါ! စာပို့ရင်း ပိုက်ဆံရှာပါ။ 1 message = 1 ကျပ်")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("withdraw", withdrawal.withdraw))
    application.add_handler(CommandHandler("addgroup", add_group.add_group))  # New command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_counter.count_message))

    application.run_polling()

if __name__ == "__main__":
    main()