from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database.database import db
import config

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    user_id = str(query.from_user.id)
    data = query.data

    try:
        if data == "balance":
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"မင်္ဂလာပါ {user['name']}!\n"
                    f"စာတိုများ: {user['messages']}\n"
                    f"လက်ကျန်: {user['balance']} {config.CURRENCY}"
                )
            )
        elif data == "top":
            top_users = await db.get_top_users()
            if not top_users:
                await context.bot.send_message(
                    chat_id=user_id,
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
                chat_id=user_id,
                text=message
            )
        elif data == "help":
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                    "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
                    "အမိန့်များ:\n"
                    "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                    "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                    "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
                    "/help - ဤစာကိုပြရန်"
                )
            )
        elif data == "withdraw":
            user = await db.get_user(user_id)
            if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
                )
                return
            
            is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
            if not is_subscribed:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
                )
                return
            
            # Store user state for withdrawal
            context.user_data["withdrawal"] = {"amount": user["balance"]}
            
            # Create payment method buttons
            keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=user_id,
                text="ငွေထုတ်ယူရန်နည်းလမ်းရွေးချယ်ပါ:",
                reply_markup=reply_markup
            )
        elif data.startswith("payment_"):
            method = data.replace("payment_", "")
            if "withdrawal" not in context.user_data:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
                )
                return
            
            context.user_data["withdrawal"]["method"] = method
            if method == "KBZ Pay":
                await context.bot.send_message(
                    chat_id=user_id,
                    text="QR ကုဒ် သို့မဟုတ် အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ (ဥပမာ: 09123456789 ZAYAR KO KO MIN ZAW)။"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"{method} အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ။"
                )
    except Exception as e:
        # Silently log errors without sending messages to group
        logger.error(f"Error in button callback for user {user_id}: {e}")

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(button_callback))