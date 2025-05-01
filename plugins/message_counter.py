# plugins/message_counter.py
from telegram import Update
from telegram.ext import CallbackContext
from config import PER_MESSAGE_REWARD, SPAM_THRESHOLD, SIMILARITY_THRESHOLD
from database.database import get_user, update_user, log_message, get_chat_group
from difflib import SequenceMatcher
import time
from plugins.force_sub import check_subscription

message_timestamps = {}
last_messages = {}

async def count_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    message_text = update.message.text.lower() if update.message.text else ""

    # Check if the chat group is registered
    chat_group = await get_chat_group(chat_id)
    if not chat_group:
        return

    # Check if user has joined required channels
    if not await check_subscription(update, context):
        return

    # Check message rate (anti-spam)
    current_time = time.time()
    user_key = f"{chat_id}:{user_id}"
    if user_key not in message_timestamps:
        message_timestamps[user_key] = []
    message_timestamps[user_key].append(current_time)
    message_timestamps[user_key] = [t for t in message_timestamps[user_key] if current_time - t < 60]

    if len(message_timestamps[user_key]) > SPAM_THRESHOLD:
        await update.message.delete()
        await context.bot.send_message(chat_id=chat_id, text=f"@{update.effective_user.username} စာပို့တာ အရမ်းများနေပါတယ်။ နှေးနှေးပို့ပါ။")
        return

    # Check for similar messages (anti-spam)
    if user_key in last_messages:
        similarity = SequenceMatcher(None, last_messages[user_key], message_text).ratio()
        if similarity > SIMILARITY_THRESHOLD:
            await update.message.delete()
            await context.bot.send_message(chat_id=chat_id, text=f"@{update.effective_user.username} တူညီတဲ့ စာများ မပို့ပါနဲ့။")
            return

    last_messages[user_key] = message_text

    # Log message and reward user
    await log_message(user_id, chat_id, message_text, current_time)
    user = await get_user(user_id, chat_id)
    balance = user.get("balance", 0) + PER_MESSAGE_REWARD if user else PER_MESSAGE_REWARD
    await update_user(user_id, chat_id, {"balance": balance})

    # Notify user every 10 messages
    if balance % 10 == 0:
        await context.bot.send_message(chat_id=chat_id, text=f"@{update.effective_user.username} သင့်မှာ {balance} ကျပ် ရှိပါတယ်။")