from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import FORCE_SUB_CHANNELS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please start with /start first.")
        return

    if user.get("joined_channels", False):
        await update.message.reply_text("You have already joined the required channels.")
        return

    all_joined = True
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
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
                await context.bot.send_message(
                    chat_id=inviter_id,
                    text=f"Your invitee {update.effective_user.full_name} joined the channels. You got 25 kyats!"
                )
    else:
        await update.message.reply_text("Please join all required channels and try again.")

def register_handlers(application: Application):
    logger.info("Registering subscription handlers")
    application.add_handler(CommandHandler("checksubscription", checksubscription))