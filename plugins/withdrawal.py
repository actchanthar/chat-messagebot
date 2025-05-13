from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import logging

# Set up logging to debug issues
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the conversation
STEP_AMOUNT = 0

# Start the withdrawal process
async def withdraw(update, context):
    await update.message.reply_text(
        "Please enter the amount you wish to withdraw (minimum: 100 kyat). 💸\n"
        "ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး 100 ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

# Handle the amount input
async def handle_amount(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    amount_text = update.message.text

    # Log the input to confirm it’s received
    logger.info(f"User {user_id} in chat {chat_id} entered amount: {amount_text}")

    try:
        amount = int(amount_text)
        if amount < 100:
            await update.message.reply_text(
                "The amount must be at least 100 kyat. Please enter a valid amount.\n"
                "ပမာဏသည် အနည်းဆုံး 100 ကျပ်ဖြစ်ရမည်။ မှန်ကန်သောပမာဏကို ထည့်ပါ။"
            )
            return STEP_AMOUNT
        else:
            await update.message.reply_text(
                f"You entered: {amount} kyat. Processing your withdrawal...\n"
                f"သင်ထည့်ထားသော ပမာဏ - {amount} ကျပ်။ ငွေထုတ်မှုကို ဆောင်ရွက်နေပါသည်..."
            )
            return ConversationHandler.END  # Exit the conversation for now
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်တစ်ခု ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

# Cancel the process if needed
async def cancel(update, context):
    await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါပြီ။")
    return ConversationHandler.END

# Set up the bot
def main():
    # Replace "YOUR_TOKEN" with your actual bot token
    application = Application.builder().token("YOUR_TOKEN").build()

    # Define the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={
            STEP_AMOUNT: [MessageHandler(filters.TEXT, handle_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the handler to the application
    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()