from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Checksubscription command by user {user_id}")

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No force-subscription channels set.")
        return

    message = "Your subscription status:\n"
    all_subscribed = True
    for channel in channels:
        subscribed = await db.check_user_subscription(user_id, channel["channel_id"])
        status = "✅ Subscribed" if subscribed else "❌ Not Subscribed"
        message += f"{channel['name']} ({channel['channel_id']}): {status}\n"
        if not subscribed:
            all_subscribed = False
            try:
                member = await context.bot.get_chat_member(channel["channel_id"], int(user_id))
                if member.status in ["member", "administrator", "creator"]:
                    await db.update_user_subscription(user_id, channel["channel_id"], True)
                    message += f"Updated: You are now subscribed to {channel['name']}!\n"
            except Exception as e:
                logger.error(f"Error checking subscription for {user_id} in {channel['channel_id']}: {e}")

    if all_subscribed:
        message += "\nYou are subscribed to all required channels!"
    else:
        message += "\nPlease join all required channels to earn rewards."
    await update.message.reply_text(message)

def register_handlers(application):
    logger.info("Registering checksubscription handlers")
    application.add_handler(CommandHandler("checksubscription", check_subscription))