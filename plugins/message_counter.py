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

    chat_group = await get_chat_group(chat_id)
    if not chat_group:
        return

    if not await check_subscription(update, context):
        return

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

    if user_key in last_messages:
        similarity = SequenceMatcher(None, last_messages[user_key], message_text).ratio()
        if similarity > SIMILARITY_THRESHOLD:
            await update.message.delete()
            await context.bot.send_message(chat_id=chat_id, text=f"@{update.effective_user.username} တူညီတဲ့ စာများ မပို့ပါနဲ့။")
            return

    last_messages[user_key] = message_text

    await log_message(user_id, chat_id, message_text, current_time)
    user = await get_user(user_id, chat_id)
    balance = user.get("balance", 0) + PER_MESSAGE_REWARD if user else PER_MESSAGE_REWARD
    await update_user(user_id, chat_id, {"balance": balance})

    # Notify user in the group every 10 messages
    if balance % 10 == 0:
        await context.bot.send_message(chat_id=chat_id, text=f"@{update.effective_user.username} သင့်မှာ {balance} ကျပ် ရှိပါတယ်။")
        # Notify the admins who added the group
        admin_ids = chat_group.get("admin_ids", [])
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📊 User @{update.effective_user.username} (ID: {user_id}) reached {balance} ကျပ် in group {chat_id}"
                )
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")