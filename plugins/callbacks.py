from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CommandHandler
)
from database.database import db
import config
import logging
from plugins.withdrawal import withdraw, handle_withdrawal_details, handle_admin_receipt, handle_payment_method_selection  # Import the new handler

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /start command from user {user_id} in chat {chat_id}")
    
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Top", callback_data="top")],
        [InlineKeyboardButton("Help", callback_data="help")],
        [InlineKeyboardButton("ထုတ်ယူရန်", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "မင်္ဂလာပါ!\n"
            f"စာတိုများ: {user['messages']}\n"
            f"လက်ကျန်: {user['balance']} {config.CURRENCY}\n"
            "Choose an option:"
        ),
        reply_markup=reply_markup
    )
    logger.info(f"Successfully sent /start response to user {user_id} in chat {chat_id}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat_id)
    data = query.data
    logger.info(f"Button callback received: user {user_id}, chat {chat_id}, data: {data}, context: {context.user_data}")

    try:
        if data == "balance":
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"မင်္ဂလာပါ {user['name']}!\n"
                    f"စာတိုများ: {user['messages']}\n"
                    f"လက်ကျန်: {user['balance']} {config.CURRENCY}"
                )
            )
            logger.info(f"Balance checked for user {user_id}")
        elif data == "top":
            top_users = await db.get_top_users()
            if not top_users:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။"
                )
                return
            message = "🏆 ထိပ်တန်းအသုံးပြုသူများ 🏆\n"
            for i, user in enumerate(top_users, 1):
                message += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"
            total_messages = sum(user['messages'] for user in top_users)
            total_balance = sum(user['balance'] for user in top_users)
            message += f"\nစုစုပေါင်းစာတိုများ: {total_messages}\nစုစုပေါင်းဆုလာဘ်: {total_balance} {config.CURRENCY}"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Top users shown for user {user_id}")
        elif data == "help":
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                    "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
                    "အမိန့်များ:\n"
                    "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                    "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                    "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
                    "/help - ဤစာကိုပြရန်\n"
                    "/reset - Reset withdrawal process\n"
                    "/debug - Check current state"
                )
            )
            logger.info(f"Help shown for user {user_id}")
        elif data == "withdraw":
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring withdraw request in group chat {chat_id}")
                await query.message.reply_text("This action is only available in private chat.")
                return
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            try:
                is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
                if not is_subscribed:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
                    )
                    logger.info(f"User {user_id} not subscribed to {config.CHANNEL_USERNAME}")
                    return
            except Exception as e:
                logger.error(f"Subscription check failed for user {user_id}: {str(e)}")
                await context.bot.send_message(chat_id=chat_id, text="Subscription check failed. Please try again later.")
                return
            # Call the new withdraw function from withdrawal.py
            await withdraw(update, context)
            logger.info(f"Withdrawal process initiated for user {user_id}")

    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text="An error occurred. Please try again later.")
        return ConversationHandler.END

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    context.user_data.clear()
    logger.info(f"Reset state for user {user_id} in chat {chat_id}")
    await update.message.reply_text("State has been reset. Use /withdraw to start again.")
    return ConversationHandler.END

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Debug for user {user_id} in chat {chat_id}: Context={context.user_data}")
    await update.message.reply_text(
        f"Debug Info:\nContext: {context.user_data}"
    )

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return False

async def debug_unhandled_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message = update.message if update.message else None
    logger.info(f"Debug unhandled message: user {user_id} in chat {chat_id}, chat type: {update.effective_chat.type}, text={message.text if message and message.text else 'None'}, photo={message.photo if message else 'None'}, context: {context.user_data}")

def register_handlers(application):
    # Register new commands
    from plugins.withdrawal import withdraw, handle_withdrawal_details, handle_admin_receipt, handle_payment_method_selection
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_withdrawal_details))
    application.add_handler(CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_.*$"))
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve_withdrawal_|reject_withdrawal_)"))
    
    # Register /start command
    application.add_handler(CommandHandler("start", start))
    
    # Handle all other button callbacks outside conversation
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(balance|top|help|withdraw)$"), group=2)
    
    # Fallback handler to debug unhandled messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, debug_unhandled_message), group=3)
    
    logger.info("Registered start command, withdrawal handlers, payment method handler, button callbacks, reset, debug, and debug handler")