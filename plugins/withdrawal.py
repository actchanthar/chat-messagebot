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
    balance = int(user.get("balance", 0))  # Cast to int
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
        await update.message.reply_text("Usage: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1ks)")
        return

    command_text = " ".join(context.args)
    pattern = r"(\d+)\s*for\s*message\s*,\s*(\d+)\s*message\s*(\d+\w*)"
    match = re.match(pattern, command_text, re.IGNORECASE)
    if not match:
        logger.info(f"Invalid /setmessage format by user {admin_id}: {command_text}")
        await update.message.reply_text("Invalid format. Use: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1ks)")
        return

    count, messages, amount_str = match.groups()
    if int(count) != int(messages):
        logger.info(f"Mismatch in message counts by user {admin_id}: count={count}, messages={messages}")
        await update.message.reply_text("Error: <count> and <messages> must be the same number.")
        return

    try:
        # Handle 'ks' for thousands, otherwise treat as literal amount
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
    balance = int(user.get("balance", 0))  # Cast to int
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