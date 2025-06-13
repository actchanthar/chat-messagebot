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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS, INVITE_THRESHOLD
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id}")

    if update.effective_chat.type != "private":
        try:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text("ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ။")
            else:
                await update.message.reply_text("ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ�।")
            logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending non-private chat message to user {user_id}: {e}")
        return ConversationHandler.END

    try:
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

        if user.get("invites", 0) < INVITE_THRESHOLD:
            logger.info(f"User {user_id} has insufficient invites: {user.get('invites', 0)} < {INVITE_THRESHOLD}")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(
                    f"You need at least {INVITE_THRESHOLD} invites to withdraw. Current invites: {user.get('invites', 0)}."
                )
            else:
                await update.message.reply_text(
                    f"You need at least {INVITE_THRESHOLD} invites to withdraw. Current invites: {user.get('invites', 0)}."
                )
            return ConversationHandler.END

        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
        if pending_count > 0:
            logger.info(f"User {user_id} has {pending_count} pending withdrawals")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(
                    "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။"
                )
            else:
                await update.message.reply_text(
                    "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။"
                )
            return ConversationHandler.END

        context.user_data.clear()
        logger.info(f"Cleared user_data for user {user_id}")

        keyboard = [[InlineKeyboardButton(method, callback_data=f"method_{method}")] for method in PAYMENT_METHODS]
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
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

    except Exception as e:
        logger.error(f"Error in withdraw command for user {user_id}: {e}")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("An error occurred. Please try again later.")
        else:
            await update.message.reply_text("An error occurred. Please try again later.")
        return ConversationHandler.END

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

    if data == "cancel":
        await query.message.reply_text("ငွေထုတ်မှု လုပ်ငန်းစဉ်ကို ပယ်ဖျက်လိုက်ပါပြီ။")
        logger.info(f"User {user_id} cancelled withdrawal")
        return ConversationHandler.END

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

        if payment_method == "Phone Bill" and amount != 1000:
            await message.reply_text("Phone Bill ဖြင့် ငွေထုတ်မှုသည် ၁၀၀၀ ကျပ်သာ လုပ်ဆောင်နိုင်ပါသည်။ ကျေးဇူးပြု၍ ၁၀၀၀ ထည့်ပါ။")
            return STEP_AMOUNT

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

        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
        if pending_count > 0:
            logger.info(f"User {user_id} has {pending_count} pending withdrawals")
            await message.reply_text(
                "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။"
            )
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
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_file_id = photo_file.file_id
            details = "QR Image"
            logger.info(f"User {user_id} uploaded QR image with file_id: {photo_file_id}")
        except Exception as e:
            logger.error(f"Error processing photo for user {user_id}: {e}")
            await update.message.reply_text("Error processing QR image. Please try again.")
            return STEP_DETAILS
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
        await update.message.reply_text("အသုံးပြုသူ မတွေ့ပါ�। ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
        return ConversationHandler.END

    telegram_user = await context.bot.get_chat(user_id)
    name = (telegram_user.first_name or "") + (" " + telegram_user.last_name if telegram_user.last_name else "")

    if user.get("balance", 0) < amount:
        logger.info(f"Insufficient balance for user {user_id}: {int(user.get('balance', 0))} < {amount}")
        await update.message.reply_text(
            f"လက်ကျန်ငွေ မလုံလောက်ပါ။ သင့်လက်ကျန်ငွေသည် {int(user.get('balance', 0))} {CURRENCY} ဖြစ်ပါသည်။ /balance ဖြင့် စစ်ဆေးပါ။"
        )
        return ConversationHandler.END

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

        await db.update_user(user_id, {
            "pending_withdrawals": user.get("pending_withdrawals", []) + [{
                "amount": amount,
                "payment_method": payment_method,
                "details": details if not photo_file_id else f"QR Image: {photo_file_id}",
                "status": "PENDING",
                "message_id": log_msg.message_id,
                "request_time": datetime.now(timezone.utc)
            }],
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name
        })
        logger.info(f"Withdrawal request submitted to log channel for user {user_id}")

        await update.message.reply_text(
            f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ Admin ၏ အတည်ပြုချက်ကို စောင့်ပါ�। ⏳"
        )
        logger.info(f"Notified user