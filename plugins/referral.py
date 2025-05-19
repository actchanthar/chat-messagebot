from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    query = update.callback_query
    if query:
        await query.answer()

    user = await db.get_user(user_id)
    invite_count = user.get("invite_count", 0)
    channels = await db.get_force_sub_channels()
    message = f"Your invites: {invite_count}\nRequired for withdrawal: {await db.get_setting('invite_threshold', 15)}\nChannels to join: {', '.join(channels)}"

    if query:
        await query.message.reply_text(message)
    else:
        await update.message.reply_text(message)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    channels = await db.get_force_sub_channels()
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, int(user_id))
            if member.status in ["member", "administrator", "creator"]:
                continue
            else:
                await update.message.reply_text(f"You must join {channel} to count as an invite.")
                return False
        except Exception:
            await update.message.reply_text(f"You must join {channel}.")
            return False

    # Reward logic
    inviter_id = (await db.get_user(user_id)).get("inviter_id")
    if inviter_id:
        inviter = await db.get_user(inviter_id)
        inviter_invites = inviter.get("invite_count", 0) + 1
        inviter_balance = inviter.get("balance", 0) + 25
        await db.update_user(inviter_id, {"invite_count": inviter_invites, "balance": inviter_balance, "invited_users": inviter.get("invited_users", []) + [user_id]})
        await context.bot.send_message(inviter_id, "Your invite joined all channels! +25 kyat.")
        await db.update_user(user_id, {"balance": user.get("balance", 0) + 50})
        await update.message.reply_text("You joined all channels! +50 kyat.")
    return True

def register_handlers(application: Application):
    application.add_handler(CallbackQueryHandler(referral_users, pattern="^referral_users$"))
    application.add_handler(CommandHandler("checksubscription", check_subscription))