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

# Define conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id}")

    if update.effective_chat.type != "private":
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ။")
        else:
            await update.message.reply_text("ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ။")
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
        else:
            await update.message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("သင်သည် ဤဘော့ကို အသုံးပြုခွင့် ပိတ်ပင်ထားပါသည်။")
        else:
            await update.message.reply_text("သင်သည် ဤဘော့ကို အသုံးပြုခွင့် ပိတ်ပင်ထားပါသည်။")
        return ConversationHandler.END

    # Check if there are pending withdrawals
    pending_withdrawals = user.get("pending_withdrawals", [])
    pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
    if pending_count > 0:
        logger.info(f"User {user_id} has {pending_count} pending withdrawals, blocking new withdrawal")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။")
        else:
            await update.message.reply_text("သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။")
        return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id}")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"method_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။ 💳",
            reply_markup=reply_markup
        )
        await update.callback_query.message.delete()
    else:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။ 💳",
            reply_markup=reply_markup
        )
    logger.info(f"Prompted user {user_id} for payment method selection")
    return STEP_PAYMENT_METHOD

async def handle_withdraw_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Withdraw button clicked by user {user_id}")
    return await withdraw(update, context)

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}, data: {data}")

    if not data.startswith("method_"):
        logger.error(f"Invalid callback data for user {user_id}: {data}")
        await query.message.reply_text("ရွေးချယ်မှု မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။")
        return ConversationHandler.END

    method = data.replace("method_", "")
    if method not in PAYMENT_METHODS:
        logger.error(f"Invalid payment method {method} for user {user_id}")
        await query.message.reply_text("ငွေပေးချေမှုနည်းလမ်း မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ ပြန်ကြိုးစားပါ။")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method: {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill ဖြင့် ငွေထုတ်မှုသည် ၁၀၀၀ ကျပ် ပုံသေဖြစ်ပါသည်။\nသင့်ဖုန်းနံပါတ်ကို ပေးပို့ပါ (ဥပမာ 09123456789)။"
        )
        return STEP_DETAILS

    await query.message.reply_text(
        f"ငွေထုတ်ရန် ပမာဏကို ထည့်ပါ (အနည်းဆုံး: {WITHDRAWAL_THRESHOLD} {CURRENCY})။"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Received amount input from user {user_id}: {message.text}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"No payment method in context for user {user_id}")
        await message.reply_text("အမှား: ငွေပေးချေမှုနည်းလမ်း မရှိပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        logger.info(f"Parsed amount for user {user_id}: {amount}")

        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"အနည်းဆုံး ငွေထုတ်ပမာဏသည် {WITHDRAWAL_THRESHOLD} {CURRENCY} ဖြစ်ပါသည်။ ကျေးဇူးပြု၍ ပြန်ကြိုးစားပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            await message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
            return ConversationHandler.END

        # Check if there are pending withdrawals
        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
        if pending_count > 0:
            logger.info(f"User {user_id} has {pending_count} pending withdrawals, blocking new withdrawal")
            await message.reply_text("သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။")
            return ConversationHandler.END

        balance = user.get("balance", 0)
        if balance < amount:
            logger.info(f"Insufficient balance for user {user_id}: {int(balance)} < {amount}")
            await message.reply_text(
                f"လက်ကျန်ငွေ မလုံလောက်ပါ။ သင့်လက်ကျန်ငွေသည် {int(balance)} {CURRENCY} ဖြစ်ပါသည်။ /balance ဖြင့် စစ်ဆေးပါ။"
            )
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                logger.info(f"Daily limit exceeded for user {user_id}: {withdrawn_today} + {amount} > {DAILY_WITHDRAWAL_LIMIT}")
                await message.reply_text(
                    f"နေ့စဉ်ထုတ်ယူနိုင်မှု ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ကျော်လွန်သွားပါပြီ။ ယနေ့ထုတ်ပြီးပမာဏ: {withdrawn_today} {CURRENCY}။"
                )
                return STEP_AMOUNT

        context.user_data["withdrawal_amount"] = amount
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}")

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "သင့် KBZ Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "သင့် Wave Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        else:  # Phone Bill
            await message.reply_text(
                "သင့်ဖုန်းနံပါတ်ကို ပေးပို့ပါ (ဥပမာ 09123456789)။"
            )

        logger.info(f"Prompted user {user_id} for payment details (method: {payment_method})")
        return STEP_DETAILS

    except ValueError:
        logger.warning(f"Invalid amount format from user {user_id}: {message.text}")
        await message.reply_text("ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်တစ်ခု ထည့်ပါ (ဥပမာ 100)။")
        return STEP_AMOUNT
    except Exception as e:
        logger.error(f"Error processing amount for user {user_id}: {e}")
        await message.reply_text("အမှားတစ်ခု ဖြစ်ပေါ်ခဲ့ပါသည်။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်ကြိုးစားပါ။")
        return ConversationHandler.END

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Received payment details from user {user_id}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    if not amount or not payment_method:
        logger.error(f"Missing amount or method for user {user_id}: {context.user_data}")
        await update.message.reply_text("အမှား: ငွေထုတ်မှု ဒေတာ မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။")
        return ConversationHandler.END

    details = None
    photo_file_id = None
    if update.message and update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_file_id = photo_file.file_id
        details = "QR Image"
        logger.info(f"User {user_id} uploaded QR image with file_id: {photo_file_id}")
    elif update.message and update.message.text:
        details = update.message.text.strip() or "အသေးစိတ် မပေးထားပါ"
        logger.info(f"User {user_id} provided text details: {details}")
    else:
        logger.warning(f"No valid input from user {user_id}")
        await update.message.reply_text("ကျေးဇူးပြု၍ အသေးစိတ် ဖြည့်ပါ သို့မဟုတ် QR ပုံကို တင်ပါ။")
        return STEP_DETAILS

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        await update.message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
        return ConversationHandler.END

    # Fetch user info from Telegram to get first_name/last_name
    telegram_user = await context.bot.get_chat(user_id)
    name = telegram_user.first_name or telegram_user.last_name or user_id

    keyboard = [
        [InlineKeyboardButton("အတည်ပြုမည် ✅", callback_data=f"approve_{user_id}_{amount}"),
         InlineKeyboardButton("ငြင်းပယ်မည် ❌", callback_data=f"reject_{user_id}_{amount}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    log_message = (
        f"ငွေထုတ်မှု တောင်းဆိုချက်:\n"
        f"အသုံးပြုသူ ID: {user_id}\n"
        f"နာမည်: {name}\n"
        f"ပမာဏ: {amount} {CURRENCY}\n"
        f"နည်းလမ်း: {payment_method}\n"
        f"အသေးစိတ်: {details if not photo_file_id else 'ပူးတွဲပါ QR ပုံကို ကြည့်ပါ'}\n"
        f"အခြေအနေ: ဆိုင်းငံ့ထားသည် ⏳"
    )

    try:
        # Send to admin log channel only
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            reply_markup=reply_markup
        )
        if photo_file_id:
            await context.bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=photo_file_id,
                caption="ငွေထုတ်မှုအတွက် ပူးတွဲပါ QR ပုံ",
                reply_to_message_id=log_msg.message_id
            )
        await context.bot.pin_chat_message(chat_id=LOG_CHANNEL_ID, message_id=log_msg.message_id)

        # Store withdrawal request without deducting balance yet
        await db.update_user(user_id, {
            "pending_withdrawals": user.get("pending_withdrawals", []) + [{
                "amount": amount,
                "payment_method": payment_method,
                "details": details if not photo_file_id else f"QR Image: {photo_file_id}",
                "status": "PENDING",
                "message_id": log_msg.message_id
            }],
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "id": user_id  # Ensure the ID is stored correctly
        })
        logger.info(f"Withdrawal request submitted to log channel for user {user_id}")

    except Exception as e:
        logger.error(f"Failed to submit withdrawal request for user {user_id}: {e}")
        await update.message.reply_text("တောင်းဆိုမှု တင်ပြရာတွင် အမှားဖြစ်ပွားခဲ့ပါသည်။ ကျေးဇူးပြု၍ ထပ်မံကြိုးစားပါ။")
        return ConversationHandler.END

    await update.message.reply_text(
        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ Admin ၏ အတည်ပြုချက်ကို စောင့်ပါ။ ⏳"
    )
    logger.info(f"Notified user {user_id} of pending withdrawal request")
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
                await query.message.reply_text(f"အသုံးပြုသူ {user_id} တွင် လက်ကျန်ငွေ မလုံလောက်ပါ။ လက်ကျန်ငွေ: {int(balance)} {CURRENCY}")
                return

            # Update status to APPROVED and deduct balance
            pending_withdrawals = user.get("pending_withdrawals", [])
            updated_withdrawals = []
            payment_method = None
            for w in pending_withdrawals:
                if w["amount"] == amount and w["status"] == "PENDING":
                    w["status"] = "APPROVED"
                    payment_method = w["payment_method"]
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
                    f"{name} သည် PHONE Bill {amount} ထည့်ခဲ့သည်။\n"
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

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch all users from the database
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("အသုံးပြုသူများ မတွေ့ပါ။ ဒေတာဘေ့စ်ထဲတွင် အသုံးပြုသူ မရှိသေးပါ။")
        logger.warning("No users found in the database for /check command")
        return

    # Sort users by balance in descending order and take top 10
    sorted_users = sorted(users, key=lambda x: x.get("balance", 0), reverse=True)[:10]
    if not sorted_users:
        await update.message.reply_text("ထိပ်တန်းအသုံးပြုသူများ မရှိပါ။")
        logger.warning("No users with balance found for /check command")
        return

    message = "ထိပ်တန်းအသုံးပြုသူ ၁၀ ယောက်၏ လက်ကျန်ငွေ:\n"
    for user in sorted_users:
        user_id = user.get("user_id")
        if not user_id:
            logger.warning(f"User with no user_id found in database: {user}")
            continue  # Skip users without a user_id

        try:
            # Fetch user info from Telegram to get first_name/last_name if not in DB
            telegram_user = await context.bot.get_chat(user_id)
            first_name = user.get("first_name") or telegram_user.first_name or "Unknown"
            last_name = user.get("last_name") or telegram_user.last_name or ""
            name = f"{first_name} {last_name}".strip() or user_id
            balance = user.get("balance", 0)
            message_count = user.get("messages", 0)  # Use 'messages' field as message_count
            message += f"{name} ({user_id}): {int(balance)} {CURRENCY}\nမက်ဆေ့ချ်အရေအတွက်: {message_count}\n"

            # Update the database with the user's name if not already present
            if not user.get("first_name") or not user.get("last_name"):
                await db.update_user(user_id, {
                    "first_name": telegram_user.first_name,
                    "last_name": telegram_user.last_name
                })
        except Exception as e:
            logger.error(f"Failed to fetch user info for {user_id}: {e}")
            message += f"Unknown ({user_id}): {int(user.get('balance', 0))} {CURRENCY}\nမက်ဆေ့ချ်အရေအတွက်: {user.get('messages', 0)}\n"

    await update.message.reply_text(message)
    logger.info("Successfully executed /check command")

async def check_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("ကျေးဇူးပြု၍ User ID တစ်ခု ထည့်ပါ (ဥပမာ: /check_id 123456789)")
        logger.warning("Invalid arguments for /check_id command")
        return

    user_id = str(context.args[0])
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text(f"User ID {user_id} နှင့် ကိုက်ညီသော အသုံးပြုသူ မတွေ့ပါ။")
        logger.warning(f"User {user_id} not found for /check_id command")
        return

    try:
        telegram_user = await context.bot.get_chat(user_id)
        first_name = user.get("first_name") or telegram_user.first_name or "Unknown"
        last_name = user.get("last_name") or telegram_user.last_name or ""
        name = f"{first_name} {last_name}".strip() or user_id
        balance = user.get("balance", 0)
        message_count = user.get("messages", 0)
        await update.message.reply_text(
            f"{name} ({user_id}) ရှိ အချက်အလက်:\n"
            f"လက်ကျန်ငွေ: {int(balance)} {CURRENCY}\n"
            f"မက်ဆေ့ချ်အရေအတွက်: {message_count}"
        )
        logger.info(f"Successfully executed /check_id for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to fetch user info for {user_id}: {e}")
        await update.message.reply_text("အသုံးပြုသူ အချက်အလက် ရယူရာတွင် အမှားဖြစ်ပွားခဲ့ပါသည်။")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(handle_withdraw_button, pattern="^withdraw$")
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method, pattern="^method_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("withdraw", withdraw)],
        conversation_timeout=300,
        per_message=False
    )
    application.add_handler(conv_handler, group=1)
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve_|reject_)"), group=1)
    application.add_handler(CommandHandler("check", check), group=1)
    application.add_handler(CommandHandler("check_id", check_id), group=1)