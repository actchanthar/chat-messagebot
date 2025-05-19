# plugins/withdrawal.py
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

# Define withdrawal steps
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    source = "button" if query else "command"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    if query:
        await query.answer()

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        reply_text = "Please use the /withdraw command in a private chat."
        if query:
            await query.message.reply_text(reply_text)
        else:
            await update.message.reply_text(reply_text)
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        reply_text = "User not found. Please start with /start."
        if query:
            await query.message.reply_text(reply_text)
        else:
            await update.message.reply_text(reply_text)
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        reply_text = "You are banned from using this bot."
        if query:
            await query.message.reply_text(reply_text)
        else:
            await update.message.reply_text(reply_text)
        return ConversationHandler.END

    # Initialize user_data for withdrawal
    context.user_data["withdrawal_source"] = source
    logger.info(f"Initialized withdrawal for user {user_id}, context: {context.user_data}")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    warning_text = (
        "Please select a payment method: 💳\n"
        "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "⚠️ Warning: Please provide accurate details. Incorrect details may result in loss of funds."
    )
    if query:
        await query.message.reply_text(warning_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(warning_text, reply_markup=reply_markup)
    logger.info(f"Prompted user {user_id} for payment method selection")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}, data: {data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
            "Please provide your phone number (e.g., 09123456789). 💳\n"
            "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ: 09123456789)"
        )
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    payment_method = context.user_data.get("payment_method")
    logger.info(f"Amount input from user {user_id}: {message.text}")

    if not payment_method:
        logger.error(f"Missing payment method for user {user_id}")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        valid_phone_bill_amounts = [1000, 2000, 3000, 4000, 5000]
        if payment_method == "Phone Bill" and amount not in valid_phone_bill_amounts:
            await message.reply_text(
                "Phone Bill withdrawals must be 1000, 2000, 3000, 4000, or 5000 kyat. Please try again."
            )
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD and payment_method != "Phone Bill":
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start again with /start.")
            return ConversationHandler.END

        # Check invite requirement
        required_invites = (await db.get_settings()).get("required_invites", 15)
        if user.get("invites", 0) < required_invites:
            await message.reply_text(
                f"You need to invite at least {required_invites} users who join the force-sub channel to withdraw. "
                f"Current invites: {user.get('invites', 0)}. Use /referral_users to invite more."
            )
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
                    await message.reply_text(
                        f"Daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded. "
                        f"You've withdrawn {withdrawn_today} {CURRENCY} today."
                    )
                    return STEP_AMOUNT
            else:
                withdrawn_today = 0

        if user.get("balance", 0) < amount:
            await message.reply_text(
                "Insufficient balance. Check your balance with /balance."
            )
            return ConversationHandler.END

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "Or send a QR image. 💳\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "Or send a QR image. 💳\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        else:
            await message.reply_text(
                f"Please provide your {payment_method} account details (e.g., 09123456789). 💳\n"
                f"ကျေးဇူးပြု၍ သင်၏ {payment_method} အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789)။"
            )
        return STEP_DETAILS

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)

    if not (amount and payment_method):
        logger.error(f"Missing data for user {user_id}: {context.user_data}")
        await message.reply_text("Error: Missing withdrawal details. Start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Please start again with /start.")
        return ConversationHandler.END

    payment_details = message.text or "QR Image provided"
    context.user_data["withdrawal_details"] = payment_details

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_first_name = user.get("name", update.effective_user.first_name or "Unknown")
    username = update.effective_user.username or user.get("username", "N/A")
    log_message = (
        f"Withdrawal Request:\n"
        f"Name: {user_first_name}\n"
        f"User ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY} 💸\n"
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

        # Broadcast to all users
        users = await db.get_all_users()
        for target_user in users:
            try:
                await context.bot.send_message(
                    chat_id=target_user["user_id"],
                    text=f"ID: {user_id}\n"
                         f"Name: {user_first_name}\n"
                         f"Username: @{username}\n"
                         f"သည် စုစုပေါင်း {amount} {CURRENCY} ငွေထုတ်ယူခဲ့ပါသည်။\n"
                         f"လက်ရှိလက်ကျန်ငွေ {user.get('balance', 0) - amount} {CURRENCY}"
                )
            except Exception as e:
                logger.error(f"Failed to broadcast withdrawal to user {target_user['user_id']}: {e}")

        # Announce to group
        mention = f"@{username}" if username and not username.isdigit() else user_first_name
        await context.bot.send_message(
            chat_id=GROUP_CHAT_IDS[0],
            text=f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
        )

    except Exception as e:
        logger.error(f"Failed to process withdrawal request for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ကျေးဇူးပြု၍ အုပ်ချုပ်ရေးမှူး၏ အတည်ပြုချက်ကို စောင့်ပါ။"
    )
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt callback: {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            _, _, user_id, amount = data.split("_")
            user_id = int(user_id)
            amount = int(amount)

            user = await db.get_user(str(user_id))
            if not user:
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if balance < amount:
                await query.message.reply_text("User has insufficient balance.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if last_withdrawal and last_withdrawal.date() == current_time.date():
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    await query.message.reply_text(f"Daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
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
                await query.message.reply_text(
                    f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal of {amount} {CURRENCY} has been approved! New balance: {new_balance} {CURRENCY}."
                )
            else:
                await query.message.reply_text("Error approving withdrawal.")

        elif data.startswith("reject_withdrawal_"):
            _, _, user_id, amount = data.split("_")
            user_id = int(user_id)
            amount = int(amount)

            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected. Contact @actanibot for support."
            )

        elif data.startswith("post_approval_"):
            _, _, user_id, amount = data.split("_")
            user_id = int(user_id)
            amount = int(amount)

            user = await db.get_user(str(user_id))
            username = user.get("username", user.get("name", "Unknown"))
            mention = f"@{username}" if username and not username.isdigit() else user["name"]
            await context.bot.send_message(
                chat_id=GROUP_CHAT_IDS[0],
                text=f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
            )
            await query.message.reply_text(f"Posted withdrawal announcement to group {GROUP_CHAT_IDS[0]}.")

    except Exception as e:
        logger.error(f"Error in handle_admin_receipt: {e}")
        await query.message.reply_text("Error processing withdrawal request.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
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
            STEP_DETAILS: [MessageHandler(filters.TEXT | filters.PHOTO, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_|post_approval_"))