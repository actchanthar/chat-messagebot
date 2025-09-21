from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY, RECEIPT_CHANNEL_ID, GENERAL_ANNOUNCEMENT_GROUPS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_referral_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set referral reward amount"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/setreferral <amount>`\n\n"
            f"**Example:**\n"
            f"`/setreferral 50`"
        )
        return
    
    try:
        amount = int(context.args[0])
        if amount < 0:
            await update.message.reply_text("❌ Amount must be positive")
            return
        
        # Update in database
        success = await db.update_settings({"referral_reward": amount})
        
        if success:
            await update.message.reply_text(
                f"✅ **Referral reward updated**\n\n"
                f"💰 **New reward:** {amount} {CURRENCY} per referral\n"
                f"👨‍💼 **Updated by:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} set referral reward to {amount} {CURRENCY}")
        else:
            await update.message.reply_text("❌ Failed to update setting")
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")

async def set_message_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set message earning rate"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/setrate <messages_per_kyat>`\n\n"
            f"**Example:**\n"
            f"`/setrate 3` (3 messages = 1 kyat)\n"
            f"`/setrate 1` (1 message = 1 kyat)"
        )
        return
    
    try:
        rate = int(context.args[0])
        if rate < 1:
            await update.message.reply_text("❌ Rate must be at least 1")
            return
        
        # Update in database
        success = await db.update_settings({"message_rate": rate})
        
        if success:
            await update.message.reply_text(
                f"✅ **Message earning rate updated**\n\n"
                f"📊 **New rate:** {rate} messages = 1 {CURRENCY}\n"
                f"👨‍💼 **Updated by:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} set message rate to {rate} messages per {CURRENCY}")
        else:
            await update.message.reply_text("❌ Failed to update setting")
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")

async def view_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view current bot settings"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Get current settings
        referral_reward = await db.get_referral_reward()
        message_rate = await db.get_message_rate()
        
        settings_text = (
            f"⚙️ **BOT SETTINGS**\n\n"
            f"💰 **Referral Reward:** {referral_reward} {CURRENCY} per referral\n"
            f"📊 **Message Rate:** {message_rate} messages = 1 {CURRENCY}\n\n"
            f"📋 **Current Configuration:**\n"
            f"• Receipt Channel: {RECEIPT_CHANNEL_ID}\n"
            f"• Announcement Groups: {len(GENERAL_ANNOUNCEMENT_GROUPS)} groups\n\n"
            f"🔧 **Admin Commands:**\n"
            f"• `/setreferral <amount>` - Set referral reward\n"
            f"• `/setrate <messages>` - Set earning rate\n"
            f"• `/viewsettings` - View current settings\n"
            f"• `/testforward` - Test auto-forward system\n"
            f"• `/testannounce` - Test announcement system"
        )
        
        await update.message.reply_text(settings_text)
        
    except Exception as e:
        logger.error(f"Error viewing settings: {e}")
        await update.message.reply_text("❌ Error retrieving settings")

async def test_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to test forwarding system"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Send test message to receipt channel
        test_msg = await context.bot.send_message(
            chat_id=RECEIPT_CHANNEL_ID,
            text="""💸 **WITHDRAWAL SUCCESSFUL!**

🎉 **Test User just received 1,000 kyat!**
💳 **Method:** KBZ Pay
📅 **Date:** 2025-09-21 16:50

✅ **PROOF OUR BOT PAYS REAL MONEY!**

💰 **Start earning too:**
• Chat in groups = Earn kyat
• Minimum withdrawal: 200 kyat
• Fast processing: 2-24 hours

🚀 **Join now:** t.me/ACTearnbot

#Withdrawal #Success #RealPayments"""
        )
        
        # Forward to groups
        import asyncio
        forwarded = 0
        
        for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
            try:
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=RECEIPT_CHANNEL_ID,
                    message_id=test_msg.message_id
                )
                forwarded += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Test forward failed to {group_id}: {e}")
        
        await update.message.reply_text(
            f"✅ **Test completed!**\n\n"
            f"📤 **Sent to receipt channel:** {RECEIPT_CHANNEL_ID}\n"
            f"📋 **Forwarded to:** {forwarded} groups\n\n"
            f"Check your channels and groups!"
        )
        
    except Exception as e:
        logger.error(f"Test forward error: {e}")
        await update.message.reply_text(f"❌ Test failed: {e}")

async def test_announce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to test announcement system"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Test announcement system
        from plugins.announcements import announcement_system
        await announcement_system.test_announcements(context)
        
        await update.message.reply_text(
            f"✅ **Announcement test sent!**\n\n"
            f"Check your channels and groups for test messages."
        )
        
    except Exception as e:
        logger.error(f"Test announce error: {e}")
        await update.message.reply_text(f"❌ Test failed: {e}")

async def manual_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to manually forward a message"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Check if replying to a message
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ **Invalid Usage**\n\n"
                "Reply to a message you want to forward to groups.\n"
                "**Example:** Reply to a withdrawal post with `/forward`"
            )
            return
        
        replied_message = update.message.reply_to_message
        
        # Forward to all main groups
        import asyncio
        forwarded_count = 0
        
        for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
            try:
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=replied_message.message_id
                )
                
                forwarded_count += 1
                logger.info(f"✅ Manual forward to group {group_id}")
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Failed manual forward to {group_id}: {e}")
        
        await update.message.reply_text(
            f"✅ **Message Forwarded**\n\n"
            f"Successfully forwarded to {forwarded_count} groups!"
        )
        
    except Exception as e:
        logger.error(f"Error in manual forward: {e}")
        await update.message.reply_text("❌ Error occurred while forwarding.")

async def system_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view system statistics"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Get system stats
        total_users = await db.get_total_users_count()
        total_earnings = await db.get_total_earnings()
        total_withdrawals = await db.get_total_withdrawals()
        
        stats_text = (
            f"📊 **SYSTEM STATISTICS**\n\n"
            f"👥 **Total Users:** {total_users:,}\n"
            f"💰 **Total Earnings:** {int(total_earnings):,} {CURRENCY}\n"
            f"💸 **Total Withdrawals:** {int(total_withdrawals):,} {CURRENCY}\n"
            f"💳 **System Balance:** {int(total_earnings - total_withdrawals):,} {CURRENCY}\n\n"
            f"⚙️ **Current Settings:**\n"
            f"• Referral Reward: {await db.get_referral_reward()} {CURRENCY}\n"
            f"• Message Rate: {await db.get_message_rate()} messages = 1 {CURRENCY}\n\n"
            f"📈 **Performance:**\n"
            f"• Average per user: {int(total_earnings/max(total_users, 1))} {CURRENCY}\n"
            f"• Withdrawal rate: {int((total_withdrawals/max(total_earnings, 1))*100)}%"
        )
        
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        await update.message.reply_text("❌ Error retrieving statistics")

def register_handlers(application: Application):
    """Register settings command handlers"""
    logger.info("Registering settings commands")
    
    # Settings commands
    application.add_handler(CommandHandler("setreferral", set_referral_reward))
    application.add_handler(CommandHandler("setrate", set_message_rate))
    application.add_handler(CommandHandler("viewsettings", view_settings))
    
    # Testing commands
    application.add_handler(CommandHandler("testforward", test_forward))
    application.add_handler(CommandHandler("testannounce", test_announce))
    
    # Manual control commands
    application.add_handler(CommandHandler("forward", manual_forward))
    application.add_handler(CommandHandler("systemstats", system_stats))
    
    logger.info("✅ Settings commands registered successfully")
