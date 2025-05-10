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
            f"မင်္ဂလာပါ {user['name']}!\n"
            f"စာတိုများ: {user['messages']}\n"
            f"လက်ကျန်: {user['balance']} {config.CURRENCY}",
            reply_to_message_id=None
        )
    elif data == "top":
        top_users = await db.get_top_users()
        if not top_users:
            await query.message.reply_text("အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။", reply_to_message_id=None)
            return
        message = "🏆 ထိပ်တန်းအသုံးပြုသူများ 🏆\n"
        for i, user in enumerate(top_users, 1):
            message += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"
        total_messages = sum(user['messages'] for user in top_users)
        total_balance = sum(user['balance'] for user in top_users)
        message += f"\nစုစုပေါင်းစာတိုများ: {total_messages}\nစုစုပေါင်းဆုလာဘ်: {total_balance} {config.CURRENCY}"
        await query.message.reply_text(message, reply_to_message_id=None)
    elif data == "help":
        await query.message.reply_text(
            "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
            "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
            "အမိန့်များ:\n"
            "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
            "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
            "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
            "/help - ဤစာကိုပြရန်",
            reply_to_message_id=None
        )
    elif data == "withdraw":
        user_id = str(query.from_user.id)
        user = await db.get_user(user_id)
        if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
            await query.message.reply_text(
                f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။",
                reply_to_message_id=None
            )
            return
        
        is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
        if not is_subscribed:
            await query.message.reply_text(
                f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။",
                reply_to_message_id=None
            )
            return
        
        # Store user state for withdrawal
        context.user_data["withdrawal"] = {"amount": user["balance"]}
        
        # Create payment method buttons
        keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "ငွေထုတ်ယူရန်နည်းလမ်းရွေးချယ်ပါ:",
            reply_markup=reply_markup,
            reply_to_message_id=None
        )
    elif data.startswith("payment_"):
        method = data.replace("payment_", "")
        if "withdrawal" not in context.user_data:
            # Send message privately to avoid group clutter
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
                )
            except:
                pass  # Ignore if can't send (e.g., user blocked bot)
            return
        
        context.user_data["withdrawal"]["method"] = method
        if method == "KBZ Pay":
            await query.message.reply_text(
                "QR ကုဒ် သို့မဟုတ် အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ (ဥပမာ: 09123456789 ZAYAR KO KO MIN ZAW)။",
                reply_to_message_id=None
            )
        else:
            await query.message.reply_text(
                f"{method} အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ။",
                reply_to_message_id=None
            )

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(button_callback))