from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import GROUP_CHAT_IDS, CURRENCY, LOG_CHANNEL_ID, ADMIN_IDS
from database.database import db
import logging
import re

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def load_message_reward_rule():
    settings = db.get_bot_settings()
    return settings.get("message_reward_rule", {})

message_reward_rule = load_message_reward_rule()

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Setmessage called by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.info(f"Non-admin user {user_id} attempted /setmessage")
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <count> for message , <messages> message <amount> (e.g., /setmessage 3 for message , 3 message 1)")
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
    db.update_bot_settings({"message_reward_rule": message_reward_rule})
    logger.info(f"Set message reward rule by admin {user_id}: {message_reward_rule}")

    await update.message.reply_text(
        f"Rule set: {count} messages earns {amount} {CURRENCY}."
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Rule Set:\nMessages: {count}\nReward: {amount} {CURRENCY}\nBy Admin: {user_id}"
    )

async def reset_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Reset_messages called by user {user_id} in chat {chat_id}")

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
        await update.message.reply_text(f"Error resetting messages for user {target_user_id}.")
        return

    await update.message.reply_text(f"Reset message count for user {target_user_id}.")
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Message Count Reset:\nUser ID: {target_user_id}\nBy Admin: {user_id}"
    )

async def count_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text[:50] if update.message.text else "Non-text message"
    logger.info(f"Message from user {user_id} in chat {chat_id}: '{message_text}'")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Chat {chat_id} not in GROUP_CHAT_IDS")
        return

    user = db.get_user(user_id)
    if not user:
        await context.bot.send_message(
            chat_id=user_id,
            text="Please run /start to register."
        )
        return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        return

    if not message_reward_rule:
        logger.warning(f"No reward rule for user {user_id} in {chat_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"No reward rule set for user {user_id} in {chat_id}"
        )
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
            logger.error(f"Failed to update user {user_id}: {update_data}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Failed to update user {user_id}"
            )
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
            logger.error(f"Failed to update user {user_id}: {update_data}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error: Failed to update user {user_id}"
            )

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

    debug_message = (
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
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Debug by {user_id}:\n{debug_message}"
    )

def register_handlers(application: Application):
    logger.info("Registering handlers")
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("reset_messages", reset_messages))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("debug_message_count", debug_message_count))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=GROUP_CHAT_IDS), count_group_message))