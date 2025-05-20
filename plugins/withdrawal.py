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
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

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

    # Check invite threshold
    invite_threshold = await db.get_invite_threshold()
    if user.get("invites", 0) < invite_threshold:
        reply_text = f"You need to invite {invite_threshold} users to withdraw. You have invited {user.get('invites', 0)} users."
        if update.message:
            await update.message.reply_text(reply_text)
        else:
            await update.callback_query.message.reply_text(reply_text)
        return ConversationHandler.END

    # Check channel subscriptions
    channels = await db.get_channels()
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel["channel_id"], int(user_id))
            if member.status not in ["member", "administrator", "creator"]:
                reply_text = f"Please join {channel['name']} ({channel['channel_id']}) to proceed with withdrawal."
                if update.message:
                    await update.message.reply_text(reply_text)
                else:
                    await update.callback_query.message.reply_text(reply_text)
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error checking channel subscription for {user_id}: {e}")
            return ConversationHandler.END

    context.user_data.clear()
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_text = (
        "Please select a payment method: 💳\n"
        "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "(Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်)"
    )
    if update.message:
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(reply_text, reply_markup=reply_markup)
    logger.info(f"Prompted user {user_id} for payment method selection")
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
        logger.info(f"Invalid payment method {method} by user {user_id}")
        await query.message.reply_text("Invalid payment method. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
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
    payment_method = context.user_data.get("payment_method")
    logger.info(f"Amount input from user {user_id}: {message.text}")

    if not payment_method:
        logger.error(f"Missing payment method for user {user_id}")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
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
                logger.info(f"User {user_id} exceeded daily limit: {withdrawn_today} + {amount}")
                await message.reply_text(
                    f"Daily withdrawal limit is {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. "
                    f"You've withdrawn {withdrawn_today} {CURRENCY} today.\n"
                    f"သင်သည် နေ့စဉ်ထုတ်ယူနိုင်မှု ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ကို ကျော်လွန်သွားပါသည်။ "
                    f"သင်သည် ယနေ့အတွက် {withdrawn_today} {CURRENCY} ထုတ်ယူပြီးပါသည်။"
                )
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        if user.get("balance", 0) < amount:
            await message.reply_text(
                "Insufficient balance. Please check your balance with /balance.\n"
                "လက်ကျန်ငွေ မလုံလောက်ပါ။ ကျေးဇူးပြု၍ သင့်လက်ကျန်ငွေကို /balance ဖြင့် စစ်ဆေးပါ။"
            )
            return ConversationHandler.END

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
                "Please provide your Wave Pay account details (e.g., phone number and name).\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ ဖုန်းနံပါတ်နှင့် နာမည်)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        else:
            await message.reply_text(
                f"Please provide your {payment_method} account details.\n"
                f"ကျေးဇူးပြု၍ သင်၏ {payment_method} အကောင့်အသေးစိတ်ကို ပေးပါ။"
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
    logger.info(f"Account details for user {user_id}: {message.text}")

    if not amount or not payment_method:
        logger.error(f"Missing amount or payment method for user {user_id}")
        await message.reply_text("Error: Withdrawal details missing. Please start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    payment_details = message.text or "No details provided"
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
        f"သည် စုစုပေါင်း {amount} {CURRENCY} ငွေထုတ်ယူခဲ့ပါသည်။\n"
        f"လက်ရှိလက်ကျန်ငွေ {user.get('balance', 0)} {CURRENCY}\n"
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
    except Exception as e:
        logger.error(f"Failed to send/pin withdrawal request for user {user_id}: {e}")
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
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = str(user_id)
            amount = int(amount)

            user = await db.get_user(user_id)
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

            if success:
                username = user.get("username", user.get("name", "Unknown"))
                mention = f"@{username}" if username and not username.isdigit() else user["name"]
                group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"

                try:
                    await context.bot.send_message(GROUP_CHAT_IDS[0], group_message)
                    await context.bot.send_message(
                        user_id,
                        f"Your withdrawal of {amount} {CURRENCY} has been approved! Your new balance is {new_balance} {CURRENCY}.\n"
                        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
                    )
                    await query.message.reply_text(
                        f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
                    )
                except Exception as e:
                    logger.error(f"Error notifying user {user_id} or group: {e}")
            else:
                await query.message.reply_text("Error approving withdrawal.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = str(user_id)
            amount = int(amount)

            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            try:
                await context.bot.send_message(
                    user_id,
                    f"Your withdrawal request of {amount} {CURRENCY} has been rejected. Contact @actanibot for support.\n"
                    f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို ပယ်ချလိုက်ပါသည်။ အကူအညီအတွက် @actanibot သို့ ဆက်သွယ်ပါ။"
                )
            except Exception as e:
                logger.error(f"Error notifying user {user_id} of rejection: {e}")

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
            CallbackQueryHandler(withdraw, pattern="^init_withdraw$"),
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