from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

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
        f"မင်္ဂလာပါ {user['name']}!\n"
        f"စာတိုများ: {user['messages']}\n"
        f"လက်ကျန်: {user['balance']} {config.CURRENCY}"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"Ignoring /withdraw in group chat {update.effective_chat.id}")
        return  # Silently ignore in group chats
    
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
        await update.message.reply_text(
            f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
        )
        return
    
    is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
    if not is_subscribed:
        await update.message.reply_text(
            f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
        )
        return
    
    # Store user state for withdrawal
    context.user_data["withdrawal"] = {"amount": user["balance"]}
    
    # Create payment method buttons
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "ငွေထုတ်ယူရန်နည်းလမ်းရွေးချယ်ပါ:",
        reply_markup=reply_markup
    )

async def handle_withdrawal_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"Ignoring withdrawal details in group chat {update.effective_chat.id}")
        return  # Silently ignore in group chats
    
    user_id = str(update.effective_user.id)
    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
        )
        return
    
    method = context.user_data["withdrawal"]["method"]
    amount = context.user_data["withdrawal"]["amount"]
    user = await db.get_user(user_id)
    
    # Get message content
    text = update.message.text or ""
    photo = update.message.photo[-1] if update.message.photo else None
    
    if not text and not photo:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ သင့်အကောင့်အသေးစိတ်အချက်အလက်များ သို့မဟုတ် QR ကုဒ်ပေးပို့ပါ။"
        )
        return
    
    # Prepare user profile and details
    username = update.effective_user.username or update.effective_user.first_name
    profile_info = (
        f"Withdrawal Request\n"
        f"User: @{username}\n"
        f"User ID: {user_id}\n"
        f"Amount: {amount} {config.CURRENCY}\n"
        f"Method: {method}\n"
        f"Details:\n"
    )
    if text:
        profile_info += f"Text: {text}\n"
    
    # Create Approve/Reject buttons
    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"withdraw_approve_{user_id}"),
            InlineKeyboardButton("Reject", callback_data=f"withdraw_reject_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Forward to admins
    for admin_id in config.ADMIN_IDS:
        if admin_id:
            try:
                if photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo.file_id,
                        caption=profile_info,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=profile_info,
                        reply_markup=reply_markup
                    )
            except RetryAfter as e:
                logger.warning(f"RetryAfter error for admin {admin_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "သင့်ငွေထုတ်ယူမှုတောင်းဆိုမှုကို အက်ဒမင်ထံပေးပို့ပြီးပါပြီ။ လုပ်ဆောင်ပြီးသည်နှင့် အကြောင်းကြားပါမည်။"
    )
    
    # Clear user state
    context.user_data.pop("withdrawal", None)

def register_handlers(application):
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND | filters.PHOTO,
        handle_withdrawal_details
    ))