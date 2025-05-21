from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user or not user.get("referrer"):
        await update.message.reply_text("You do not have a referrer.")
        return

    force_sub_channels = await db.get_force_sub_channels()
    if not force_sub_channels:
        await update.message.reply_text("No force subscription channels set.")
        return

    subscribed = True
    for channel_id in force_sub_channels:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                subscribed = False
                break
        except Exception:
            subscribed = False
            break

    if subscribed:
        referrer_id = user["referrer"]
        if user_id not in user.get("invites", []):
            await db.add_invite(referrer_id, user_id)
            await db.update_user(user_id, {"balance": user.get("balance", 0) + 50})
            referrer = await db.get_user(referrer_id)
            await db.update_user(referrer_id, {"balance": referrer.get("balance", 0) + 25})
            await update.message.reply_text("You’ve subscribed and received 50 kyats!")
            await context.bot.send_message(referrer_id, f"Your invite {user['name']} joined, you got 25 kyats!")
    else:
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{channel_id[1:]}")] for channel_id in force_sub_channels]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please join all required channels:", reply_markup=reply_markup)

def register_handlers(application):
    application.add_handler(CommandHandler("checksubscription", checksubscription))