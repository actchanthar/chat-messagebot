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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, INVITE_THRESHOLD, ADMIN_IDS
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
        await (update.message or update.callback_query.message).reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await (update.message or update.callback_query.message).reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        await (update.message or update.callback_query.message).reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Skip invite check for admins
    if user_id not in ADMIN_IDS:
        invite_count = user.get("invited_users", 0)  # Use invited_users instead of invites
        if invite_count < INVITE_THRESHOLD:
            logger.info(f"User {user_id} has insufficient invites: {invite_count}/{INVITE_THRESHOLD}")
            await (update.message or update.callback_query.message).reply_text(
                f"You need at least {INVITE_THRESHOLD} invites to withdraw. Current invites: {invite_count}."
            )
            return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id} before starting withdrawal process")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await (update.message or update.callback_query.message).reply_text(
        "Please select a payment method: 💳\n"
        "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
        "Warning ⚠️: အချက်လက်လိုသေချာစွာရေးပါ မှားရေးပါက ငွေများပြန်ရမည်မဟုတ်",
        reply_markup=reply_markup
    )
    logger.info(f"User {user_id} prompted for payment method selection with buttons: {PAYMENT_METHODS}")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Handling payment method selection for user {user_id}, data: {data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}, context: {context.user_data}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
            "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ : 09123456789)"
        )
        logger.info(f"User {user_id} selected Phone Bill, fixed amount to 1000 kyat")
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received message for amount input from user {user_id} in chat {chat_id}: {message.text}, context: {context.user_data}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"User {user_id} missing payment method in context")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if payment_method == "Phone Bill" and amount not in [1000, 2000, 3000, 4000, 5000]:
            await message.reply_text(
                "Phone Bill withdrawals must be 1000, 2000, 3000, 4000, or 5000 kyat.\n"
                "ကျေးဇူးပြု၍ ဖုန်းဘေလ်ထုတ်ယူမှုသည် 1000၊ 2000၊ 3000၊ 4000 သို့မဟုတ် 5000 ကျပ်ဖြစ်ရပါမည်။"
            )
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start again with /start.")
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal:
            last_withdrawal_date = last_withdrawal.date()
            current_date = current_time.date()
            if last_withdrawal_date == current_date:
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.info(f"User {user_id} exceeded daily limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                    await message.reply_text(
                        f"User has exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. "
                        f"You've already withdrawn {withdrawn_today} {CURRENCY} today.\n"
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
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}, context: {context.user_data}")

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။\n"
                "သို့မဟုတ် QR Image ဖြင့်၎င်း ပေးပို့နိုင်သည်။"
            )
        else:
            await message.reply_text(
                "သင့်ရဲ့ဖုန်းနံပါတ်ကိုပို့ပေးပါ (ဥပမာ : 09123456789)"
            )
        logger.info(f"User {user_id} prompted for {payment_method} account details")
        return STEP_DETAILS

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်�ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Handling account details for user {user_id}: {message.text}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    if not amount or not payment_method:
        logger.error(f"User {user_id} missing amount or payment method in context: {context.user_data}")
        await message.reply_text("Error: Withdrawal amount or payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await message.reply_text("User not found. Please start again with /start.")
        return ConversationHandler.END

    payment_details = message.text if message.text else "No details provided"
    context.user_data["withdrawal_details"] = payment_details
    logger.info(f"User {user_id} submitted account details, context: {context.user_data}")

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
        f"ID: {user_id}\n"
        f"First name: {user_first_name}\n"
        f"Username: @{username}\n"
        f"သည် စုစုပေါင်း {amount} ငွေထုတ်ယူခဲ့ပါသည်။\n"
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
        await db.update_user(user_id, {
            "pending_withdrawals": user.get("pending_withdrawals", []) + [{
                "amount": amount,
                "payment_method": payment_method,
                "details": payment_details,
                "status": "PENDING",
                "message_id": log_msg.message_id
            }]
        })
        logger.info(f"Sent and pinned withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send or pin withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ကျေးဇူးပြု၍ အုပ်ချုပ်ရေးမှူး၏ အတည်ပြုချက်ကို စောင့်ပါ။"
    )
    logger.info(f"User {user_id} submitted withdrawal request for {amount} {CURRENCY}")

    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt callback for user {query.from_user.id}, data: {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = str(user_id)
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if balance < amount:
                logger.error(f"Insufficient balance for user {user_id}. Requested: {amount}, Balance: {balance}")
                await query.message.reply_text("User has insufficient balance for this withdrawal.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)

            if last_withdrawal:
                last_withdrawal_date = last_withdrawal.date()
                current_date = current_time.date()
                if last_withdrawal_date == current_date:
                    if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                        logger.error(f"User {user_id} exceeded daily withdrawal limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                        await query.message.reply_text(
                            f"User has exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}."
                        )
                        return
                else:
                    withdrawn_today = 0

            new_balance = balance - amount
            new_withdrawn_today = withdrawn_today + amount
            pending_withdrawals = user.get("pending_withdrawals", [])
            updated_withdrawals = [w for w in pending_withdrawals if w["amount"] != amount or w["status"] != "PENDING"]

            success = await db.update_user(user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": new_withdrawn_today,
                "pending_withdrawals": updated_withdrawals
            })

            if success:
                logger.info(f"Withdrawal approved for user {user_id}. Amount: {amount}, New balance: {new_balance}")
                await query.message.reply_text(
                    f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Post to Group 📢", callback_data=f"post_approval_{user_id}_{amount}")]
                    ])
                )
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Your withdrawal of {amount} {CURRENCY} has been approved! "
                            f"Your new balance: {new_balance} {CURRENCY}\n"
                            f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။ "
                            f"သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
                        )
                    )
                    logger.info(f"Notified user {user_id} of withdrawal approval")
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id} of withdrawal approval: {e}")
            else:
                logger.error(f"Failed to update user {user_id} for withdrawal approval")
                await query.message.reply_text("Error approving withdrawal. Please try again.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = str(user_id)
            amount = int(amount)

            user = await db.get_user(user_id)
            if user:
                pending_withdrawals = user.get("pending_withdrawals", [])
                updated_withdrawals = [w for w in pending_withdrawals if w["amount"] != amount or w["status"] != "PENDING"]
                await db.update_user(user_id, {"pending_withdrawals": updated_withdrawals})

            logger.info(f"Withdrawal rejected for user {user_id}. Amount: {amount}")
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Your withdrawal request of {amount} {CURRENCY} has been rejected. Please contact support for more details.\n"
                        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို ပယ်ချခဲ့ပါသည်။ အသေးစိတ်အတွက် support သို့ ဆက်သွယ်ပါ။"
                    )
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} of withdrawal rejection: {e}")

    except Exception as e:
        logger.error(f"Error handling admin receipt callback for {data}: {e}")
        await query.message.reply_text("Error processing withdrawal request. Please try again.")

async def post_approval_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    try:
        if data.startswith("post_approval_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data for posting approval: {data}")
                await query.message.reply_text("Error posting approval to group.")
                return
            _, _, user_id, amount = parts
            user_id = str(user_id)
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for posting approval")
                await query.message.reply_text("User not found.")
                return

            user_first_name = user.get("name", update.effective_user.first_name or "Unknown")
            username = update.effective_user.username or user.get("username", "N/A")
            message = (
                f"🎉 Withdrawal Approved!\n"
                f"User: @{username} ({user_first_name})\n"
                f"Amount: {amount} {CURRENCY}\n"
                f"Congratulations! Your withdrawal has been processed successfully."
            )
            await context.bot.send_message(
                chat_id=GROUP_CHAT_IDS[0],
                text=message,
                parse_mode="Markdown"
            )
            logger.info(f"Posted withdrawal approval for user {user_id} amount {amount} to group {GROUP_CHAT_IDS[0]}")
            await query.message.reply_text("Approval posted to the group successfully.")
        else:
            logger.error(f"Invalid callback data for posting approval: {data}")
            await query.message.reply_text("Error processing request.")
    except Exception as e:
        logger.error(f"Error posting approval to group for {data}: {e}")
        await query.message.reply_text("Error posting approval to group.")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^withdraw$")
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("withdraw", withdraw)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve_withdrawal|reject_withdrawal)"))
    application.add_handler(CallbackQueryHandler(post_approval_to_group, pattern="^post_approval_"))