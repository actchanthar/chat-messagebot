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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)
ADMIN_ID = "5062124930"

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        query = update.callback_query
        message = query.message if query else update.message
        source = "button" if query else "command"
        logger.info(f"Withdraw initiated by {user_id} via {source} in chat {chat_id}")

        if query:
            await query.answer()

        if update.effective_chat.type != "private":
            await message.reply_text("Please use /withdraw in a private chat.")
            return ConversationHandler.END

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Use /start.")
            return ConversationHandler.END

        if user.get("banned", False):
            await message.reply_text("You are banned.")
            return ConversationHandler.END

        # Skip invite requirement for admin
        if user_id != ADMIN_ID:
            invite_threshold = await db.get_setting("invite_threshold", 15)
            if user.get("invite_count", 0) < invite_threshold:
                await message.reply_text(f"You need to invite {invite_threshold} users who join our channels to withdraw.")
                return ConversationHandler.END

        context.user_data.clear()
        keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(
            "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။ "
            "(Warning ⚠️: Provide accurate details; incorrect info means no refund.)",
            reply_markup=reply_markup
        )
        return STEP_PAYMENT_METHOD
    except Exception as e:
        logger.error(f"Error in withdraw for {user_id}: {e}")
        await message.reply_text("An error occurred. Try again.")
        return ConversationHandler.END

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    method = query.data.replace("payment_", "")
    user_id = str(query.from_user.id)

    if method not in PAYMENT_METHODS:
        await query.message.reply_text("Invalid payment method.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals start at 1000 kyat.\n"
            "Provide your phone number (e.g., 09123456789):"
        )
        return STEP_DETAILS
    await query.message.reply_text(
        f"Enter amount to withdraw (min: {WITHDRAWAL_THRESHOLD} {CURRENCY}):"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount_text = update.message.text.strip()
    payment_method = context.user_data.get("payment_method")

    try:
        amount = int(amount_text)
        if payment_method == "Phone Bill" and amount % 1000 != 0:
            await update.message.reply_text("Phone Bill amounts must be multiples of 1000 (e.g., 1000, 2000).")
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD:
            await update.message.reply_text(f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} {CURRENCY}.")
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if user.get("balance", 0) < amount:
            await update.message.reply_text("Insufficient balance.")
            return ConversationHandler.END

        context.user_data["withdrawal_amount"] = amount
        if payment_method == "KBZ Pay":
            await update.message.reply_text(
                "Provide KBZ Pay details (e.g., 09123456789 ZAYAR KO KO MIN ZAW) or QR image:"
            )
        elif payment_method == "Wave Pay":
            await update.message.reply_text(
                "Provide Wave Pay details (e.g., 09123456789 ZAYAR KO KO MIN ZAW) or QR image:"
            )
        else:
            await update.message.reply_text("Provide your phone number (e.g., 09123456789):")
        return STEP_DETAILS
    except ValueError:
        await update.message.reply_text("Enter a valid number.")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    details = update.message.text

    user = await db.get_user(user_id)
    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    log_message = (
        f"Withdrawal Request:\n"
        f"ID: {user_id}\n"
        f"Name: {user['name']}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Amount: {amount} {CURRENCY}\n"
        f"Method: {payment_method}\n"
        f"Details: {details}\n"
        f"Status: PENDING"
    )
    log_msg = await context.bot.send_message(LOG_CHANNEL_ID, log_message, reply_markup=reply_markup)
    await context.bot.pin_chat_message(LOG_CHANNEL_ID, log_msg.message_id, disable_notification=True)

    await update.message.reply_text(f"Your withdrawal of {amount} {CURRENCY} is submitted. Awaiting approval.")
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    action, _, user_id, amount = parts[:4]
    amount = int(amount)

    user = await db.get_user(user_id)
    if action == "approve":
        balance = user.get("balance", 0)
        if balance >= amount:
            new_balance = balance - amount
            await db.update_user(user_id, {"balance": new_balance, "last_withdrawal": datetime.utcnow()})
            await query.message.reply_text(f"Approved {amount} {CURRENCY} for {user_id}. New balance: {new_balance}.")
            await context.bot.send_message(
                user_id,
                f"Your withdrawal of {amount} {CURRENCY} is approved. New balance: {new_balance} {CURRENCY}."
            )
            group_msg = f"@{user.get('username', user['name'])} သည် {amount} ကျပ်ထုတ်ယူခဲ့ပါသည်။ လက်ရှိလက်ကျန် {new_balance}"
            await context.bot.send_message(GROUP_CHAT_IDS[0], group_msg)
    elif action == "reject":
        await query.message.reply_text(f"Rejected {amount} {CURRENCY} for {user_id}.")
        await context.bot.send_message(user_id, f"Your withdrawal of {amount} {CURRENCY} was rejected.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Withdrawal canceled.")
    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^withdraw$"),
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_"))