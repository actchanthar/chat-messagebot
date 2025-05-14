from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from config import GROUP_CHAT_ID, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define withdrawal steps
STEP_AMOUNT, STEP_PAYMENT_METHOD, STEP_DETAILS = range(3)

# Entry point for /withdraw command and button callback
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    # If triggered by a button, answer the callback query
    if update.callback_query:
        await update.callback_query.answer()
        # Store the chat context to ensure the next message is linked
        context.user_data["conversation_chat_id"] = chat_id

    # Ensure this is a private chat
    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        if update.message:
            await update.message.reply_text("Please use the /withdraw command in a private chat.")
        else:
            await update.callback_query.message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(str(user_id))
    if not user:
        logger.error(f"User {user_id} not found in database")
        if update.message:
            await update.message.reply_text("User not found. Please start with /start.")
        else:
            await update.callback_query.message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        if update.message:
            await update.message.reply_text("You are banned from using this bot.")
        else:
            await update.callback_query.message.reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Prompt for withdrawal amount
    logger.info(f"Prompting user {user_id} for withdrawal amount in chat {chat_id}")
    if update.message:
        await update.message.reply_text(
            f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
            f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
        )
    else:
        await update.callback_query.message.reply_text(
            f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
            f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
        )
    return STEP_AMOUNT

# Handle withdrawal amount input
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received message for amount input from user {user_id} in chat {chat_id}: {message.text}")

    # Ensure this is the correct chat context (especially for button-initiated conversations)
    expected_chat_id = context.user_data.get("conversation_chat_id")
    if expected_chat_id and chat_id != expected_chat_id:
        logger.info(f"Message from wrong chat {chat_id}, expected {expected_chat_id}")
        await message.reply_text("Please respond in the same chat where you started the withdrawal.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(str(user_id))
        if not user or user.get("balance", 0) < amount:
            await message.reply_text("Insufficient balance or user not found. Please check your balance with /balance.")
            return ConversationHandler.END

        # Check daily withdrawal limit
        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal:
            last_withdrawal_date = last_withdrawal.date()
            current_date = current_time.date()
            if last_withdrawal_date == current_date:
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.info(f"User {user_id} exceeded daily limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                    await message.reply_text(f"Daily withdrawal limit is {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. You've already withdrawn {withdrawn_today} {CURRENCY} today.")
                    return STEP_AMOUNT
            else:
                withdrawn_today = 0

        # Store amount in context
        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today

        # Show payment method selection buttons
        keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(
            "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} prompted for payment method selection with buttons: {PAYMENT_METHODS}")
        return STEP_PAYMENT_METHOD

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

# Handle payment method selection
async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    logger.info(f"Handling payment method selection for user {user_id}, data: {data}, context: {context.user_data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    if not context.user_data.get("withdrawal_amount"):
        logger.error(f"User {user_id} has no withdrawal amount in context")
        await query.message.reply_text("Withdrawal amount not found. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}, context: {context.user_data}")

    if method == "KBZ Pay":
        await query.message.reply_text(
            "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW). 💳\n"
            "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။"
        )
    elif method == "Wave Pay":
        await query.message.reply_text(
            "Please provide your Wave Pay account details (e.g., phone number and name). 💳\n"
            "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ ဖုန်းနံပါတ်နှင့် နာမည်)။"
        )
    elif method == "Phone Bill":
        await query.message.reply_text(
            "Please provide your phone number for Phone Bill payment. 💳\n"
            "ကျေးဇူးပြု၍ ဖုန်းဘေလ်ငွေပေးချေမှုအတွက် သင့်ဖုန်းနံပါတ်ကို ပေးပါ။"
        )
    else:
        await query.message.reply_text(
            f"Please provide your {method} account details. 💳\n"
            f"ကျေးဇူးပြု၍ သင်၏ {method} အကောင့်အသေးစိတ်ကို ပေးပါ။"
        )
    logger.info(f"User {user_id} prompted for {method} account details")
    return STEP_DETAILS

# Handle account details input
async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Handling account details for user {user_id}: {message.text}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    if not amount or not payment_method:
        logger.error(f"User {user_id} missing amount or payment method in context: {context.user_data}")
        await message.reply_text("Error: Withdrawal amount or payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    payment_details = message.text if message.text else "No details provided"
    context.user_data["withdrawal_details"] = payment_details
    logger.info(f"User {user_id} submitted account details, context: {context.user_data}")

    # Send withdrawal request to admin log channel
    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=(
                f"Withdrawal Request:\n"
                f"User ID: {user_id}\n"
                f"User: @{update.effective_user.username or 'N/A'}\n"
                f"Amount: {amount} {CURRENCY} 💸\n"
                f"Payment Method: {payment_method}\n"
                f"Details: {payment_details}\n"
                f"Status: PENDING ⏳"
            ),
            reply_markup=reply_markup
        )
        logger.info(f"Sent withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ကျေးဇူးပြု၍ အုပ်ချုပ်ရေးမှူး၏ အတည်ပြုချက်ကို စောင့်ပါ။"
    )
    logger.info(f"User {user_id} submitted withdrawal request for {amount} {CURRENCY}")

    # Clear context after submission
    context.user_data.clear()
    logger.info(f"Cleared context for user {user_id} after withdrawal submission")
    return ConversationHandler.END

# Handle admin approval/rejection
async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt callback for user {query.from_user.id}, data: {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = int(user_id)
            amount = int(amount)

            user = await db.get_user(str(user_id))
            if not user:
                logger.error(f"User {user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if amount > balance:
                logger.error(f"Insufficient balance for user {user_id}. Requested: {amount}, Balance: {balance}")
                await query.message.reply_text("User has insufficient balance for this withdrawal.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)

            if last_withdrawal:
                last_withdrawal_date = last_withdrawal.date()
                current_date = current_time.date()
                if last_withdrawal_date == current_date:
                    if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                        logger.error(f"User {user_id} exceeded daily withdrawal limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                        await query.message.reply_text(f"User has exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}.")
                        return
                else:
                    withdrawn_today = 0

            new_balance = balance - amount
            new_withdrawn_today = withdrawn_today + amount
            success = await db.update_user(str(user_id), {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": new_withdrawn_today
            })

            if success:
                logger.info(f"Withdrawal approved for user {user_id}. Amount: {amount}, New balance: {new_balance}")
                await query.message.reply_text(f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.")
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Your withdrawal of {amount} {CURRENCY} has been approved! Your new balance is {new_balance} {CURRENCY}.\n"
                             f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
                    )
                    username = user.get("username", user["name"])
                    mention = f"@{username}" if username else user["name"]
                    group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        text=group_message
                    )
                    logger.info(f"Sent withdrawal announcement to group {GROUP_CHAT_ID} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id} or send group announcement: {e}")
            else:
                logger.error(f"Failed to update user {user_id} for withdrawal approval")
                await query.message.reply_text("Error approving withdrawal. Please try again.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = int(user_id)
            amount = int(amount)

            logger.info(f"Withdrawal rejected for user {user_id}. Amount: {amount}")
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected by the admin. If there are any problems or you wish to appeal, please contact @actanibot.\n"
                         f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို အုပ်ချုပ်ရေးမှူးမှ ပယ်ချလိုက်ပါသည်။ ပြဿနာများရှိပါက သို့မဟုတ် အယူခံဝင်လိုပါက @actanibot သို့ ဆက်သွယ်ပါ။"
                )
                logger.info(f"Notified user {user_id} of withdrawal rejection")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} of withdrawal rejection: {e}")
    except Exception as e:
        logger.error(f"Error in handle_admin_receipt: {e}")
        await query.message.reply_text("Error processing withdrawal request. Please try again.")

# Cancel the withdrawal process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"User {user_id} canceled the withdrawal process")
    await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။")
    context.user_data.clear()
    return ConversationHandler.END

# Register handlers for the application
def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^withdraw$"),  # Handle button click
        ],
        states={
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_"))