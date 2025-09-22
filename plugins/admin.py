from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from collections import defaultdict
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add mandatory channel command - FIXED"""
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
            "2. Channel ID သည် -100 နဲ့စပြီး ဂဏန်းရှည်ဖြစ်ပါသည်\n"
            "3. Bot ကို channel ထဲ admin အဖြစ် ထည့်ပါ"
        )
        return
    
    try:
        channel_id = context.args[0].strip()
        channel_name = " ".join(context.args[1:]).strip()
        
        logger.info(f"Admin {user_id} attempting to add channel: {channel_id} - {channel_name}")
        
        # Basic validation - channel ID format
        if not channel_id.startswith('-100'):
            await update.message.reply_text(
                "❌ **Invalid Channel ID Format**\n\n"
                "Channel ID သည် -100 ဖြင့်စရပါမည်။\n"
                "ဥပမာ: -1001234567890"
            )
            return
        
        # Try to get channel info to validate
        channel_accessible = False
        actual_channel_name = channel_name
        try:
            chat = await context.bot.get_chat(channel_id)
            actual_channel_name = chat.title or channel_name
            channel_accessible = True
            logger.info(f"Channel accessible: {actual_channel_name}")
        except Exception as e:
            logger.warning(f"Cannot access channel {channel_id}: {e}")
            # Continue anyway - channel might be private
            channel_accessible = False
        
        # Add channel to database - FORCE ADD EVEN IF NOT ACCESSIBLE
        logger.info(f"Adding channel to database...")
        success = await db.add_mandatory_channel(channel_id, channel_name, user_id)
        
        if success:
            status_msg = "✅ **Channel ထည့်ပြီးပါပြီ**\n\n"
            
            if channel_accessible:
                status_msg += f"📺 **Channel:** {actual_channel_name}\n"
                status_msg += f"✅ **Status:** Bot can access channel\n"
            else:
                status_msg += f"📺 **Channel:** {channel_name}\n"
                status_msg += f"⚠️ **Status:** Channel not accessible (might be private)\n"
                status_msg += f"**ရှင်းလင်းချက်:** Bot သည် channel ကို access မလုပ်နိုင်ပါ။\n"
                status_msg += f"**ဖြေရှင်းနည်း:** Bot ကို channel သို့ admin အဖြစ် ထည့်ပါ။\n\n"
            
            status_msg += f"🆔 **Channel ID:** `{channel_id}`\n"
            status_msg += f"👤 **ထည့်သူ:** Admin {user_id}\n"
            status_msg += f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            status_msg += f"ယခုမှစ၍ users များသည် withdraw လုပ်ရန် ဤ channel ကို join လုပ်ရပါမည်။"
            
            await update.message.reply_text(status_msg)
            logger.info(f"✅ Admin {user_id} successfully added mandatory channel: {channel_id} - {channel_name}")
        else:
            await update.message.reply_text(
                "❌ **Channel ထည့်၍မရပါ**\n\n"
                "**ဖြစ်နိုင်သောအကြောင်းရင်းများ:**\n"
                "1. Database connection error\n"
                "2. Channel already exists\n"
                "3. Invalid channel ID\n\n"
                "**ဖြေရှင်းနည်း:**\n"
                "• Channel ID မှန်ကန်ကြောင်း စစ်ဆေးပါ\n"
                "• `/listchannels` ဖြင့် ရှိပြီးသား channels များ ကြည့်ပါ\n"
                "• ထပ်မံကြိုးစားပါ"
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid Channel ID**\n\n"
            "Channel ID သည် number များသာ ပါရှိရပါမည်။\n"
            "ဥပမာ: -1001234567890"
        )
    except Exception as e:
        logger.error(f"Error in add_channel: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            "❌ **System Error**\n\n"
            f"Error occurred while adding channel.\n"
            f"Please try again or contact developer.\n\n"
            f"Error: {str(e)[:100]}"
        )

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove mandatory channel command"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** `/removechannel <channel_id>`\n\n"
            "**ဥပမာ:** `/removechannel -1001234567890`\n\n"
            "**လမ်းညွှန်:** `/listchannels` ဖြင့် channel ID များကို ကြည့်နိုင်ပါသည်။"
        )
        return
    
    try:
        channel_id = context.args[0].strip()
        
        # Remove channel from database
        success = await db.remove_mandatory_channel(channel_id)
        
        if success:
            await update.message.reply_text(
                f"✅ **Channel ဖယ်ရှားပြီးပါပြီ**\n\n"
                f"🆔 **Channel ID:** `{channel_id}`\n"
                f"👤 **ဖယ်ရှားသူ:** Admin {user_id}\n"
                f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"ယခုမှစ၍ users များသည် ဤ channel ကို join မလုပ်ရတော့ပါ။"
            )
            logger.info(f"Admin {user_id} removed mandatory channel: {channel_id}")
        else:
            await update.message.reply_text(
                "❌ **Channel ဖယ်ရှား၍မရပါ**\n\n"
                "**ဖြစ်နိုင်သောအကြောင်းရင်းများ:**\n"
                "• Channel ID ရှာမတွေ့ပါ\n"
                "• ထည့်ထားသော channel မဟုတ်ပါ\n\n"
                "**ဖြေရှင်းနည်း:**\n"
                "• `/listchannels` ဖြင့် စစ်ဆေးပါ\n"
                "• Channel ID မှန်ကန်ကြောင်း စစ်ဆေးပါ"
            )
    
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
                "**Channel ထည့်ရန်:** `/addchannel <channel_id> <name>`\n"
                "**ဥပမာ:** `/addchannel -1001234567890 Main Channel`"
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
            
            # Format date
            try:
                if len(str(added_at)) > 10:
                    formatted_date = str(added_at)[:10]
                else:
                    formatted_date = str(added_at)
                text += f"   📅 Date: {formatted_date}\n\n"
            except:
                text += f"   📅 Date: {added_at}\n\n"
        
        text += f"📊 **Total channels:** {len(channels)}\n\n"
        text += f"**Available Commands:**\n"
        text += f"• `/addchannel <id> <name>` - Add channel\n"
        text += f"• `/removechannel <id>` - Remove channel\n"
        text += f"• `/listchannels` - View all channels"
        
        await update.message.reply_text(text)
    
    except Exception as e:
        logger.error(f"Error in list_channels: {e}")
        await update.message.reply_text("❌ Error loading channels list.")

async def update_user_names_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to update user names from Telegram API"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        await update.message.reply_text("🔄 Updating user names from Telegram API...")
        
        # Update user names
        updated_count = await db.bulk_update_user_names(context)
        
        await update.message.reply_text(
            f"✅ **User Names Updated**\n\n"
            f"📊 **Updated:** {updated_count} users\n"
            f"⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"🔄 Check leaderboard now - should show real names!"
        )
        
        logger.info(f"Admin {user_id} updated {updated_count} user names")
        
    except Exception as e:
        logger.error(f"Error in update user names command: {e}")
        await update.message.reply_text("❌ Error updating user names.")

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to ban a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/ban <user_id> [အကြောင်းရင်း]`\n\n"
            f"**ဥပမာ:** `/ban 123456789 Spamming`"
        )
        return
    
    try:
        target_user_id = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Admin မှ ပိတ်ပင်ခြင်း"
        
        # Ban user in database
        success = await db.ban_user(target_user_id, reason)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "သုံးစွဲသူ"
            except:
                user_name = "သုံးစွဲသူ"
            
            await update.message.reply_text(
                f"✅ **သုံးစွဲသူကို ပိတ်ပင်ပြီးပါပြီ**\n\n"
                f"👤 **သုံးစွဲသူ:** {user_name} ({target_user_id})\n"
                f"📝 **အကြောင်းရင်း:** {reason}\n"
                f"👨‍💼 **ပိတ်ပင်သူ:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} banned user {target_user_id}: {reason}")
        else:
            await update.message.reply_text("❌ သုံးစွဲသူကို ပိတ်ပင်၍မရပါ။ သုံးစွဲသူ မတွေ့ပါ။")
    
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await update.message.reply_text("❌ Error occurred while banning user.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to unban a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/unban <user_id>`\n\n"
            f"**ဥပမာ:** `/unban 123456789`"
        )
        return
    
    try:
        target_user_id = context.args[0]
        
        # Unban user in database
        success = await db.unban_user(target_user_id)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "သုံးစွဲသူ"
            except:
                user_name = "သုံးစွဲသူ"
            
            await update.message.reply_text(
                f"✅ **သုံးစွဲသူကို ပြန်လည်ခွင့်ပြုပြီးပါပြီ**\n\n"
                f"👤 **သုံးစွဲသူ:** {user_name} ({target_user_id})\n"
                f"👨‍💼 **ပြန်လည်ခွင့်ပြုသူ:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} unbanned user {target_user_id}")
        else:
            await update.message.reply_text("❌ သုံးစွဲသူကို ပြန်လည်ခွင့်ပြု၍မရပါ။")
    
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await update.message.reply_text("❌ Error occurred while unbanning user.")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check system status - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        # Get system stats
        total_users = await db.get_total_users_count()
        total_earnings = await db.get_total_earnings()
        total_withdrawals = await db.get_total_withdrawals()
        channels = await db.get_mandatory_channels()
        
        uptime_str = "Running"
        
        status_text = (
            f"🤖 **စနစ်အခြေအနေ**\n\n"
            f"👥 **စုစုပေါင်းသုံးစွဲသူ:** {total_users:,}\n"
            f"💰 **စုစုပေါင်းရရှိငွေ:** {int(total_earnings):,} {CURRENCY}\n"
            f"💸 **စုစုပေါင်းထုတ်ယူငွေ:** {int(total_withdrawals):,} {CURRENCY}\n"
            f"💳 **စနစ်ရှိငွေ:** {int(total_earnings - total_withdrawals):,} {CURRENCY}\n"
            f"📺 **Mandatory Channels:** {len(channels)}\n\n"
            f"🛡️ **Anti-spam:** အလုပ်လုပ်နေသည်\n"
            f"📊 **Database:** ချိတ်ဆက်ထားသည်\n"
            f"⏱️ **Bot status:** {uptime_str}\n\n"
            f"✅ **စနစ်အားလုံး ကောင်းမွန်စွာအလုပ်လုပ်နေပါသည်**"
        )
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in system status: {e}")
        await update.message.reply_text("❌ စနစ်အခြေအနေ စစ်ဆေး၍မရပါ။")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all users - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/broadcast <မက်ဆေ့ချ်>`\n\n"
            f"**ဥပမာ:** `/broadcast သုံးစွဲသူအားလုံးအတွက် အရေးကြီးသောအချက်အလက်!`"
        )
        return
    
    try:
        message = " ".join(context.args)
        
        # Get all users
        users = await db.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        await update.message.reply_text(f"📡 **{len(users)} သုံးစွဲသူများထံ ပို့နေပါသည်...**")
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **ကြေငြာချက်**\n\n{message}\n\n- Admin Team"
                )
                sent_count += 1
            except:
                failed_count += 1
        
        await update.message.reply_text(
            f"✅ **Broadcast ပြီးစီးပါပြီ**\n\n"
            f"📤 **ပို့အောင်မြင်:** {sent_count} သုံးစွဲသူ\n"
            f"❌ **ပို့မရ:** {failed_count} သုံးစွဲသူ\n"
            f"👨‍💼 **ပို့သူ:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} broadcasted to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ Broadcast ပို့၍မရပါ။")

def register_handlers(application: Application):
    """Register admin command handlers"""
    logger.info("Registering admin handlers with Myanmar language support")
    
    # Channel management commands - HIGHEST PRIORITY
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("listchannels", list_channels))
    application.add_handler(CommandHandler("channels", list_channels))
    
    # User management commands
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    
    # System commands
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("systemstatus", system_status))
    
    # User name update command
    application.add_handler(CommandHandler("updatenames", update_user_names_command))
    
    logger.info("✅ Admin handlers with Myanmar language registered successfully")
