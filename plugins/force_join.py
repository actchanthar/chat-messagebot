from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add mandatory channel command"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** `/addchannel <channel_id> <channel_name>`\n\n"
            "**ဥပမာ:** `/addchannel -1001234567890 Main Channel`\n\n"
            "**လမ်းညွှန်:**\n"
            "1. Channel ID ရယူရန် @userinfobot ကို channel ထဲထည့်ပါ\n"
            "2. Channel ID သည် - နဲ့စပြီး ဂဏန်းရှည်ဖြစ်ပါသည်"
        )
        return
    
    try:
        channel_id = context.args[0]
        channel_name = " ".join(context.args[1:])
        
        # Validate channel ID format
        if not channel_id.startswith('-100'):
            await update.message.reply_text("❌ Channel ID သည် -100 ဖြင့်စရပါမည်။")
            return
        
        # Try to get channel info to validate
        try:
            chat = await context.bot.get_chat(channel_id)
            actual_name = chat.title or channel_name
        except TelegramError as e:
            await update.message.reply_text(
                f"❌ **Channel စစ်ဆေး၍မရပါ:** {e}\n\n"
                f"**ဖြေရှင်းနည်း:**\n"
                f"1. Bot ကို channel သို့ admin အဖြစ်ထည့်ပါ\n"
                f"2. Channel ID မှန်ကန်ကြောင်း စစ်ဆေးပါ\n"
                f"3. Channel သည် private ဖြစ်နေလျှင် public လုပ်ပါ"
            )
            return
        
        # Add channel to database
        success = await db.add_mandatory_channel(channel_id, channel_name)
        
        if success:
            await update.message.reply_text(
                f"✅ **Channel ထည့်ပြီးပါပြီ**\n\n"
                f"📺 **Channel:** {channel_name}\n"
                f"🆔 **Channel ID:** {channel_id}\n"
                f"👤 **ထည့်သူ:** Admin {user_id}\n\n"
                f"ယခုမှစ၍ users များသည် withdraw လုပ်ရန် ဤ channel ကို join လုပ်ရပါမည်။"
            )
            logger.info(f"Admin {user_id} added mandatory channel: {channel_id} - {channel_name}")
        else:
            await update.message.reply_text("❌ Channel ထည့်၍မရပါ။ ထပ်မံကြိုးစားပါ။")
    
    except Exception as e:
        logger.error(f"Error in add_channel: {e}")
        await update.message.reply_text("❌ Error occurred while adding channel.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove mandatory channel command"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** `/removechannel <channel_id>`\n\n"
            "**ဥပမာ:** `/removechannel -1001234567890`"
        )
        return
    
    try:
        channel_id = context.args[0]
        
        # Remove channel from database
        success = await db.remove_mandatory_channel(channel_id)
        
        if success:
            await update.message.reply_text(
                f"✅ **Channel ဖယ်ရှားပြီးပါပြီ**\n\n"
                f"🆔 **Channel ID:** {channel_id}\n"
                f"👤 **ဖယ်ရှားသူ:** Admin {user_id}\n\n"
                f"ယခုမှစ၍ users များသည် ဤ channel ကို join မလုပ်ရတော့ပါ။"
            )
            logger.info(f"Admin {user_id} removed mandatory channel: {channel_id}")
        else:
            await update.message.reply_text("❌ Channel ဖယ်ရှား၍မရပါ။ Channel ID စစ်ဆေးပါ။")
    
    except Exception as e:
        logger.error(f"Error in remove_channel: {e}")
        await update.message.reply_text("❌ Error occurred while removing channel.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all mandatory channels"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        channels = await db.get_mandatory_channels()
        
        if not channels:
            await update.message.reply_text(
                "📺 **Mandatory Channels စာရင်း**\n\n"
                "❌ **မည်သည့် channel မှ မထည့်ရသေးပါ**\n\n"
                "**Channel ထည့်ရန်:** `/addchannel <channel_id> <name>`"
            )
            return
        
        text = "📺 **MANDATORY CHANNELS**\n\n"
        
        for i, channel in enumerate(channels, 1):
            channel_id = channel.get('channel_id', 'Unknown')
            channel_name = channel.get('channel_name', 'Unknown')
            added_by = channel.get('added_by', 'Unknown')
            added_at = channel.get('added_at', 'Unknown')
            
            text += f"{i}. **{channel_name}**\n"
            text += f"   🆔 ID: `{channel_id}`\n"
            text += f"   👤 Added by: Admin {added_by}\n"
            text += f"   📅 Date: {added_at[:10] if len(str(added_at)) > 10 else added_at}\n\n"
        
        text += f"📊 **Total channels:** {len(channels)}\n"
        text += f"**Commands:**\n"
        text += f"• `/addchannel <id> <name>` - Add channel\n"
        text += f"• `/removechannel <id>` - Remove channel"
        
        await update.message.reply_text(text)
    
    except Exception as e:
        logger.error(f"Error in list_channels: {e}")
        await update.message.reply_text("❌ Error loading channels list.")

async def check_user_subscriptions(user_id: str, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, list, list]:
    """Check if user has joined all mandatory channels and invited enough users"""
    try:
        # Get mandatory channels
        channels = await db.get_mandatory_channels()
        
        joined_channels = []
        not_joined_channels = []
        
        # Check each channel
        for channel in channels:
            channel_id = channel.get('channel_id')
            channel_name = channel.get('channel_name', 'Unknown Channel')
            
            try:
                # Check if user is member of channel
                member = await context.bot.get_chat_member(channel_id, int(user_id))
                
                if member.status in ['member', 'administrator', 'creator']:
                    joined_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'status': 'joined'
                    })
                else:
                    not_joined_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'status': 'not_joined'
                    })
                    
            except TelegramError:
                # User is not a member or channel not accessible
                not_joined_channels.append({
                    'id': channel_id,
                    'name': channel_name,
                    'status': 'not_joined'
                })
        
        # Check referral count
        user = await db.get_user(user_id)
        referral_count = user.get('successful_referrals', 0) if user else 0
        
        # User must join all channels AND have 10+ referrals
        all_requirements_met = len(not_joined_channels) == 0 and referral_count >= 10
        
        return all_requirements_met, joined_channels, not_joined_channels, referral_count
        
    except Exception as e:
        logger.error(f"Error checking subscriptions for {user_id}: {e}")
        return False, [], [], 0

def register_handlers(application: Application):
    """Register force join handlers"""
    logger.info("Registering force join handlers")
    
    # Admin commands
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("listchannels", list_channels))
    application.add_handler(CommandHandler("channels", list_channels))
    
    logger.info("✅ Force join handlers registered successfully")
