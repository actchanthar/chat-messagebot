from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import FORCE_SUB_CHANNEL_IDS, FORCE_SUB_CHANNEL_LINKS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        await db.update_subscription_status(user_id, channel_id, is_member)
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
        return False

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"CheckSubscription command initiated by user {user_id} in chat {chat_id}")

    not_subscribed_channels = []
    for channel_id in FORCE_SUB_CHANNEL_IDS:
        if not await check_subscription(context, user_id, channel_id):
            not_subscribed_channels.append(channel_id)

    if not_subscribed_channels:
        channel_links = "\n".join(
            [f"- <a href='{FORCE_SUB_CHANNEL_LINKS[channel_id]}'>{channel_id}</a>"
             for channel_id in not_subscribed_channels]
        )
        await update.message.reply_text(
            f"You need to join the following channel(s) to use the bot:\n{channel_links}",
            parse_mode="HTML"
        )
    else:
        user = await db.get_user(user_id)
        referrer_id = user.get("referrer_id")
        if referrer_id:
            referrer = await db.get_user(referrer_id)
            if referrer:
                new_invite_link = f"https://t.me/{context.bot.username}?start=referrer={referrer_id}"
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 User {update.effective_user.full_name} confirmed their subscription to the required channel(s)! "
                             f"You now have {referrer.get('invited_users', 0) + 1} invites.\n"
                             f"Share this link to invite more: {new_invite_link}"
                    )
                    logger.info(f"Notified referrer {referrer_id} of confirmed subscription by user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer_id}: {e}")
        await update.message.reply_text("You are subscribed to all required channels! 🎉")

def register_handlers(application: Application):
    logger.info("Registering checksubscription handlers")
    application.add_handler(CommandHandler("checksubscription", checksubscription))