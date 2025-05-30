from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database.database import db
import logging
from datetime import datetime, timezone
from config import GROUP_CHAT_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        logger.error(f"User {user_id} not found in database")
        return ConversationHandler.END

    balance = user.get("balance", 0)
    if balance <= 0:
        await update.message.reply_text(
            f"Your balance is {int(balance)} {CURRENCY}. You need at least 1 {CURRENCY} to withdraw.\n"
            f"သင့်လက်ကျန်ငွေသည် {int(balance)} {CURRENCY} ဖြစ်ပြီး၊ ငွေထုတ်ရန် အနည်းဆုံး 1 {CURRENCY} လိုအပ်ပါသည်။"
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Phone Bill", callback_data="method_phone")],
        [InlineKeyboardButton("Wave Money", callback_data="method_wave")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a payment method:\nဆက်သွယ်ပို့မှုနည်းပညာကို ရွေးချယ်ပါ။",
        reply_markup=reply_markup
    )
    return STEP_PAYMENT_METHOD

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    method = query.data.replace("method_", "")
    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method: {method}")

    await query.message.reply_text(
        f"You selected {method}. Please enter the amount to withdraw (minimum 10 {CURRENCY}):\n"
        f"သင်ရွေးချယ်သည် {method}။ ထုတ်ယူမည့် ပမာဏကို ထည့်ပါ (အနည်းဆုံး 10 {CURRENCY})။"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    amount_text = update.message.text.strip()
    logger.info(f"User {user_id} entered amount: {amount_text}")

    try:
        amount = int(amount_text)
        if amount < 10:
            await update.message.reply_text("Minimum withdrawal amount is 10 kyat. Please try again.")
            return STEP_AMOUNT
        user = await db.get_user(user_id)
        balance = user.get("balance", 0)
        if balance < amount:
            await update.message.reply_text(
                f"Insufficient balance. Your balance is {int(balance)} {CURRENCY}, but you requested {amount} {CURRENCY}.\n"
                f"ငွေမလုံလောက်ပါ။ သင့်လက်ကျန်ငွေသည် {int(balance)} {CURRENCY} ဖြစ်ပြီး၊ {amount} {CURRENCY} တောင်းဆိုထားသည်။"
            )
            return STEP_AMOUNT

        context.user_data["amount"] = amount
        await update.message.reply_text(
            "Please provide your payment details (e.g., phone number or Wave ID) or send a photo of your payment proof:\n"
            "သင့်ဆက်သွယ်မှုအသေးအတွက် (ဥပမာ- ဖုန်းနံပါတ် သို့ Wave ID) ပေးပါ သို့မဟုတ် ငွေပေးချေမှုအထောက်အထား ဓာတ်ပုံပို့ပါ။"
        )
        return STEP_DETAILS
    except ValueError:
        await update.message.reply_text("Please enter a valid number. ကျေးဇူးပြု၍ တစ်ခုချင်းပေးပါ။")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    details = update.message.text if update.message.text else update.message.photo[-1].file_id if update.message.photo else None
    if not details:
        await update.message.reply_text("Please provide valid details or a photo. ကျေးဇူးပြု၍ အသေးအတွက် သို့မဟုတ် ဓာတ်ပုံပေးပါ။")
        return STEP_DETAILS

    amount = context.user_data.get("amount")
    method = context.user_data.get("payment_method")
    current_time = datetime.now(timezone.utc)

    user = await db.get_user(user_id)
    balance = user.get("balance", 0)
    new_balance = max(0, balance - amount)  # Prevent negative balance
    withdrawn_today = user.get("withdrawn_today", 0)
    if user.get("last_withdrawal") and user["last_withdrawal"].date() == current_time.date():
        withdrawn_today += amount
    else:
        withdrawn_today = amount

    pending_withdrawals = user.get("pending_withdrawals", [])
    pending_withdrawals.append({
        "amount": amount,
        "method": method,
        "details": details,
        "status": "PENDING",
        "request_time": current_time
    })

    await db.update_user(user_id, {
        "balance": new_balance,
        "last_withdrawal": current_time,
        "withdrawn_today": withdrawn_today,
        "pending_withdrawals": pending_withdrawals
    })

    logger.info(f"User {user_id} requested withdrawal of {amount} {CURRENCY} via {method}")

    # Notify admin
    admin_id = await db.get_admin_id()  # Assuming you have an admin ID in the database
    if admin_id:
        keyboard = [
            [InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}_{amount}")],
            [InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}_{amount}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"Withdrawal Request:\n"
                f"User ID: {user_id}\n"
                f"Amount: {amount} {CURRENCY}\n"
                f"Method: {method}\n"
                f"Details: {details[:50] + '...' if len(details) > 50 else details}\n"
                f"Status: Pending ⏳"
            ),
            reply_markup=reply_markup
        )

    await update.message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval.\n"
        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြပြီးပါသည်။ အက်ဒမင် အတည်ပြုမှသာ ဆက်လုပ်ပါမည်။"
    )
    return ConversationHandler.END

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin action received: {data}")

    try:
        if data.startswith("approve_"):
            _, user_id, amount = data.split("_")
            user_id, amount = str(user_id), int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"Invalid approval for user {user_id} (user not found)")
                await query.message.reply_text("အမှား: အသုံးပြုသူ မတွေ့ပါ။")
                return

            # Check if balance is sufficient before approving
            balance = user.get("balance", 0)
            if balance < amount:
                logger.info(f"Insufficient balance for user {user_id}: {int(balance)} < {amount}")
                await query.message.edit_text(
                    query.message.text.replace("အခြေအနေ: ဆိုင်းငံ့ထားသည် ⏳", "အခြေအနေ: ငွေမလုံလောက်ပါ ❌")
                )
                await query.message.reply_text(f"အသုံးပြုသူ {user_id} တွင် လက်ကျန်ငွေ မလုံလောက်ပါ။ လက်ကျန်ငွေ: {int(balance)} {CURRENCY}")
                return

            # Update status to APPROVED and deduct balance
            pending_withdrawals = user.get("pending_withdrawals", [])
            updated_withdrawals = []
            payment_method = None
            for w in pending_withdrawals:
                if w["amount"] == amount and w["status"] == "PENDING":
                    w["status"] = "APPROVED"
                    payment_method = w["method"]
                updated_withdrawals.append(w)

            # Deduct balance and ensure it doesn't go below 0
            new_balance = max(0, balance - amount)
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if user.get("last_withdrawal") and user["last_withdrawal"].date() == current_time.date():
                withdrawn_today += amount
            else:
                withdrawn_today = amount

            await db.update_user(user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": withdrawn_today,
                "pending_withdrawals": updated_withdrawals
            })
            logger.info(f"Approved withdrawal of {amount} {CURRENCY} for user {user_id}, new balance: {new_balance}")

            # Edit the message to remove buttons and update status
            updated_message = query.message.text.replace("အခြေအနေ: ဆိုင်းငံ့ထားသည် ⏳", "အခြေအနေ: အတည်ပြုပြီး ✅")
            await query.message.edit_text(updated_message)

            await query.message.reply_text(f"အသုံးပြုသူ {user_id} အတွက် {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။")
            await context.bot.send_message(
                user_id,
                f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။ လက်ကျန်ငွေ: {int(new_balance)} {CURRENCY}။"
            )

            # Announce in group after approval
            telegram_user = await context.bot.get_chat(user_id)
            name = telegram_user.first_name or telegram_user.last_name or user_id
            if payment_method == "Phone Bill":
                group_message = (
                    f"{name} သည် PHONE Bill {amount} {CURRENCY} ထည့်ခဲ့သည်။\n"
                    f"လက်ရှိလက်ကျန်ငွေ {int(new_balance)} {CURRENCY}။"
                )
            else:
                group_message = (
                    f"{name} သည် ငွေ {amount} {CURRENCY} ထုတ်ယူခဲ့သည်။\n"
                    f"လက်ရှိလက်ကျန်ငွေ {int(new_balance)} {CURRENCY}။"
                )
            for group_id in GROUP_CHAT_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=group_message
                    )
                    logger.info(f"Announced approved withdrawal to group {group_id} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to announce approved withdrawal to group {group_id}: {e}")

        elif data.startswith("reject_"):
            _, user_id, amount = data.split("_")
            user_id, amount = str(user_id), int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"Invalid rejection for user {user_id} (user not found)")
                await query.message.reply_text("အမှား: အသုံးပြုသူ မတွေ့ပါ။")
                return

            # Remove the withdrawal request without modifying balance
            pending_withdrawals = user.get("pending_withdrawals", [])
            updated_withdrawals = [w for w in pending_withdrawals if w["amount"] != amount or w["status"] != "PENDING"]

            await db.update_user(user_id, {
                "pending_withdrawals": updated_withdrawals
            })
            logger.info(f"Rejected withdrawal of {amount} {CURRENCY} for user {user_id}")

            # Edit the message to remove buttons and update status
            updated_message = query.message.text.replace("အခြေအနေ: ဆိုင်းငံ့ထားသည် ⏳", "အခြေအနေ: ငြင်းပယ်ပြီး ❌")
            await query.message.edit_text(updated_message)

            await query.message.reply_text(f"အသုံးပြုသူ {user_id} အတွက် {amount} {CURRENCY} ကို ငြင်းပယ်လိုက်ပါပြီ။")
            await context.bot.send_message(
                user_id,
                f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို ငြင်းပယ်လိုက်ပါပြီ။ လက်ကျန်ငွေ: {int(user.get('balance', 0))} {CURRENCY}။ ပံ့ပိုးကူညီမှုအတွက် ဆက်သွယ်ပါ။"
            )

    except Exception as e:
        logger.error(f"Error in admin action for {data}: {e}")
        await query.message.reply_text("တောင်းဆိုမှု လုပ်ဆောင်ရာတွင် အမှားဖြစ်ပွားခဲ့ပါသည်။")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method, pattern="^method_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
        conversation_timeout=300,
        per_message=False
    )
    application.add_handler(conv_handler, group=1)
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve_|reject_)"), group=1)