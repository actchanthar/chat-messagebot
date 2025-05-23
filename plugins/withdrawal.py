from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID
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
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id} with {trigger} {update.message.text if update.message else update.callback_query.data}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please contact support.") if update.message else await update.callback_query.message.reply_text("User not found. Please contact support.")
        logger.error(f"User {user_id} not found for withdrawal")
        return ConversationHandler.END

    balance = user.get("balance", 0)
    context.user_data["balance"] = balance
    context.user_data["user_id"] = user_id

    if balance < 100:  # Minimum for all methods
        await update.message.reply_text(f"Your balance is {balance:.2f} kyat. Minimum withdrawal is 100 kyat.") if update.message else await update.callback_query.message.reply_text(f"Your balance is {balance:.2f} kyat. Minimum withdrawal is 100 kyat.")
        logger.info(f"User {user_id} has insufficient balance: {balance}")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("KBZ Pay", callback_data="method_kbzpay")],
        [InlineKeyboardButton("Wave Pay", callback_data="method_wavepay")],
        [InlineKeyboardButton("Phone Bill", callback_data="method_phonebill")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.reply_text("Please select your payment method:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please select your payment method:", reply_markup=reply_markup)
    return SELECT_METHOD

async def select_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1]  # e.g., "method_kbzpay" -> "kbzpay"
    context.user_data["method"] = method

    await query.message.reply_text(
        f"Please enter the amount to withdraw (minimum: 100 kyat, your balance: {context.user_data['balance']:.2f} kyat):"
    )
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = context.user_data["user_id"]
    method = context.user_data["method"]
    balance = context.user_data["balance"]
    text = update.message.text

    try:
        amount = float(text)
        if amount <= 0:
            await update.message.reply_text("Amount must be greater than 0.")
            return ENTER_AMOUNT

        if amount > balance:
            await update.message.reply_text(f"Insufficient balance. Your balance is {balance:.2f} kyat.")
            return ENTER_AMOUNT

        if amount < 100:  # Minimum 100 kyat for all methods
            await update.message.reply_text("Minimum withdrawal is 100 kyat.")
            return ENTER_AMOUNT

        context.user_data["amount"] = amount
        if method in ["kbzpay", "wavepay"]:
            await update.message.reply_text("Please send your KBZ Pay or Wave Pay account (e.g., phone number or account ID):")
            return ENTER_KPAY
        else:  # Phone Bill (no account needed yet)
            return await submit_withdrawal(update, context)

    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ENTER_AMOUNT
    except Exception as e:
        await update.message.reply_text(f"Error processing amount: {str(e)}. Contact support.")
        logger.error(f"Error in enter_amount for user {user_id}: {e}")
        return ENTER_AMOUNT

async def enter_kpay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = context.user_data["user_id"]
    method = context.user_data["method"]
    kpay_account = update.message.text.strip()
    context.user_data["kpay_account"] = kpay_account

    return await submit_withdrawal(update, context)

async def submit_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = context.user_data["user_id"]
    method = context.user_data["method"]
    amount = context.user_data.get("amount")
    kpay_account = context.user_data.get("kpay_account", "Not provided")

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
        f"Amount: {amount:.2f} kyat\n"
        f"Payment Method: {method_display}\n"
        f"Account: {kpay_account}\n"  # Added KPay account
        f"Time: {datetime.utcnow()}"
    )
    logger.info(f"Attempting to send withdrawal request to {LOG_CHANNEL_ID} for user {user_id}")
    try:
        request_sent = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=request_message,
            reply_markup=reply_markup
        )
        logger.info(f"Withdrawal request sent for user {user_id}: {withdrawal_id}, message_id={request_sent.message_id}")
    except Exception as e:
        logger.error(f"Failed to send message to {LOG_CHANNEL_ID}: {e}")
        await update.message.reply_text(f"Failed to send withdrawal request: {str(e)}. Contact support.")
        return ConversationHandler.END

    try:
        await db.withdrawals.insert_one({
            "withdrawal_id": withdrawal_id,
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "account": kpay_account,  # Store KPay account
            "status": "pending",
            "message_id": str(request_sent.message_id),
            "chat_id": str(LOG_CHANNEL_ID),
            "created_at": datetime.utcnow()
        })
        logger.info(f"Withdrawal record inserted for user {user_id}: {withdrawal_id}")
    except Exception as e:
        logger.error(f"Failed to insert withdrawal record for user {user_id}: {e}")
        await update.message.reply_text(f"Failed to save withdrawal request: {str(e)}. Contact support.")
        return ConversationHandler.END

    # Update user's withdrawal tracking
    user = await db.get_user(user_id)
    withdrawn_today = user.get("withdrawn_today", 0) + amount
    await db.update_user(user_id, {
        "withdrawn_today": withdrawn_today,
        "last_withdrawal": datetime.utcnow()
    })

    await update.message.reply_text(
        f"Withdrawal request for {amount:.2f} kyat via {method_display} submitted. Awaiting admin approval."
    )
    logger.info(f"User {user_id} submitted withdrawal request for {amount:.2f} kyat via {method_display}")
    return ConversationHandler.END

async def handle_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

    logger.info(f"Callback received: {data} by user {user_id}")

    if user_id not in ADMIN_IDS:
        await query.answer("You are not authorized.", show_alert=True)
        logger.warning(f"Unauthorized withdrawal callback by user {user_id}")
        return

    try:
        action, withdrawal_id = data.split("_", 1)
        withdrawal = await db.withdrawals.find_one({"withdrawal_id": withdrawal_id, "status": "pending"})
        if not withdrawal:
            await query.answer("Request not found or already processed.")
            logger.info(f"Withdrawal {withdrawal_id} not found or processed")
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
            if not user or user.get("balance", 0) < amount:
                await query.answer("Insufficient balance or user not found.", show_alert=True)
                logger.error(f"Cannot approve withdrawal {withdrawal_id}: user {target_user_id}")
                return

            new_balance = user.get("balance", 0) - amount
            await db.update_user(target_user_id, {"balance": new_balance})

            await db.withdrawals.update_one(
                {"withdrawal_id": withdrawal_id},
                {"$set": {"status": "approved", "processed_at": datetime.utcnow()}}
            )

            updated_message = (
                f"Withdrawal Approved\n"
                f"User ID: {target_user_id}\n"
                f"Amount: {amount:.2f} kyat\n"
                f"Payment Method: {method_display}\n"
                f"Account: {account}\n"  # Added KPay account
                f"Time: {datetime.utcnow()}"
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_message,
                reply_markup=None
            )

            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal of {amount:.2f} kyat via {method_display} to {account} was approved."
            )

            log_message = f"Admin {user_id} approved withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} kyat via {method_display} to {account}"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
            logger.info(log_message)

        elif action == "reject":
            await db.withdrawals.update_one(
                {"withdrawal_id": withdrawal_id},
                {"$set": {"status": "rejected", "processed_at": datetime.utcnow()}}
            )

            updated_message = (
                f"Withdrawal Rejected\n"
                f"User ID: {target_user_id}\n"
                f"Amount: {amount:.2f} kyat\n"
                f"Payment Method: {method_display}\n"
                f"Account: {account}\n"  # Added KPay account
                f"Time: {datetime.utcnow()}"
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_message,
                reply_markup=None
            )

            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal of {amount:.2f} kyat via {method_display} to {account} was rejected."
            )

            log_message = f"Admin {user_id} rejected withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} kyat via {method_display} to {account}"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
            logger.info(log_message)

        await query.answer("Action completed.")

    except Exception as e:
        await query.answer(f"Error: {str(e)}")
        logger.error(f"Error in withdrawal callback {data} for user {user_id}: {e}")

def register_handlers(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(["withdrawal", "Withdrawal"], withdrawal_start),
            CallbackQueryHandler(withdrawal_start, pattern="^Withdrawal$")  # Handle the button click
        ],
        states={
            SELECT_METHOD: [CallbackQueryHandler(select_method, pattern="^method_")],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            ENTER_KPAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_kpay)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_withdrawal_callback, pattern="^(approve|reject)_"))
    logger.info("Withdrawal handlers registered successfully")