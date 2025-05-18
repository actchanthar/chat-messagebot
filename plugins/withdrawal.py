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

# Temporary in-memory storage for message reward rule (replace with db.set_config if available)
message_reward_rule = {}

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        bot_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        bot_is_admin = bot_member.status in ["administrator", "creator"]
        if not bot_is_admin:
            logger.error(f"Bot is not an admin in channel {channel_id}. Bot status: {bot_member.status}")
            return False
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        logger.info(f"User {user_id} subscription check for channel {channel_id}: status={member.status}, is_member={is_member}")
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
        return False

async def debug_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Debug_message_count called by user {user_id} in chat {chat_id}")

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database for debug")
        try:
            await update.message.reply_text("Error: User not found in database. Please run /start.")
        except Exception as e:
            logger.error(f"Failed to send user not found message to {user_id}: {e}")
        return

    group_messages = user.get("group_messages", 0)
    balance = user.get("balance", 0)
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

    try:
        await update.message.reply_text(debug_message)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Debug Message Count by {user_id}:\n{debug_message}"
        )
        logger.info(f"Sent debug info for user {user_id} to chat {chat_id} and log channel")
    except Exception as e:
        logger.error(f"Failed to send debug info for user {user_id}: {str(e)}")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Setmessage called by user {admin_id} in chat {chat_id}")

    if admin_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {admin_id} attempted /setmessage")
        try:
            await update.message.reply_text("You are not authorized to use this command.")
        except Exception as e:
            logger.error(f"Failed to send unauthorized message to {admin_id}: {e}")
        return

    if not context.args:
        logger.info(f"User {admin_id} used /setmessage without arguments")
        try:
            await update.message.reply_text("Usage: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1ks)")
        except Exception as e:
            logger.error(f"Failed to send usage message to {admin_id}: {e}")
        return

    command_text = " ".join(context.args)
    pattern = r"(\d+)\s*for\s*message\s*,\s*(\d+)\s*message\s*(\d+\w*)"
    match = re.match(pattern, command_text, re.IGNORECASE)
    if not match:
        logger.info(f"Invalid /setmessage format by user {admin_id}: {command_text}")
        try:
            await update.message.reply_text("Invalid format. Use: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1ks)")
        except Exception as e:
            logger.error(f"Failed to send invalid format message to {admin_id}: {e}")
        return

    count, messages, amount_str = match.groups()
    if int(count) != int(messages):
        logger.info(f"Mismatch in message counts by user {admin_id}: count={count}, messages={messages}")
        try:
            await update.message.reply_text("Error: <count> and <messages> must be the same number.")
        except Exception as e:
            logger.error(f"Failed to send mismatch message to {admin_id}: {e}")
        return

    try:
        amount = int(amount_str.replace("ks", "000").replace("k", "000"))
    except ValueError:
        logger.info(f"Invalid amount format by user {admin_id}: {amount_str}")
        try:
            await update.message.reply_text("Invalid amount. Use a number (e.g., 1ks for 1000, or 1000).")
        except Exception as e:
            logger.error(f"Failed to send invalid amount message to {admin_id}: {e}")
        return

    global message_reward_rule
    message_reward_rule = {
        "messages_required": int(count),
        "reward_amount": amount
    }
    # TODO: Replace with db.set_config("message_reward_rule", message_reward_rule) if db supports it
    logger.info(f"Set message reward rule by admin {admin_id}: {message_reward_rule}")

    try:
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
    except Exception as e:
        logger.error(f"Failed to send confirmation or log message for /setmessage by {admin_id}: {e}")

async def count_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text[:50] if update.message.text else "Non-text message"
    logger.info(f"Received message from user {user_id} in chat {chat_id}: '{message_text}' | GROUP_CHAT_IDS: {GROUP_CHAT_IDS}")

    # Check if chat is in GROUP_CHAT_IDS
    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Chat {chat_id} not in GROUP_CHAT_IDS. Ignoring message from user {user_id}.")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Debug: Chat {chat_id} not in GROUP_CHAT_IDS for user {user_id}. GROUP_CHAT_IDS: {GROUP_CHAT_IDS}"
            )
        except Exception as e:
            logger.error(f"Failed to log GROUP_CHAT_IDS mismatch to {LOG_CHANNEL_ID}: {e}")
        return

    # Verify bot is a member of the group
    bot_id = (await context.bot.get_me()).id
    bot_username = (await context.bot.get_me()).username
    try:
        bot_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=bot_id)
        if bot_member.status not in ["member", "administrator", "creator"]:
            logger.error(f"Bot {bot_id} (@{bot_username}) is not a member of group {chat_id}. Status: {bot_member.status}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Bot @{bot_username} is not a member of group {chat_id} (status: {bot_member.status}). Please add it to count messages."
            )
            return
        logger.info(f"Bot @{bot_username} is {bot_member.status} in group {chat_id}")
    except Exception as e:
        logger.error(f"Failed to check bot membership in group {chat_id}: {str(e)}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Error: Cannot verify bot membership in group {chat_id} for user {user_id}: {str(e)}"
        )
        return

    # Check user in database
    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Error: You are not registered. Please run /start to register."
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: User {user_id} (@{update.effective_user.username or 'N/A'}) not found in database while counting message in group {chat_id}."
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} or log user not found: {e}")
        return

    # Check if user is banned
    if user.get("banned", False):
        logger.info(f"User {user_id} is banned, ignoring message in group {chat_id}")
        return

    # Check message reward rule
    if not message_reward_rule:
        logger.warning(f"No message reward rule set for user {user_id} in group {chat_id}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Warning: No message reward rule set while processing message from user {user_id} in group {chat_id}."
            )
        except Exception as e:
            logger.error(f"Failed to log missing reward rule to {LOG_CHANNEL_ID}: {e}")
        return

    # Increment message count
    group_messages = user.get("group_messages", 0) + 1
    balance = user.get("balance", 0)
    update_data = {"group_messages": group_messages}
    logger.info(f"User {user_id} message count incremented to {group_messages} in group {chat_id} (previous: {group_messages-1})")

    # Apply reward if applicable
    if group_messages >= message_reward_rule["messages_required"]:
        reward_amount = message_reward_rule["reward_amount"]
        balance += reward_amount
        update_data["balance"] = balance
        update_data["group_messages"] = 0  # Reset message count
        logger.info(f"User {user_id} reached {group_messages} messages, earning {reward_amount} {CURRENCY}")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Congratulations! You've earned {reward_amount} {CURRENCY} for sending {message_reward_rule['messages_required']} messages in the group!\n"
                    f"ဂုဏ်ယူပါသည်။ အုပ်စုတွင် မက်ဆေ့ချ် {message_reward_rule['messages_required']} စောင်ပို့ခြင်းဖြင့် {reward_amount} {CURRENCY} ရရှိခဲ့ပါသည်။"
                )
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"Message Reward:\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{update.effective_user.username or 'N/A'}\n"
                    f"Messages Sent: {group_messages}\n"
                    f"Reward: {reward_amount} {CURRENCY}\n"
                    f"New Balance: {balance} {CURRENCY}\n"
                    f"Group: {chat_id}"
                )
            )
            logger.info(f"Notified user {user_id} and logged reward of {reward_amount} {CURRENCY} in group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} or log reward: {str(e)}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Failed to notify user {user_id} or log reward in group {chat_id}: {str(e)}"
            )

    # Update database
    try:
        result = db.update_user(user_id, update_data)
        if not result:
            logger.error(f"Failed to update user {user_id} with data {update_data} in group {chat_id}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Failed to update user {user_id} message count or balance in group {chat_id}. Data: {update_data}"
            )
            await context.bot.send_message(
                chat_id=user_id,
                text="Error: Failed to record your message. Please try again or contact support."
            )
        else:
            logger.info(f"Successfully updated user {user_id}: group_messages={group_messages}, balance={balance} in group {chat_id}")
    except Exception as e:
        logger.error(f"Database error updating user {user_id} in group {chat_id}: {str(e)}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Error: Database failure updating user {user_id} in group {chat_id}: {str(e)}"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="Error: Database issue while recording your message. Please try again or contact support."
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Balance function called for user {user_id} in chat {chat_id} via {'button' if update.callback_query else 'command'}")

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as e:
            logger.warning(f"Failed to answer balance query for user {user_id}: {e}")

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        message = "User not found. Please start with /start."
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send user not found message to {user_id}: {e}")
        return

    balance = user.get("balance", 0)
    message = f"Your balance: {balance} {CURRENCY}"
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(message)
        else:
            await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Failed to send balance message to user {user_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=message)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as e:
            logger.warning(f"Failed to answer withdraw query for user {user_id}: {e}")

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        message = "Please use the /withdraw command in a private chat."
        try:
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send private chat message to {user_id}: {e}")
        return ConversationHandler.END

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        message = "User not found. Please start with /start."
        try:
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send user not found message to {user_id}: {e}")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        message = "You are banned from using this bot."
        try:
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send banned message to {user_id}: {e}")
        return ConversationHandler.END

    balance = user.get("balance", 0)
    if balance < WITHDRAWAL_THRESHOLD:
        message = f"Your balance is {balance} {CURRENCY}. You need at least {WITHDRAWAL_THRESHOLD} {CURRENCY} to withdraw."
        logger.info(f"User {user_id} has insufficient balance: {balance}")
        try:
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send insufficient balance message to {user_id}: {e}")
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
                try:
                    if update.message:
                        await update.message.reply_text(message, reply_markup=reply_markup)
                    else:
                        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Failed to send subscription message to {user_id}: {e}")
                logger.info(f"User {user_id} not subscribed to channels: {not_subscribed}")
                return ConversationHandler.END

    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        logger.info(f"User {user_id} has a pending withdrawal: {pending_withdrawals}")
        message = ("You have a pending withdrawal request. Please wait for it to be processed before requesting another.\n"
                   "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်တောင်းဆိုမှုရှိပါသည်။ နောက်တစ်ကြိမ်တောင်းဆိုခြင်းမပြုမီ ပြီးစီးရန်စောင့်ပါ�।")
        try:
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
        except Exception as e:
            logger.error(f"Failed to send pending withdrawal message to {user_id}: {e}")
        return ConversationHandler.END

    if str(user_id) not in ADMIN_IDS:
        try:
            bot_username = (await context.bot.get_me()).username
            can_withdraw, reason = db.can_withdraw(user_id, bot_username)
            logger.info(f"can_withdraw for user {user_id}: can_withdraw={can_withdraw}, reason={reason}")
            if not can_withdraw:
                logger.info(f"User {user_id} cannot withdraw: {reason}")
                try:
                    if update.message:
                        await update.message.reply_text(reason, parse_mode="HTML")
                    else:
                        await update.callback_query.message.reply_text(reason, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Failed to send withdrawal reason to {user_id}: {str(e)}")
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error checking withdrawal eligibility for user {user_id}: {str(e)}", exc_info=True)
            message = "Error checking eligibility. Please try again later or contact support."
            try:
                if update.message:
                    await update.message.reply_text(message)
                else:
                    await update.callback_query.message.reply_text(message)
            except Exception as e:
                logger.error(f"Failed to send eligibility error to {user_id}: {str(e)}")
            return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။"
    try:
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send payment method prompt to {user_id}: {e}")
        return ConversationHandler.END
    logger.info(f"User {user_id} prompted for payment method selection with buttons: {PAYMENT_METHODS}")
    return STEP_PAYMENT_METHOD

async def reset_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Resetwithdraw called by user {admin_id} in chat {chat_id}")

    if admin_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {admin_id} attempted /resetwithdraw")
        try:
            await update.message.reply_text("You are not authorized to use this command.")
        except Exception as e:
            logger.error(f"Failed to send unauthorized message to {admin_id}: {e}")
        return

    if not context.args:
        logger.info(f"User {admin_id} used /resetwithdraw without user_id")
        try:
            await update.message.reply_text("Please provide a user ID (e.g., /resetwithdraw 7796351432).")
        except Exception as e:
            logger.error(f"Failed to send missing user_id message to {admin_id}: {e}")
        return

    target_user_id = context.args[0]
    user = db.get_user(target_user_id)
    if not user:
        logger.error(f"User {target_user_id} not found for resetwithdraw")
        try:
            await update.message.reply_text(f"User {target_user_id} not found.")
        except Exception as e:
            logger.error(f"Failed to send user not found message to {admin_id}: {e}")
        return

    pending_withdrawals = user.get("pending_withdrawals", [])
    if not pending_withdrawals:
        logger.info(f"User {target_user_id} has no pending withdrawals")
        try:
            await update.message.reply_text(f"User {target_user_id} has no pending withdrawal requests.")
        except Exception as e:
            logger.error(f"Failed to send no pending withdrawals message to {admin_id}: {e}")
        return

    amount = pending_withdrawals[0]["amount"]
    balance = user.get("balance", 0)
    new_balance = balance + amount
    result = db.update_user(target_user_id, {
        "balance": new_balance,
        "pending_withdrawals": []
    })
    if not result:
        logger.error(f"Failed to reset withdrawal for user {target_user_id}")
        try:
            await update.message.reply_text(f"Error resetting withdrawal for user {target_user_id}. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send reset error message to {admin_id}: {e}")
        return

    logger.info(f"Reset withdrawal for user {target_user_id}. Refunded {amount} {CURRENCY}. New balance: {new_balance}")
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"Your pending withdrawal request of {amount} {CURRENCY} has been reset by an admin. "
                f"The amount has been refunded to your balance. Your new balance is {new_balance} {CURRENCY}.\n"
                f"သင့်ဆိုင်းငံ့ထားသော ငွေထုတ်တောင်းဆိုမှု {amount} {CURRENCY} ကို အုပ်ချုပ်ရေးမှူးမှ ပြန်လည်သတ်မှတ်လိုက်ပါသည်။ "
                f"ပမာဏကို သင့်လက်ကျန်သို့ ပြန်လည်ထည့်သွင်းပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
            )
        )
        logger.info(f"Notified user {target_user_id} of withdrawal reset")
    except Exception as e:
        logger.error(f"Failed to notify user {target_user_id} of withdrawal reset: {e}")

    try:
        await update.message.reply_text(
            f"Successfully reset withdrawal for user {target_user_id}. Refunded {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}."
        )
    except Exception as e:
        logger.error(f"Failed to send reset confirmation to admin {admin_id}: {e}")

    try:
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
        logger.info(f"Logged withdrawal reset for user {target_user_id} to log channel {LOG_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Failed to log withdrawal reset to {LOG_CHANNEL_ID}: {e}")

async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Handling payment method selection for user {user_id}, data: {data}")

    try:
        await query.answer()
    except BadRequest as e:
        logger.warning(f"Failed to answer payment method query for user {user_id}: {e}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback data for user {user_id}: {data}")
        try:
            await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send invalid method message to {user_id}: {e}")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        try:
            await query.message.reply_text("Invalid payment method selected. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send invalid method message to {user_id}: {e}")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        try:
            await query.message.reply_text(
                "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
                "Please provide your phone number for Phone Bill payment. 💳\n"
                "ကျေးဇူးပြု၍ ဖုန်းဘေလ်ငွေပေးချေမှုအတွက် သင့်ဖုန်းနံပါတ်ကို ပေးပါ။"
            )
        except Exception as e:
            logger.error(f"Failed to send phone bill prompt to {user_id}: {e}")
            return ConversationHandler.END
        logger.info(f"User {user_id} selected Phone Bill, fixed amount to 1000 kyat")
        return STEP_DETAILS

    try:
        await query.message.reply_text(
            f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
            f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
        )
    except Exception as e:
        logger.error(f"Failed to send amount prompt to {user_id}: {e}")
        return ConversationHandler.END
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received amount input from user {user_id} in chat {chat_id}: {message.text}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"User {user_id} missing payment method in context")
        try:
            await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send payment method error to {user_id}: {e}")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            try:
                await message.reply_text(
                    f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                    f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
                )
            except Exception as e:
                logger.error(f"Failed to send minimum amount message to {user_id}: {e}")
            return STEP_AMOUNT

        user = db.get_user(user_id)
        if not user:
            try:
                await message.reply_text("User not found. Please start again with /start.")
            except Exception as e:
                logger.error(f"Failed to send user not found message to {user_id}: {e}")
            return ConversationHandler.END

        balance = user.get("balance", 0)
        if balance < amount:
            try:
                await message.reply_text(
                    "Insufficient balance. Please check your balance with /balance.\n"
                    "လက်ကျန်ငွေ မလုံလောက်ပါ။ ကျေးဇူးပြု၍ သင့်လက်ကျန်ငွေကို /balance ဖြင့် စစ်ဆေးပါ။"
                )
            except Exception as e:
                logger.error(f"Failed to send insufficient balance message to {user_id}: {e}")
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
                    try:
                        await message.reply_text(
                            f"You've exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. "
                            f"You've already withdrawn {withdrawn_today} {CURRENCY} today.\n"
                            f"သင်သည် နေ့စဉ်ထုတ်ယူနိုင်မှု ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ကို ကျော်လွန်သွားပါသည်။ "
                            f"သင်သည် ယနေ့အတွက် {withdrawn_today} {CURRENCY} ထုတ်ယူပြီးပါသည်။"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send daily limit message to {user_id}: {e}")
                    return STEP_AMOUNT
            else:
                withdrawn_today = 0

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}")

        if payment_method == "KBZ Pay":
            message_text = (
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW). 💳\n"
                "ကျေးဇူးပြု၍ သင့် KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။"
            )
        elif payment_method == "Wave Pay":
            message_text = (
                "Please provide your Wave Pay account details (e.g., phone number and name). 💳\n"
                "ကျေးဇူးပြု၍ သင့် Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ ဖုန်းနံပါတ်နှင့် နာမည်)။"
            )
        else:
            message_text = (
                f"Please provide your {payment_method} account details. 💳\n"
                f"ကျေးဇူးပြု၍ {payment_method} အကောင့်အသေးစိတ်ကို ပေးပါ။"
            )
        try:
            await message.reply_text(message_text)
        except Exception as e:
            logger.error(f"Failed to send payment details prompt to {user_id}: {e}")
            return ConversationHandler.END
        logger.info(f"User {user_id} prompted for {payment_method} account details")
        return STEP_DETAILS

    except ValueError:
        try:
            await message.reply_text(
                "Please enter a valid number (e.g., 100).\n"
                "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
            )
        except Exception as e:
            logger.error(f"Failed to send invalid number message to {user_id}: {e}")
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
        try:
            await message.reply_text("Error: Withdrawal amount or payment method not found. Please start again with /withdraw.")
        except Exception as e:
            logger.error(f"Failed to send context error to {user_id}: {e}")
        return ConversationHandler.END

    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        try:
            await message.reply_text("User not found. Please start again with /start.")
        except Exception as e:
            logger.error(f"Failed to send user not found message to {user_id}: {e}")
        return ConversationHandler.END

    balance = user.get("balance", 0)
    if balance < amount:
        try:
            await message.reply_text(
                "Insufficient balance. Please check your balance with /balance.\n"
                "လက်ကျန်ငွေ မလုံလောက်ပါ။ ကျေးဇူးပြု၍ သင့်လက်ကျန်ငွေကို /balance ဖြင့် စစ်ဆေးပါ။"
            )
        except Exception as e:
            logger.error(f"Failed to send insufficient balance message to {user_id}: {e}")
        return ConversationHandler.END

    new_balance = balance - amount
    payment_details = message.text if message.text else "No details provided"
    group_message_count = 0  # Counter for successful group messages

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
        logger.error(f"Failed to deduct amount for user {user_id} during withdrawal request")
        try:
            await message.reply_text("Error submitting request. Please try again later.")
        except Exception as e:
            logger.error(f"Failed to send deduction error to {user_id}: {e}")
        return ConversationHandler.END

    logger.info(f"Deducted {amount} from user {user_id}'s balance. New balance: {new_balance}")
    context.user_data["withdrawal_details"] = payment_details
    logger.info(f"User {user_id} submitted account details")

    user_first_name = user.get("name", update.effective_user.first_name or "Unknown")
    username = update.effective_user.username or user.get("username", "N/A")
    withdrawal_message = (
        f"Withdrawal Request:\n"
        f"User: {user_first_name}\n"
        f"User ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY} 💸\n"
        f"Payment Method: **{payment_method}**\n"
        f"Details: {payment_details}\n"
        f"Invited Users: {user.get('invited_users', 0)}\n"
        f"Status: PENDING ⏳"
    )

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
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
        logger.info(f"Sent and pinned withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id} with message ID {log_msg.message_id}")
    except Exception as e:
        db.update_user(user_id, {
            "balance": balance,
            "pending_withdrawals": []
        })
        logger.error(f"Failed to send or pin withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
        try:
            await message.reply_text("Error submitting request. Please try again later.")
        except Exception as e:
            logger.error(f"Failed to send log channel error to {user_id}: {e}")
        return ConversationHandler.END

    simplified_message = f"@{username} သည် ငွေ {amount} {CURRENCY} ထုတ်ယူခဲ့သည်။"
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
            logger.info(f"Sent simplified withdrawal message to group {group_id} for user {user_id}")
        except Forbidden as e:
            logger.error(f"Failed to send simplified message to group {group_id} for user {user_id}: {e}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Warning: Bot is not a member of group {group_id}. Please add @{bot_username} as a member/admin to send withdrawal messages."
            )
        except TelegramError as e:
            logger.error(f"Failed to send simplified message to group {group_id} for user {user_id}: {e}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Warning: Failed to send simplified message to group {group_id} for user {user_id}: {e}"
            )

    pending_withdrawal["group_message_count"] = group_message_count
    db.update_user(user_id, {
        "pending_withdrawals": [pending_withdrawal]
    })
    logger.info(f"Sent withdrawal messages to {group_message_count} groups for user {user_id}")

    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Withdrawal notification for user {user_id} sent to {group_message_count}/{len(GROUP_CHAT_IDS)} groups."
        )
    except Exception as e:
        logger.error(f"Failed to log group message count to {LOG_CHANNEL_ID} for user {user_id}: {e}")

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=simplified_message
        )
        logger.info(f"Sent simplified withdrawal message as DM to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send simplified DM to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Warning: Failed to send simplified DM to user {user_id}: {e}"
        )

    try:
        await message.reply_text(
            f"Your withdrawal request for {amount} {CURRENCY} has been submitted. The amount has been deducted from your balance and will be processed by an admin. Your new balance is {new_balance} {CURRENCY}. Notification sent to {group_message_count} group(s). ⏳\n"
            f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ပမာဏကို သင့်လက်ကျန်မှ နုတ်ယူလိုက်ပြီး အုပ်ချုပ်ရေးမှူးမှ ဆောင်ရွက်ပေးပါမည်။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။ အုပ်စုပေါင်း {group_message_count} ခုသို့ အကြောင်းကြားပြီးပါပြီ။"
        )
    except Exception as e:
        logger.error(f"Failed to send confirmation message to {user_id}: {e}")
        return ConversationHandler.END

    logger.info(f"User {user_id} submitted withdrawal request for {amount} {CURRENCY}, notified {group_message_count} groups")
    return ConversationHandler.END

async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Admin receipt callback for user {user_id}, data: {data}")

    try:
        await query.answer()
    except BadRequest as e:
        logger.warning(f"Failed to answer admin receipt query for user {user_id}: {e}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                try:
                    await query.message.reply_text("Error processing withdrawal request.")
                except Exception as e:
                    logger.error(f"Failed to send error message to admin {user_id}: {e}")
                return
            _, _, target_user_id, amount = parts
            amount = int(amount)

            user = db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for withdrawal approval")
                try:
                    await query.message.reply_text("User not found.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to admin {user_id}: {e}")
                return

            result = db.update_user(target_user_id, {
                "pending_withdrawals": [],
                "last_withdrawal": datetime.now(timezone.utc),
                "withdrawn_today": user.get("withdrawn_today", 0) + amount
            })
            logger.info(f"db.update_user returned: {result}")

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
                        f"Amount: {amount} {CURRENCY} 💸\n"
                        f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                        f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                        f"Invited Users: {user.get('invited_users', 0)}\n"
                        f"Status: Approved ✅"
                    )
                    try:
                        await context.bot.edit_message_text(
                            chat_id=query.message.chat_id,
                            message_id=message_id,
                            text=updated_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"Updated message {message_id} to 'Approved' for user {target_user_id}")
                    except Exception as e:
                        logger.error(f"Failed to edit message {message_id} for user {target_user_id}: {e}")

                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=f"Your withdrawal of {amount} {CURRENCY} has been approved!\n"
                             f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။"
                    )
                    logger.info(f"Notified user {target_user_id} of withdrawal approval")
                except Exception as e:
                    logger.error(f"Failed to notify user {target_user_id} of withdrawal approval: {e}")

                try:
                    await query.message.reply_text("Approve done ✅")
                except Exception as e:
                    logger.error(f"Failed to send approval confirmation to admin {user_id}: {e}")
                logger.info(f"Confirmed approval to admin for user {target_user_id}")

            else:
                logger.error(f"Failed to clear pending withdrawal for user {target_user_id}. Result: {result}")
                try:
                    await query.message.reply_text("Error approving withdrawal. Please try again.")
                except Exception as e:
                    logger.error(f"Failed to send approval error to admin {user_id}: {e}")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                try:
                    await query.message.reply_text("Error processing withdrawal request.")
                except Exception as e:
                    logger.error(f"Failed to send error message to admin {user_id}: {e}")
                return
            _, _, target_user_id, amount = parts
            amount = int(amount)

            user = db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for withdrawal rejection")
                try:
                    await query.message.reply_text("User not found.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to admin {user_id}: {e}")
                return

            balance = user.get("balance", 0)
            new_balance = balance + amount
            result = db.update_user(target_user_id, {
                "balance": new_balance,
                "pending_withdrawals": []
            })
            logger.info(f"db.update_user returned: {result} for user {target_user_id} on rejection")

            message_id = context.chat_data.get('log_message_ids', {}).get(target_user_id)
            if message_id:
                user_first_name = user.get("name", "Unknown")
                username = user.get("username", "N/A")
                updated_message = (
                    f"Withdrawal Request:\n"
                    f"User: {user_first_name}\n"
                    f"User ID: {target_user_id}\n"
                    f"Username: @{username}\n"
                    f"Amount: {amount} {CURRENCY} 💸\n"
                    f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                    f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                    f"Invited Users: {user.get('invited_users', 0)}\n"
                    f"Status: Rejected ❌"
                )
                try:
                    await context.bot.edit_message_text(
                        chat_id=query.message.chat_id,
                        message_id=message_id,
                        text=updated_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Updated message {message_id} to 'Rejected' for user {target_user_id}")
                except Exception as e:
                    logger.error(f"Failed to edit message {message_id} for user {target_user_id}: {e}")

            logger.info(f"Withdrawal rejected for user {target_user_id}. Amount: {amount}, Refunded balance: {new_balance}")
            try:
                await query.message.reply_text(f"Withdrawal rejected for user {target_user_id}. Amount: {amount} {CURRENCY}.")
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected by the admin. The amount has been refunded to your balance. Your new balance is {new_balance} {CURRENCY}. If there are any problems or you wish to appeal, please contact @actanibot.\n"
                         f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို အုပ်ချုပ်ရေးမှူးမှ ပယ်ချလိုက်ပါသည်။ ပမာဏကို သင့်လက်ကျန်သို့ ပြန်လည်ထည့်သွင်းပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။ ပြဿနာများရှိပါက သို့မဟုတ် အယူခံဝင်လိုပါက @actanibot သို့ ဆက်သွယ်ပါ။"
                )
                logger.info(f"Notified user {target_user_id} of withdrawal rejection")
            except Exception as e:
                logger.error(f"Failed to notify user {target_user_id} of withdrawal rejection: {e}")

        elif data.startswith("post_approval_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                try:
                    await query.message.reply_text("Error processing approval post.")
                except Exception as e:
                    logger.error(f"Failed to send error message to admin {user_id}: {e}")
                return
            _, _, target_user_id, amount = parts
            amount = int(amount)

            user = db.get_user(target_user_id)
            if not user:
                logger.error(f"User {target_user_id} not found for approval post")
                try:
                    await query.message.reply_text("User not found.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to admin {user_id}: {e}")
                return

            username = user.get("username", user.get("name", "Unknown"))
            mention = f"@{username}" if username and not username.isdigit() else user["name"]
            group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"

            try:
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_IDS[0],
                    text=group_message
                )
                await query.message.reply_text(f"Posted withdrawal announcement to group {GROUP_CHAT_IDS[0]}.")
                logger.info(f"Sent withdrawal announcement to group {GROUP_CHAT_IDS[0]} for user {target_user_id}")
            except Exception as e:
                logger.error(f"Failed to send group announcement for user {target_user_id}: {e}")
                try:
                    await query.message.reply_text("Failed to post to group. Please try again.")
                except Exception as e:
                    logger.error(f"Failed to send group post error to admin {user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in handle_admin_receipt for user {user_id}: {str(e)}", exc_info=True)
        try:
            await query.message.reply_text("Error processing withdrawal request. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send error message to admin {user_id}: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the withdrawal process")

    user = db.get_user(user_id)
    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        amount = pending_withdrawals[0]["amount"]
        balance = user.get("balance", 0)
        new_balance = balance + amount
        db.update_user(user_id, {
            "balance": new_balance,
            "pending_withdrawals": []
        })
        logger.info(f"Refunded {amount} to user {user_id} on cancellation. New balance: {new_balance}")
        try:
            await update.message.reply_text(
                f"Withdrawal canceled. The amount has been refunded to your balance. Your new balance is {new_balance} {CURRENCY}.\n"
                f"ငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။ ပမာဏကို သင့်လက်ကျန်သို့ ပြန်လညထည့်သွင်းပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
            )
        except Exception as e:
            logger.error(f"Failed to send cancellation message to {user_id}: {e}")
    else:
        try:
            await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်�।")
        except Exception as e:
            logger.error(f"Failed to send cancellation message to {user_id}: {e}")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=GROUP_CHAT_IDS), count_group_message))