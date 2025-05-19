from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setinvite <number>")
        return
    threshold = int(context.args[0])
    await db.set_setting("invite_threshold", threshold)
    await update.message.reply_text(f"Invite threshold set to {threshold}.")

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addchnl <channel_id>")
        return
    channel_id = context.args[0]
    channels = await db.get_force_sub_channels()
    if channel_id in channels:
        await update.message.reply_text(f"Channel {channel_id} already added.")
        return
    await db.add_channel(channel_id)
    await update.message.reply_text(f"Added {channel_id} to force-sub channels.")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return
    channel_id = context.args[0]
    await db.remove_channel(channel_id)
    await update.message.reply_text(f"Removed {channel_id} from force-sub channels.")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    channels = await db.get_force_sub_channels()
    if not channels:
        await update.message.reply_text("No force-sub channels set.")
        return
    await update.message.reply_text(f"Force-sub channels:\n" + "\n".join(channels))

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setmessage <messages_per_kyat>")
        return
    rate = int(context.args[0])
    await db.set_setting("message_rate", rate)
    await update.message.reply_text(f"Set {rate} messages = 1 kyat.")

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    group_id = GROUP_CHAT_IDS[0] if GROUP_CHAT_IDS else None
    if not group_id:
        await update.message.reply_text("No group configured.")
        return
    messages = await db.get_group_messages(group_id)
    if not messages:
        await update.message.reply_text(f"No messages in group {group_id}.")
        return
    msg = f"Messages in group {group_id}:\n"
    for user_id, count in messages.items():
        user = await db.get_user(user_id)
        msg += f"{user['name']}: {count} messages\n"
    await update.message.reply_text(msg)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    user_id = context.args[0] if context.args else str(update.effective_user.id)
    channels = await db.get_force_sub_channels()
    if not channels:
        await update.message.reply_text("No force-sub channels set.")
        return
    subscribed = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, int(user_id))
            if member.status in ["member", "administrator", "creator"]:
                subscribed.append(channel)
        except Exception:
            pass
    await update.message.reply_text(
        f"User {user_id} subscribed to:\n" + ("\n".join(subscribed) if subscribed else "No channels")
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    count = await db.get_user_count()
    await update.message.reply_text(f"Total users: {count}")

async def rmamount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /rmamount <user_id> <amount>")
        return
    user_id, amount = context.args[0], int(context.args[1])
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    new_balance = max(0, user.get("balance", 0) - amount)
    await db.update_user(user_id, {"balance": new_balance})
    await update.message.reply_text(f"Removed {amount} kyat from {user['name']}. New balance: {new_balance}.")
    await context.bot.send_message(user_id, f"Admin removed {amount} kyat. Your new balance: {new_balance}.")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("setinvite", setinvite))
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("checkgroup", checkgroup))
    application.add_handler(CommandHandler("checksubscription", checksubscription))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("rmamount", rmamount))