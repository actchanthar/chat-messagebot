from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
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
    message = (
        f"Your invites: {invite_count}\n"
        f"Required for withdrawal: {await db.get_setting('invite_threshold', 15)}\n"
        f"Channels to join: {', '.join(channels) if channels else 'No channels set'}\n"
        f"Earn 25 kyat per invite when they join all channels!"
    )

    if query:
        await query.message.reply_text(message)
    else:
        await update.message.reply_text(message)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    channels = await db.get_force_sub_channels()
    if not channels:
        await update.message.reply_text("No force-sub channels set.")
        return False

    all_subscribed = True
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, int(user_id))
            if member.status not in ["member", "administrator", "creator"]:
                await update.message.reply_text(f"You must join {channel} to count as an invite.")
                all_subscribed = False
        except Exception:
            await update.message.reply_text(f"You must join {channel}.")
            all_subscribed = False

    if all_subscribed:
        # Reward logic
        user = await db.get_user(user_id)
        inviter_id = user.get("inviter_id")
        if inviter_id:
            inviter = await db.get_user(inviter_id)
            inviter_invites = inviter.get("invite_count", 0) + 1
            inviter_balance = inviter.get("balance", 0) + 25
            await db.update_user(inviter_id, {
                "invite_count": inviter_invites,
                "balance": inviter_balance,
                "invited_users": inviter.get("invited_users", []) + [user_id]
            })
            await context.bot.send_message(inviter_id, f"Your invite joined all channels! +25 kyat. Total invites: {inviter_invites}.")
            await db.update_user(user_id, {"balance": user.get("balance", 0) + 50})
            await update.message.reply_text("You joined all channels! +50 kyat.")
        return True
    return False

def register_handlers(application: Application):
    application.add_handler(CallbackQueryHandler(referral_users, pattern="^referral_users$"))
    application.add_handler(CommandHandler("checksubscription", check_subscription))
    application.add_handler(CommandHandler("referral_users", referral_users))