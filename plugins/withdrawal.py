from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database.database import db
import logging
import datetime
from config import WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, ADMIN_IDS, PAYMENT_METHODS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Check balance called by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found. Please start with /start.")
        return

    balance = user.get("balance", 0)
    await query.message.reply_text(
        f"Your current balance is {balance} {CURRENCY}.\n"
        f"သင့်လက်ကျန်ငွေမှာ {balance} {CURRENCY} ဖြစ်ပါသည်။"
    )

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Start withdraw called by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found. Please start with /start.")
        return

    balance = user.get("balance", 0)
    if balance < WITHDRAWAL_THRESHOLD:
        await query.message.reply_text(
            f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw.\n"
            f"သင့်လက်ကျန်ငွေမှာ {balance} {CURRENCY} ဖြစ်သည်။ ငွေထုတ်ရန် အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} လိုအပ်သည်။"
        )
        return

    bot_username = context.bot.username.lstrip('@')
    can_withdraw, message = await db.can_withdraw(user_id, bot_username)
    if not can_withdraw:
        await query.message.reply_text(message)
        return

    keyboard = [[InlineKeyboardButton(method, callback_data=f"withdraw_{method}")] for method in PAYMENT_METHODS]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_withdraw")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        f"Your balance is {balance} {CURRENCY}. Select a payment method to withdraw:\n"
        f"သင့်လက်ကျန်ငွေမှာ {balance} {CURRENCY} ဖြစ်သည်။ ငွေထုတ်ရန် ငွေပေးချေမှုနည်းလမ်းတစ်ခုကို ရွေးချယ်ပါ။",
        reply_markup=reply_markup
    )
    context.user_data["withdrawal_step"] = "select_method"

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Withdraw callback by user {user_id}: {data}")

    if data == "cancel_withdraw":
        await query.message.reply_text("Withdrawal cancelled.")
        context.user_data.clear()
        return

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found. Please start with /start.")
        return

    if data.startswith("withdraw_"):
        payment_method = data.split("_")[1]
        context.user_data["payment_method"] = payment_method
        balance = user.get("balance", 0)

        bot_username = context.bot.username.lstrip('@')
        can_withdraw, message = await db.can_withdraw(user_id, bot_username)
        if not can_withdraw:
            await query.message.reply_text(message)
            context.user_data.clear()
            return

        if balance < WITHDRAWAL_THRESHOLD:
            await query.message.reply_text(
                f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw.\n"
                f"သင့်လက်ကျန်ငွေမှာ {balance} {CURRENCY} ဖြစ်သည်။ ငွေထုတ်ရန် အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} လိုအပ်သည်။"
            )
            context.user_data.clear()
            return

        await query.message.reply_text(
            f"Please provide your {payment_method} account details (e.g., phone number or account ID) to proceed with the withdrawal of {balance} {CURRENCY}.\n"
            f"ငွေထုတ်ယူမှုအတွက် {payment_method} အကောင့်အသေးစိတ်အချက်အလက်များ (ဥပမာ၊ ဖုန်းနံပါတ် သို့မဟုတ် အကောင့် ID) ကို ပေးပါ။"
        )
        context.user_data["withdrawal_step"] = "awaiting_account_details"
        return

async def handle_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if context.user_data.get("withdrawal_step") != "awaiting_account_details":
        return

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    payment_method = context.user_data.get("payment_method")
    account_details = update.message.text
    balance = user.get("balance", 0)
    logger.info(f"Received account details from user {user_id} for {payment_method}: {account_details}")

    bot_username = context.bot.username.lstrip('@')
    can_withdraw, message = await db.can_withdraw(user_id, bot_username)
    if not can_withdraw:
        await update.message.reply_text(message)
        context.user_data.clear()
        return

    if balance < WITHDRAWAL_THRESHOLD:
        await update.message.reply_text(
            f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw.\n"
            f"သင့်လက်ကျန်ငွေမှာ {balance} {CURRENCY} ဖြစ်သည်။ ငွေထုတ်ရန် အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} လိုအပ်သည်။"
        )
        context.user_data.clear()
        return

    if balance > DAILY_WITHDRAWAL_LIMIT:
        await update.message.reply_text(
            f"Your withdrawal request of {balance} {CURRENCY} exceeds the daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. Please request a smaller amount.\n"
            f"သင်၏ ငွေထုတ်ယူမှု {balance} {CURRENCY} သည် နေ့စဉ်ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ထက်ကျော်လွန်နေသည်။ ကျေးဇူးပြု၍ ပမာဏနည်းပါးစွာ တောင်းဆိုပါ။"
        )
        context.user_data.clear()
        return

    # Create withdrawal request
    withdrawal_id = str(datetime.datetime.utcnow().timestamp())
    withdrawal = {
        "withdrawal_id": withdrawal_id,
        "user_id": user_id,
        "amount": balance,
        "payment_method": payment_method,
        "account_details": account_details,
        "status": "pending",
        "created_at": datetime.datetime.utcnow()
    }
    await db.create_withdrawal(withdrawal)

    # Notify admin
    log_message = (
        f"New Withdrawal Request\n"
        f"Withdrawal ID: {withdrawal_id}\n"
        f"User ID: {user_id}\n"
        f"Name: {user['name']}\n"
        f"Amount: {balance} {CURRENCY}\n"
        f"Payment Method: {payment_method}\n"
        f"Account Details: {account_details}\n"
        f"Time: {datetime.datetime.utcnow()}"
    )
    keyboard = [
        [InlineKeyboardButton("Approve", callback_data=f"approve_withdrawal_{withdrawal_id}")],
        [InlineKeyboardButton("Reject", callback_data=f"reject_withdrawal_{withdrawal_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=log_message,
                reply_markup=reply_markup
            )
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message
        )
        logger.info(f"Sent withdrawal request to admins and log channel for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send withdrawal request notifications: {e}")

    await update.message.reply_text(
        f"Your withdrawal request of {balance} {CURRENCY} via {payment_method} has been submitted. You will be notified once it is processed.\n"
        f"သင်၏ {balance} {CURRENCY} ငွေထုတ်ယူမှုကို {payment_method} မှတစ်ဆင့် တင်သွင်းပြီးပါပြီ။ လုပ်ဆောင်ပြီးသည်နှင့် သင့်ကို အကြောင်းကြားပါမည်။"
    )
    context.user_data.clear()

async def handle_admin_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_id = str(query.from_user.id)
    data = query.data

    if admin_id not in ADMIN_IDS:
        await query.message.reply_text("Only admins can approve or reject withdrawals.")
        return

    if data.startswith("approve_withdrawal_") or data.startswith("reject_withdrawal_"):
        withdrawal_id = data.split("_")[2]
        withdrawal = await db.get_withdrawal(withdrawal_id)
        if not withdrawal:
            await query.message.reply_text("Withdrawal request not found.")
            return

        user_id = withdrawal["user_id"]
        amount = withdrawal["amount"]
        payment_method = withdrawal["payment_method"]
        account_details = withdrawal["account_details"]

        if data.startswith("approve_withdrawal_"):
            await db.update_withdrawal(withdrawal_id, {"status": "approved"})
            await db.update_user(user_id, {"balance": 0})
            status_message = (
                f"Your withdrawal of {amount} {CURRENCY} via {payment_method} has been approved and processed.\n"
                f"သင်၏ {amount} {CURRENCY} ငွေထုတ်ယူမှုကို {payment_method} မှတစ်ဆင့် အတည်ပြုပြီး လုပ်ဆောင်ပြီးပါပြီ။"
            )
            admin_log = f"Withdrawal {withdrawal_id} approved for user {user_id}."
        else:
            await db.update_withdrawal(withdrawal_id, {"status": "rejected"})
            status_message = (
                f"Your withdrawal of {amount} {CURRENCY} via {payment_method} was rejected. Please contact support.\n"
                f"သင်၏ {amount} {CURRENCY} ငွေထုတ်ယူမှုကို {payment_method} မှတစ်ဆင့် ပယ်ချခံရသည်။ အကူအညီအတွက် ဆက်သွယ်ပါ။"
            )
            admin_log = f"Withdrawal {withdrawal_id} rejected for user {user_id}."

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=status_message
            )
            await query.message.reply_text(admin_log)
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"{admin_log}\nAccount Details: {account_details}"
            )
            logger.info(admin_log)
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} or log withdrawal status: {e}")
            await query.message.reply_text(f"{admin_log} but failed to notify user.")

async def view_withdrawal_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Withdrawal history requested by user {user_id}")

    withdrawals = await db.get_user_withdrawals(user_id)
    if not withdrawals:
        await update.message.reply_text("You have no withdrawal history.")
        return

    history_message = "Your Withdrawal History:\n\n"
    for w in withdrawals:
        history_message += (
            f"ID: {w['withdrawal_id']}\n"
            f"Amount: {w['amount']} {CURRENCY}\n"
            f"Method: {w['payment_method']}\n"
            f"Status: {w['status'].capitalize()}\n"
            f"Date: {w['created_at']}\n\n"
        )
    await update.message.reply_text(history_message)

async def admin_view_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can view pending withdrawals.")
        return

    withdrawals = await db.get_pending_withdrawals()
    if not withdrawals:
        await update.message.reply_text("No pending withdrawals.")
        return

    message = "Pending Withdrawals:\n\n"
    for w in withdrawals:
        user = await db.get_user(w["user_id"])
        message += (
            f"Withdrawal ID: {w['withdrawal_id']}\n"
            f"User: {user['name']} ({w['user_id']})\n"
            f"Amount: {w['amount']} {CURRENCY}\n"
            f"Method: {w['payment_method']}\n"
            f"Account: {w['account_details']}\n"
            f"Date: {w['created_at']}\n\n"
        )
    await update.message.reply_text(message)

async def set_message_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/setmessage command initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can set the message rate.")
        logger.info(f"User {user_id} attempted to set message rate but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide a number of messages per 1 kyat (e.g., /setmessage 2 for 2 messages = 1 kyat).")
        logger.info(f"User {user_id} provided no arguments for /setmessage")
        return

    try:
        rate = int(context.args[0])
        if rate <= 0:
            await update.message.reply_text("Message rate must be a positive number.")
            logger.info(f"User {user_id} provided invalid message rate: {rate}")
            return
    except ValueError:
        await update.message.reply_text("Please provide a valid number for the message rate.")
        logger.info(f"User {user_id} provided non-numeric message rate: {context.args[0]}")
        return

    await db.set_message_rate(rate)
    await update.message.reply_text(f"Message rate set to {rate} messages per 1 kyat.")
    logger.info(f"User {user_id} set message rate to {rate} messages per kyat")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(start_withdraw, pattern="^start_withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw_|^cancel_withdraw$"))
    application.add_handler(CallbackQueryHandler(handle_admin_withdrawal, pattern="^approve_withdrawal_|^reject_withdrawal_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, handle_account_details))
    application.add_handler(CommandHandler("withdrawal_history", view_withdrawal_history))
    application.add_handler(CommandHandler("pending_withdrawals", admin_view_pending_withdrawals))
    application.add_handler(CommandHandler("setmessage", set_message_rate))