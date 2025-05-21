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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS, REQUIRED_CHANNELS
from database.database import db
import logging
from datetime import datetime, timezone
import asyncio

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
        try:
            await query.answer()
            logger.info(f"Callback query answered for user {user_id}")
        except Exception as e:
            logger.error(f"Error answering callback for user {user_id}: {e}", exc_info=True)

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        try:
            await message.reply_text("Please use /withdraw in a private chat.")
        except Exception as e:
            logger.error(f"Failed to send non-private chat message to {user_id}: {e}")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        for _ in range(2):
            user = await db.create_user(user_id, update.effective_user.full_name or "Unknown")
            if user:
                break
        if not user:
            logger.error(f"User {user_id} not found and could not be created")
            try:
                await message.reply_text("Error: User not found. Please start with /start.")
            except Exception as e:
                logger.error(f"Failed to send user not found message to {user_id}: {e}")
            return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        try:
            await message.reply_text("You are banned from using this bot.")
        except Exception as e:
            logger.error(f"Failed to send banned message to {user_id}: {e}")
        return ConversationHandler.END

    if user_id not in ADMIN_IDS:
        invite_requirement = await db.get_setting("invite_requirement", 15)
        invited_users = user.get("invited_users", 0) if isinstance(user.get("invited_users"), (int, float)) else len(user.get("invited_users", [])) if isinstance(user.get("invited_users"), list) else 0
        if invited_users < invite_requirement:
            logger.info(f"User {user_id} has insufficient invites: {invited_users}/{invite_requirement}")
            try:
                await message.reply_text(f"You need to invite at least {invite_requirement} users who have joined the channels to withdraw.")
            except Exception as e:
                logger.error(f"Failed to send insufficient invites message to {user_id}: {e}")
            return ConversationHandler.END
        if not user.get("joined_channels", False):
            required_channels = await db.get_required_channels()
            channels_text = "\n".join([f"https://t.me/{channel.lstrip('@')}" for channel in required_channels])
            logger.info(f"User {user_id} has not joined required channels")
            try:
                await message.reply_text(
                    f"Please join all required channels and use /checksubscription:\n{channels_text}\n"
                    "ဤချန်နယ်များအားလုံးသို့ ဝင်ရောက်ပြီး /checksubscription ကို အသုံးပြုပါ။"
                )
            except Exception as e:
                logger.error(f"Failed to send join channels message to {user_id}: {e}")
            return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id}")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await message.reply_text(
            "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။\n"
            "(Warning ⚠️: အချက်အလက်များကို သေချာစွာရေးပါ၊ မမှန်ကန်ပါက ငွေများပြန်ရမည်မဟုတ်ပါ။)",
            reply_markup=reply_markup
        )
        logger.info(f"Sent payment method selection prompt to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send payment method prompt to {user_id}: {e}", exc_info=True)
        return ConversationHandler.END
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Payment method selection by user {user_id}: {data}")

    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Error answering payment method callback for {user_id}: {e}")

    if not data.startswith("payment_"):
        logger.warning(f"Invalid payment method callback for user {user_id}: {data}")
        try:
            await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send invalid method message to {user_id}: {e}")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.warning(f"Unsupported payment method for user {user_id}: {method}")
        try:
            await query.message.reply_text("Invalid payment method. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send invalid method message to {user_id}: {e}")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method: {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        try:
            await query.message.reply_text(
                "သင့်ဖုန်းနံပါတ်ကို ပို့ပေးပါ (ဥပမာ: 09123456789)\n"
                "Phone Bill top-up is fixed at 1000 kyat increments (e.g., 1000, 2000, 3000)."
            )
            logger.info(f"Sent phone bill details prompt to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send phone bill prompt to {user_id}: {e}")
            return ConversationHandler.END
        return STEP_DETAILS

    try:
        await query.message.reply_text(
            f"Please enter the amount (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
            f"ငွေထုတ်ရန် ပမာဏကို ရေးပို့ပါ၊ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှ ထုတ်လို့ရမှာပါ။"
        )
        logger.info(f"Sent amount prompt to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send amount prompt to {user_id}: {e}")
        return ConversationHandler.END
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    payment_method = context.user_data.get("payment_method")
    logger.info(f"Amount input by user {user_id}: {message.text if message else 'None'}")

    if not payment_method:
        logger.error(f"Missing payment method for user {user_id}")
        try:
            await message.reply_text("Error: Payment method missing. Start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send missing method message to {user_id}: {e}")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if payment_method == "Phone Bill" and amount % 1000 != 0:
            logger.warning(f"Invalid Phone Bill amount by user {user_id}: {amount}")
            try:
                await message.reply_text("Phone Bill withdrawals must be in 1000 kyat increments (e.g., 1000, 2000).")
            except Exception as e:
                logger.error(f"Failed to send invalid amount message to {user_id}: {e}")
            return STEP_AMOUNT
        if amount < WITHDRAWAL_THRESHOLD:
            logger.warning(f"Amount below threshold by user {user_id}: {amount}")
            try:
                await message.reply_text(f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Try again.")
            except Exception as e:
                logger.error(f"Failed to send low amount message to {user_id}: {e}")
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user or user.get("balance", 0) < amount:
            logger.error(f"Insufficient balance for user {user_id}: {user.get('balance', 0) if user else 'None'} vs {amount}")
            try:
                await message.reply_text("Insufficient balance. Check with /balance.")
            except Exception as e:
                logger.error(f"Failed to send insufficient balance message to {user_id}: {e}")
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                logger.warning(f"Daily limit exceeded for user {user_id}: {withdrawn_today + amount}")
                try:
                    await message.reply_text(f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
                except Exception as e:
                    logger.error(f"Failed to send daily limit message to {user_id}: {e}")
                return STEP_AMOUNT
        else:
            withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"User {user_id} entered valid amount: {amount}")

        prompt = (
            "Please provide your {} account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).\n\n💳\n"
            "ကျေးဇူးပြု၍ သင်၏ {} အကောင့်အသေးစိတ်ကို ပေးပါ။ သို့မဟုတ် QR Image ဖြင့်ပေးပို့နိုင်သည်။"
        )
        if payment_method == "KBZ Pay":
            prompt = prompt.format("KBZ Pay", "KBZ Pay")
        elif payment_method == "Wave Pay":
            prompt = prompt.format("Wave Pay", "Wave Pay")
        try:
            await message.reply_text(prompt)
            logger.info(f"Sent details prompt to user {user_id} for {payment_method}")
        except Exception as e:
            logger.error(f"Failed to send details prompt to {user_id}: {e}")
            return ConversationHandler.END
        return STEP_DETAILS
    except ValueError:
        logger.warning(f"Invalid amount input by user {user_id}: {message.text}")
        try:
            await message.reply_text("Please enter a valid number (e.g., 100).")
        except Exception as e:
            logger.error(f"Failed to send invalid number message to {user_id}: {e}")
        return STEP_AMOUNT
    except Exception as e:
        logger.error(f"Error in handle_amount for user {user_id}: {e}", exc_info=True)
        try:
            await message.reply_text("An error occurred. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send error message to {user_id}: {e}")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    logger.info(f"Details input by user {user_id}: {message.text if message.text else 'Photo'}")

    if not amount or not payment_method:
        logger.error(f"Missing data for user {user_id}: amount={amount}, method={payment_method}")
        try:
            await message.reply_text("Error: Missing data. Start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send missing data message to {user_id}: {e}")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in handle_details")
        try:
            await message.reply_text("Error: User not found. Start again with /start.")
        except Exception as e:
            logger.error(f"Failed to send user not found message to {user_id}: {e}")
        return ConversationHandler.END

    payment_details = message.text or "Photo provided" if message.photo else "No details provided"
    context.user_data["withdrawal_details"] = payment_details

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_name = user.get("name", update.effective_user.full_name or "Unknown")
    username = user.get("username") or update.effective_user.username or "N/A"
    log_message = (
        f"Withdrawal Request:\n"
        f"ID: {user_id}\n"
        f"Name: {user_name}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY}\n"
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
        await context.bot.pin_chat_message(chat_id=LOG_CHANNEL_ID, message_id=log_msg.message_id, disable_notification=True)
        logger.info(f"Sent and pinned withdrawal request for user {user_id} to log channel")
    except Exception as e:
        logger.error(f"Failed to send/pin withdrawal request for {user_id}: {e}", exc_info=True)
        try:
            await message.reply_text("Error submitting request. Try again later.")
        except Exception as e:
            logger.error(f"Failed to send error message to {user_id}: {e}")
        return ConversationHandler.END

    try:
        await message.reply_text(
            f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please await approval.\n"
            f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်သွင်းပြီးပါပြီ။ အတည်ပြုချက်ကို စောင့်ပါ�।"
        )
        logger.info(f"Sent withdrawal confirmation to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send withdrawal confirmation to {user_id}: {e}")
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Admin {user_id} handling receipt: {data}")

    if user_id not in ADMIN_IDS:
        try:
            await query.answer()
            await query.message.reply_text("Unauthorized.")
        except Exception as e:
            logger.error(f"Failed to send unauthorized message to {user_id}: {e}")
        return

    try:
        await query.answer()
        if data.startswith("approve_withdrawal_"):
            _, _, target_user_id, amount = data.split("_")
            target_user_id = str(target_user_id)
            amount = int(amount)

            user = await db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for approval")
                try:
                    await query.message.reply_text(f"User {target_user_id} not found.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to {user_id}: {e}")
                return

            balance = user.get("balance", 0)
            if balance < amount:
                logger.warning(f"Insufficient balance for user {target_user_id}: {balance} vs {amount}")
                try:
                    await query.message.reply_text("Insufficient balance.")
                except Exception as e:
                    logger.error(f"Failed to send insufficient balance message to {user_id}: {e}")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if last_withdrawal and last_withdrawal.date() == current_time.date():
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.warning(f"Daily limit exceeded for user {target_user_id}: {withdrawn_today + amount}")
                    try:
                        await query.message.reply_text(f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
                    except Exception as e:
                        logger.error(f"Failed to send daily limit message to {user_id}: {e}")
                    return
            else:
                withdrawn_today = 0

            new_balance = balance - amount
            new_withdrawn_today = withdrawn_today + amount
            await db.update_user(target_user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": new_withdrawn_today
            })

            try:
                await query.message.edit_text(
                    f"Withdrawal approved for user {target_user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.\n"
                    f"Status: APPROVED ✅",
                    parse_mode="Markdown"
                )
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"Your withdrawal of {amount} {CURRENCY} has been approved! New balance: {new_balance} {CURRENCY}.\n"
                        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။ လက်ကျန်ငွေ: {new_balance} {CURRENCY}."
                    )
                )
                logger.info(f"Approved withdrawal for user {target_user_id}: {amount} {CURRENCY}")
            except Exception as e:
                logger.error(f"Failed to send approval messages for {target_user_id}: {e}")

            users = await db.get_all_users()
            sent_count = 0
            failed_count = 0
            for u in users:
                if u["user_id"] == target_user_id:
                    continue
                try:
                    username = user.get("username") or user.get("name", "Unknown")
                    await context.bot.send_message(
                        chat_id=u["user_id"],
                        text=(
                            f"User @{username} has withdrawn {amount} {CURRENCY}!\n"
                            f"လက်ရှိလက်ကျန်ငွေ: {new_balance} {CURRENCY}"
                        )
                    )
                    sent_count += 1
                    if sent_count % 30 == 0:
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to announce to user {u['user_id']}: {e}")
                    failed_count += 1

            try:
                await query.message.reply_text(
                    f"Withdrawal approved and announced to {sent_count} users (failed: {failed_count}).",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Post to Group 📢", callback_data=f"post_approval_{target_user_id}_{amount}")]])
                )
                logger.info(f"Sent approval summary to admin {user_id}: {sent_count} successes, {failed_count} failures")
            except Exception as e:
                logger.error(f"Failed to send approval summary to {user_id}: {e}")

        elif data.startswith("reject_withdrawal_"):
            _, _, target_user_id, amount = data.split("_")
            target_user_id = str(target_user_id)
            amount = int(amount)
            try:
                await query.message.edit_text(
                    f"Withdrawal rejected for user {target_user_id}. Amount: {amount} {CURRENCY}.\nStatus: REJECTED ❌",
                    parse_mode="Markdown"
                )
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"Your withdrawal request of {amount} {CURRENCY} has been rejected.\n"
                        f"Contact @actearnbot for issues."
                    )
                )
                logger.info(f"Rejected withdrawal for user {target_user_id}: {amount} {CURRENCY}")
            except Exception as e:
                logger.error(f"Failed to send rejection messages for {target_user_id}: {e}")

        elif data.startswith("post_approval_"):
            _, _, target_user_id, amount = data.split("_")
            target_user_id = str(target_user_id)
            amount = int(amount)
            user = await db.get_user(target_user_id)
            mention = f"@{user.get('username', user['name'])}" if user.get("username") else user["name"]
            try:
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_IDS[0],
                    text=f"{mention} သည် ငွေ {amount} ကျပ်ထုတ်ခဲ့သည်။ ချိုချဉ်စားပါ 🍬"
                )
                await query.message.reply_text(f"Posted to group {GROUP_CHAT_IDS[0]}.")
                logger.info(f"Posted withdrawal announcement for {target_user_id} to group {GROUP_CHAT_IDS[0]}")
            except Exception as e:
                logger.error(f"Failed to post to group for {target_user_id}: {e}")
    except Exception as e:
        logger.error(f"Error in handle_admin_receipt for admin {user_id}: {e}", exc_info=True)
        try:
            await query.message.reply_text("An error occurred during approval/rejection.")
        except Exception as e:
            logger.error(f"Failed to send error message to {user_id}: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Withdrawal canceled by user {user_id}")
    try:
        await update.message.reply_text("Withdrawal canceled.")
    except Exception as e:
        logger.error(f"Failed to send cancel message to {user_id}: {e}")
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
            STEP_DETAILS: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_details)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_|post_approval_"))