from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
    await update.message.reply_text(
        f"Hi {user['name']}!\n"
        f"Messages: {user['messages']}\n"
        f"Balance: {user['balance']} {config.CURRENCY}"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user or user['balance'] == 0:
        await update.message.reply_text("No balance to withdraw.")
        return
    
    is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
    if not is_subscribed:
        await update.message.reply_text(
            f"Join {config.CHANNEL_USERNAME} to withdraw.\nThen try /withdraw again."
        )
        return
    
    await update.message.reply_text(
        f"Withdrawal request for {user['balance']} {config.CURRENCY} submitted.\n"
        f"Admin will contact you."
    )

def register_handlers(application):
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("withdraw", withdraw))