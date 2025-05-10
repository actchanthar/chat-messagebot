from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database.database import db
import config

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    data = query.data
    if data == "balance":
        user_id = str(query.from_user.id)
        user = await db.get_user(user_id)
        if not user:
            await db.create_user(user_id, query.from_user.first_name)
            user = await db.get_user(user_id)
        await query.message.reply_text(
            f"Hi {user['name']}!\n"
            f"Messages: {user['messages']}\n"
            f"Balance: {user['balance']} {config.CURRENCY}"
        )
    elif data == "top":
        top_users = await db.get_top_users()
        if not top_users:
            await query.message.reply_text("No stats yet.")
            return
        message = "🏆 Top Users 🏆\n"
        for i, user in enumerate(top_users, 1):
            message += f"{i}. {user['name']}: {user['messages']} messages, {user['balance']} {config.CURRENCY}\n"
        total_messages = sum(user['messages'] for user in top_users)
        total_balance = sum(user['balance'] for user in top_users)
        message += f"\nTotal Messages: {total_messages}\nTotal Rewards: {total_balance} {config.CURRENCY}"
        await query.message.reply_text(message)
    elif data == "help":
        await query.message.reply_text(
            "Earn 1 kyat per valid message.\n"
            "Join our channel to withdraw.\n\n"
            "Commands:\n"
            "/balance - Check earnings\n"
            "/top - View top users\n"
            "/withdraw - Request withdrawal\n"
            "/help - Show this message"
        )
    elif data == "withdraw":
        user_id = str(query.from_user.id)
        user = await db.get_user(user_id)
        if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
            await query.message.reply_text(
                f"You need at least {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} to withdraw."
            )
            return
        
        is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
        if not is_subscribed:
            await query.message.reply_text(
                f"Join {config.CHANNEL_USERNAME} to withdraw.\nThen try again."
            )
            return
        
        # Store user state for withdrawal
        context.user_data["withdrawal"] = {"amount": user["balance"]}
        
        # Create payment method buttons
        keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "Select a payment method:",
            reply_markup=reply_markup
        )
    elif data.startswith("payment_"):
        method = data.replace("payment_", "")
        if "withdrawal" not in context.user_data:
            await query.message.reply_text("Please start the withdrawal process with /withdraw.")
            return
        
        context.user_data["withdrawal"]["method"] = method
        if method == "KBZ Pay":
            await query.message.reply_text(
                "Send your QR code or account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW)."
            )
        else:
            await query.message.reply_text(
                f"Send your {method} account details."
            )

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(button_callback))