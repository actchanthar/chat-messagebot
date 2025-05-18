from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS, DEFAULT_REQUIRED_INVITES
from database.database import db
import logging
import re
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

def load_message_reward_rule():
    settings = db.get_bot_settings()
    rule = settings.get("message_reward_rule", {})
    if not rule:
        rule = {"messages_required": 3, "reward_amount": 1}
        db.update_bot_settings({"message_reward_rule": rule})
        logger.info("Set fallback reward rule: 3 messages = 1 kyat")
    logger.info(f"Loaded reward rule: {rule}")
    return rule

message_reward_rule = load_message_reward_rule()

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Setmessage by {user_id} in {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.info(f"Non-admin {user_id} attempted /setmessage")
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <count> for message , <messages> message <amount>")
        return

    command_text = " ".join(context.args)
    pattern = r"(\d+)\s*for\s*message\s*,\s*(\d+)\s*message\s*(\d+\w*)"
    match = re.match(pattern, command_text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("Invalid format. Use: /setmessage 3 for message , 3 message 1")
        return

    count, messages, amount_str = match.groups()
    if int(count) != int(messages):
        await update.message.reply_text("Error: <count> and <messages> must match.")
        return

    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount. Use a number (e.g., 1).")
        return

    global message_reward_rule
    message_reward_rule = {
        "messages_required": int(count),
        "reward_amount": amount
    }
    result = db.update_bot_settings({"message_reward_rule": message_reward_rule})
    logger.info(f"Set reward rule by {user_id}: {message_reward_rule}, db result: {result}")

    await update.message.reply_text(f"Rule set: {count} messages earns {amount} {CURRENCY}.")
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Rule Set:\nMessages: {count}\nReward: {amount} {CURRENCY}\nBy Admin: {user_id}"
    )

async def reset_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Reset_messages by {user_id} in {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reset_messages <user_id>")
        return

    target_user_id = context.args[0]
    user = db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        return

    result = db.update_user(target_user_id, {"group_messages": {}})
    if not result:
        await update.message.reply_text(f"Error resetting messages for {target_user_id}.")
        return

    await update.message.reply_text(f"Reset message count for {target_user_id}.")
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Message Count Reset:\nUser ID: {target_user_id}\nBy Admin: {user_id}"
    )

async def count_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text[:50] if update.message.text else "Non-text message"
    logger.info(f"Message from {user_id} in {chat_id}: '{message_text}' | GROUP_CHAT_IDS: {GROUP_CHAT_IDS}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Chat {chat_id} not in GROUP_CHAT_IDS")
        return

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        await context.bot.send_message(chat_id=user_id, text="Run /start to register.")
        return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        return

    if not message_reward_rule:
        logger.warning(f"No reward rule for {user_id} in {chat_id}")
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"No reward rule for {user_id} in {chat_id}")
        return

    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
    balance = float(user.get("balance", 0))
    update_data = {"group_messages": group_messages}
    logger.info(f"User {user_id} count: {group_messages[chat_id]}, balance: {balance}")

    if group_messages[chat_id] >= message_reward_rule["messages_required"]:
        reward_amount = message_reward_rule["reward_amount"]
        new_balance = balance + reward_amount
        update_data["balance"] = new_balance
        update_data["group_messages"][chat_id] = 0
        logger.info(f"Applying reward for {user_id}: {reward_amount} {CURRENCY}, new balance: {new_balance}")

        result = db.update_user(user_id, update_data)
        if not result:
            logger.error(f"Failed to update {user_id}: {update_data}")
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Error: Failed to update {user_id}")
            return

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Earned {reward_amount} {CURRENCY} for {message_reward_rule['messages_required']} messages! Balance: {new_balance} {CURRENCY}"
        )
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Reward:\nUser: {user_id}\nMessages: {group_messages[chat_id]}\nReward: {reward_amount} {CURRENCY}\nBalance: {new_balance} {CURRENCY}"
        )
    else:
        result = db.update_user(user_id, update_data)
        if not result:
            logger.error(f"Failed to update {user_id}: {update_data}")
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Error: Failed to update {user_id}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Run /start to register.")
        return
    balance = float(user.get("balance", 0))
    await update.message.reply_text(f"Your balance: {balance} {CURRENCY}")

async def debug_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Run /start to register.")
        return

    group_messages = user.get("group_messages", {})
    balance = float(user.get("balance", 0))
    banned = user.get("banned", False)
    rule_info = (
        f"Messages Required: {message_reward_rule.get('messages_required', 'Not set')}\n"
        f"Reward Amount: {message_reward_rule.get('reward_amount', 'Not set')} {CURRENCY}"
    ) if message_reward_rule else "No reward rule set."

    debug402_message = (
        f"Debug:\n"
        f"User ID: {user_id}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Group Messages: {group_messages}\n"
        f"Balance: {balance} {CURRENCY}\n"
        f"Banned: {banned}\n"
        f"Reward Rule:\n{rule_info}\n"
        f"GROUP_CHAT_IDS: {GROUP_CHAT_IDS}\n"
        f"Chat ID: {chat_id}"
    )
    await update.message.reply_text(debug_message)
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Debug by {user_id}:\n{debug_message}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw by {user_id} in {chat_id}")

    if update.effective_chat.type != "private":
        await update.message.reply_text("Use /withdraw in private chat.")
        return ConversationHandler.END

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Run /start to register.")
        return ConversationHandler.END

    if user.get("banned", False):
        await update.message.reply_text("You are banned.")
        return ConversationHandler.END

    balance = float(user.get("balance", 0))
    if balance < WITHDRAWAL_THRESHOLD:
        await update.message.reply_text(f"Need at least {WITHDRAWAL_THRESHOLD} {CURRENCY}. Your balance: {balance} {CURRENCY}")
        return ConversationHandler.END

    if user_id not in ADMIN_IDS:
        required_channels = db.get_required_channels() or []
        if required_channels:
            subscribed_channels = user.get("subscribed_channels", [])
            not_subscribed = [ch for ch in required_channels if ch not in subscribed_channels]
            if not_subscribed:
                keyboard = [[InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.replace('-100', '')}")] for ch in not_subscribed]
                await update.message.reply_text("Join all required channels.", reply_markup=InlineKeyboardMarkup(keyboard))
                return ConversationHandler.END

        invited_users = user.get("invited_users", 0)
        if invited_users < DEFAULT_REQUIRED_INVITES:
            bot_username = (await context.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start=referral_{user_id}"
            await update.message.reply_text(
                f"Need {DEFAULT_REQUIRED_INVITES} invited users. You have {invited_users}.\nInvite Link: {invite_link}"
            )
            return ConversationHandler.END

    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        await update.message.reply_text("Pending withdrawal exists. Wait for processing.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    await update.message.reply_text("Select payment method:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection by {user_id}: {data}")

    await query.answer()
    if not data.startswith("payment_"):
        await query.message.reply_text("Invalid method. Use /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        await query.message.reply_text("Invalid method.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    await query.message.reply_text(f"Enter amount to withdraw (min: {WITHDRAWAL_THRESHOLD} {CURRENCY}).")
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount_text = update.message.text.strip()
    logger.info(f"Amount input by {user_id}: {amount_text}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        await update.message.reply_text("Error: No payment method. Use /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(amount_text)
        if amount < WITHDRAWAL_THRESHOLD:
            await update.message.reply_text(f"Minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}.")
            return STEP_AMOUNT

        user = db.get_user(user_id)
        balance = float(user.get("balance", 0))
        if balance < amount:
            await update.message.reply_text("Insufficient balance.")
            return ConversationHandler.END

        context.user_data["withdrawal_amount"] = amount
        await update.message.reply_text(f"Provide your {payment_method} details.")
        return STEP_DETAILS
    except ValueError:
        await update.message.reply_text("Enter a valid number.")
        return STEP_AMOUNT

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    payment_details = update.message.text
    logger.info(f"Details by {user_id}: {payment_details}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    if not (amount and payment_method):
        await update.message.reply_text("Error: Missing data. Use /withdraw.")
        return ConversationHandler.END

    user = db.get_user(user_id)
    balance = float(user.get("balance", 0))
    if balance < amount:
        await update.message.reply_text("Insufficient balance.")
        return ConversationHandler.END

    new_balance = balance - amount
    pending_withdrawal = {
        "amount": amount,
        "payment_method": payment_method,
        "payment_details": payment_details,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc)
    }
    result = db.update_user(user_id, {
        "balance": new_balance,
        "pending_withdrawals": [pending_withdrawal]
    })
    if not result:
        logger.error(f"Failed to deduct amount for {user_id}")
        await update.message.reply_text("Error submitting request.")
        return ConversationHandler.END

    withdrawal_message = (
        f"Withdrawal Request:\n"
        f"User ID: {user_id}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Amount: {amount} {CURRENCY}\n"
        f"Method: {payment_method}\n"
        f"Details: {payment_details}\n"
        f"Status: PENDING"
    )
    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=withdrawal_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text(f"Withdrawal request for {amount} {CURRENCY} submitted. New balance: {new_balance} {CURRENCY}")
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Admin receipt by {user_id}: {data}")

    await query.answer()
    if data.startswith("approve_withdrawal_"):
        _, _, target_user_id, amount = data.split("_")
        amount = int(amount)
        user = db.get_user(target_user_id)
        result = db.update_user(target_user_id, {
            "pending_withdrawals": [],
            "last_withdrawal": datetime.now(timezone.utc),
            "withdrawn_today": user.get("withdrawn_today", 0) + amount
        })
        if result:
            await context.bot.send_message(chat_id=target_user_id, text=f"Withdrawal of {amount} {CURRENCY} approved!")
            await query.message.edit_text(query.message.text + "\nStatus: Approved")
        else:
            await query.message.reply_text("Error approving.")
    elif data.startswith("reject_withdrawal_"):
        _, _, target_user_id, amount = data.split("_")
        amount = int(amount)
        user = db.get_user(target_user_id)
        new_balance = float(user.get("balance", 0)) + amount
        result = db.update_user(target_user_id, {
            "balance": new_balance,
            "pending_withdrawals": []
        })
        if result:
            await context.bot.send_message(chat_id=target_user_id, text=f"Withdrawal of {amount} {CURRENCY} rejected.")
            await query.message.edit_text(query.message.text + "\nStatus: Rejected")
        else:
            await query.message.reply_text("Error rejecting.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Cancel by {user_id}")
    await update.message.reply_text("Withdrawal canceled.")
    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve_withdrawal_|reject_withdrawal_)"))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("reset_messages", reset_messages))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("debug_message_count", debug_message_count))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=GROUP_CHAT_IDS), count_group_message))