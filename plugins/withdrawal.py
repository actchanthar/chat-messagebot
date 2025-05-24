from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
SELECT_METHOD, ENTER_AMOUNT, ENTER_KPAY = range(3)

async def withdrawal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    trigger = "button" if update.callback_query else "command"
    logger.info(f"START: Withdraw command initiated by user {user_id} in chat {chat_id} with {trigger} {update.message.text if update.message else update.callback_query.data}")

    # Clear previous user_data to avoid stale state
    context.user_data.clear()
    logger.info(f"START: Cleared user_data for user {user_id}")

    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use /withdrawal in a private chat.")
        logger.info(f"START: User {user_id} attempted withdrawal in non-private chat {chat_id}")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please contact support.") if update.message else await update.callback_query.message.reply_text("User not found. Please contact support.")
        logger.error(f"START: User {user_id} not found for withdrawal")
        return ConversationHandler.END
    logger.info(f"START: Retrieved user {user_id} from database: {user}")

    balance = user.get("balance", 0)
    context.user_data["balance"] = balance
    context.user_data["user_id"] = user_id
    context.user_data["last_message"] = None  # Track last sent message
    logger.info(f"START: Set user_data for user {user_id} - balance: {balance}")

    if balance < 100:
        await update.message.reply_text(f"Your balance is {balance:.2f} {CURRENCY}. Minimum withdrawal is 100 {CURRENCY}.") if update.message else await update.callback_query.message.reply_text(f"Your balance is {balance:.2f} {CURRENCY}. Minimum withdrawal is 100 {CURRENCY}.")
        logger.info(f"START: User {user_id} has insufficient balance: {balance}")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("KBZ Pay", callback_data="method_kbzpay")],
        [InlineKeyboardButton("Wave Pay", callback_data="method_wavepay")],
        [InlineKeyboardButton("Phone Bill", callback_data="method_phonebill")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text("Please select your payment method:", reply_markup=reply_markup)
            logger.info(f"START: Edited message with payment method selection for user {user_id}")
        else:
            await update.message.reply_text("Please select your payment method:", reply_markup=reply_markup)
            logger.info(f"START: Sent payment method selection message to user {user_id}")
    except Exception as e:
        logger.error(f"START: Failed to send payment method selection message to user {user_id}: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END
    return SELECT_METHOD

async def select_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"SELECT_METHOD: User {user_id} triggered select_method with data: {query.data}")

    if not context.user_data.get("user_id"):
        await query.message.reply_text("Session expired. Please start again with /withdrawal.")
        logger.warning(f"SELECT_METHOD: Session expired for user {user_id}")
        return ConversationHandler.END
    logger.info(f"SELECT_METHOD: Session valid for user {user_id}, user_data: {context.user_data}")

    method = query.data.split("_")[1]  # Extract method (kbzpay, wavepay, phonebill)
    context.user_data["method"] = method
    logger.info(f"SELECT_METHOD: User {user_id} selected payment method: {method}")

    # Prevent duplicate prompts
    prompt = f"Please enter the amount to withdraw (minimum: 100 {CURRENCY}, your balance: {context.user_data['balance']:.2f} {CURRENCY}):"
    if context.user_data.get("last_message") == prompt:
        logger.info(f"SELECT_METHOD: Duplicate prompt prevented for user {user_id}")
        return ENTER_AMOUNT

    context.user_data["last_message"] = prompt
    try:
        await query.message.edit_text(prompt)
        logger.info(f"SELECT_METHOD: Sent amount prompt to user {user_id}")
    except Exception as e:
        logger.error(f"SELECT_METHOD: Error editing message for user {user_id}: {e}")
        await query.message.reply_text(prompt)
        logger.info(f"SELECT_METHOD: Fallback - sent amount prompt as new message to user {user_id}")
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"ENTER_AMOUNT: User {user_id} entered amount: {update.message.text}")

    if not context.user_data.get("user_id"):
        await update.message.reply_text("Session expired. Please start again with /withdrawal.")
        logger.warning(f"ENTER_AMOUNT: Session expired for user {user_id}")
        return ConversationHandler.END
    logger.info(f"ENTER_AMOUNT: Session valid for user {user_id}, user_data: {context.user_data}")

    user_id = context.user_data["user_id"]
    method = context.user_data["method"]
    balance = context.user_data["balance"]
    text = update.message.text

    try:
        amount = float(text)
        logger.info(f"ENTER_AMOUNT: Parsed amount {amount} for user {user_id}")
        if amount <= 0:
            await update.message.reply_text("Amount must be greater than 0.")
            logger.info(f"ENTER_AMOUNT: Amount {amount} is invalid (<= 0) for user {user_id}")
            return ENTER_AMOUNT

        if amount > balance:
            await update.message.reply_text(f"Insufficient balance. Your balance is {balance:.2f} {CURRENCY}.")
            logger.info(f"ENTER_AMOUNT: Insufficient balance for user {user_id}, balance: {balance}, amount: {amount}")
            return ENTER_AMOUNT

        if amount < 100:
            await update.message.reply_text(f"Minimum withdrawal is 100 {CURRENCY}.")
            logger.info(f"ENTER_AMOUNT: Amount {amount} below minimum (100) for user {user_id}")
            return ENTER_AMOUNT

        context.user_data["amount"] = amount
        logger.info(f"ENTER_AMOUNT: Set amount {amount} in user_data for user {user_id}")
        if method in ["kbzpay", "wavepay"]:
            prompt = "Please send your KBZ Pay or Wave Pay account (e.g., phone number or account ID) or an image QR:"
            context.user_data["last_message"] = prompt
            await update.message.reply_text(prompt)
            logger.info(f"ENTER_AMOUNT: Sent KBZ/Wave Pay account prompt to user {user_id}")
            return ENTER_KPAY
        else:
            logger.info(f"ENTER_AMOUNT: Proceeding to submit withdrawal for user {user_id} (method: {method})")
            return await submit_withdrawal(update, context)

    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        logger.info(f"ENTER_AMOUNT: Invalid number entered by user {user_id}: {text}")
        return ENTER_AMOUNT
    except Exception as e:
        await update.message.reply_text(f"Error processing amount: {str(e)}. Contact support.")
        logger.error(f"ENTER_AMOUNT: Error for user {user_id}: {e}")
        return ENTER_AMOUNT

async def enter_kpay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"ENTER_KPAY: User {user_id} entered KBZ/Wave Pay details")

    if not context.user_data.get("user_id"):
        await update.message.reply_text("Session expired. Please start again with /withdrawal.")
        logger.warning(f"ENTER_KPAY: Session expired for user {user_id}")
        return ConversationHandler.END
    logger.info(f"ENTER_KPAY: Session valid for user {user_id}, user_data: {context.user_data}")

    user_id = context.user_data["user_id"]
    method = context.user_data["method"]

    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        context.user_data["kpay_account"] = f"QR_IMAGE:{file_id}"
        logger.info(f"ENTER_KPAY: User {user_id} uploaded QR image with file_id {file_id}")
    elif update.message.text:
        kpay_account = update.message.text.strip()
        context.user_data["kpay_account"] = kpay_account
        logger.info(f"ENTER_KPAY: User {user_id} provided kpay account: {kpay_account}")
    else:
        prompt = "Please send a phone number/account ID or an image QR."
        if context.user_data.get("last_message") != prompt:
            context.user_data["last_message"] = prompt
            await update.message.reply_text(prompt)
            logger.info(f"ENTER_KPAY: Sent fallback prompt to user {user_id} for phone number or QR")
        return ENTER_KPAY

    logger.info(f"ENTER_KPAY: Proceeding to submit withdrawal for user {user_id} (method: {method})")
    return await submit_withdrawal(update, context)

async def submit_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = context.user_data["user_id"]
    method = context.user_data["method"]
    amount = context.user_data.get("amount")
    kpay_account = context.user_data.get("kpay_account", "Not provided")
    logger.info(f"SUBMIT_WITHDRAWAL: Submitting withdrawal for user {user_id}, method: {method}, amount: {amount}, account: {kpay_account}")

    withdrawal_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_{withdrawal_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_{withdrawal_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    method_display = {"kbzpay": "KBZ Pay", "wavepay": "Wave Pay", "phonebill": "Phone Bill"}[method]
    request_message = (
        f"Withdrawal Request\n"
        f"User ID: {user_id}\n"
        f"Username: {(await db.get_user(user_id)).get('username', 'None')}\n"
        f"Amount: {amount:.2f} {CURRENCY}\n"
        f"Payment Method: {method_display}\n"
        f"Account: {kpay_account}\n"
        f"Time: {datetime.utcnow()}"
    )
    logger.info(f"SUBMIT_WITHDRAWAL: Attempting to send withdrawal request to {LOG_CHANNEL_ID} for user {user_id}")
    try:
        if kpay_account.startswith("QR_IMAGE:"):
            file_id = kpay_account.split(":")[1]
            request_sent = await context.bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=file_id,
                caption=request_message,
                reply_markup=reply_markup
            )
            logger.info(f"SUBMIT_WITHDRAWAL: Sent QR photo withdrawal request for user {user_id}: {withdrawal_id}, message_id={request_sent.message_id}")
        else:
            request_sent = await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=request_message,
                reply_markup=reply_markup
            )
            logger.info(f"SUBMIT_WITHDRAWAL: Sent text withdrawal request for user {user_id}: {withdrawal_id}, message_id={request_sent.message_id}")
    except Exception as e:
        logger.error(f"SUBMIT_WITHDRAWAL: Failed to send message to {LOG_CHANNEL_ID} for user {user_id}: {e}")
        await update.message.reply_text(f"Failed to send withdrawal request: {str(e)}. Contact support.")
        return ConversationHandler.END

    try:
        await db.withdrawals.insert_one({
            "withdrawal_id": withdrawal_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "account": kpay_account,
            "status": "pending",
            "message_id": str(request_sent.message_id),
            "chat_id": str(LOG_CHANNEL_ID),
            "created_at": datetime.utcnow()
        })
        logger.info(f"SUBMIT_WITHDRAWAL: Withdrawal record inserted for user {user_id}: {withdrawal_id}")
    except Exception as e:
        logger.error(f"SUBMIT_WITHDRAWAL: Failed to insert withdrawal record for user {user_id}: {e}")
        await update.message.reply_text(f"Failed to save withdrawal request: {str(e)}. Contact support.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    withdrawn_today = user.get("withdrawn_today", 0) + amount
    try:
        await db.update_user(user_id, {
            "withdrawn_today": withdrawn_today,
            "last_withdrawal": datetime.utcnow()
        })
        logger.info(f"SUBMIT_WITHDRAWAL: Updated user {user_id} with withdrawn_today: {withdrawn_today}")
    except Exception as e:
        logger.error(f"SUBMIT_WITHDRAWAL: Failed to update user {user_id} with withdrawal details: {e}")
        await update.message.reply_text(f"Failed to update user data: {str(e)}. Contact support.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"Withdrawal request for {amount:.2f} {CURRENCY} via {method_display} submitted. Awaiting admin approval."
    )
    logger.info(f"SUBMIT_WITHDRAWAL: User {user_id} submitted withdrawal request for {amount:.2f} {CURRENCY} via {method_display}")
    return ConversationHandler.END

async def handle_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"HANDLE_CALLBACK: Callback received: {data} by user {user_id} in chat {query.message.chat_id}")

    if user_id not in ADMIN_IDS:
        await query.answer("You are not authorized.", show_alert=True)
        logger.warning(f"HANDLE_CALLBACK: Unauthorized withdrawal callback by user {user_id}")
        return

    try:
        action, withdrawal_id = data.split("_", 1)
        logger.info(f"HANDLE_CALLBACK: Processing {action} for withdrawal_id {withdrawal_id}")
        withdrawal = await db.withdrawals.find_one({"withdrawal_id": withdrawal_id, "status": "pending"})
        if not withdrawal:
            await query.answer("Request not found or already processed.", show_alert=True)
            logger.info(f"HANDLE_CALLBACK: Withdrawal {withdrawal_id} not found or already processed")
            return

        target_user_id = withdrawal["user_id"]
        amount = withdrawal["amount"]
        method = withdrawal["method"]
        account = withdrawal.get("account", "Not provided")
        message_id = withdrawal["message_id"]
        chat_id = withdrawal["chat_id"]
        method_display = {"kbzpay": "KBZ Pay", "wavepay": "Wave Pay", "phonebill": "Phone Bill"}[method]

        if action == "approve":
            user = await db.get_user(target_user_id)
            if not user:
                await query.answer("User not found.", show_alert=True)
                logger.error(f"HANDLE_CALLBACK: Cannot approve withdrawal {withdrawal_id}: user {target_user_id} not found")
                return
            balance = user.get("balance", 0)
            if balance < amount:
                await query.answer("Insufficient balance.", show_alert=True)
                logger.error(f"HANDLE_CALLBACK: Cannot approve withdrawal {withdrawal_id}: insufficient balance for user {target_user_id}, balance={balance}, amount={amount}")
                return

            new_balance = balance - amount
            await db.update_user(target_user_id, {"balance": new_balance})
            logger.info(f"HANDLE_CALLBACK: Deducted {amount} {CURRENCY} from user {target_user_id}, new balance: {new_balance}")

            await db.withdrawals.update_one(
                {"withdrawal_id": withdrawal_id},
                {"$set": {"status": "approved", "processed_at": datetime.utcnow()}}
            )
            logger.info(f"HANDLE_CALLBACK: Updated withdrawal {withdrawal_id} status to approved")

            updated_message = (
                f"Withdrawal Approved\n"
                f"User ID: {target_user_id}\n"
                f"Amount: {amount:.2f} {CURRENCY}\n"
                f"Payment Method: {method_display}\n"
                f"Account: {account}\n"
                f"Time: {datetime.utcnow()}"
            )
            if account.startswith("QR_IMAGE:"):
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=updated_message,
                    reply_markup=None
                )
                logger.info(f"HANDLE_CALLBACK: Edited QR caption for withdrawal {withdrawal_id} in chat {chat_id}")
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=updated_message,
                    reply_markup=None
                )
                logger.info(f"HANDLE_CALLBACK: Edited message for withdrawal {withdrawal_id} in chat {chat_id}")

            if account.startswith("QR_IMAGE:"):
                file_id = account.split(":")[1]
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=file_id,
                    caption=f"Your withdrawal of {amount:.2f} {CURRENCY} via {method_display} to the provided QR was approved."
                )
                logger.info(f"HANDLE_CALLBACK: Notified user {target_user_id} of approved QR withdrawal")
            else:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Your withdrawal of {amount:.2f} {CURRENCY} via {method_display} to {account} was approved."
                )
                logger.info(f"HANDLE_CALLBACK: Notified user {target_user_id} of approved withdrawal")

            log_message = f"Admin {user_id} approved withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} {CURRENCY} via {method_display} to {account}"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
            logger.info(f"HANDLE_CALLBACK: Logged approval - {log_message}")

        elif action == "reject":
            await db.withdrawals.update_one(
                {"withdrawal_id": withdrawal_id},
                {"$set": {"status": "rejected", "processed_at": datetime.utcnow()}}
            )
            logger.info(f"HANDLE_CALLBACK: Updated withdrawal {withdrawal_id} status to rejected")

            updated_message = (
                f"Withdrawal Rejected\n"
                f"User ID: {target_user_id}\n"
                f"Amount: {amount:.2f} {CURRENCY}\n"
                f"Payment Method: {method_display}\n"
                f"Account: {account}\n"
                f"Time: {datetime.utcnow()}"
            )
            if account.startswith("QR_IMAGE:"):
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=updated_message,
                    reply_markup=None
                )
                logger.info(f"HANDLE_CALLBACK: Edited QR caption for withdrawal {withdrawal_id} in chat {chat_id}")
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=updated_message,
                    reply_markup=None
                )
                logger.info(f"HANDLE_CALLBACK: Edited message for withdrawal {withdrawal_id} in chat {chat_id}")

            if account.startswith("QR_IMAGE:"):
                file_id = account.split(":")[1]
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=file_id,
                    caption=f"Your withdrawal of {amount:.2f} {CURRENCY} via {method_display} to the provided QR was rejected."
                )
                logger.info(f"HANDLE_CALLBACK: Notified user {target_user_id} of rejected QR withdrawal")
            else:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Your withdrawal of {amount:.2f} {CURRENCY} via {method_display} to {account} was rejected."
                )
                logger.info(f"HANDLE_CALLBACK: Notified user {target_user_id} of rejected withdrawal")

            log_message = f"Admin {user_id} rejected withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} {CURRENCY} via {method_display} to {account}"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
            logger.info(f"HANDLE_CALLBACK: Logged rejection - {log_message}")

        await query.answer("Action completed.")
        logger.info(f"HANDLE_CALLBACK: Action {action} completed for withdrawal {withdrawal_id}")

    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)
        logger.error(f"HANDLE_CALLBACK: Error in withdrawal callback {data} for user {user_id}: {e}")

async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"CANCEL: User {user_id} cancelled withdrawal conversation")
    await update.message.reply_text("Withdrawal process cancelled.")
    return ConversationHandler.END

def register_handlers(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(["withdrawal", "Withdrawal"], withdrawal_start),
            CallbackQueryHandler(withdrawal_start, pattern="^Withdrawal$")
        ],
        states={
            SELECT_METHOD: [CallbackQueryHandler(select_method, pattern="^method_(kbzpay|wavepay|phonebill)$")],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, enter_amount)],
            ENTER_KPAY: [
                MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, enter_kpay),
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, enter_kpay)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_withdrawal)
        ],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_withdrawal_callback, pattern="^(approve|reject)_"))
    logger.info("Withdrawal handlers registered successfully")