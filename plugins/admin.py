from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging
import sys
import os
from collections import defaultdict
import time
from datetime import datetime
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY, APPROVED_GROUPS

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

async def set_referral_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set referral reward amount - FIXED"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** `/setreferral <amount>`\n\n"
            "**ဥပမာ:** `/setreferral 25`\n\n"
            "**လက်ရှိ Referral Reward ကြည့်ရန်:** `/viewsettings`"
        )
        return
    
    try:
        new_reward = int(context.args[0])
        
        if new_reward < 0:
            await update.message.reply_text("❌ Referral reward cannot be negative.")
            return
        
        if new_reward > 1000:
            await update.message.reply_text("❌ Referral reward cannot exceed 1000.")
            return
            
        logger.info(f"Admin {user_id} attempting to set referral reward to {new_reward}")
        
        success = await db.update_settings({"referral_reward": new_reward})
        
        if success:
            # Verify the update by getting current settings
            current_settings = await db.get_settings()
            actual_reward = current_settings.get("referral_reward", 0)
            
            if actual_reward == new_reward:
                await update.message.reply_text(
                    f"✅ **Referral Reward Updated Successfully**\n\n"
                    f"💰 **New Reward:** {new_reward} {CURRENCY} per successful referral\n"
                    f"👨‍💼 **Updated by:** Admin {user_id}\n"
                    f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"💡 **Note:** Users get {new_reward} {CURRENCY} when their referrals join mandatory channels."
                )
                logger.info(f"✅ Admin {user_id} successfully updated referral reward to {new_reward}")
            else:
                await update.message.reply_text(
                    f"⚠️ **Update completed but verification failed**\n\n"
                    f"Expected: {new_reward}, Got: {actual_reward}\n"
                    f"Please check database connection."
                )
        else:
            await update.message.reply_text("❌ Failed to update referral reward. Please try again.")
            logger.error(f"❌ Admin {user_id} failed to update referral reward to {new_reward}")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
    except Exception as e:
        logger.error(f"Error setting referral reward: {e}")
        await update.message.reply_text("❌ Error occurred while updating referral reward.")

async def set_message_rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set message earning rate"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** `/setrate <messages>`\n\n"
            "**ဥပမာ:** `/setrate 3` (3 messages = 1 kyat)\n\n"
            "**လက်ရှိ Message Rate ကြည့်ရန်:** `/viewsettings`"
        )
        return
    
    try:
        new_rate = int(context.args[0])
        
        if new_rate < 1:
            await update.message.reply_text("❌ Message rate must be at least 1.")
            return
        
        if new_rate > 100:
            await update.message.reply_text("❌ Message rate cannot be more than 100.")
            return
            
        success = await db.update_settings({"message_rate": new_rate})
        
        if success:
            # Verify the update
            current_settings = await db.get_settings()
            actual_rate = current_settings.get("message_rate", 0)
            
            if actual_rate == new_rate:
                await update.message.reply_text(
                    f"✅ **Message Earning Rate Updated Successfully**\n\n"
                    f"💬 **New Rate:** {new_rate} messages = 1 {CURRENCY}\n"
                    f"👨‍💼 **Updated by:** Admin {user_id}\n"
                    f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"💡 **Note:** Users now earn 1 {CURRENCY} for every {new_rate} messages."
                )
                logger.info(f"Admin {user_id} updated message rate to {new_rate}")
            else:
                await update.message.reply_text(f"⚠️ Update verification failed: Expected {new_rate}, got {actual_rate}")
        else:
            await update.message.reply_text("❌ Failed to update message rate. Please try again.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid rate. Please enter a valid number between 1-100.")
    except Exception as e:
        logger.error(f"Error setting message rate: {e}")
        await update.message.reply_text("❌ Error occurred while updating message rate.")

async def view_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View current bot settings"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        settings = await db.get_settings()
        channels = await db.get_mandatory_channels()
        stats = await db.get_user_stats_summary()
        
        referral_reward = settings.get('referral_reward', 50)
        message_rate = settings.get('message_rate', 3)
        last_order_id = settings.get('last_order_id', 0)
        
        settings_text = (
            f"⚙️ **BOT CONFIGURATION SETTINGS**\n\n"
            f"💰 **Financial Settings:**\n"
            f"• Referral Reward: {referral_reward} {CURRENCY} per referral\n"
            f"• Message Rate: {message_rate} messages = 1 {CURRENCY}\n"
            f"• Last Order ID: {last_order_id}\n\n"
            f"📺 **Force Join Settings:**\n"
            f"• Mandatory Channels: {len(channels)} channels\n"
            f"• Required Referrals: 10 for withdrawal\n"
            f"• Minimum Messages: 50 for withdrawal\n\n"
            f"📊 **Current Statistics:**\n"
            f"• Total Users: {stats.get('total_users', 0):,}\n"
            f"• Active Users: {stats.get('active_users', 0):,}\n"
            f"• Total Earnings: {int(stats.get('total_earnings', 0)):,} {CURRENCY}\n"
            f"• System Balance: {int(stats.get('system_balance', 0)):,} {CURRENCY}\n\n"
            f"📅 **Last Checked:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**Management Commands:**\n"
            f"• `/setreferral <amount>` - Change referral reward\n"
            f"• `/setrate <messages>` - Change message earning rate\n"
            f"• `/addchannel <id> <name>` - Add mandatory channel\n"
            f"• `/removechannel <id>` - Remove channel\n"
            f"• `/systemstats` - Detailed system statistics"
        )
        
        await update.message.reply_text(settings_text)
        
    except Exception as e:
        logger.error(f"Error viewing settings: {e}")
        await update.message.reply_text("❌ Error loading bot settings.")

async def system_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View detailed system statistics"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        # Get comprehensive stats
        total_users = await db.get_total_users_count()
        total_earnings = await db.get_total_earnings()
        total_withdrawals = await db.get_total_withdrawals()
        channels = await db.get_mandatory_channels()
        settings = await db.get_settings()
        
        # Get more detailed stats
        stats = await db.get_user_stats_summary()
        withdrawal_stats = await db.get_withdrawal_stats()
        
        # Calculate additional metrics
        system_balance = int(total_earnings - total_withdrawals)
        avg_earnings_per_user = int(total_earnings / max(total_users, 1))
        avg_messages_per_user = int(stats.get('total_messages', 0) / max(stats.get('active_users', 1), 1))
        withdrawal_rate = (withdrawal_stats.get('total_withdrawers', 0) / max(total_users, 1)) * 100
        
        stats_text = (
            f"📊 **COMPREHENSIVE SYSTEM STATISTICS**\n\n"
            f"👥 **USER ANALYTICS:**\n"
            f"• Total Registered: {total_users:,} users\n"
            f"• Active Users: {stats.get('active_users', 0):,} ({(stats.get('active_users', 0)/max(total_users, 1)*100):.1f}%)\n"
            f"• Banned Users: {stats.get('banned_users', 0):,}\n"
            f"• Withdrawal Rate: {withdrawal_rate:.1f}% of users withdrew\n\n"
            f"💰 **FINANCIAL OVERVIEW:**\n"
            f"• Total Distributed: {int(total_earnings):,} {CURRENCY}\n"
            f"• Total Withdrawn: {int(total_withdrawals):,} {CURRENCY}\n"
            f"• System Balance: {system_balance:,} {CURRENCY}\n"
            f"• Active Withdrawers: {withdrawal_stats.get('total_withdrawers', 0):,} users\n"
            f"• Average Withdrawal: {int(withdrawal_stats.get('avg_withdrawal', 0)):,} {CURRENCY}\n"
            f"• Max Single Withdrawal: {int(withdrawal_stats.get('max_withdrawal', 0)):,} {CURRENCY}\n\n"
            f"📈 **ENGAGEMENT METRICS:**\n"
            f"• Total Messages: {stats.get('total_messages', 0):,}\n"
            f"• Average Messages/User: {avg_messages_per_user:,}\n"
            f"• Average Earnings/User: {avg_earnings_per_user:,} {CURRENCY}\n"
            f"• Message-to-Earning Ratio: {stats.get('total_messages', 0) // max(int(total_earnings), 1)}:1\n\n"
            f"⚙️ **SYSTEM CONFIGURATION:**\n"
            f"• Referral Reward: {settings.get('referral_reward', 50)} {CURRENCY}/referral\n"
            f"• Message Rate: {settings.get('message_rate', 3)} messages = 1 {CURRENCY}\n"
            f"• Mandatory Channels: {len(channels)} active\n"
            f"• Total Orders Processed: {settings.get('last_order_id', 0):,}\n\n"
            f"📱 **INFRASTRUCTURE:**\n"
            f"• Approved Groups: {len(APPROVED_GROUPS)} groups\n"
            f"• Admin Users: {len(ADMIN_IDS)} admins\n"
            f"• Database Status: ✅ Connected\n"
            f"• Anti-Spam: ✅ Active\n\n"
            f"⏰ **Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error in system stats: {e}")
        await update.message.reply_text("❌ Error loading system statistics.")

async def update_user_names_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to update user names from Telegram API"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        await update.message.reply_text("🔄 **Updating user names from Telegram API...**\n\nThis may take a few seconds...")
        
        # Update user names
        updated_count = await db.bulk_update_user_names(context)
        
        await update.message.reply_text(
            f"✅ **User Names Update Complete**\n\n"
            f"📊 **Successfully Updated:** {updated_count} users\n"
            f"👨‍💼 **Initiated by:** Admin {user_id}\n"
            f"⏰ **Completed at:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"🔄 **Check leaderboard now - should show real names!**\n"
            f"💡 **Tip:** Run `/systemstats` to see overall improvements."
        )
        
        logger.info(f"Admin {user_id} updated {updated_count} user names")
        
    except Exception as e:
        logger.error(f"Error in update user names command: {e}")
        await update.message.reply_text("❌ Error updating user names. Please try again later.")

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to ban a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/ban <user_id> [အကြောင်းရင်း]`\n\n"
            f"**ဥပမာ:** `/ban 123456789 Spamming messages`\n\n"
            f"**Note:** User ID ကို forward လုပ်ထားသော message မှ ရယူနိုင်ပါသည်။"
        )
        return
    
    try:
        target_user_id = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Admin မှ ပိတ်ပင်ခြင်း - No reason specified"
        
        # Check if trying to ban another admin
        if target_user_id in ADMIN_IDS:
            await update.message.reply_text("❌ Cannot ban another admin user.")
            return
        
        # Ban user in database
        success = await db.ban_user(target_user_id, reason)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "Unknown User"
                username = f"@{user_info.username}" if user_info.username else "No username"
            except:
                user_name = "Unknown User"
                username = "Unknown"
            
            await update.message.reply_text(
                f"✅ **USER BANNED SUCCESSFULLY**\n\n"
                f"👤 **User:** {user_name} ({username})\n"
                f"🆔 **User ID:** {target_user_id}\n"
                f"📝 **Reason:** {reason}\n"
                f"👨‍💼 **Banned by:** Admin {user_id}\n"
                f"📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🚫 **User can no longer:**\n"
                f"• Earn money from messages\n"
                f"• Use withdrawal functions\n"
                f"• Participate in referral system"
            )
            
            logger.info(f"Admin {user_id} banned user {target_user_id}: {reason}")
        else:
            await update.message.reply_text("❌ Failed to ban user. User may not exist or already banned.")
    
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
                user_name = user_info.first_name or "Unknown User"
                username = f"@{user_info.username}" if user_info.username else "No username"
            except:
                user_name = "Unknown User"
                username = "Unknown"
            
            await update.message.reply_text(
                f"✅ **USER UNBANNED SUCCESSFULLY**\n\n"
                f"👤 **User:** {user_name} ({username})\n"
                f"🆔 **User ID:** {target_user_id}\n"
                f"👨‍💼 **Unbanned by:** Admin {user_id}\n"
                f"📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"✅ **User can now:**\n"
                f"• Earn money from messages\n"
                f"• Use withdrawal functions\n"
                f"• Participate in referral system"
            )
            
            logger.info(f"Admin {user_id} unbanned user {target_user_id}")
        else:
            await update.message.reply_text("❌ Failed to unban user. User may not exist or not banned.")
    
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
        
        # Check database connection
        db_status = "🟢 Connected" if db.connected else "🔴 Disconnected"
        
        uptime_str = "Running"
        
        status_text = (
            f"🤖 **SYSTEM STATUS OVERVIEW**\n\n"
            f"📊 **Core Metrics:**\n"
            f"• Total Users: {total_users:,}\n"
            f"• Total Earnings: {int(total_earnings):,} {CURRENCY}\n"
            f"• Total Withdrawals: {int(total_withdrawals):,} {CURRENCY}\n"
            f"• System Balance: {int(total_earnings - total_withdrawals):,} {CURRENCY}\n\n"
            f"🔧 **System Components:**\n"
            f"• Database: {db_status}\n"
            f"• Mandatory Channels: {len(channels)} active\n"
            f"• Approved Groups: {len(APPROVED_GROUPS)} groups\n"
            f"• Admin Users: {len(ADMIN_IDS)} admins\n\n"
            f"🛡️ **Security Status:**\n"
            f"• Anti-spam System: 🟢 Active\n"
            f"• Force Join: 🟢 {'Active' if channels else 'No channels'}\n"
            f"• Withdrawal Control: 🟢 Active\n\n"
            f"⏱️ **Uptime:** {uptime_str}\n"
            f"📅 **Status Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"✅ **All systems operational**"
        )
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in system status: {e}")
        await update.message.reply_text("❌ Error checking system status.")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all users - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/broadcast <မက်ဆေ့ချ်>`\n\n"
            f"**ဥပမာ:** `/broadcast သုံးစွဲသူအားလုံးအတွက် အရေးကြီးသောအချက်အလက်!`\n\n"
            f"**Note:** Message will be sent to all registered users."
        )
        return
    
    try:
        message = " ".join(context.args)
        
        # Get all users
        users = await db.get_all_users()
        active_users = [user for user in users if not user.get('banned', False)]
        
        sent_count = 0
        failed_count = 0
        
        status_msg = await update.message.reply_text(f"📡 **Broadcasting to {len(active_users)} active users...**")
        
        for i, user in enumerate(active_users):
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **OFFICIAL ANNOUNCEMENT**\n\n{message}\n\n━━━━━━━━━━━━━\n🤖 **Admin Team**\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                sent_count += 1
                
                # Update progress every 50 users
                if (i + 1) % 50 == 0:
                    try:
                        await status_msg.edit_text(f"📡 **Broadcasting... {i + 1}/{len(active_users)} users processed**")
                    except:
                        pass
                    
                # Small delay to avoid rate limiting
                if sent_count % 20 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                failed_count += 1
                if "bot was blocked" not in str(e).lower():
                    logger.warning(f"Failed to send broadcast to {user['user_id']}: {e}")
        
        # Final status report
        success_rate = (sent_count / max(len(active_users), 1)) * 100
        
        await status_msg.edit_text(
            f"✅ **BROADCAST COMPLETED**\n\n"
            f"📤 **Successfully sent:** {sent_count} users\n"
            f"❌ **Failed to send:** {failed_count} users\n"
            f"📊 **Success Rate:** {success_rate:.1f}%\n"
            f"👨‍💼 **Broadcast by:** Admin {user_id}\n"
            f"📅 **Completed at:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"💡 **Failed messages typically due to users blocking the bot.**"
        )
        
        logger.info(f"Admin {user_id} broadcasted to {sent_count}/{len(active_users)} users")
    
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ Error occurred during broadcast.")

async def test_forward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test auto-forward system"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        test_message = (
            f"🧪 **AUTO-FORWARD SYSTEM TEST**\n\n"
            f"⏰ **Test Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🤖 **Test initiated by:** Admin {user_id}\n\n"
            f"✅ **If you see this message, auto-forward is working!**"
        )
        
        forwarded_count = 0
        failed_count = 0
        
        # Forward to all approved groups
        for group_id in APPROVED_GROUPS:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=test_message
                )
                forwarded_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to forward test to group {group_id}: {e}")
        
        await update.message.reply_text(
            f"🧪 **AUTO-FORWARD TEST RESULTS**\n\n"
            f"✅ **Successfully forwarded:** {forwarded_count} groups\n"
            f"❌ **Failed to forward:** {failed_count} groups\n"
            f"📊 **Total groups:** {len(APPROVED_GROUPS)}\n\n"
            f"💡 **Check the groups to verify message delivery.**"
        )
        
    except Exception as e:
        logger.error(f"Error in test forward: {e}")
        await update.message.reply_text("❌ Error during forward test.")

async def test_announce_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test announcement system"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        # Try to import announcement groups, fallback to approved groups
        try:
            from config import GENERAL_ANNOUNCEMENT_GROUPS
            announcement_groups = GENERAL_ANNOUNCEMENT_GROUPS
        except ImportError:
            announcement_groups = APPROVED_GROUPS
            logger.info("Using APPROVED_GROUPS as announcement groups (GENERAL_ANNOUNCEMENT_GROUPS not configured)")
        
        test_announcement = (
            f"📣 **SYSTEM ANNOUNCEMENT TEST**\n\n"
            f"🎯 **This is a test announcement**\n"
            f"⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}\n"
            f"🔧 **Test by:** Admin {user_id}\n\n"
            f"✅ **Announcement system is working properly!**"
        )
        
        announced_count = 0
        failed_count = 0
        
        # Send to announcement groups
        for group_id in announcement_groups:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=test_announcement
                )
                announced_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to announce test to group {group_id}: {e}")
        
        await update.message.reply_text(
            f"📣 **ANNOUNCEMENT TEST RESULTS**\n\n"
            f"✅ **Successfully announced:** {announced_count} groups\n"
            f"❌ **Failed to announce:** {failed_count} groups\n"
            f"📊 **Total announcement groups:** {len(announcement_groups)}\n\n"
            f"💡 **Check announcement groups for message delivery.**"
        )
        
    except Exception as e:
        logger.error(f"Error in test announce: {e}")
        await update.message.reply_text("❌ Error during announcement test.")

async def handle_forward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward a message to all approved groups"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    # Check if replying to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ **အသုံးပြုပုံ:** Reply to a message with `/forward`\n\n"
            "**လမ်းညွှန်:**\n"
            "1. Forward လုပ်ရန် message ကို reply လုပ်ပါ\n"
            "2. `/forward` command ရိုက်ပါ\n"
            "3. Message သည် approved groups အားလုံးသို့ ပို့သွားပါမည်"
        )
        return
    
    try:
        forwarded_count = 0
        failed_count = 0
        
        status_msg = await update.message.reply_text("📤 **Forwarding message to all groups...**")
        
        # Forward to all approved groups
        for group_id in APPROVED_GROUPS:
            try:
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.reply_to_message.message_id
                )
                forwarded_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to forward to group {group_id}: {e}")
        
        await status_msg.edit_text(
            f"📤 **FORWARD COMPLETED**\n\n"
            f"✅ **Successfully forwarded:** {forwarded_count} groups\n"
            f"❌ **Failed to forward:** {failed_count} groups\n"
            f"📊 **Total groups:** {len(APPROVED_GROUPS)}\n"
            f"👨‍💼 **Forwarded by:** Admin {user_id}\n"
            f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}"
        )
        
        logger.info(f"Admin {user_id} forwarded message to {forwarded_count} groups")
        
    except Exception as e:
        logger.error(f"Error in forward command: {e}")
        await update.message.reply_text("❌ Error occurred during forwarding.")

async def debug_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Debug user information - FIXED"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/debuguser <user_id>`\n\n**Example:** `/debuguser 123456789`")
        return
    
    try:
        target_user_id = context.args[0]
        user = await db.get_user(target_user_id)
        
        if not user:
            await update.message.reply_text(f"❌ **User {target_user_id} not found in database**")
            return
        
        debug_text = f"🔍 **USER DEBUG INFORMATION**\n\n"
        debug_text += f"🆔 **User ID:** {user.get('user_id', 'Unknown')}\n"
        debug_text += f"👤 **Name:** {user.get('first_name', '')} {user.get('last_name', '')}\n"
        debug_text += f"📧 **Username:** @{user.get('username', 'None')}\n"
        debug_text += f"💰 **Balance:** {user.get('balance', 0)} {CURRENCY}\n"
        debug_text += f"📈 **Total Earnings:** {user.get('total_earnings', 0)} {CURRENCY}\n"
        debug_text += f"💸 **Total Withdrawn:** {user.get('total_withdrawn', 0)} {CURRENCY}\n"
        debug_text += f"👥 **Referred By:** {user.get('referred_by', 'None')}\n"
        debug_text += f"✅ **Successful Referrals:** {user.get('successful_referrals', 0)}\n"
        debug_text += f"📺 **Channels Joined:** {user.get('referral_channels_joined', False)}\n"
        debug_text += f"🎁 **Referral Reward Given:** {user.get('referral_reward_given', False)}\n"
        debug_text += f"💬 **Messages:** {user.get('messages', 0)}\n"
        debug_text += f"📊 **Message Count:** {user.get('message_count', 0)}\n"
        debug_text += f"🚫 **Banned:** {user.get('banned', False)}\n"
        debug_text += f"📅 **Created:** {str(user.get('created_at', 'Unknown'))[:10]}\n"
        debug_text += f"⏰ **Last Activity:** {str(user.get('last_activity', 'Unknown'))[:10]}"
        
        await update.message.reply_text(debug_text)
        
        logger.info(f"Admin {user_id} debugged user {target_user_id}")
        
    except Exception as e:
        logger.error(f"Error in debug user: {e}")
        await update.message.reply_text("❌ Debug error occurred")

async def reset_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user for testing - DANGEROUS COMMAND"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/resetuser <user_id>`\n\n**⚠️ WARNING:** This will DELETE the user completely!")
        return
    
    try:
        target_user_id = context.args[0]
        
        # Extra safety check
        if target_user_id in ADMIN_IDS:
            await update.message.reply_text("❌ **SECURITY ERROR:** Cannot reset admin user!")
            return
        
        result = await db.users.delete_one({"user_id": target_user_id})
        
        if result.deleted_count > 0:
            await update.message.reply_text(
                f"✅ **USER RESET SUCCESSFUL**\n\n"
                f"🆔 **User ID:** {target_user_id}\n"
                f"🗑️ **Status:** Completely deleted from database\n"
                f"👨‍💼 **Reset by:** Admin {user_id}\n"
                f"📅 **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"💡 **User can now rejoin with /start for fresh account**"
            )
            logger.warning(f"Admin {user_id} RESET (deleted) user {target_user_id}")
        else:
            await update.message.reply_text(f"❌ **User {target_user_id} not found or already deleted**")
            
    except Exception as e:
        logger.error(f"Error in reset user: {e}")
        await update.message.reply_text(f"❌ **Error:** {e}")

def register_handlers(application: Application):
    """Register admin command handlers - COMPLETE WITH ALL COMMANDS"""
    logger.info("Registering comprehensive admin handlers with all commands")
    
    # Channel management commands
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("listchannels", list_channels))
    application.add_handler(CommandHandler("channels", list_channels))
    
    # User management commands
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    
    # System configuration commands
    application.add_handler(CommandHandler("setreferral", set_referral_reward_command))
    application.add_handler(CommandHandler("setrate", set_message_rate_command))
    application.add_handler(CommandHandler("viewsettings", view_settings_command))
    application.add_handler(CommandHandler("systemstats", system_stats_command))
    
    # System monitoring commands
    application.add_handler(CommandHandler("systemstatus", system_status))
    application.add_handler(CommandHandler("updatenames", update_user_names_command))
    
    # Communication commands
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("forward", handle_forward_command))
    
    # Testing commands
    application.add_handler(CommandHandler("testforward", test_forward_command))
    application.add_handler(CommandHandler("testannounce", test_announce_command))
    
    # Debug and development commands
    application.add_handler(CommandHandler("debuguser", debug_user_command))
    application.add_handler(CommandHandler("resetuser", reset_user_command))
    
    logger.info("✅ All admin handlers registered successfully")
    logger.info("Available admin commands:")
    logger.info("  Channel: /addchannel, /removechannel, /listchannels")
    logger.info("  Users: /ban, /unban, /debuguser, /resetuser")
    logger.info("  Config: /setreferral, /setrate, /viewsettings")
    logger.info("  Stats: /systemstats, /systemstatus, /updatenames")
    logger.info("  Communication: /broadcast, /forward")
    logger.info("  Testing: /testforward, /testannounce")
