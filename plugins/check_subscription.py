from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import FORCE_SUB_CHANNEL_LINKS, FORCE_SUB_CHANNEL_NAMES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        # Verify bot's admin status in the channel
        bot_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        bot_is_admin = bot_member.status in ["administrator", "creator"]
        if not bot_is_admin:
            logger.error(f"Bot is not an admin in channel {channel_id}. Bot status: {bot_member.status}")
            return False

        # Check user membership
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        logger.info(f"User {user_id} subscription check for channel {channel_id}: status={member.status}, is_member={is_member}")
        await db.update_subscription_status(user_id, channel_id, is_member)
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
        return False

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"CheckSubscription command initiated by user {user_id} in chat {chat_id}")

    force_sub_channels = await db.get_force_sub_channels()
    logger.info(f"Force-sub channels from database: {force_sub_channels}")
    not_subscribed_channels = []
    for channel_id in force_sub_channels:
        if not await check_subscription(context, user_id, channel_id):
            not_subscribed_channels.append(channel_id)

    if not_subscribed_channels:
        keyboard = [
            [InlineKeyboardButton(
                f"Join {FORCE_SUB_CHANNEL_NAMES.get(channel_id, 'Channel')}",
                url=FORCE_SUB_CHANNEL_LINKS.get(channel_id, 'https://t.me/yourchannel')
            )]
            for channel_id in not_subscribed_channels
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🎉 You need to join the following channel(s) to use the bot:\n\n",
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
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
                             f"You now have {referrer.get('invited_users', 0)} invites.\n"
                             f"Share this link to invite more: {new_invate_link}",
                        disable_web_page_preview=True
                    )
                    logger.info(f"Notified referrer {referrer_id} of confirmed subscription by user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer_id}: {e}")
        await update.message.reply_text("🎉 You are subscribed to all required channels! Enjoy the bot! 🚀", parse_mode="HTML")

def register_handlers(application: Application):
    logger.info("Registering checksubscription handlers")
    application.add_handler(CommandHandler("checksubscription", checksubscription))