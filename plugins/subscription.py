from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import REQUIRED_CHANNELS, BOT_USERNAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please start with /start first.")
            return

        if user.get("joined_channels", False):
            await update.message.reply_text("You have already joined the required channels.")
            return

        all_joined = True
        for channel_id in REQUIRED_CHANNELS:
            try:
                member = await context.bot.get_chat_member(channel_id, int(user_id))
                if member.status not in ["member", "administrator", "creator"]:
                    all_joined = False
                    break
            except Exception as e:
                logger.error(f"Error checking membership for {user_id} in {channel_id}: {e}")
                all_joined = False
                break

        if all_joined:
            await db.update_user(user_id, {"joined_channels": True, "balance": user.get("balance", 0) + 50})
            await update.message.reply_text("You joined all channels and received 50 kyats!")
            inviter_id = user.get("inviter")
            if inviter_id:
                inviter = await db.get_user(inviter_id)
                if inviter:
                    new_invited = inviter.get("invited_users", 0) + 1
                    await db.update_user(inviter_id, {
                        "invited_users": new_invited,
                        "balance": inviter.get("balance", 0) + 25
                    })
                    try:
                        await context.bot.send_message(
                            chat_id=inviter_id,
                            text=f"Your invitee {update.effective_user.full_name} joined the channels. You got 25 kyats!"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify inviter {inviter_id}: {e}")
        else:
            channels_text = "\n".join([f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=join_{channel_id}" for channel_id in REQUIRED_CHANNELS])
            await update.message.reply_text(f"Please join all required channels:\n{channels_text}\nThen use /checksubscription again.")
    except Exception as e:
        logger.error(f"Error in checksubscription for user {user_id}: {e}")
        try:
            await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as reply_e:
            logger.error(f"Failed to send error message to {user_id}: {reply_e}")

def register_handlers(application: Application):
    logger.info("Registering subscription handlers")
    application.add_handler(CommandHandler("checksubscription", checksubscription, block=False))