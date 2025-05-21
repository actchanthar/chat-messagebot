from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
from utils.rate_limiter import send_messages_batch
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, pin=False):
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users found.")
        return

    # Prepare messages for batch sending
    messages = [
        (user["user_id"], message, {"parse_mode": "HTML"} if pin else {})
        for user in users
    ]

    # Send messages in batches
    await send_messages_batch(context.bot, messages, batch_size=30, delay=1)

    success_count = len([m for m in messages if m[0]])  # Approximate success count
    await update.message.reply_text(f"Sent to ~{success_count} users.")

    # Pin messages if pbroadcast
    if pin:
        pin_tasks = []
        for user in users:
            try:
                msg = await send_message_rate_limited(
                    context.bot,
                    user["user_id"],
                    message,
                    parse_mode="HTML"
                )
                if msg:
                    pin_tasks.append(
                        context.bot.pin_chat_message(
                            user["user_id"],
                            msg.message_id,
                            disable_notification=True
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to pin message for {user['user_id']}: {e}")
        await asyncio.gather(*pin_tasks, return_exceptions=True)

async def pbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await broadcast(update, context, pin=True)

def register_handlers(application):
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("pbroadcast", pbroadcast))