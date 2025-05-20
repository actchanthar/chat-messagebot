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

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    query = update.callback_query
    message = update.message if update.message else query.message if query else None
    logger.info(f"Withdraw initiated by user {user_id} in chat {chat_id} via {'button' if query else 'command'}")

    if query:
        await query.answer()
        logger.info(f"Callback query answered for user {user_id}")

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        await message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        await message.reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Check invite requirement (skip for admin)
    if user_id != "5062124930":
        invite_requirement = await db.get_setting("invite_requirement", 15)
        if user.get("invited_users", 0) < invite_requirement:
            await message.reply_text(f"You need to invite at least {invite_requirement} users who have joined the channels to withdraw.")
            return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id}")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n(Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်)",
        reply_markup=reply_markup
    )
    logger.info(f"Prompted user {user_id} for payment method selection")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Payment method selection by user {user_id}: {data}")

    if not data.startswith("payment_"):
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        await query.message.reply_text("Invalid payment method. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ: 09123456789)\n"
            "Phone Bill top-up is fixed at 1000 kyat increments (e.g., 1000, 2000, 3000)."
        )
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    payment_method = context.user_data.get("payment_method")

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Try again.")
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if user.get("balance", 0) < amount:
            await message.reply_text("Insufficient balance. Check with /balance.")
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                await message.reply_text(f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n\n💳\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ။ သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n\n💳\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ။ သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        return STEP_DETAILS
    except ValueError:
        await message.reply_text("Please enter a valid number (e.g., 100).")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)

    if not amount or not payment_method:
        await message.reply_text("Error: Missing data. Start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    payment_details = message.text or "No details provided"
    context.user_data["withdrawal_details"] = payment_details

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_name = user.get("name", update.effective_user.full_name)
    username = update.effective_user.username or "N/A"
    log_message = (
        f"Withdrawal Request:\n"
        f"ID: {user_id}\n"
        f"{user_name}\n"
        f"Username: @{username}\n"
        f"သည် စုစုပေါင်း {amount} {CURRENCY} ငွေထုတ်ယူခဲ့ပါသည်။\n"
        f"Payment Method: **{payment_method}**\n"
        f"Details: {payment_details}\n"
        f"Status: PENDING ⏳"
    )

    log_msg = await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=log_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await context.bot.pin_chat_message(chat_id=LOG_CHANNEL_ID, message_id=log_msg.message_id, disable_notification=True)

    await message.reply_text(f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Await approval.")
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_withdrawal_"):
        _, _, user_id, amount = data.split("_")
        user_id = str(user_id)
        amount = int(amount)

        user = await db.get_user(user_id)
        balance = user.get("balance", 0)
        if balance < amount:
            await query.message.reply_text("Insufficient balance.")
            return

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                await query.message.reply_text(f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
                return
        else:
            withdrawn_today = 0

        new_balance = balance - amount
        new_withdrawn_today = withdrawn_today + amount
        await db.update_user(user_id, {
            "balance": new_balance,
            "last_withdrawal": current_time,
            "withdrawn_today": new_withdrawn_today
        })

        await query.message.reply_text(
            f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Post to Group 📢", callback_data=f"post_approval_{user_id}_{amount}")]])
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Your withdrawal of {amount} {CURRENCY} has been approved! New balance: {new_balance} {CURRENCY}."
        )

    elif data.startswith("reject_withdrawal_"):
        _, _, user_id, amount = data.split("_")
        user_id = str(user_id)
        amount = int(amount)
        await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected. Contact @actanibot for issues."
        )

    elif data.startswith("post_approval_"):
        _, _, user_id, amount = data.split("_")
        user_id = str(user_id)
        amount = int(amount)
        user = await db.get_user(user_id)
        mention = f"@{user.get('username', user['name'])}" if user.get("username") else user["name"]
        await context.bot.send_message(
            chat_id=GROUP_CHAT_IDS[0],
            text=f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
        )
        await query.message.reply_text(f"Posted to group {GROUP_CHAT_IDS[0]}.")

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
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_|post_approval_"))