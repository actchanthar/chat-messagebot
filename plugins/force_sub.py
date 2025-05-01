from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from config import REQUIRED_CHANNELS

# Cache for invite links to avoid generating them repeatedly
invite_links_cache = {}

async def get_channel_invite_link(context: CallbackContext, channel_id: int) -> str:
    """
    Generate or retrieve the invite link for a channel.
    """
    if channel_id in invite_links_cache:
        return invite_links_cache[channel_id]

    try:
        # Use exportChatInviteLink to generate an invite link
        invite_link = await context.bot.export_chat_invite_link(chat_id=channel_id)
        invite_links_cache[channel_id] = invite_link
        return invite_link
    except Exception as e:
        print(f"Error generating invite link for channel {channel_id}: {e}")
        return f"https://t.me/{channel_id}"  # Fallback (though this won't work for private channels)

async def check_subscription(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    all_subscribed = True

    for channel_id in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                all_subscribed = False
                break
        except:
            all_subscribed = False
            break

    if not all_subscribed:
        # Generate invite links for each required channel
        keyboard = []
        for channel_id in REQUIRED_CHANNELS:
            invite_link = await get_channel_invite_link(context, channel_id)
            keyboard.append([InlineKeyboardButton(f"ချန်နယ် {channel_id} သို့ ဝင်ပါ", url=invite_link)])
        keyboard.append([InlineKeyboardButton("စစ်ဆေးရန် ✅", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("ဆက်လက်ရှာဖွေရန် ချန်နယ်များသို့ ဝင်ပါ။", reply_markup=reply_markup)
        return False
    return True