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
from utils.rate_limiter import send_message_rate_limited, send_messages_batch
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw initiated by user {user_id} in chat {chat_id}")

    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message

    if update.effective_chat.type != "private":
        await message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        await message.reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Check invite requirement
    invite_requirement = await db.get_invite_requirement()
    invite_count = user.get("invite_count", 0)
    if invite_count < invite_requirement and user_id != "5062124930":  # Admin exempt
        await message.reply_text(
            f"You need to invite {invite_requirement} people to withdraw. You've invited {invite_count}. "
            f"Use /referral_users to check your invites."
        )
        return ConversationHandler.END

    context.user_data.clear()
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "(Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်)",
        reply_markup=reply_markup
    )
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    method = query.data.replace("payment_", "")
    context.user_data["payment_method"] = method

    if method == "Phone Bill":
        await query.message.reply_text(
            "For Phone Bill, enter an amount in increments of 1000 kyats (e.g., 1000, 2000, 3000).\n"
            "ဖုန်းဘေလ်အတွက် ပမာဏကို 1000 ကျပ်စီ တိုးပြီး ထည့်ပါ (ဥပမာ 1000, 2000, 3000)။"
        )
    else:
        await query.message.reply_text(
            f"Please enter the amount to withdraw (minimum: {WITHDRAWAL_THRESHOLD} kyat).\n"
            f"ထုတ်ယူလိုသော ပမာဏကို ထည့်ပါ (အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ကျပ်)။"
        )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    payment_method = context.user_data.get("payment_method")
    try:
        amount = int(update.message.text.strip())
        if payment_method == "Phone Bill":
            if amount < 1000 or amount % 1000 != 0:
                await update.message.reply_text(
                    "Phone Bill withdrawals must be in increments of 1000 kyats (e.g., 1000, 2000). Try again."
                )
                return STEP_AMOUNT
        elif amount < WITHDRAWAL_THRESHOLD:
            await update.message.reply_text(f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} kyat. Try again.")
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if user.get("balance", 0) < amount:
            await update.message.reply_text("Insufficient balance. Check with /balance.")
            return ConversationHandler.END

        withdrawn_today = user.get("withdrawn_today", 0)
        last_withdrawal = user.get("last_withdrawal")
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                await update.message.reply_text(
                    f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} kyat exceeded. You've withdrawn {withdrawn_today} kyat today."
                )
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today

        if payment_method == "KBZ Pay":
            await update.message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ။\n"
                "သို့မဟုတ် QR Image ဖြင့် ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Wave Pay":
            await update.message.reply_text(
                "Please provide your Wave Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ။\n"
                "သို့မဟုတ် QR Image ဖြင့် ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Phone Bill":
            await update.message.reply_text(
                "Please provide your phone number (e.g., 09123456789).\n"
                "သင့်ဖုန်းနံပါတ်ကို ပို့ပေးပါ (ဥပမာ: 09123456789)။"
            )
        return STEP_DETAILS
    except ValueError:
        await update.message.reply_text("Please enter a valid number (e.g., 1000). Try again.")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    payment_details = update.message.text
    user = await db.get_user(user_id)

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    log_message = (
        f"Withdrawal Request:\n"
        f"ID: {user_id}\n"
        f"First name Last name: {user['name']}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Amount: {amount} kyat\n"
        f"Payment Method: {payment_method}\n"
        f"Details: {payment_details}\n"
        f"Status: PENDING ⏳"
    )
    log_msg = await send_message_rate_limited(
        context.bot,
        chat_id=LOG_CHANNEL_ID,
        text=log_message,
        reply_markup=reply_markup
    )
    if log_msg:
        await context.bot.pin_chat_message(LOG_CHANNEL_ID, log_msg.message_id, disable_notification=True)

    await update.message.reply_text(
        f"Your withdrawal request for {amount} kyat has been submitted. Awaiting approval."
    )
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    action, user_id, amount = parts[0], parts[1], int(parts[2])

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found.")
        return

    if action == "approve":
        balance = user.get("balance", 0)
        if balance < amount:
            await query.message.reply_text("Insufficient balance.")
            return
        withdrawn_today = context.user_data.get("withdrawn_today", user.get("withdrawn_today", 0))
        new_balance = balance - amount
        new_withdrawn_today = withdrawn_today + amount
        await db.update_user(user_id, {
            "balance": new_balance,
            "last_withdrawal": datetime.now(timezone.utc),
            "withdrawn_today": new_withdrawn_today
        })

        # Send group announcement
        announcement = (
            f"ID: {user_id}\n"
            f"First name Last name: {user['name']}\n"
            f"Username: @{query.from_user.username or 'N/A'}\n"
            f"သည် စုစုပေါင်း {amount} ငွေထုတ်ယူခဲ့ပါသည်။\n"
            f"လက်ရှိလက်ကျန်ငွေ {new_balance} kyat"
        )
        await send_message_rate_limited(context.bot, GROUP_CHAT_IDS[0], announcement)

        # Batch send announcements to users
        users = await db.get_all_users()
        messages = [
            (bot_user["user_id"], announcement, {})
            for bot_user in users
            if bot_user["user_id"] != user_id  # Exclude the withdrawing user
        ]
        await send_messages_batch(context.bot, messages, batch_size=30, delay=1)

        await query.message.reply_text(f"Approved withdrawal of {amount} kyat for user {user_id}.")
        await send_message_rate_limited(
            context.bot,
            user_id,
            f"Your withdrawal of {amount} kyat has been approved!"
        )
    elif action == "reject":
        await query.message.reply_text(f"Rejected withdrawal of {amount} kyat for user {user_id}.")
        await send_message_rate_limited(
            context.bot,
            user_id,
            f"Your withdrawal request of {amount} kyat was rejected."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Withdrawal canceled.")
    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^withdraw$")
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_"))