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
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    source = "button" if update.callback_query else "command"
    logger.info(f"Withdraw initiated by user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        await update.callback_query.answer()

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            "Please use /withdraw in a private chat."
        )
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            "User not found. Please start with /start."
        )
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            "You are banned from using this bot."
        )
        return ConversationHandler.END

    # Check invite requirement
    invite_requirement = await db.get_invite_requirement()
    if user.get("invites", 0) < invite_requirement:
        logger.info(f"User {user_id} has {user.get('invites', 0)} invites, needs {invite_requirement}")
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            f"You need to invite {invite_requirement} users who join the required channels to withdraw. "
            f"You have {user.get('invites', 0)} invites. Use /referral_users to invite more."
        )
        return ConversationHandler.END

    context.user_data.clear()
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await (update.callback_query.message if update.callback_query else update.message).reply_text(
        "Please select a payment method: 💳\n"
        "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "( Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်)",
        reply_markup=reply_markup
    )
    logger.info(f"Prompted user {user_id} for payment method")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}: {data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
            "Please provide your phone number (e.g., 09123456789). 💳\n"
            "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ : 09123456789)"
        )
        logger.info(f"User {user_id} selected Phone Bill, fixed amount 1000 kyat")
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}, multiples of 1000 for Phone Bill). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY}"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    payment_method = context.user_data.get("payment_method")
    logger.info(f"Amount input for user {user_id}: {message.text}")

    if not payment_method:
        logger.error(f"Missing payment method for user {user_id}")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if payment_method == "Phone Bill" and amount not in [1000, 2000, 3000, 4000, 5000]:
            await message.reply_text(
                "Phone Bill withdrawals must be 1000, 2000, 3000, 4000, or 5000 kyat. Please try again."
            )
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again."
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start with /start.")
            return ConversationHandler.END

        if user.get("balance", 0) < amount:
            await message.reply_text(
                "Insufficient balance. Check your balance with /balance."
            )
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                await message.reply_text(
                    f"Daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded. "
                    f"You've withdrawn {withdrawn_today} {CURRENCY} today."
                )
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        else:
            await message.reply_text(
                "Please provide your phone number (e.g., 09123456789)."
            )
        return STEP_DETAILS
    except ValueError:
        await message.reply_text("Please enter a valid number (e.g., 1000).")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    logger.info(f"Details input for user {user_id}: {message.text}")

    if not amount or not payment_method:
        logger.error(f"Missing amount or payment method for user {user_id}")
        await message.reply_text("Error: Withdrawal data missing. Please start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    payment_details = message.text if message.text else "No details provided"
    context.user_data["withdrawal_details"] = payment_details

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
        f"First name: {user.get('name', 'Unknown')}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY}\n"
        f"Payment Method: {payment_method}\n"
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
        logger.info(f"Pinned withdrawal request for user {user_id} in log channel")
    except Exception as e:
        logger.error(f"Failed to send/pin withdrawal request for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval."
    )
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt for {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            _, _, user_id, amount = data.split("_")
            user_id = str(user_id)
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                await query.message.reply_text("User not found.")
                return

            if user.get("balance", 0) < amount:
                await query.message.reply_text("User has insufficient balance.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if last_withdrawal and last_withdrawal.date() == current_time.date():
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    await query.message.reply_text(
                        f"User exceeded daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}."
                    )
                    return
            else:
                withdrawn_today = 0

            new_balance = user.get("balance", 0) - amount
            new_withdrawn_today = withdrawn_today + amount
            success = await db.update_user(user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": new_withdrawn_today
            })

            if success:
                username = user.get("username", user.get("name", "Unknown"))
                mention = f"@{username}" if username and not username.isdigit() else user["name"]
                group_message = (
                    f"ID: {user_id}\n"
                    f"First name: {user.get('name', 'Unknown')}\n"
                    f"Username: {mention}\n"
                    f"သည် စုစုပေါင်း {amount} {CURRENCY} ငွေထုတ်ယူခဲ့ပါသည်။\n"
                    f"လက်ရှိလက်ကျန်ငွေ {new_balance} {CURRENCY}"
                )

                for group_id in GROUP_CHAT_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=group_message
                        )
                        logger.info(f"Announced withdrawal for user {user_id} in group {group_id}")
                    except Exception as e:
                        logger.error(f"Failed to announce withdrawal in group {group_id}: {e}")

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal of {amount} {CURRENCY} has been approved! New balance: {new_balance} {CURRENCY}."
                )
                await query.message.reply_text(
                    f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
                )
                logger.info(f"Approved withdrawal for user {user_id}: {amount} {CURRENCY}")
            else:
                await query.message.reply_text("Error approving withdrawal.")

        elif data.startswith("reject_withdrawal_"):
            _, _, user_id, amount = data.split("_")
            user_id = str(user_id)
            amount = int(amount)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"Your withdrawal request of {amount} {CURRENCY} was rejected. Contact @actanibot for details."
            )
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            logger.info(f"Rejected withdrawal for user {user_id}: {amount} {CURRENCY}")

    except Exception as e:
        logger.error(f"Error in admin receipt: {e}")
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
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_"))