from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Withdraw initiated by user {user_id} in chat {chat_id}")

    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("User not found.")
            logger.info(f"User {user_id} not found for withdrawal")
            return

        balance = user.get("balance", 0)
        if balance < 10:
            await update.message.reply_text("Minimum withdrawal is 10 kyat.")
            logger.info(f"User {user_id} has insufficient balance: {balance}")
            return

        withdrawal_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{withdrawal_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{withdrawal_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        request_message = (
            f"Withdrawal Request\n"
            f"User ID: {user_id}\n"
            f"Username: {user.get('username', 'None')}\n"
            f"Amount: {balance:.2f} kyat\n"
            f"Time: {datetime.utcnow()}"
        )
        request_sent = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=request_message,
            reply_markup=reply_markup
        )
        logger.info(f"Withdrawal request sent for user {user_id}: {withdrawal_id}")

        await db.withdrawals.insert_one({
            "withdrawal_id": withdrawal_id,
            "user_id": user_id,
            "amount": balance,
            "status": "pending",
            "message_id": str(request_sent.message_id),
            "chat_id": str(LOG_CHANNEL_ID),
            "created_at": datetime.utcnow()
        })

        await update.message.reply_text(
            f"Withdrawal request for {balance:.2f} kyat submitted. Awaiting admin approval."
        )

    except Exception as e:
        await update.message.reply_text("Error processing withdrawal. Try again later.")
        logger.error(f"Error in withdrawal for user {user_id}: {e}")

async def handle_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

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
        message_id = withdrawal["message_id"]
        chat_id = withdrawal["chat_id"]

        if action == "approve":
            user = await db.get_user(target_user_id)
            if not user or user.get("balance", 0) < amount:
                await query.answer("Insufficient balance or user not found.")
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
                f"Time: {datetime.utcnow()}"
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_message,
                reply_markup=None  # Explicitly remove buttons
            )

            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal of {amount:.2f} kyat was approved."
            )

            log_message = f"Admin {user_id} approved withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} kyat"
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
                f"Time: {datetime.utcnow()}"
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_message,
                reply_markup=None  # Explicitly remove buttons
            )

            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal of {amount:.2f} kyat was rejected."
            )

            log_message = f"Admin {user_id} rejected withdrawal {withdrawal_id} for user {target_user_id}: {amount:.2f} kyat"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
            logger.info(log_message)

        await query.answer("Action completed.")

    except Exception as e:
        await query.answer("Error processing request. Check logs.")
        logger.error(f"Error in withdrawal callback {data} for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("withdrawal", withdrawal))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_callback, pattern="^(approve|reject)_"))