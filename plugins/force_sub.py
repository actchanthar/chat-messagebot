from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from config import REQUIRED_CHANNELS

invite_links_cache = {}
channel_names_cache = {}  # Cache for channel names

async def get_channel_info(context: CallbackContext, channel_id: int) -> tuple:
    """
    Get the invite link and name of a channel.
    Returns a tuple of (invite_link, channel_name).
    """
    # Check cache for invite link and name
    invite_link = invite_links_cache.get(channel_id)
    channel_name = channel_names_cache.get(channel_id)

    if not invite_link or not channel_name:
        try:
            # Get channel details (including name)
            chat = await context.bot.get_chat(chat_id=channel_id)
            channel_name = chat.title  # Get the channel's name
            channel_names_cache[channel_id] = channel_name

            # Generate invite link
            invite_link = await context.bot.export_chat_invite_link(chat_id=channel_id)
            invite_links_cache[channel_id] = invite_link
        except Exception as e:
            print(f"Error getting info for channel {channel_id}: {e}")
            invite_link = f"https://t.me/{channel_id}"  # Fallback
            channel_name = f"Channel {channel_id}"  # Fallback name
            channel_names_cache[channel_id] = channel_name
            invite_links_cache[channel_id] = invite_link

    return invite_link, channel_name

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
        keyboard = []
        for channel_id in REQUIRED_CHANNELS:
            invite_link, channel_name = await get_channel_info(context, channel_id)
            keyboard.append([InlineKeyboardButton(f"ချန်နယ် {channel_name} သို့ ဝင်ပါ", url=invite_link)])
        keyboard.append([InlineKeyboardButton("စစ်ဆေးရန် ✅", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("ဆက်လက်ရှာဖွေရန် ချန်နယ်များသို့ ဝင်ပါ။", reply_markup=reply_markup)
        return False
    return True