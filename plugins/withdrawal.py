# plugins/withdrawal.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from config import ADMIN_IDS, GROUP_CHAT_ID, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, PAYMENT_METHODS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await db.get_user(str(user_id))

    if not user:
        if update.message:
            await update.message.reply_text("User not found. Please start with /start.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("User not found. Please start with /start.")
        return

    if user.get("banned", False):
        if update.message:
            await update.message.reply_text("You are banned from using this bot.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("You are banned from using this bot.")
        return

    # Clear previous state to avoid loops, including any residual keys
    logger.info(f"Clearing context.user_data for user {user_id}: {context.user_data}")
    context.user_data.clear()
    context.user_data["awaiting_withdrawal_amount"] = True
    context.user_data["awaiting_payment_method"] = False
    context.user_data["awaiting_withdrawal_details"] = False
    context.user_data["withdrawal_amount"] = None
    context.user_data["payment_method"] = None
    logger.info(f"Initialized context.user_data for user {user_id}: {context.user_data}")

    # Send the withdrawal prompt based on update type
    if update.message:
        await update.message.reply_text(
            f"Please enter the amount you wish to withdraw (e.g., {WITHDRAWAL_THRESHOLD}). 💸 \n\n ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ ငွေထုတ်ရန် အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            f"Please enter the amount you wish to withdraw (e.g., {WITHDRAWAL_THRESHOLD}). 💸 \n\n ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ ငွေထုတ်ရန် အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
        )
    logger.info(f"User {user_id} prompted for withdrawal amount")

async def handle_payment_method_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    logger.info(f"Payment method callback received: user {user_id}, data: {data}, context: {context.user_data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback data: {data}")
        await query.message.reply_text("Invalid callback data. Please start the withdrawal process again with /withdraw.")
        return

    if not context.user_data.get("awaiting_payment_method"):
        await query.message.reply_text("Please enter the withdrawal amount first. Start the process again with /withdraw.")
        logger.info(f"User {user_id} tried to select payment method without proper context")
        return

    if not context.user_data.get("withdrawal_amount"):
        await query.message.reply_text("Withdrawal amount not found. Please start the withdrawal process again with /withdraw.")
        logger.info(f"User {user_id} tried to select payment method without a withdrawal amount")
        return

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        return

    context.user_data["payment_method"] = method
    context.user_data["awaiting_payment_method"] = False
    context.user_data["awaiting_withdrawal_details"] = True
    logger.info(f"Updated context.user_data after payment method selection for user {user_id}: {context.user_data}")

    if method == "KBZ Pay":
        await query.message.reply_text(
            "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW). 💳"
        )
    elif method == "Wave Pay":
        await query.message.reply_text(
            "Please provide your Wave Pay account details (e.g., phone number and name). 💳"
        )
    elif method == "Phone Bill":
        await query.message.reply_text(
            "Please provide your phone number for Phone Bill payment. 💳"
        )
    else:
        await query.message.reply_text(
            f"Please provide your {method} account details. 💳"
        )
    logger.info(f"User {user_id} selected payment method {method} and prompted for details")

async def handle_withdrawal_details(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = await db.get_user(str(user_id))
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    message = update.message

    # Step 1: Handle the withdrawal amount
    if context.user_data.get("awaiting_withdrawal_amount"):
        logger.info(f"User {user_id} entered amount: {message.text}, context: {context.user_data}")
        amount = None
        try:
            amount = int(message.text)
        except (ValueError, TypeError):
            await message.reply_text(f"Please enter a valid amount (e.g., {WITHDRAWAL_THRESHOLD}).")
            logger.info(f"User {user_id} entered invalid amount: {message.text}")
            return

        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}.")
            logger.info(f"User {user_id} entered amount {amount} below minimum {WITHDRAWAL_THRESHOLD}")
            return

        balance = user.get("balance", 0)
        if amount > balance:
            await message.reply_text("Insufficient balance for this withdrawal.")
            logger.info(f"User {user_id} has insufficient balance. Requested: {amount}, Balance: {balance}")
            return

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)

        if last_withdrawal:
            last_withdrawal_date = last_withdrawal.date()
            current_date = current_time.date()
            if last_withdrawal_date == current_date:
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    await message.reply_text(f"Daily withdrawal limit is {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. You've already withdrawn {withdrawn_today} {CURRENCY} today.")
                    logger.info(f"User {user_id} exceeded daily limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                    return
            else:
                withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["awaiting_withdrawal_amount"] = False
        context.user_data["awaiting_payment_method"] = True
        logger.info(f"Updated context.user_data after amount entry for user {user_id}: {context.user_data}")

        # Show payment method selection buttons
        keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.info(f"Sending payment method selection buttons to user {user_id}: {PAYMENT_METHODS}")
        await message.reply_text(
            "Please select a payment method: 💳",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} prompted for payment method selection after entering amount {amount}")
        return

    # Step 2: Handle the withdrawal details (after payment method selection)
    if context.user_data.get("awaiting_withdrawal_details"):
        logger.info(f"User {user_id} entered withdrawal details: {message.text}, context: {context.user_data}")
        amount = context.user_data.get("withdrawal_amount")
        payment_method = context.user_data.get("payment_method")
        if not amount or not payment_method:
            await message.reply_text("Error: Withdrawal amount or payment method not found. Please start the withdrawal process again with /withdraw.")
            logger.error(f"User {user_id} has no withdrawal amount or payment method in context")
            return

        payment_details = message.text if message.text else "No details provided"

        context.user_data["awaiting_withdrawal_details"] = False
        context.user_data["withdrawal_details"] = payment_details
        logger.info(f"Updated context.user_data after details entry for user {user_id}: {context.user_data}")

        keyboard = [
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Send the withdrawal request message to each admin
            for admin_id in ADMIN_IDS:
                if admin_id:
                    withdrawal_message = await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"Withdrawal Request:\n"
                            f"User ID: {user_id}\n"
                            f"User: @{update.effective_user.username or 'N/A'}\n"
                            f"Amount: {amount} {CURRENCY} 💸\n"
                            f"Payment Method: {payment_method}\n"
                            f"Details: {payment_details}\n"
                            f"Status: PENDING ⏳"
                        ),
                        reply_markup=reply_markup
                    )
                    logger.info(f"Sent withdrawal request to admin {admin_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send withdrawal request to admins: {e}")
            await message.reply_text("Error submitting withdrawal request. Please try again later.")
            return

        await message.reply_text(
            f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳"
        )
        logger.info(f"User {user_id} submitted withdrawal request for {amount} {CURRENCY}")

async def handle_admin_receipt(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"handle_admin_receipt triggered with data: {data}, context: {context.user_data}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request. Invalid callback data.")
                return
            _, _, user_id, amount = parts
            user_id = int(user_id)
            amount = int(amount)

            user = await db.get_user(str(user_id))
            if not user:
                logger.error(f"User {user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if amount > balance:
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
                        await query.message.reply_text(f"User has exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}.")
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
                logger.info(f"Withdrawal approved for user {user_id}. Amount: {amount}, New balance: {new_balance}")
                await query.message.reply_text(f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.")
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Your withdrawal of {amount} {CURRENCY} has been approved! Your new balance is {new_balance} {CURRENCY}."
                    )
                    # Send announcement to the group
                    username = user.get("username", user["name"])
                    mention = f"@{username}" if username else user["name"]
                    group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
                    try:
                        await context.bot.send_message(
                            chat_id=GROUP_CHAT_ID,
                            text=group_message
                        )
                        logger.info(f"Sent withdrawal announcement to group {GROUP_CHAT_ID} for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send announcement to group {GROUP_CHAT_ID}: {str(e)}")
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
                await query.message.reply_text("Error processing withdrawal request. Invalid callback data.")
                return
            _, _, user_id, amount = parts
            user_id = int(user_id)
            amount = int(amount)

            logger.info(f"Withdrawal rejected for user {user_id}. Amount: {amount}")
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected by the admin. If there are any problems or you wish to appeal, please contact @actanibot"
                )
                logger.info(f"Notified user {user_id} of withdrawal rejection")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} of withdrawal rejection: {e}")
    except Exception as e:
        logger.error(f"Error in handle_admin_receipt: {e}")
        await query.message.reply_text("Error processing withdrawal request. Please try again.")