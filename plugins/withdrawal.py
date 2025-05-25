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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    source = "command" if update.message else "button"
    logger.info(f"Withdraw called for user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        await update.callback_query.answer()

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        reply_text = "Please use /withdraw in a private chat."
        if update.message:
            await update.message.reply_text(reply_text)
        else:
            await update.callback_query.message.reply_text(reply_text)
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        reply_text = "User not found. Please start with /start."
        if update.message:
            await update.message.reply_text(reply_text)
        else:
            await update.callback_query.message.reply_text(reply_text)
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        reply_text = "You are banned from using this bot."
        if update.message:
            await update.message.reply_text(reply_text)
        else:
            await update.callback_query.message.reply_text(reply_text)
        return ConversationHandler.END

    if user_id not in ADMIN_IDS:
        invite_requirement = await db.get_invite_requirement()
        invite_count = await db.get_invites(user_id)
        if invite_count < invite_requirement:
            logger.info(f"User {user_id} has {invite_count} invites, needs {invite_requirement}")
            await (update.message or update.callback_query.message).reply_text(
                f"You need to invite {invite_requirement} users who join all required channels. "
                f"You have invited {invite_count} users. Use /referral_users to get your referral link."
            )
            return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id}")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_text = (
        "Please select a payment method: 💳\n"
        "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်"
    )
    if update.message:
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(reply_text, reply_markup=reply_markup)
    logger.info(f"Prompted user {user_id} for payment method")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}: {data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals start at 1000 kyat and must be in increments of 1000.\n"
            "Please provide your phone number (e.g., 09123456789).\n"
            "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ: 09123456789)"
        )
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Amount input from user {user_id}: {message.text}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"Missing payment method for user {user_id}")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if payment_method == "Phone Bill" and (amount % 1000 != 0 or amount < 1000):
            await message.reply_text(
                "Phone Bill withdrawals must be in increments of 1000 kyat (e.g., 1000, 2000, 3000).\n"
                "ကျေးဇူးပြု၍ 1000 ကျပ်အဆင့်ဖြင့်ထုတ်ပါ (ဥပမာ: 1000, 2000, 3000)"
            )
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။"
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start with /start.")
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                logger.info(f"User {user_id} exceeded daily limit: {withdrawn_today}+{amount}")
                await message.reply_text(
                    f"Daily withdrawal limit is {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. "
                    f"You've withdrawn {withdrawn_today} {CURRENCY} today.\n"
                    f"နေ့စဉ်ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ဖြစ်သည်။"
                )
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        if user.get("balance", 0) < amount:
            await message.reply_text(
                "Insufficient balance. Check with /balance.\n"
                "လက်ကျန်ငွေ မလုံလောက်ပါ။ /balance ဖြင့်စစ်ဆေးပါ။"
            )
            return ConversationHandler.END

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}")

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "Or send a QR code image.\n"
                "ကျေးဇူးပြု၍ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., phone number and name).\n"
                "Or send a QR code image.\n"
                "ကျေးဇူးပြု၍ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ။"
            )
        else:
            await message.reply_text(
                "Please provide your phone number (e.g., 09123456789).\n"
                "သင့်ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ 09123456789)"
            )
        return STEP_DETAILS

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးလပ်နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    logger.info(f"Account details for user {user_id}: {message.text}")

    if not amount or not payment_method:
        logger.error(f"Missing amount or payment method for user {user_id}")
        await message.reply_text("Error: Withdrawal data missing. Please start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    payment_details = message.text if message.text else "No details provided"
    if message.photo:
        payment_details += " (QR code image received)"
    context.user_data["withdrawal_details"] = payment_details

    await db.add_withdrawal(user_id, amount, payment_method, payment_details)

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    username = update.effective_user.username or user.get("name", "N/A")
    log_message = (
        f"Withdrawal Request:\n"
        f"ID: {user_id}\n"
        f"First name Last name: {user.get('name', 'Unknown')}\n"
        f"Username: @{username}\n"
        f"သည် စုစု‌ပေါင်း {amount} ငွေထုတ်ယူခဲ့ပါသည်။\n"
        f"Payment Method: **{payment_method}**\n"
        f"Details: {payment_details}\n"
        f"Status: PENDING ⏳"
    )

    try:
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        await context.bot.pin_chat_message(
            chat_id=LOG_CHANNEL_ID,
            message_id=log_msg.message_id,
            disable_notification=True
        )
        logger.info(f"Pinned withdrawal request for user {user_id} in {LOG_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Failed to send/pin withdrawal request for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။"
    )
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt for {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data: {data}")
                await query.message.reply_text("Error processing withdrawal.")
                return
            _, _, user_id, amount = parts
            user_id, amount = str(user_id), int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if balance < amount:
                logger.error(f"Insufficient balance for user {user_id}: {balance} < {amount}")
                await query.message.reply_text("User has insufficient balance.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if last_withdrawal and last_withdrawal.date() == current_time.date():
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.error(f"User {user_id} exceeded daily limit: {withdrawn_today}+{amount}")
                    await query.message.reply_text(f"User exceeded daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}.")
                    return
            else:
                withdrawn_today = 0

            new_balance = balance - amount
            new_withdrawn_today = withdrawn_today + amount
            success = await db.update_user(user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": new_withdrawn_today
            })
            await db.withdrawals.update_one(
                {"user_id": user_id, "amount": amount, "status": "PENDING"},
                {"$set": {"status": "APPROVED", "approved_at": current_time}}
            )

            if success:
                logger.info(f"Approved withdrawal for user {user_id}: {amount}, new balance: {new_balance}")
                username = user.get("username", user.get("name", "Unknown"))
                mention = f"@{username}" if username and not username.isdigit() else user["name"]
                group_message = (
                    f"ID: {user_id}\n"
                    f"First name Last name: {user['name']}\n"
                    f"Username: {mention}\n"
                    f"သည် စုစု‌ပေါင်း {amount} ငွေထုတ်ယူခဲ့ပါသည်။\n"
                    f"လက်ရှိလက်ကျန်ငွေ {new_balance}"
                )
                try:
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_IDS[0],
                        text=group_message
                    )
                    logger.info(f"Posted withdrawal announcement for user {user_id} to group {GROUP_CHAT_IDS[0]}")
                except Exception as e:
                    logger.error(f"Failed to post group announcement for user {user_id}: {e}")

                await query.message.reply_text(
                    f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal of {amount} {CURRENCY} has been approved! New balance: {new_balance} {CURRENCY}.\n"
                         f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။"
                )
            else:
                await query.message.reply_text("Error approving withdrawal.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data: {data}")
                await query.message.reply_text("Error processing withdrawal.")
                return
            _, _, user_id, amount = parts
            user_id, amount = str(user_id), int(amount)

            await db.withdrawals.update_one(
                {"user_id": user_id, "amount": amount, "status": "PENDING"},
                {"$set": {"status": "REJECTED", "rejected_at": datetime.now(timezone.utc)}}
            )
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Your withdrawal request of {amount} {CURRENCY} was rejected. Contact @actanibot for support.\n"
                     f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို ပယ်ချလိုက်ပါသည်။"
            )

    except Exception as e:
        logger.error(f"Error in handle_admin_receipt: {e}")
        await query.message.reply_text("Error processing withdrawal request.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled withdrawal")
    await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။")
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
            STEP_DETAILS: [MessageHandler(filters.TEXT | filters.PHOTO, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_"))