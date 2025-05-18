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
from telegram.error import BadRequest, Forbidden, TelegramError
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS
from database.database import db
import logging
from datetime import datetime, timezone
import re

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

# Temporary in-memory storage for message reward rule
message_reward_rule = {}

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        bot_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            logger.error(f"Bot is not an admin in channel {channel_id}. Status: {bot_member.status}")
            return False
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        logger.info(f"User {user_id} subscription check for {channel_id}: status={member.status}")
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in {channel_id}: {str(e)}")
        return False

async def debug_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Debug_message_count called by user {user_id} in chat {chat_id}")

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database for debug")
        await update.message.reply_text("Error: User not found in database. Please run /start.")
        return

    group_messages = user.get("group_messages", 0)
    balance = int(user.get("balance", 0))
    banned = user.get("banned", False)
    rule_info = (
        f"Messages Required: {message_reward_rule.get('messages_required', 'Not set')}\n"
        f"Reward Amount: {message_reward_rule.get('reward_amount', 'Not set')} {CURRENCY}"
    ) if message_reward_rule else "No message reward rule set."

    debug_message = (
        f"Debug Message Count:\n"
        f"User ID: {user_id}\n"
        f"Username: @{update.effective_user.username or 'N/A'}\n"
        f"Group Messages: {group_messages}\n"
        f"Balance: {balance} {CURRENCY}\n"
        f"Banned: {banned}\n"
        f"Message Reward Rule:\n{rule_info}\n"
        f"GROUP_CHAT_IDS: {GROUP_CHAT_IDS}\n"
        f"Current Chat ID: {chat_id}"
    )

    await update.message.reply_text(debug_message)
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Debug Message Count by {user_id}:\n{debug_message}"
    )
    logger.info(f"Sent debug info for user {user_id}")

async def force_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Force_reward called by user {admin_id} in chat {chat_id}")

    if admin_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {admin_id} attempted /force_reward")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"User {admin_id} used /force_reward without user_id")
        await update.message.reply_text("Usage: /force_reward <user_id> (e.g., /force_reward 7796351432)")
        return

    target_user_id = context.args[0]
    user = db.get_user(target_user_id)
    if not user:
        logger.error(f"User {target_user_id} not found for force_reward")
        await update.message.reply_text(f"User {target_user_id} not found.")
        return

    if not message_reward_rule:
        logger.warning(f"No message reward rule set for force_reward by {admin_id}")
        await update.message.reply_text("Error: No message reward rule set. Use /setmessage first.")
        return

    reward_amount = message_reward_rule["reward_amount"]
    balance = int(user.get("balance", 0))
    new_balance = balance + reward_amount
    update_data = {
        "balance": new_balance,
        "group_messages": 0
    }

    result = db.update_user(target_user_id, update_data)
    if not result:
        logger.error(f"Failed to force reward for user {target_user_id}: {update_data}")
        await update.message.reply_text(f"Error: Failed to apply reward for user {target_user_id}.")
        return

    logger.info(f"Forced reward for user {target_user_id}: {reward_amount} {CURRENCY}, new balance: {new_balance}")
    await update.message.reply_text(
        f"Successfully forced reward for user {target_user_id}: {reward_amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Forced Reward:\nUser ID: {target_user_id}\nReward: {reward_amount} {CURRENCY}\nNew Balance: {new_balance} {CURRENCY}\nBy Admin: {admin_id}"
    )
    await context.bot.send_message(
        chat_id=target_user_id,
        text=f"Admin applied a reward of {reward_amount} {CURRENCY}. Your new balance is {new_balance} {CURRENCY}."
    )

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Setmessage called by user {admin_id} in chat {chat_id}")

    if admin_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {admin_id} attempted /setmessage")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"User {admin_id} used /setmessage without arguments")
        await update.message.reply_text("Usage: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1)")
        return

    command_text = " ".join(context.args)
    pattern = r"(\d+)\s*for\s*message\s*,\s*(\d+)\s*message\s*(\d+\w*)"
    match = re.match(pattern, command_text, re.IGNORECASE)
    if not match:
        logger.info(f"Invalid /setmessage format by user {admin_id}: {command_text}")
        await update.message.reply_text("Invalid format. Use: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1)")
        return

    count, messages, amount_str = match.groups()
    if int(count) != int(messages):
        logger.info(f"Mismatch in message counts by user {admin_id}: count={count}, messages={messages}")
        await update.message.reply_text("Error: <count> and <messages> must be the same number.")
        return

    try:
        if amount_str.lower().endswith('ks'):
            amount = int(amount_str[:-2]) * 1000
        else:
            amount = int(amount_str)
    except ValueError:
        logger.info(f"Invalid amount format by user {admin_id}: {amount_str}")
        await update.message.reply_text("Invalid amount. Use a number (e.g., 1ks for 1000, or 1 for 1 kyat).")
        return

    global message_reward_rule
    message_reward_rule = {
        "messages_required": int(count),
        "reward_amount": amount
    }
    logger.info(f"Set message reward rule by admin {admin_id}: {message_reward_rule}")

    await update.message.reply_text(
        f"Message reward rule set: {count} messages in group earns {amount} {CURRENCY}."
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=(
            f"Message Reward Rule Set:\n"
            f"Messages Required: {count}\n"
            f"Reward Amount: {amount} {CURRENCY}\n"
            f"Set by Admin: {admin_id}"
        )
    )
    logger.info(f"Logged message reward rule to log channel {LOG_CHANNEL_ID}")

async def count_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text[:50] if update.message.text else "Non-text message"
    logger.info(f"Processing message from user {user_id} in chat {chat_id}: '{message_text}' | GROUP_CHAT_IDS: {GROUP_CHAT_IDS}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Chat {chat_id} not in GROUP_CHAT_IDS for user {user_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Debug: Chat {chat_id} not in GROUP_CHAT_IDS for user {user_id}"
        )
        return

    bot_id = (await context.bot.get_me()).id
    bot_username = (await context.bot.get_me()).username
    try:
        bot_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=bot_id)
        if bot_member.status not in ["member", "administrator", "creator"]:
            logger.error(f"Bot {bot_id} (@{bot_username}) not a member of group {chat_id}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Bot @{bot_username} not in group {chat_id}. Please add it."
            )
            return
        logger.info(f"Bot @{bot_username} is {bot_member.status} in group {chat_id}")
    except Exception as e:
        logger.error(f"Failed to check bot membership in {chat_id}: {str(e)}")
        return

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await context.bot.send_message(
            chat_id=user_id,
            text="Error: Please run /start to register."
        )
        return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        return

    if not message_reward_rule:
        logger.warning(f"No message reward rule set for user {user_id} in {chat_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Error: No message reward rule set for user {user_id} in {chat_id}"
        )
        return

    group_messages = user.get("group_messages", 0) + 1
    balance = int(user.get("balance", 0))
    update_data = {"group_messages": group_messages}
    logger.info(f"User {user_id} message count: {group_messages} (prev: {group_messages-1}), balance: {balance}")

    if group_messages >= message_reward_rule["messages_required"]:
        reward_amount = message_reward_rule["reward_amount"]
        new_balance = balance + reward_amount
        update_data["balance"] = new_balance
        update_data["group_messages"] = 0
        logger.info(f"Applying reward for user {user_id}: {reward_amount} {CURRENCY}, prev balance: {balance}, new balance: {new_balance}")

        try:
            result = db.update_user(user_id, update_data)
            if not result:
                logger.error(f"Failed to update user {user_id}: {update_data}")
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"Error: Failed to update user {user_id} with {update_data}"
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Error: Failed to record reward. Contact support."
                )
                return
            logger.info(f"Reward applied for user {user_id}: group_messages=0, balance={new_balance}")

            await context.bot.send_message(
                chat_id=user_id,
                text=f"Congratulations! You've earned {reward_amount} {CURRENCY} for {message_reward_rule['messages_required']} messages!\nYour new balance is {new_balance} {CURRENCY}."
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"Message Reward Applied:\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{update.effective_user.username or 'N/A'}\n"
                    f"Messages: {group_messages}\n"
                    f"Reward: {reward_amount} {CURRENCY}\n"
                    f"Previous Balance: {balance} {CURRENCY}\n"
                    f"New Balance: {new_balance} {CURRENCY}\n"
                    f"Group: {chat_id}"
                )
            )
            logger.info(f"Notified user {user_id} of reward: {reward_amount} {CURRENCY}")
        except Exception as e:
            logger.error(f"Error applying reward for user {user_id}: {str(e)}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Failed to apply reward for user {user_id}: {str(e)}"
            )
            return
    else:
        try:
            result = db.update_user(user_id, update_data)
            if not result:
                logger.error(f"Failed to update user {user_id}: {update_data}")
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"Error: Failed to update user {user_id} with {update_data}"
                )
                return
            logger.info(f"Updated user {user_id}: group_messages={group_messages}, balance={balance}")
        except Exception as e:
            logger.error(f"Database error for user {user_id}: {str(e)}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Database failure for user {user_id}: {str(e)}"
            )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Balance function called for user {user_id} in chat {chat_id} via {'button' if update.callback_query else 'command'}")

    if update.callback_query:
        await update.callback_query.answer()

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        message = "User not found. Please start with /start."
        if update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return

    balance = int(user.get("balance", 0))
    message = f"Your balance: {balance} {CURRENCY}"
    if update.callback_query:
        await update.callback_query.message.edit_text(message)
    else:
        await update.message.reply_text(message)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        await update.callback_query.answer()

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        message = "Please use the /withdraw command in a private chat."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return ConversationHandler.END

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        message = "User not found. Please start with /start."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        message = "You are banned from using this bot."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return ConversationHandler.END

    balance = int(user.get("balance", 0))
    if balance < WITHDRAWAL_THRESHOLD:
        message = f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw."
        logger.info(f"User {user_id} has insufficient balance: {balance}")
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return ConversationHandler.END

    if str(user_id) not in ADMIN_IDS:
        required_channels = db.get_required_channels() or []
        if required_channels:
            not_subscribed = []
            for channel_id in required_channels:
                if not await check_subscription(context, user_id, channel_id):
                    not_subscribed.append(channel_id)
            if not_subscribed:
                keyboard = []
                for channel_id in not_subscribed:
                    try:
                        chat = await context.bot.get_chat(channel_id)
                        invite_link = await context.bot.export_chat_invite_link(channel_id)
                        keyboard.append([InlineKeyboardButton(f"Join {chat.title}", url=invite_link)])
                    except Exception as e:
                        logger.error(f"Failed to get invite link for {channel_id}: {e}")
                        keyboard.append([InlineKeyboardButton(f"Join Channel {channel_id}", url=f"https://t.me/{channel_id.replace('-100', '')}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = "You must join all required channels to withdraw.\nAfter joining, try again."
                if update.message:
                    await update.message.reply_text(message, reply_markup=reply_markup)
                else:
                    await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
                logger.info(f"User {user_id} not subscribed to channels: {not_subscribed}")
                return ConversationHandler.END

    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        logger.info(f"User {user_id} has a pending withdrawal: {pending_withdrawals}")
        message = "You have a pending withdrawal request. Please wait for it to be processed."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return ConversationHandler.END

    if str(user_id) not in ADMIN_IDS:
        try:
            bot_username = (await context.bot.get_me()).username
            can_withdraw, reason = db.can_withdraw(user_id, bot_username)
            if not can_withdraw:
                logger.info(f"User {user_id} cannot withdraw: {reason}")
                if update.message:
                    await update.message.reply_text(reason, parse_mode="HTML")
                else:
                    await update.callback_query.message.reply_text(reason, parse_mode="HTML")
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error checking withdrawal eligibility for user {user_id}: {str(e)}")
            message = "Error checking eligibility. Please try again later."
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
            return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Please select a payment method:"
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
    logger.info(f"User {user_id} prompted for payment method selection")
    return STEP_PAYMENT_METHOD

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Handling payment method selection for user {user_id}, data: {data}")

    await query.answer()

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
    logger.info(f"User {user_id} selected payment method {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat.\nPlease provide your phone number."
        )
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY})."
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received amount input from user {user_id} in chat {chat_id}: {message.text}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"User {user_id} missing payment method in context")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again."
            )
            return STEP_AMOUNT

        user = db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start again with /start.")
            return ConversationHandler.END

        balance = int(user.get("balance", 0))
        if balance < amount:
            await message.reply_text(
                "Insufficient balance. Please check your balance with /balance."
            )
            return ConversationHandler.END

        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal:
            last_withdrawal_date = last_withdrawal.date()
            current_date = current_time.date()
            if last_withdrawal_date == current_date:
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.info(f"User {user_id} exceeded daily limit. Withdrawn today: {withdrawn_today}")
                    await message.reply_text(
                        f"You've exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}."
                    )
                    return STEP_AMOUNT
            else:
                withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}")

        message_text = f"Please provide your {payment_method} account details."
        await message.reply_text(message_text)
        logger.info(f"User {user_id} prompted for {payment_method} account details")
        return STEP_DETAILS

    except ValueError:
        await message.reply_text("Please enter a valid number (e.g., 100).")
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
        logger.error(f"User {user_id} missing amount or payment_method in context")
        await message.reply_text("Error: Withdrawal amount or payment method not found.")
        return ConversationHandler.END

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await message.reply_text("User not found. Please start again with /start.")
        return ConversationHandler.END

    balance = int(user.get("balance", 0))
    if balance < amount:
        await message.reply_text("Insufficient balance. Please check your balance with /balance.")
        return ConversationHandler.END

    new_balance = balance - amount
    payment_details = message.text if message.text else "No details provided"
    group_message_count = 0

    pending_withdrawal = {
        "amount": amount,
        "payment_method": payment_method,
        "payment_details": payment_details,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc),
        "group_message_count": group_message_count
    }
    result = db.update_user(user_id, {
        "balance": new_balance,
        "pending_withdrawals": [pending_withdrawal]
    })
    if not result:
        logger.error(f"Failed to deduct amount for user {user_id}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    logger.info(f"Deducted {amount} from user {user_id}'s balance. New balance: {new_balance}")
    context.user_data["withdrawal_details"] = payment_details

    user_first_name = user.get("name", update.effective_user.first_name or "Unknown")
    username = update.effective_user.username or user.get("username", "N/A")
    withdrawal_message = (
        f"Withdrawal Request:\n"
        f"User: {user_first_name}\n"
        f"User ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY}\n"
        f"Payment Method: **{payment_method}**\n"
        f"Details: {payment_details}\n"
        f"Invited Users: {user.get('invited_users', 0)}\n"
        f"Status: PENDING"
    )

    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=withdrawal_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        await context.bot.pin_chat_message(
            chat_id=LOG_CHANNEL_ID,
            message_id=log_msg.message_id,
            disable_notification=True
        )
        if 'log_message_ids' not in context.chat_data:
            context.chat_data['log_message_ids'] = {}
        context.chat_data['log_message_ids'][user_id] = log_msg.message_id
        logger.info(f"Sent and pinned withdrawal request for user {user_id}")
    except Exception as e:
        db.update_user(user_id, {
            "balance": balance,
            "pending_withdrawals": []
        })
        logger.error(f"Failed to send withdrawal request to log channel for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    simplified_message = f"@{username} withdrew {amount} {CURRENCY}."
    bot_username = (await context.bot.get_me()).username
    bot_id = (await context.bot.get_me()).id

    for group_id in GROUP_CHAT_IDS:
        try:
            bot_member = await context.bot.get_chat_member(chat_id=group_id, user_id=bot_id)
            if bot_member.status not in ["member", "administrator", "creator"]:
                raise Forbidden(f"Bot is not a member of group {group_id}")
            await context.bot.send_message(
                chat_id=group_id,
                text=simplified_message
            )
            group_message_count += 1
            logger.info(f"Sent withdrawal message to group {group_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to group {group_id} for user {user_id}: {e}")

    pending_withdrawal["group_message_count"] = group_message_count
    db.update_user(user_id, {
        "pending_withdrawals": [pending_withdrawal]
    })
    logger.info(f"Sent withdrawal messages to {group_message_count} groups for user {user_id}")

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. New balance: {new_balance} {CURRENCY}."
    )
    return ConversationHandler.END

async def reset_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Resetwithdraw called by user {admin_id} in chat {chat_id}")

    if admin_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {admin_id} attempted /resetwithdraw")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"User {admin_id} used /resetwithdraw without user_id")
        await update.message.reply_text("Please provide a user ID (e.g., /resetwithdraw 7796351432).")
        return

    target_user_id = context.args[0]
    user = db.get_user(target_user_id)
    if not user:
        logger.error(f"User {target_user_id} not found for resetwithdraw")
        await update.message.reply_text(f"User {target_user_id} not found.")
        return

    pending_withdrawals = user.get("pending_withdrawals", [])
    if not pending_withdrawals:
        logger.info(f"User {target_user_id} has no pending withdrawals")
        await update.message.reply_text(f"User {target_user_id} has no pending withdrawal requests.")
        return

    amount = pending_withdrawals[0]["amount"]
    balance = int(user.get("balance", 0))
    new_balance = balance + amount
    result = db.update_user(target_user_id, {
        "balance": new_balance,
        "pending_withdrawals": []
    })
    if not result:
        logger.error(f"Failed to reset withdrawal for user {target_user_id}")
        await update.message.reply_text(f"Error resetting withdrawal for user {target_user_id}.")
        return

    logger.info(f"Reset withdrawal for user {target_user_id}. Refunded {amount} {CURRENCY}")
    await context.bot.send_message(
        chat_id=target_user_id,
        text=f"Your pending withdrawal of {amount} {CURRENCY} has been reset. New balance: {new_balance} {CURRENCY}."
    )
    await update.message.reply_text(
        f"Successfully reset withdrawal for user {target_user_id}. Refunded {amount} {CURRENCY}."
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=(
            f"Withdrawal Reset:\n"
            f"User ID: {target_user_id}\n"
            f"Amount: {amount} {CURRENCY}\n"
            f"New Balance: {new_balance} {CURRENCY}\n"
            f"Reset by Admin: {admin_id}"
        )
    )

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Admin receipt callback for user {user_id}, data: {data}")

    await query.answer()

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, target_user_id, amount = parts
            amount = int(amount)

            user = db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            result = db.update_user(target_user_id, {
                "pending_withdrawals": [],
                "last_withdrawal": datetime.now(timezone.utc),
                "withdrawn_today": user.get("withdrawn_today", 0) + amount
            })
            if result:
                logger.info(f"Withdrawal approved for user {target_user_id}. Amount: {amount}")
                message_id = context.chat_data.get('log_message_ids', {}).get(target_user_id)
                if message_id:
                    user_first_name = user.get("name", "Unknown")
                    username = user.get("username", "N/A")
                    updated_message = (
                        f"Withdrawal Request:\n"
                        f"User: {user_first_name}\n"
                        f"User ID: {target_user_id}\n"
                        f"Username: @{username}\n"
                        f"Amount: {amount} {CURRENCY}\n"
                        f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                        f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                        f"Status: Approved"
                    )
                    await context.bot.edit_message_text(
                        chat_id=query.message.chat_id,
                        message_id=message_id,
                        text=updated_message,
                        parse_mode="Markdown"
                    )
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Your withdrawal of {amount} {CURRENCY} has been approved!"
                )
                await query.message.reply_text("Approve done")
            else:
                logger.error(f"Failed to clear pending withdrawal for user {target_user_id}")
                await query.message.reply_text("Error approving withdrawal.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, target_user_id, amount = parts
            amount = int(amount)

            user = db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for withdrawal rejection")
                await query.message.reply_text("User not found.")
                return

            balance = int(user.get("balance", 0))
            new_balance = balance + amount
            result = db.update_user(target_user_id, {
                "balance": new_balance,
                "pending_withdrawals": []
            })
            message_id = context.chat_data.get('log_message_ids', {}).get(target_user_id)
            if message_id:
                user_first_name = user.get("name", "Unknown")
                username = user.get("username", "N/A")
                updated_message = (
                    f"Withdrawal Request:\n"
                    f"User: {user_first_name}\n"
                    f"User ID: {target_user_id}\n"
                    f"Username: @{username}\n"
                    f"Amount: {amount} {CURRENCY}\n"
                    f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                    f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                    f"Status: Rejected"
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=message_id,
                    text=updated_message,
                    parse_mode="Markdown"
                )
            logger.info(f"Withdrawal rejected for user {target_user_id}. Amount: {amount}")
            await query.message.reply_text(f"Withdrawal rejected for user {target_user_id}.")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected."
            )

    except Exception as e:
        logger.error(f"Error in handle_admin_receipt for user {user_id}: {str(e)}")
        await query.message.reply_text("Error processing withdrawal request.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the withdrawal process")

    user = db.get_user(user_id)
    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        amount = pending_withdrawals[0]["amount"]
        balance = int(user.get("balance", 0))
        new_balance = balance + amount
        db.update_user(user_id, {
            "balance": new_balance,
            "pending_withdrawals": []
        })
        logger.info(f"Refunded {amount} to user {user_id} on cancellation")
        await update.message.reply_text(
            f"Withdrawal canceled. New balance: {new_balance} {CURRENCY}."
        )
    else:
        await update.message.reply_text("Withdrawal canceled.")

    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^start_withdraw$"),
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^(Cancel|cancel)$"), cancel),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve_withdrawal_|reject_withdrawal_|post_approval_)"))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CallbackQueryHandler(balance, pattern="^check_balance$"))
    application.add_handler(CommandHandler("resetwithdraw", reset_withdraw))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("debug_message_count", debug_message_count))
    application.add_handler(CommandHandler("force_reward", force_reward))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=GROUP_CHAT_IDS), count_group_message))